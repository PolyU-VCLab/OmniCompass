#!/usr/bin/env python3
"""Portable extraction, validation, prompt export, and scoring for OmniCompass."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def safe(root, name):
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts or str(relative) != name:
        raise ValueError(f"Unsafe path: {name}")
    path = root.joinpath(*relative.parts)
    if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
        raise ValueError(f"Unsafe destination: {name}")
    return path


def selected_videos(data, video_ids):
    videos = rows(data / "videos.jsonl")
    available = {v["video_id"] for v in videos}
    if len(available) != len(videos):
        raise ValueError("Duplicate video IDs")
    if video_ids and not set(video_ids) <= available:
        raise ValueError("Unknown video IDs")
    return [v for v in videos if not video_ids or v["video_id"] in video_ids]


def selected_questions(data, video_ids=None, track=None):
    videos = {v["video_id"] for v in selected_videos(data, video_ids)}
    questions = rows(data / "questions.jsonl")
    if len({q["question_id"] for q in questions}) != len(questions):
        raise ValueError("Duplicate question IDs")
    return [q for q in questions if q["video_id"] in videos and
            (track is None or q["track"] == track)]


def media_selection(data, video_ids):
    videos = selected_videos(data, video_ids)
    questions = selected_questions(data, video_ids)
    names = {v["video_path"] for v in videos}
    # Legacy releases may still declare separately published audio files.
    names.update(v["audio_path"] for v in videos if v.get("audio_path"))
    names.update(q["reference_image"] for q in questions)
    manifest = rows(data / "media_manifest.jsonl")
    lookup = {r["public_path"]: r for r in manifest}
    if len(lookup) != len(manifest) or not names <= set(lookup):
        raise ValueError("Media manifest does not cover the selected annotations")
    return {name: lookup[name] for name in sorted(names)}


def verify(data, video_ids):
    selected = media_selection(data, video_ids)
    total = 0
    for name, row in selected.items():
        path = safe(data, name)
        if not path.is_file() or path.stat().st_size != row["bytes"] or sha(path) != row["sha256"]:
            raise ValueError(f"Missing or changed media: {name}")
        total += row["bytes"]
    return {"verified_files": len(selected), "bytes": total,
            "selection": video_ids or "all", "check": "bytes_and_sha256_not_decode"}


def extract(data, out, video_ids):
    if out.exists():
        raise ValueError("Choose a new output directory; existing files are never overwritten")
    selected = media_selection(data, video_ids)
    all_media = {r["public_path"]: r for r in rows(data / "media_manifest.jsonl")}
    archives = json.loads((data / "archives.json").read_text())
    out.mkdir(parents=True)
    seen, written = set(), set()
    for info in archives:
        # The archive index stores contiguous public paths for each media kind.
        if not any(info["first_path"] <= name <= info["last_path"] for name in selected):
            continue
        source = safe(data, info["path"])
        if source.stat().st_size != info["bytes"] or sha(source) != info["sha256"]:
            raise ValueError(f"Archive checksum mismatch: {info['path']}")
        with tarfile.open(source, "r:") as archive:
            for member in archive:
                if not member.isfile() or member.name not in all_media or member.name in seen:
                    raise ValueError(f"Unexpected or duplicate archive member: {member.name}")
                seen.add(member.name)
                if member.name not in selected:
                    continue
                expected = selected[member.name]
                if member.size != expected["bytes"]:
                    raise ValueError(f"Member size mismatch: {member.name}")
                target = safe(out, member.name)
                target.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                with archive.extractfile(member) as src, target.open("xb") as dst:
                    for chunk in iter(lambda: src.read(8 * 1024 * 1024), b""):
                        digest.update(chunk)
                        dst.write(chunk)
                if digest.hexdigest() != expected["sha256"]:
                    raise ValueError(f"Extracted checksum mismatch: {member.name}")
                written.add(member.name)
    if written != set(selected):
        raise ValueError("Archives did not supply all selected media")
    for name in ("videos.jsonl", "questions.jsonl", "taxonomy.json", "schema.json",
                 "release.json", "archives.json", "media_manifest.jsonl", "MEDIA_SHA256SUMS",
                 "KNOWN_ISSUES.md", "README.md"):
        source = data / name
        if source.is_file():
            shutil.copyfile(source, out / name)
    return {"extracted_files": len(written), "selection": video_ids or "all"}


def prompts(data, out, video_ids, track, settings=("text", "text_image"), tasks=("TG", "SG", "QA"),
            audio_mode="auto"):
    from omnicompass_public_adapter import render_prompt, uses_audio

    videos = {v["video_id"]: v for v in selected_videos(data, video_ids)}
    questions = [q for q in selected_questions(data, video_ids, track) if q["task"] in tasks]
    count = 0
    with out.open("x") as handle:
        for question in questions:
            video = videos[question["video_id"]]
            for setting in settings:
                reference = question["reference_image"] if setting == "text_image" else None
                enabled = uses_audio(question["track"], audio_mode)
                if enabled and video.get("has_audio") is False:
                    raise ValueError(f"No audio in {video['video_id']}; choose videos with audio or --audio off")
                row = {
                    "question_id": question["question_id"], "setting": setting,
                    "video_id": video["video_id"], "track": question["track"],
                    "task": question["task"], "video_path": video["video_path"],
                    "audio_source": video["video_path"] if enabled else None,
                    "audio_enabled": enabled, "reference_image": reference,
                    "prompt": render_prompt(question, setting, video["duration_seconds"], use_audio=enabled),
                    "media_order": ["timestamped_video_frames"] +
                                  (["audio"] if enabled else []) +
                                  (["reference_image"] if reference else []) + ["prompt"],
                }
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                count += 1
    return {"requests": count, "model_calls": 0, "frames": "chosen_by_evaluation_config"}


def score(data, predictions, out, video_ids, track, settings=("text", "text_image"), tasks=("TG", "SG", "QA")):
    from omnicompass_public_adapter import evaluate_public_predictions

    questions = [q for q in selected_questions(data, video_ids, track) if q["task"] in tasks]
    if not questions:
        raise ValueError("Empty question selection")
    report = evaluate_public_predictions(questions, rows(predictions), settings)
    with out.open("x") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return {"questions": len(questions), "tracks": {
        key: {"complete": value["complete"], "paired_cs": value["paired_cs"]}
        for key, value in report["tracks"].items()}}


def validate(data):
    release = json.loads((data / "release.json").read_text())
    for name, expected in release["files"].items():
        if sha(safe(data, name)) != expected:
            raise ValueError(f"Annotation checksum mismatch: {name}")
    videos = selected_videos(data, None)
    questions = selected_questions(data)
    if len(videos) != 820 or len(questions) != 3180:
        raise ValueError("Unexpected frozen annotation counts")
    counts = Counter((q["track"], q["task"]) for q in questions)
    expected = {(track, task): 820 if track == "VL" else 240
                for track in ("VL", "AV") for task in ("TG", "SG", "QA")}
    if counts != expected:
        raise ValueError("Unexpected track/task counts")
    manifest = rows(data / "media_manifest.jsonl")
    version = release["schema_version"]
    if version not in {"1.0", "1.1"}:
        raise ValueError(f"Unsupported schema version: {version}")
    expected_media = 4000 if version == "1.1" else 4240
    kinds = Counter(row["kind"] for row in manifest)
    expected_kinds = {"video": 820, "reference_image": 3180}
    if version == "1.0":
        expected_kinds["audio"] = 240
    if (len(manifest) != expected_media or kinds != expected_kinds
            or len(media_selection(data, None)) != expected_media):
        raise ValueError("Unexpected media count or relationships")
    return {"videos": 820, "questions": 3180, "requests": 6360,
            "media": expected_media, "checks": "frozen_hashes_counts_relationships"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "extract", "verify", "prompts", "score"])
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--video-id", action="append")
    parser.add_argument("--track", choices=["VL", "AV"])
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--setting", choices=["text", "text_image", "both"], default="both")
    parser.add_argument("--tasks", default="TG,SG,QA")
    parser.add_argument("--audio", choices=["auto", "on", "off"], default="auto",
                        help="Prompt export only: audio from MP4, auto follows track defaults")
    args = parser.parse_args()
    settings = ("text", "text_image") if args.setting == "both" else (args.setting,)
    tasks = args.tasks.split(",")
    if not tasks or len(set(tasks)) != len(tasks) or not set(tasks) <= {"TG", "SG", "QA"}:
        parser.error("--tasks must be a comma-separated subset of TG,SG,QA")
    if args.command in {"extract", "prompts", "score"} and args.out is None:
        parser.error("--out is required")
    if args.command == "score" and args.predictions is None:
        parser.error("--predictions is required")
    if args.command == "validate":
        result = validate(args.data)
    elif args.command == "extract":
        result = extract(args.data, args.out, args.video_id)
    elif args.command == "verify":
        result = verify(args.data, args.video_id)
    elif args.command == "prompts":
        result = prompts(args.data, args.out, args.video_id, args.track, settings, tasks, args.audio)
    else:
        result = score(args.data, args.predictions, args.out, args.video_id, args.track, settings, tasks)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
