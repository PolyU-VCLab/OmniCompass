"""Synthetic export tests. Fixture scores must never be published."""

from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
import export_hf_results as exporter


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.revision = "a" * 40
        self.questions, self.videos, self.media = [], [], []
        self.receipts, self.predictions = {"references": {}}, []
        for track, count in (("VL", 820), ("AV", 240)):
            for i in range(count):
                vid = f"{track}_{i}"
                video = {"video_id": vid, "video_path": f"videos/{vid}.mp4"}
                self.videos.append(video)
                self.media.append({"public_path": video["video_path"], "sha256": "b" * 64})
                self.receipts[vid] = dict.fromkeys(
                    ("source_sha256", "sampling_sha256", "audio_sha256", "audio_manifest_sha256"),
                    "b" * 64,
                )
                for task in exporter.TASKS:
                    qid = f"{vid}_{task}"
                    q = {"question_id": qid, "video_id": vid, "track": track, "task": task,
                         "reference_image": f"references/{qid}.png"}
                    if task == "QA":
                        q["ground_truth"] = {"answer": "A"}
                        answer = "A"
                    elif task == "TG":
                        q["ground_truth"] = {"start_time": 1, "end_time": 2}
                        answer = json.dumps(q["ground_truth"])
                    else:
                        q["given_interval"] = [1, 2]
                        q["ground_truth"] = dict.fromkeys(("start_bbox", "end_bbox"), [0, 0, 100, 100])
                        answer = json.dumps({**q["ground_truth"], "start_time": 1, "end_time": 2})
                    self.questions.append(q)
                    self.media.append({"public_path": q["reference_image"], "sha256": "b" * 64})
                    self.receipts["references"][qid] = "b" * 64
                    self.predictions.extend(
                        {"question_id": qid, "setting": setting, "raw_output": answer}
                        for setting in exporter.SETTINGS
                    )
        self.manifest = {"files": {}}
        for name, values in (("questions.jsonl", self.questions), ("videos.jsonl", self.videos),
                             ("media_manifest.jsonl", self.media)):
            (self.root / name).write_text("".join(json.dumps(v) + "\n" for v in values))
            self.manifest["files"][name] = exporter.sha(self.root / name)
        mock = patch.object(exporter, "hub_manifest", return_value=self.manifest)
        mock.start()
        self.addCleanup(mock.stop)
        self.configure("VL")

    def configure(self, track):
        qs = [q for q in self.questions if q["track"] == track]
        vids = {q["video_id"] for q in qs}
        videos = [v for v in self.videos if v["video_id"] in vids]
        self.config = {
            "model": "synthetic-test-only", "track": track, "tasks": sorted(exporter.TASKS),
            "settings": list(exporter.SETTINGS), "video_ids": sorted(vids),
            "questions_sha256": exporter.digest(qs), "videos_sha256": exporter.digest(videos),
            "audio": {"enabled": track == "AV"}, "nframe": 32, "fps": None,
            "max_side": 640, "jpeg_quality": 85, "max_completion_tokens": 32768,
            "thinking": {"mode": "default", "api": "auto"},
            "code_sha256": {n: exporter.sha(Path(exporter.__file__).parent / n)
                            for n in exporter.PROTOCOL_FILES},
            "api_base": "https://private-endpoint.invalid", "secret": "DO-NOT-EXPORT",
        }
        self.write_config()
        receipts = {v: self.receipts[v] for v in vids}
        qids = {q["question_id"] for q in qs}
        receipts["references"] = {q: h for q, h in self.receipts["references"].items() if q in qids}
        (self.root / "input_receipts.json").write_text(json.dumps(receipts))
        self.active_predictions = [p for p in self.predictions if p["question_id"] in qids]
        self.write_predictions()

    def write_config(self):
        (self.root / "run_config.json").write_text(json.dumps(self.config))

    def write_predictions(self):
        (self.root / "predictions.jsonl").write_text(
            "".join(json.dumps(p) + "\n" for p in self.active_predictions)
        )

    def export(self, **overrides):
        kwargs = dict(data=self.root, run_dir=self.root, revision=self.revision,
                      model_repo="test/model", model_revision="test-revision",
                      evaluated_on="2026-10-01", source_url="https://example.org/evidence")
        return exporter.build_entry(**{**kwargs, **overrides})

    def test_complete_vl_and_av(self):
        for track in ("VL", "AV"):
            self.configure(track)
            result = self.export()
            self.assertEqual(result["value"], 100)
            self.assertEqual(result["dataset"]["task_id"], f"OmniCompass-{track}")
            self.assertNotIn("verifyToken", result)
            self.assertNotIn("DO-NOT-EXPORT", json.dumps(result))
            self.assertNotIn("private-endpoint", json.dumps(result))

    def test_partial_config_rejected(self):
        for field, value in (("video_ids", ["VL_0"]), ("tasks", ["QA"]),
                             ("settings", ["text"]), ("questions_sha256", "changed"),
                             ("audio", {"enabled": True}), ("nframe", 0)):
            old = deepcopy(self.config)
            self.config[field] = value
            self.write_config()
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.export()
            self.config = old
        self.write_config()

    def test_missing_and_duplicate_predictions(self):
        removed = self.active_predictions.pop()
        self.write_predictions()
        with self.assertRaises(ValueError):
            self.export()
        self.active_predictions.extend([removed, removed])
        self.write_predictions()
        with self.assertRaises(ValueError):
            self.export()

    def test_transport_failure_and_retry(self):
        original = self.active_predictions[0]
        self.active_predictions[0] = {**original, "error": "timeout", "error_kind": "transport"}
        self.write_predictions()
        with self.assertRaisesRegex(ValueError, "Transport"):
            self.export()
        self.active_predictions.append(original)
        self.write_predictions()
        self.assertEqual(self.export()["value"], 100)

    def test_empty_completed_answer_scores_zero(self):
        self.active_predictions[0]["raw_output"] = ""
        self.write_predictions()
        self.assertLess(self.export()["value"], 100)

    def test_policy_exclusions_are_disclosed(self):
        self.active_predictions[0].update(error="content_policy_violation",
                                          error_kind="content_policy", raw_output="")
        self.write_predictions()
        result = self.export()
        notes = json.loads(result["notes"])
        self.assertEqual(notes["policy_excluded_requests"], 1)
        self.assertEqual(notes["eligible_pairs"]["TG"], 819)
        self.assertEqual(result["value"], 100)

    def test_task_without_eligible_pairs_is_rejected(self):
        for row in self.active_predictions:
            if row["question_id"].endswith("_TG"):
                row.update(error="content_policy_violation",
                           error_kind="content_policy", raw_output="")
        self.write_predictions()
        with self.assertRaisesRegex(ValueError, "eligible pairs"):
            self.export()

    def test_fps_sampling(self):
        self.config.update(nframe=None, fps=1)
        self.write_config()
        notes = json.loads(self.export()["notes"])
        self.assertEqual(notes["fps"], 1)
        self.assertIsNone(notes["nframe"])
        for fps in (0, -1, float("nan"), float("inf"), True):
            self.config["fps"] = fps
            self.write_config()
            with self.subTest(fps=fps), self.assertRaises(ValueError):
                self.export()

    def test_changed_annotations_and_protocol_rejected(self):
        (self.root / "questions.jsonl").write_text("{}\n")
        with self.assertRaisesRegex(ValueError, "differs"):
            self.export()
        self.config["code_sha256"]["extract_frames.py"] = "changed"
        with self.assertRaisesRegex(ValueError, "protocol"):
            exporter.validate_run(
                self.config,
                json.loads((self.root / "input_receipts.json").read_text()),
                [q for q in self.questions if q["track"] == "VL"],
                [v for v in self.videos if v["video_id"].startswith("VL_")],
                {r["public_path"]: r for r in self.media},
            )

    def test_missing_input_receipts(self):
        (self.root / "input_receipts.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "receipts"):
            self.export()

    def test_urls_and_dates(self):
        for url in ("http://example.org", "https://user:secret@example.org",
                    "https://example.org?token=secret", "https://localhost/x"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.export(source_url=url)
        with self.assertRaises(ValueError):
            self.export(evaluated_on=(date.today() + timedelta(days=1)).isoformat())

    def test_yaml_output_roundtrip_and_no_overwrite(self):
        import yaml

        entry = self.export()
        target = self.root / "result.yaml"
        exporter.write_yaml(target, entry)
        self.assertEqual(yaml.safe_load(target.read_text()), [entry])
        with self.assertRaises(FileExistsError):
            exporter.write_yaml(target, entry)


if __name__ == "__main__":
    unittest.main()
