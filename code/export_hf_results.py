#!/usr/bin/env python3
"""Export full-track reference-runner results for a Hugging Face leaderboard."""

import argparse
from collections import Counter
from datetime import date
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit

import requests
import yaml

from omnicompass_public_adapter import evaluate_public_predictions
from release_tools import rows, sha
from run_eval import digest, load_predictions


DATASET = "VCLab-PolyU/OmniCompass"
TASKS = ("TG", "SG", "QA")
SETTINGS = ("text", "text_image")
PROTOCOL_FILES = (
    "run_eval.py", "extract_frames.py", "extract_audio.py", "omnicompass_public_adapter.py",
    "omnicompass_frame_prompt.py", "omnicompass_av_frame_prompt.py",
    "omnicompass_release.py", "omnicompass_scoring.py",
    "print_frame_eval_results.py", "print_modality_gain_results.py",
)


def checked_url(value: str) -> str:
    """Require a public HTTPS evidence link without embedded credentials."""
    url = urlsplit(value)
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or url.query or any(c.isspace() for c in value)
            or url.hostname in {"localhost", "127.0.0.1", "::1"}):
        raise ValueError("Use a public HTTPS source URL without credentials or query parameters")
    return value


def hub_manifest(revision: str) -> dict:
    """Read only the official release manifest, never media or model weights."""
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("--dataset-revision must be a full commit hash, not main")
    response = requests.get(
        f"https://huggingface.co/datasets/{DATASET}/resolve/{revision}/release.json",
        timeout=(10, 60),
    )
    response.raise_for_status()
    return response.json()


def load_track(data: Path, revision: str, track: str) -> tuple[list, list, dict]:
    """Bind the local annotations and media manifest to an official Hub revision."""
    release = hub_manifest(revision)
    for name in ("questions.jsonl", "videos.jsonl", "media_manifest.jsonl"):
        if sha(data / name) != release["files"][name]:
            raise ValueError(f"Local {name} differs from the official dataset revision")
    questions = [q for q in rows(data / "questions.jsonl") if q["track"] == track]
    count = 820 if track == "VL" else 240
    if (Counter(q["task"] for q in questions) != Counter(dict.fromkeys(TASKS, count))
            or len({q["question_id"] for q in questions}) != 3 * count
            or len({q["video_id"] for q in questions}) != count):
        raise ValueError("Expected the complete frozen track, not a subset")
    ids = {q["video_id"] for q in questions}
    videos = [v for v in rows(data / "videos.jsonl") if v["video_id"] in ids]
    media = {r["public_path"]: r for r in rows(data / "media_manifest.jsonl")}
    return questions, videos, media


def validate_run(config: dict, receipts: dict, questions: list,
                 videos: list, media: dict) -> None:
    """Reject incomplete selections, modality ablations, and changed protocols."""
    track = config["track"]
    if (sorted(config["tasks"]) != sorted(TASKS)
            or sorted(config["settings"]) != sorted(SETTINGS)
            or config["video_ids"] != sorted(v["video_id"] for v in videos)
            or config["questions_sha256"] != digest(questions)
            or config["videos_sha256"] != digest(videos)):
        raise ValueError("Run must cover the full track, all three tasks and both specifications")
    if config["audio"]["enabled"] is not (track == "AV"):
        raise ValueError("Leaderboard requires VL without audio and AV with complete audio")
    nframe, fps = config.get("nframe"), config.get("fps")
    if (nframe is None) == (fps is None):
        raise ValueError("Exactly one sampling mode is required")
    if nframe is not None and (type(nframe) is not int or nframe <= 0):
        raise ValueError("Invalid frame count")
    if fps is not None and (type(fps) not in (int, float) or not math.isfinite(fps) or fps <= 0):
        raise ValueError("Invalid FPS")
    if type(config.get("max_completion_tokens")) is not int or config["max_completion_tokens"] <= 0:
        raise ValueError("Invalid output budget")
    for name in PROTOCOL_FILES:
        if config.get("code_sha256", {}).get(name) != sha(Path(__file__).parent / name):
            raise ValueError(f"Run used a different protocol file: {name}")
    if set(receipts) != {v["video_id"] for v in videos} | {"references"}:
        raise ValueError("Missing or unexpected input receipts")
    for video in videos:
        receipt = receipts[video["video_id"]]
        if receipt.get("source_sha256") != media[video["video_path"]]["sha256"]:
            raise ValueError(f"Source video receipt mismatch: {video['video_id']}")
        for field in ("sampling_sha256",) + (
            ("audio_sha256", "audio_manifest_sha256") if track == "AV" else ()
        ):
            if not re.fullmatch(r"[0-9a-f]{64}", receipt.get(field, "")):
                raise ValueError(f"Invalid {field} receipt: {video['video_id']}")
    expected = {q["question_id"]: media[q["reference_image"]]["sha256"] for q in questions}
    if receipts["references"] != expected:
        raise ValueError("Reference image receipts differ from the release")


