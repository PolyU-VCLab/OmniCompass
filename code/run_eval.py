#!/usr/bin/env python3
"""Run OmniCompass with an OpenAI-compatible HTTP endpoint."""

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from contextlib import contextmanager
import csv
import hashlib
import ipaddress
import json
import mimetypes
import os
from pathlib import Path
import re
import time
from urllib.parse import urlsplit

from extract_frames import extract_video
from extract_audio import extract_audio, PROTOCOL as AUDIO_PROTOCOL, ENCODING as AUDIO_ENCODING
from release_tools import rows, safe, selected_questions, selected_videos, sha
from omnicompass_public_adapter import evaluate_public_predictions, render_prompt, uses_audio
from omnicompass_release import format_number
from print_frame_eval_results import is_content_policy_error, is_terminal_policy_refusal


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def validate_api_base(base):
    host = urlsplit(base)
    try:
        local = ipaddress.ip_address(host.hostname or "").is_loopback
    except ValueError:
        local = host.hostname == "localhost"
    if (not host.hostname or host.username or host.password or host.query or host.fragment
            or any(char.isspace() for char in base)
            or not (host.scheme == "https" or (host.scheme == "http" and local))):
        raise ValueError("Use HTTPS for remote APIs; HTTP is allowed only on loopback addresses. "
                         "Do not embed credentials, queries or fragments in the API base.")
    _ = host.port
    return host


def write_json(path, value):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)


def image_item(path):
    mime = mimetypes.guess_type(path.name)[0]
    if mime not in {"image/jpeg", "image/png", "image/webp"}:
        raise ValueError(f"Unsupported image format: {path.suffix}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"type": "image_url", "image_url": {
        "url": f"data:{mime};base64,{encoded}", "detail": "high"}}


def build_content(data, video, question, setting, frames, audio_encoding, *,
                  audio_path=None, use_audio=None):
    directory, manifest = frames
    content = []
    for frame in manifest["frames"]:
        content.append({"type": "text", "text":
                        f"Timestamp: {format_number(frame['timestamp_sec'])} seconds."})
        content.append(image_item(safe(directory, frame["path"])))
    if use_audio is None:
        use_audio = uses_audio(question["track"])
    if use_audio:
        if audio_path is None:
            raise ValueError("Prepare the complete audio from the source MP4 before inference")
        audio = Path(audio_path)
        if audio.suffix.lower() != ".mp3":
            raise ValueError("The API adapter requires extracted MP3 audio")
        encoded = base64.b64encode(audio.read_bytes()).decode("ascii")
        if audio_encoding == "data-uri":
            encoded = "data:;base64," + encoded
        content.append({"type": "input_audio", "input_audio": {"data": encoded, "format": "mp3"}})
    if setting == "text_image":
        content.append(image_item(safe(data, question["reference_image"])))
    content.append({"type": "text", "text":
                    render_prompt(question, setting, video["duration_seconds"], use_audio=use_audio)})
    return content


def terminal(row):
    return row.get("error") is None or is_terminal_policy_refusal(row)


def load_predictions(path, expected):
    saved = {}
    if not path.exists():
        return saved
    # An interrupted final line is an explicit repair case, never silently lost.
    for row in rows(path):
        key = (row["question_id"], row["setting"])
        if key not in expected:
            raise ValueError(f"Unknown saved prediction: {key}")
        if key in saved and terminal(saved[key]):
            raise ValueError(f"Duplicate terminal prediction: {key}")
        saved[key] = row
    return saved


def redact(text, secret):
    text = str(text).replace(secret, "[REDACTED]") if secret else str(text)
    text = re.sub(r"data:[^\\s\"']*;base64,[A-Za-z0-9+/=]+", "[MEDIA]", text)
    text = re.sub(r"[A-Za-z0-9+/=]{160,}", "[ENCODED_DATA]", text)
    return text[:1600]


