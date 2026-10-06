#!/usr/bin/env python3
"""Sample full videos at a fixed frame budget or cadence; cache JPEGs and PTS."""

import argparse
from contextlib import contextmanager
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile

from release_tools import safe, selected_videos, sha

PROTOCOL = "omnicompass-uniform-time-pts-v1"
OFFSETS = (0, -0.25, 0.25, -0.5, 0.5, -1, 1, -2, 2, -5, 5)


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("Must be a positive integer")
    return number


def positive_float(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("Must be finite and positive")
    return number


def targets(duration, nframe=None, fps=None, max_frames=10000):
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Video duration must be finite and positive")
    if (nframe is None) == (fps is None):
        raise ValueError("Choose exactly one of nframe and fps")
    if nframe is not None:
        if isinstance(nframe, bool) or not isinstance(nframe, int) or nframe <= 0:
            raise ValueError("nframe must be a positive integer")
        count = nframe
    else:
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("fps must be finite and positive")
        # Decimal fractions prevent spurious extra samples at an exact endpoint.
        count = math.ceil(Fraction(str(duration)) * Fraction(str(fps)))
    if count > max_frames:
        raise ValueError(f"{count} samples exceed --max-frames {max_frames}; no silent truncation")
    if nframe is not None:
        return [duration * i / (count + 1) for i in range(1, count + 1)]
    return [float(Fraction(i) / Fraction(str(fps))) for i in range(count)]


class VideoReader:
    def __init__(self, path):
        import av

        self.container = av.open(str(path))
        try:
            if not self.container.streams.video:
                raise ValueError("No video stream")
            self.stream = self.container.streams.video[0]
            self.stream.codec_context.options = {"err_detect": "explode"}
            self.stream.thread_count = 1
            self.time_base = self.stream.time_base
            video_start = float((self.stream.start_time or 0) * self.time_base)
            # Keep a delayed video stream aligned with the container's audio clock.
            self.origin = (float(self.container.start_time / av.time_base)
                           if self.container.start_time is not None else video_start)
            if self.stream.duration is not None:
                self.duration = video_start + float(self.stream.duration * self.time_base) - self.origin
            elif self.container.duration is not None:
                self.duration = float(self.container.duration / av.time_base)
            else:
                raise ValueError("Video duration is unavailable")
            if not math.isfinite(self.duration) or self.duration <= 0:
                raise ValueError("Invalid video duration")
        except Exception:
            self.container.close()
            raise
        self.info = {
            "duration_seconds": self.duration,
            "width": self.stream.width,
            "height": self.stream.height,
            "stream_start_seconds": video_start,
            "timeline_origin_seconds": self.origin,
            "time_base": str(self.time_base),
        }

    def close(self):
        self.container.close()

    def frame_at(self, seconds):
        absolute = seconds + self.origin
        offset = math.floor(absolute / float(self.time_base))
        self.container.seek(offset, stream=self.stream, backward=True, any_frame=False)
        last = None
        for frame in self.container.decode(self.stream):
            if frame.pts is None:
                raise ValueError("Decoded frame has no presentation timestamp")
            elapsed = float(frame.pts * frame.time_base) - self.origin
            if elapsed + 1e-9 < seconds:
                last = frame
                continue
            if frame.is_corrupt:
                raise ValueError("Decoder marked the selected frame corrupt")
            return frame.to_image(), elapsed, frame.pts, str(frame.time_base)
        # The last frame remains on screen until its presentation interval ends.
        if last is not None and not last.is_corrupt and last.duration:
            end = float((last.pts + last.duration) * last.time_base) - self.origin
            if seconds < end:
                elapsed = float(last.pts * last.time_base) - self.origin
                return last.to_image(), elapsed, last.pts, str(last.time_base)
        raise ValueError("No decodable frame at or after the requested time")


def sample(reader, requested, previous, on_error):
    attempts = []
    for offset in OFFSETS if on_error == "nearest" else (0,):
        candidate = requested + offset
        if candidate < 0 or candidate >= reader.duration:
            continue
        try:
            image, actual, pts, time_base = reader.frame_at(candidate)
            if actual + 1e-9 < previous:
                raise ValueError("Fallback frame would break chronological order")
            if actual >= reader.duration + 1e-6:
                raise ValueError("Decoded timestamp lies outside the video duration")
            # Large jumps can hide undecodable regions even when seeking succeeds.
            if abs(actual - requested) > 5.0 + 1e-6:
                raise ValueError("Decoded frame is more than five seconds from the target")
            return image, {
                "requested_timestamp_sec": requested,
                "candidate_timestamp_sec": candidate,
                "timestamp_sec": actual,
                "pts": pts,
                "time_base": time_base,
                "fallback_offset_sec": offset,
                "attempts": attempts,
            }
        except Exception as exc:
            attempts.append({"candidate_timestamp_sec": candidate, "error": str(exc)})
    raise ValueError(f"Cannot sample at {requested:.6f}s: {attempts}")


def decoder_versions():
    import av
    import PIL

    return {"pyav": av.__version__, "pillow": PIL.__version__,
            "ffmpeg_libraries": {k: list(v) for k, v in av.library_versions.items()}}


@contextmanager
def cache_lock(root, key):
    lock = root / f".{key}.lock"
    try:
        lock.mkdir()
    except FileExistsError:
        raise ValueError(f"Cache is in use: {lock}. Remove this lock only after its writer stops.")
    try:
        yield
    finally:
        lock.rmdir()


def check_cache(directory, identity, count):
    if directory.is_symlink():
        raise ValueError("Cache directory must not be a symbolic link")
    manifest = json.loads((directory / "sampling.json").read_text())
    if manifest["identity"] != identity or len(manifest["frames"]) != count:
        raise ValueError("Cache identity/count mismatch")
    previous = -math.inf
    for ordinal, frame in enumerate(manifest["frames"]):
        if frame["ordinal"] != ordinal or frame["timestamp_sec"] < previous:
            raise ValueError("Cache frame order mismatch")
        previous = frame["timestamp_sec"]
        path = safe(directory, frame["path"])
        if not path.is_file() or sha(path) != frame["sha256"]:
            raise ValueError(f"Missing or changed cached image: {path}")
    return manifest


def extract_video(video, cache_dir, *, nframe=None, fps=None, max_side=640,
                  jpeg_quality=95, on_error="nearest", max_frames=10000):
    video = Path(video).resolve(strict=True)
    if not video.is_file():
        raise ValueError("Video must be a regular file")
    if max_side < 0 or not 1 <= jpeg_quality <= 100:
        raise ValueError("max_side must be nonnegative and JPEG quality must be 1..100")
    if on_error not in {"nearest", "fail"} or max_frames < 1:
        raise ValueError("Invalid fallback policy or frame limit")
    source_stat = video.stat()
    source_hash = sha(video)
    identity = {
        "protocol": PROTOCOL, "source_sha256": source_hash,
        "sampler_sha256": sha(Path(__file__)),
        "nframe": nframe, "fps": fps, "max_side": max_side,
        "jpeg_quality": jpeg_quality, "on_decode_error": on_error,
        "decoder": decoder_versions(),
    }
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    root = Path(cache_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    destination = root / key
    reader = VideoReader(video)
    try:
        schedule = targets(reader.duration, nframe, fps, max_frames)
        with cache_lock(root, key):
            if destination.exists():
                try:
                    manifest = check_cache(destination, identity, len(schedule))
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    raise ValueError(f"Invalid cache {destination}: {exc}. "
                                     "Use a new cache directory or remove only this cache entry.") from exc
                return destination, manifest, True
            stage = Path(tempfile.mkdtemp(prefix=f".{key}.", dir=root))
            try:
                frames = []
                previous = -math.inf
                for ordinal, requested in enumerate(schedule):
                    image, row = sample(reader, requested, previous, on_error)
                    previous = row["timestamp_sec"]
                    image = image.convert("RGB")
                    if max_side and max(image.size) > max_side:
                        from PIL import Image

                        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
                    name = f"frame_{ordinal:06d}.jpg"
                    image.save(stage / name, quality=jpeg_quality)
                    row.update(ordinal=ordinal, path=name, width=image.width,
                               height=image.height, sha256=sha(stage / name))
                    frames.append(row)
                current = video.stat()
                if (current.st_size, current.st_mtime_ns, current.st_ino) != (
                        source_stat.st_size, source_stat.st_mtime_ns, source_stat.st_ino):
                    raise ValueError("Source video changed during extraction")
                manifest = {
                    "identity": identity, "source_bytes": source_stat.st_size,
                    "video": reader.info,
                    "timestamp_origin": "container_start_or_video_start_if_unavailable",
                    "frames": frames,
                    "fallback_frames": sum(bool(f["fallback_offset_sec"]) for f in frames),
                    "duplicate_frames": len(frames) - len({f["pts"] for f in frames}),
                }
                (stage / "sampling.json").write_text(json.dumps(manifest, indent=2) + "\n")
                stage.rename(destination)
            finally:
                if stage.exists():
                    shutil.rmtree(stage)
            return destination, manifest, False
    finally:
        reader.close()


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    source = cli.add_mutually_exclusive_group(required=True)
    source.add_argument("--video", type=Path, help="Single video file")
    source.add_argument("--data", type=Path, help="Extracted dataset with videos.jsonl")
    cli.add_argument("--video-id", action="append", help="Repeat to select dataset videos")
    cli.add_argument("--track", choices=["VL", "AV"], help="Filter dataset videos")
    mode = cli.add_mutually_exclusive_group(required=True)
    mode.add_argument("--nframe", type=positive_int)
    mode.add_argument("--fps", type=positive_float, help="Local sampling cadence, not native-video FPS")
    cli.add_argument("--cache-dir", type=Path, required=True)
    cli.add_argument("--max-side", type=int, default=640, help="JPEG longest edge; 0 keeps original size")
    cli.add_argument("--jpeg-quality", type=int, default=95)
    cli.add_argument("--on-decode-error", choices=["nearest", "fail"], default="nearest")
    cli.add_argument("--max-frames", type=positive_int, default=10000)
    return cli


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    if args.video and (args.video_id or args.track):
        cli.error("--video-id and --track require --data")
    if args.max_side < 0 or not 1 <= args.jpeg_quality <= 100:
        cli.error("--max-side must be >= 0; --jpeg-quality must be 1..100")
    try:
        decoder_versions()
        if args.video:
            jobs = [(None, args.video)]
        else:
            videos = selected_videos(args.data, args.video_id)
            jobs = [(v["video_id"], safe(args.data, v["video_path"])) for v in videos
                    if not args.track or args.track in v["tracks"]]
        if not jobs:
            raise ValueError("No videos selected")
        failures = 0
        for video_id, video in jobs:
            try:
                directory, manifest, reused = extract_video(
                    video, args.cache_dir, nframe=args.nframe, fps=args.fps,
                    max_side=args.max_side, jpeg_quality=args.jpeg_quality,
                    on_error=args.on_decode_error, max_frames=args.max_frames)
                print(json.dumps({
                    "status": "ok", "video_id": video_id, "video": str(video),
                    "manifest": str(directory / "sampling.json"), "cache_hit": reused,
                    "frames": len(manifest["frames"]), "fallback_frames": manifest["fallback_frames"],
                    "duplicate_frames": manifest["duplicate_frames"],
                }), flush=True)
            except Exception as exc:
                failures += 1
                print(json.dumps({"status": "error", "video_id": video_id,
                                  "video": str(video), "error": str(exc)}), flush=True)
        return 1 if failures else 0
    except ImportError as exc:
        cli.exit(1, f"Missing dependency: {exc}. Install requirements-frames.txt.\n")
    except (ValueError, OSError) as exc:
        cli.exit(1, f"{exc}\n")


if __name__ == "__main__":
    sys.exit(main())