def build_entry(data: Path, run_dir: Path, revision: str, model_repo: str,
                model_revision: str, evaluated_on: str, source_url: str) -> dict:
    """Recompute official scores and return one HF result; this is not verification."""
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", model_repo):
        raise ValueError("--model-repo must be an owner/model Hub repository ID")
    if not model_revision.strip() or any(c in model_revision for c in "\r\n"):
        raise ValueError("Provide a model revision or explicit provider version")
    if date.fromisoformat(evaluated_on) > date.today():
        raise ValueError("Evaluation date cannot be in the future")
    checked_url(source_url)
    config = json.loads((run_dir / "run_config.json").read_text())
    track = config["track"]
    if track not in {"VL", "AV"}:
        raise ValueError("Unknown track")
    questions, videos, media = load_track(data, revision, track)
    validate_run(config, json.loads((run_dir / "input_receipts.json").read_text()),
                 questions, videos, media)
    expected = {(q["question_id"], s) for q in questions for s in SETTINGS}
    predictions = list(load_predictions(run_dir / "predictions.jsonl", expected).values())
    result = evaluate_public_predictions(questions, predictions)["tracks"][track]
    if not result["complete"]:
        raise ValueError("Transport failures remain; resume the evaluation before exporting")
    cs = result["paired_cs"]
    scores = [cs["tasks"][task]["value"] for task in TASKS]
    if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in scores):
        raise ValueError("All tasks must have finite CS scores and eligible pairs")
    overall = sum(scores) / 3
    if not math.isclose(overall, cs["overall"], abs_tol=1e-12):
        raise ValueError("Overall CS differs from the unweighted three-task mean")
    # Publish a small allowlist, never endpoint URLs, raw answers, or credentials.
    notes = {
        "metric": "Overall CS", "scale": "0-100",
        "model_repo": model_repo, "model_revision": model_revision,
        "requested_model": config["model"], "runner": "omnicompass",
        "nframe": config["nframe"], "fps": config["fps"],
        "max_side": config["max_side"], "jpeg_quality": config["jpeg_quality"],
        "output_budget": config["max_completion_tokens"],
        "thinking": config["thinking"]["mode"],
        "thinking_api": config["thinking"]["api"],
        "reasoning_effort": config["thinking"].get("reasoning_effort"),
        "audio": config["audio"]["enabled"], "expected_requests": len(expected),
        "policy_excluded_requests": len(result["policy_excluded_ids"]),
        "eligible_pairs": {t: cs["tasks"][t]["scored_pairs"] for t in TASKS},
        "task_cs": {t: round(100 * v, 6) for t, v in zip(TASKS, scores)},
        "predictions_sha256": sha(run_dir / "predictions.jsonl"),
        "run_config_sha256": sha(run_dir / "run_config.json"),
    }
    return {
        "dataset": {"id": DATASET, "task_id": f"OmniCompass-{track}",
                    "revision": revision},
        "value": round(100 * overall, 6), "date": evaluated_on,
        "source": {"url": source_url, "name": "Evaluation evidence"},
        "notes": json.dumps(notes, sort_keys=True),
    }


def write_yaml(path: Path, entry: dict) -> None:
    """Serialize the HF result schema; never overwrite a result."""
    text = yaml.safe_dump([entry], sort_keys=False, allow_unicode=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("data", "run-dir", "output"):
        parser.add_argument(f"--{flag}", type=Path, required=True)
    for flag in ("dataset-revision", "model-repo", "model-revision", "date", "source-url"):
        parser.add_argument(f"--{flag}", required=True)
    args = parser.parse_args()
    try:
        entry = build_entry(args.data, args.run_dir, args.dataset_revision, args.model_repo,
                            args.model_revision, args.date, args.source_url)
        write_yaml(args.output, entry)
    except (ValueError, KeyError, OSError, requests.RequestException) as error:
        parser.exit(1, f"Export refused: {error}\n")
    print(f"Exported {entry['dataset']['task_id']}: Overall CS = {entry['value']:.6f}")
    print("Review this file and the evidence before submitting it to the model repository.")
    print("No result was uploaded. This export does not grant HF verified status.")


if __name__ == "__main__":
    main()
