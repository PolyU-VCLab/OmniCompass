"""Offline checks for sampling, generation defaults, and paper scoring rules."""

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from extract_frames import sample, targets
from omnicompass_public_adapter import evaluate_public_predictions
from run_eval import build_content, load_predictions, parser, send_request, terminal


def question(task):
    row = {"question_id": f"test_{task}", "video_id": "test_video", "track": "VL",
           "task": task, "question": {"text": "Find the target.",
                                     "text_image": "Find the reference target."}}
    if task == "QA":
        row.update(ground_truth={"answer": "C"}, options=dict(zip("ABCDE", "12345")))
    elif task == "TG":
        row["ground_truth"] = {"start_time": 10, "end_time": 20}
    else:
        row.update(given_interval=[10, 20], ground_truth={
            "start_bbox": [100, 100, 300, 300], "end_bbox": [200, 200, 400, 400]})
    return row


def arguments(*extra):
    return parser().parse_args([
        "--data", "data", "--model", "test-model", "--track", "VL",
        "--api-base", "http://localhost:8000/v1", "--setting", "both",
        "--nframe", "32", "--output", "output", *extra,
    ])


class EvaluationContractTests(unittest.TestCase):
    def test_defaults_and_historical_override(self):
        self.assertEqual(arguments().max_completion_tokens, 32768)
        self.assertEqual(arguments().timeout, 1200)
        self.assertEqual(arguments("--max-completion-tokens", "8192").max_completion_tokens, 8192)

    def test_exact_sampling_count_and_no_model_specific_cap(self):
        for count in (32, 64, 128, 1024):
            schedule = targets(2400, nframe=count)
            self.assertEqual(len(schedule), count)
            self.assertEqual(schedule[0], 2400 / (count + 1))
            self.assertEqual(schedule[-1], 2400 * count / (count + 1))
        self.assertEqual(targets(2400, fps=1), list(range(2400)))

    def test_payload_retains_all_frames_and_actual_timestamps(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "frame.jpg").write_bytes(b"image-fixture")
            frames = [{"path": "frame.jpg", "timestamp_sec": i + 0.04} for i in range(1024)]
            content = build_content(root, {"duration_seconds": 1200}, question("QA"),
                                    "text", (root, {"frames": frames}), "base64")
            self.assertEqual(sum(item["type"] == "image_url" for item in content), 1024)
            self.assertEqual(content[0]["text"], "Timestamp: 0.04 seconds.")
            self.assertEqual(content[-3]["text"], "Timestamp: 1023.04 seconds.")

    def test_failed_reseek_reuses_only_a_recent_real_frame(self):
        reader = MagicMock(duration=20)
        reader.frame_at.side_effect = ValueError("Cannot seek into damaged GOP")
        image = object()
        prior = (image, {"timestamp_sec": 3, "pts": 75, "time_base": "1/25",
                         "decode_recovery": False})
        returned, row = sample(reader, 4, 3, "nearest", prior)
        self.assertIs(returned, image)
        self.assertEqual((row["timestamp_sec"], row["pts"], row["time_base"]),
                         (3, 75, "1/25"))
        self.assertTrue(row["reused_previous_frame"])
        for target, policy in ((4, "fail"), (9, "nearest")):
            with self.subTest(target=target, policy=policy), self.assertRaises(ValueError):
                sample(reader, target, 3, policy, prior)

    def test_exhaustion_stays_in_task_and_cs_denominators(self):
        for track in ("VL", "AV"):
            for task in ("TG", "SG", "QA"):
                q = {**question(task), "track": track}
                rows = [{"question_id": q["question_id"], "setting": setting,
                         "raw_output": "", "error": None, "response_meta": {
                             "finish_reason": "length",
                             "usage": {"completion_tokens": 32768}}}
                        for setting in ("text", "text_image")]
                with self.subTest(track=track, task=task):
                    report = evaluate_public_predictions([q], rows)
                    info = report["tracks"][track]
                    self.assertTrue(all(terminal(row) for row in rows))
                    self.assertTrue(info["complete"])
                    self.assertEqual(len(info["scoring_ids"]), 2)
                    self.assertEqual([r["score"] for r in report["parsed_predictions"]], [0, 0])
                    self.assertEqual(info["paired_cs"]["tasks"][task]["scored_pairs"], 1)
                    self.assertEqual(info["paired_cs"]["tasks"][task]["value"], 0)

    def test_parseable_truncation_keeps_legacy_score(self):
        q = question("QA")
        rows = [{"question_id": q["question_id"], "setting": setting, "raw_output": "C",
                 "error": None, "response_meta": {"finish_reason": "length"}}
                for setting in ("text", "text_image")]
        report = evaluate_public_predictions([q], rows)
        self.assertEqual([r["score"] for r in report["parsed_predictions"]], [1, 1])
        self.assertEqual(report["tracks"]["VL"]["paired_cs"]["tasks"]["QA"]["value"], 1)

    def test_exhaustion_is_not_retried_and_remains_terminal_on_resume(self):
        body = {"choices": [{"message": {"content": ""}, "finish_reason": "length"}],
                "usage": {"completion_tokens": 32768}}
        with patch("requests.Session") as session:
            response = MagicMock(status_code=200)
            response.json.return_value = body
            post = session.return_value.__enter__.return_value.post
            post.return_value = response
            result = send_request(arguments("--retries", "3"), "local-test-key", [],
                                  question("QA"), "text")
            self.assertEqual(post.call_count, 1)
            self.assertEqual(post.call_args.kwargs["json"]["max_completion_tokens"], 32768)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "predictions.jsonl"
            path.write_text(json.dumps(result) + "\n")
            saved = load_predictions(path, {(result["question_id"], "text")})
            self.assertTrue(terminal(saved[(result["question_id"], "text")]))

    def test_context_rejection_remains_incomplete_without_request_retry(self):
        q = question("QA")
        error = json.dumps({"error": {"code": "context_length_exceeded",
                                    "message": "Input plus output exceeds the context limit"}})
        with patch("requests.Session") as session:
            post = session.return_value.__enter__.return_value.post
            post.return_value = MagicMock(status_code=400, text=error)
            result = send_request(arguments("--retries", "3"), "local-test-key", [], q, "text")
            self.assertEqual(post.call_count, 1)
            self.assertFalse(terminal(result))
            self.assertEqual(result["error_kind"], "http")
        answer = {"question_id": q["question_id"], "setting": "text_image",
                  "raw_output": "C", "error": None}
        report = evaluate_public_predictions([q], [result, answer])
        info = report["tracks"]["VL"]
        self.assertFalse(info["complete"])
        self.assertEqual(len(info["scoring_ids"]), 1)
        self.assertEqual(len(info["transport_excluded_ids"]), 1)
        self.assertFalse(info["policy_excluded_ids"])


if __name__ == "__main__":
    unittest.main()