def send_request(args, secret, content, question, setting):
    import requests

    result = {"question_id": question["question_id"], "setting": setting,
              "requested_model": args.model, "raw_output": "", "error": None,
              "input_sha256": digest(content), "attempt_records": []}
    payload = {"model": args.model, "messages": [{"role": "user", "content": content}],
               "max_completion_tokens": args.max_completion_tokens, "temperature": 0}
    if args.reasoning_effort:
        payload["reasoning_effort"] = args.reasoning_effort
    started = time.monotonic()
    with requests.Session() as session:
        session.trust_env = False
        for attempt in range(args.retries + 1):
            status = None
            retryable = False
            try:
                response = session.post(args.api_base.rstrip("/") + "/chat/completions",
                                        headers={"Authorization": f"Bearer {secret}"},
                                        json=payload, timeout=(30, args.timeout))
                status = response.status_code
                if status != 200:
                    error = redact(response.text, secret)
                    kind = "content_policy" if is_content_policy_error(error) else "http"
                    retryable = status in {408, 429, 500, 502, 503, 504} and kind != "content_policy"
                    result.update(error=error, error_kind=kind, http_status=status)
                else:
                    body = response.json()
                    choice = body["choices"][0]
                    message = choice["message"]
                    output = message.get("content") or ""
                    if not isinstance(output, str):
                        raise ValueError("Non-text completion content")
                    result.update(raw_output=output, error=None, error_kind=None,
                                  http_status=status, response_meta={
                                      "response_id": body.get("id"),
                                      "returned_model": body.get("model"),
                                      "finish_reason": choice.get("finish_reason"),
                                      "usage": body.get("usage"),
                                      "reasoning_content": message.get("reasoning_content"),
                                  })
                    if message.get("refusal"):
                        result["validation_error"] = "content_policy_refusal"
                    result["attempt_records"].append({"attempt": attempt + 1, "http_status": status})
                    break
            except requests.RequestException as exc:
                result.update(error=redact(exc, secret), error_kind="transport", http_status=status)
                retryable = True
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                result.update(error=redact(exc, secret), error_kind="response_schema", http_status=status)
            result["attempt_records"].append({"attempt": attempt + 1, "http_status": status,
                                              "error": result["error"]})
            if not retryable or attempt == args.retries:
                break
            time.sleep(min(2 ** (attempt + 1), 8))
    result["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return result


def summary_rows(report, track):
    info = report["tracks"][track]
    output = []
    for task, metric in (("TG", "TG_m_tIoU"), ("SG", "SG_m_sIoU"), ("QA", "QA_accuracy")):
        values = info["main_metrics"]
        cs = ((info["paired_cs"] or {}).get("tasks") or {}).get(task, {})
        output.append({
            "task": task, "metric": {"TG": "m_tIoU", "SG": "m_sIoU", "QA": "Accuracy"}[task],
            "text": values.get("text_target", {}).get(metric),
            "text_image": values.get("reference_image", {}).get(metric),
            "cs": cs.get("value") if info["complete"] else None,
            "eligible_pairs": cs.get("scored_pairs") if info["complete"] else None,
        })
    return output


def format_table(records):
    lines = ["Task  Metric     Text     Text+Image  CS       Pairs",
             "----  ---------  -------  ----------  -------  -----"]
    for r in records:
        fmt = lambda x: "N/A" if x is None else f"{100 * x:.2f}"
        lines.append(f"{r['task']:<4}  {r['metric']:<9}  {fmt(r['text']):>7}  "
                     f"{fmt(r['text_image']):>10}  {fmt(r['cs']):>7}  "
                     f"{r['eligible_pairs'] if r['eligible_pairs'] is not None else 'N/A':>5}")
    return "\n".join(lines)


@contextmanager
def run_lock(output):
    import fcntl

    with (output / ".run.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("This output directory already has an active runner") from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def run(args):
    args.output.mkdir(parents=True, exist_ok=True)
    with run_lock(args.output):
        return run_locked(args)


def run_locked(args):
    started = time.monotonic()
    settings = ("text", "text_image") if args.setting == "both" else (args.setting,)
    tasks = args.tasks.split(",")
    if not tasks or len(set(tasks)) != len(tasks) or not set(tasks) <= {"TG", "SG", "QA"}:
        raise ValueError("--tasks must be a comma-separated subset of TG,SG,QA")
    questions = [q for q in selected_questions(args.data, args.video_id, args.track) if q["task"] in tasks]
    if not questions:
        raise ValueError("Empty question selection")
    videos = {v["video_id"]: v for v in selected_videos(args.data, args.video_id)
              if any(q["video_id"] == v["video_id"] for q in questions)}
    use_audio = uses_audio(args.track, args.audio)
    if use_audio:
        missing = [v["video_id"] for v in videos.values() if v.get("has_audio") is False]
        if missing:
            raise ValueError(f"Selected videos have no audio: {', '.join(missing)}. "
                             "Select videos with audio or use --audio off; no videos are skipped.")
    host = validate_api_base(args.api_base)
    encoding = args.audio_encoding
    if encoding == "auto":
        encoding = "data-uri" if host.hostname.endswith(".aliyuncs.com") else "base64"
    config = {
        "version": 2, "model": args.model, "display_model": args.display_model or args.model,
        "api_base": args.api_base, "track": args.track, "tasks": sorted(tasks),
        "settings": list(settings), "video_ids": sorted(videos),
        "questions_sha256": digest(questions), "videos_sha256": digest(list(videos.values())),
        "nframe": args.nframe, "fps": args.fps, "max_side": args.max_side,
        "jpeg_quality": args.jpeg_quality, "temperature": 0,
        "max_completion_tokens": args.max_completion_tokens,
        "thinking": {"reasoning_effort": args.reasoning_effort, "otherwise": "provider_default"},
        "audio_encoding": encoding, "image_detail": "high", "stream": False,
        "audio": {"mode": args.audio, "enabled": use_audio,
                  "protocol": AUDIO_PROTOCOL if use_audio else None,
                  "encoding": AUDIO_ENCODING if use_audio else None},
        "timeout": args.timeout, "retries": args.retries,
        "code_sha256": {p.name: sha(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
    }
    # The source layout keeps shared prompt/scoring code one level above.
    import omnicompass_public_adapter
    shared = Path(omnicompass_public_adapter.__file__).parent
    for name in ("omnicompass_public_adapter.py", "omnicompass_frame_prompt.py",
                 "omnicompass_av_frame_prompt.py", "omnicompass_release.py",
                 "omnicompass_scoring.py", "print_frame_eval_results.py", "print_modality_gain_results.py"):
        config["code_sha256"][name] = sha(shared / name)
    config_path = args.output / "run_config.json"
    if config_path.exists():
        if not args.resume:
            raise ValueError("Existing run: pass --resume or choose a new output directory")
        if json.loads(config_path.read_text()) != config:
            raise ValueError("Resume configuration differs; choose a new output directory")
    else:
        if (args.output / "predictions.jsonl").exists():
            raise ValueError("Predictions exist without a configuration")
        write_json(config_path, config)
    log = (args.output / "run.log").open("a", buffering=1)

    def say(message):
        print(message, flush=True)
        log.write(message + "\n")

    try:
        frames, audios, receipts = {}, {}, {}
        for vid, video in videos.items():
            directory, manifest, hit = extract_video(
                safe(args.data, video["video_path"]), args.cache_dir,
                nframe=args.nframe, fps=args.fps, max_side=args.max_side, jpeg_quality=args.jpeg_quality)
            frames[vid] = (directory, manifest)
            receipts[vid] = {"sampling_sha256": sha(directory / "sampling.json"),
                             "source_sha256": manifest["identity"]["source_sha256"]}
            if use_audio:
                audio, audio_manifest, audio_hit = extract_audio(
                    safe(args.data, video["video_path"]), args.audio_cache_dir)
                if audio_manifest["identity"]["source_sha256"] != receipts[vid]["source_sha256"]:
                    raise ValueError("Source video changed between frame and audio extraction")
                if abs(audio_manifest["timeline_origin_seconds"] -
                       manifest["video"]["timeline_origin_seconds"]) > 1e-4:
                    raise ValueError("Audio and frame timeline origins differ")
                audios[vid] = audio
                receipts[vid]["audio_sha256"] = audio_manifest["sha256"]
                receipts[vid]["audio_manifest_sha256"] = sha(audio.parent / "audio.json")
                say(f"Audio {vid}: complete MP3 from video, cache={audio_hit}")
            say(f"Frames {len(frames)}/{len(videos)} {vid}: {len(manifest['frames'])}, cache={hit}")
        if "text_image" in settings:
            receipts["references"] = {q["question_id"]: sha(safe(args.data, q["reference_image"])) for q in questions}
        receipt_path = args.output / "input_receipts.json"
        if receipt_path.exists() and json.loads(receipt_path.read_text()) != receipts:
            raise ValueError("Resume media changed")
        write_json(receipt_path, receipts)
        jobs = [(q, s) for q in questions for s in settings]
        expected = {(q["question_id"], s) for q, s in jobs}
        predictions_path = args.output / "predictions.jsonl"
        saved = load_predictions(predictions_path, expected)
        pending = [(q, s) for q, s in jobs if (q["question_id"], s) not in saved
                   or not terminal(saved[(q["question_id"], s)])]
        if args.max_requests is not None:
            pending = pending[:args.max_requests]
        secret = os.environ.get(args.api_key_env, "").strip()
        if pending and not secret:
            raise ValueError(f"Set the {args.api_key_env} environment variable")
        initial = sum(terminal(r) for r in saved.values())
        calls, finished, previous, last_report = 0, 0, initial, time.monotonic()

        def progress(force=False):
            nonlocal previous, last_report
            now = time.monotonic()
            if not force and now - last_report < args.progress_interval:
                return
            done = sum(terminal(r) for r in saved.values())
            elapsed = now - started
            eta = None if not finished else round((len(pending) - finished) * elapsed / finished)
            status = {"model": config["display_model"], "track": args.track,
                      "completed": done, "total": len(jobs), "new": done - previous,
                      "requests_finished_this_run": finished, "new_api_calls": calls,
                      "remaining": len(jobs) - done, "eta_seconds": eta,
                      "elapsed_seconds": round(elapsed), "updated_at": time.time()}
            write_json(args.output / "progress.json", status)
            bars = int(20 * done / len(jobs))
            say(f"{config['display_model']} | {args.track} | audio={'on' if use_audio else 'off'} | "
                f"[{'#' * bars}{'.' * (20-bars)}] "
                f"{done}/{len(jobs)} | +{done-previous} | ETA {eta if eta is not None else '?'}s")
            previous, last_report = done, now

        def execute(job):
            q, setting = job
            content = build_content(args.data, videos[q["video_id"]], q, setting,
                                    frames[q["video_id"]], encoding,
                                    audio_path=audios.get(q["video_id"]), use_audio=use_audio)
            return send_request(args, secret, content, q, setting)

        progress(True)
        with predictions_path.open("a", buffering=1) as handle, ThreadPoolExecutor(args.concurrency) as pool:
            iterator = iter(pending)
            active = set()
            for _ in range(min(args.concurrency, len(pending))):
                active.add(pool.submit(execute, next(iterator)))
            while active:
                completed, active = wait(active, timeout=args.progress_interval, return_when=FIRST_COMPLETED)
                for future in completed:
                    row = future.result()
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                    saved[(row["question_id"], row["setting"])] = row
                    calls += len(row["attempt_records"])
                    finished += 1
                    job = next(iterator, None)
                    if job is not None:
                        active.add(pool.submit(execute, job))
                progress()
        progress(True)
        complete_records = []
        for q, setting in jobs:
            complete_records.append(saved.get((q["question_id"], setting), {
                "question_id": q["question_id"], "setting": setting, "raw_output": "",
                "error": "not_requested", "error_kind": "missing"}))
        report = evaluate_public_predictions(questions, complete_records, settings)
        report["run"] = {"model": config["display_model"], "requested_model": args.model,
                         "audio": config["audio"],
                         "new_api_calls": calls, "selected_videos": len(videos),
                         "expected_requests": len(jobs), "saved_requests": len(saved),
                         "returned_models": sorted({r.get("response_meta", {}).get("returned_model")
                                                   for r in saved.values()
                                                   if r.get("response_meta", {}).get("returned_model")})}
        table = [r for r in summary_rows(report, args.track) if r["task"] in tasks]
        write_json(args.output / "scores.json", report)
        with (args.output / "scores.csv").open("w") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(table[0]))
            writer.writeheader()
            writer.writerows(table)
        complete = report["tracks"][args.track]["complete"]
        say(f"\n{config['display_model']} | {args.track} | audio={'on' if use_audio else 'off'} | "
            f"{'COMPLETE' if complete else 'INCOMPLETE'}")
        say(format_table(table))
        say(f"API calls this invocation: {calls}")
        return 0 if complete else 2
    finally:
        log.close()


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--data", type=Path, required=True)
    cli.add_argument("--model", required=True)
    cli.add_argument("--display-model")
    cli.add_argument("--api-base", required=True)
    cli.add_argument("--api-key-env", default="OMNICOMPASS_API_KEY")
    cli.add_argument("--track", choices=["VL", "AV"], required=True)
    cli.add_argument("--tasks", default="TG,SG,QA")
    cli.add_argument("--setting", choices=["text", "text_image", "both"], required=True)
    sampling = cli.add_mutually_exclusive_group(required=True)
    sampling.add_argument("--nframe", type=int)
    sampling.add_argument("--fps", type=float)
    cli.add_argument("--max-side", type=int, default=640)
    cli.add_argument("--jpeg-quality", type=int, default=95)
    cli.add_argument("--cache-dir", type=Path, default=Path(".frame_cache"))
    cli.add_argument("--audio-cache-dir", type=Path, default=Path(".audio_cache"))
    cli.add_argument("--audio", choices=["auto", "on", "off"], default="auto",
                     help="auto: VL vision-only, AV with audio; on/off are explicit modality overrides")
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument("--video-id", action="append")
    cli.add_argument("--resume", action="store_true")
    cli.add_argument("--concurrency", type=int, default=4)
    cli.add_argument("--max-completion-tokens", type=int, default=8192)
    cli.add_argument("--reasoning-effort")
    cli.add_argument("--audio-encoding", choices=["auto", "base64", "data-uri"], default="auto")
    cli.add_argument("--timeout", type=float, default=180)
    cli.add_argument("--retries", type=int, default=1)
    cli.add_argument("--progress-interval", type=float, default=15)
    cli.add_argument("--max-requests", type=int, help="Stop after this many selected requests; resume later")
    return cli


def main():
    cli = parser()
    args = cli.parse_args()
    if (args.concurrency < 1 or args.timeout <= 0 or args.retries < 0
            or args.progress_interval <= 0 or args.max_completion_tokens < 1
            or (args.max_requests is not None and args.max_requests < 0)):
        cli.error("Invalid concurrency, timeout, retry, budget or progress limit")
    raise SystemExit(run(args))


if __name__ == "__main__":
    main()
