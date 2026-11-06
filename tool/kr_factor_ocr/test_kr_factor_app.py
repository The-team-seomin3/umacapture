"""App adapter contract tests. Inference and input pixels are explicitly synthetic."""
import copy
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import kr_factor_app as app
import kr_factor_export as exporter
import kr_factor_ocr as kr
import test_kr_factor_export as fixtures


class AppAdapter(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.VerifiedExport()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        self.work = f.root / "app-run"
        self.request = {"schema_version": 1, "capture": str(f.source), "master": str(f.master),
                        "master_sha256": kr.digest(f.master), "factor_info": str(f.source / "factor_info.json"),
                        "factor_info_sha256": kr.digest(f.source / "factor_info.json"),
                        "module_version": str(f.source / "version_info.json"),
                        "model": str(f.source / "model.onnx"), "working_dir": str(self.work)}
        # Only these tests permit a synthetic model identity; production never does.
        pin = patch.object(kr, "MODEL_SHA256", kr.digest(f.source / "model.onnx"))
        pin.start()
        self.addCleanup(pin.stop)
        inference = patch.object(kr, "recognize", return_value=[("가ㅇ", .8)] * 3)
        self.inference = inference.start()
        self.addCleanup(inference.stop)
        self.before = {p: kr.digest(p) for p in f.source.iterdir()}

    def call(self, command, request=None):
        path = self.fixture.root / "request.json"
        path.write_bytes(exporter.encoded(request or self.request))
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = app.main([command, "--request", str(path)])
        lines = stdout.getvalue().splitlines()
        self.assertEqual(len(lines), 1, stdout.getvalue())
        return code, json.loads(lines[0])

    def start(self):
        code, result = self.call("run")
        self.assertEqual(code, 2, result)
        return result

    def completed_review(self, result):
        review = copy.deepcopy(result["review"])
        review["reviewer"] = "Synthetic independently checked pixel reviewer"
        review["coverage"] = {**{k: True for k in exporter.COVERAGE}, "evidence": "Synthetic coverage checked"}
        for row in review["rows"]:
            row.update(decision="confirmed", observed_name="가○", master_name="가○", star=2,
                       app_sid=0, factor_id=102, factor_group_id=1, evidence="Synthetic pixels checked")
        return review

    def save(self, result, review=None):
        request = {**self.request, "review": review or self.completed_review(result),
                   "expected_review_sha256": result["review_sha256"]}
        return self.call("save-review", request)

    def test_run_and_resume_need_review_without_accepting_candidates(self):
        result = self.start()
        self.assertEqual(result["status"], "needs_review")
        self.assertFalse(result["completed"])
        self.assertFalse(result["ready_to_export"])
        self.assertEqual([r["group"] for r in result["rows"]], list(kr.GROUPS))
        self.assertTrue(all(r["decision"] == "unreviewed" for r in result["review"]["rows"]))
        self.assertTrue(all(not r["verified"] for r in result["rows"]))
        self.assertTrue(all(Path(r["name_crop"]).is_file() and Path(r["star_crop"]).is_file()
                            for r in result["rows"]))
        self.assertEqual(self.call("load")[0], 2)
        self.assertEqual(self.call("validate-review")[0], 2)
        self.assertEqual({p: kr.digest(p) for p in self.fixture.source.iterdir()}, self.before)
        self.assertEqual(self.call("run")[0], 1)

    def test_lookup_sid_zero_star_paging_and_read_only_pins(self):
        before = kr.digest(self.fixture.master)
        request = {k: self.request[k] for k in ("master", "master_sha256", "factor_info", "factor_info_sha256")}
        request.update(query=" 가 ○ ", star=2)
        code, result = self.call("lookup", request)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["matches"][0]["app_sids"], [0])
        self.assertTrue(result["matches"][0]["selectable"])
        self.assertEqual(result["matches"][0]["factor_id"], 102)
        self.assertEqual(kr.digest(self.fixture.master), before)
        self.assertEqual(self.call("lookup", {**request, "query": "", "limit": 1, "offset": 1})[1]["total"], 2)
        self.assertEqual(self.call("lookup", {**request, "query": "", "star": None})[1]["total"], 5)
        self.assertEqual(self.call("lookup", {**request, "factor_info_sha256": "0" * 64})[0], 1)
        self.assertEqual(self.call("lookup", {**request, "master_sha256": "0" * 64})[0], 1)
        self.assertEqual(self.call("lookup", {**request, "star": 0})[0], 1)
        self.assertEqual(self.call("lookup", {**request, "limit": 201})[0], 1)

    def test_partial_save_and_coverage_cannot_export(self):
        result = self.start()
        review = self.completed_review(result)
        review["rows"][1] = result["review"]["rows"][1]
        code, partial = self.save(result, review)
        self.assertEqual(code, 2, partial)
        self.assertNotEqual(result["review_sha256"], partial["review_sha256"])
        output = self.fixture.root / "output/record-kr.json"
        request = {**self.request, "output": str(output), "evidence_output": str(self.fixture.root / "evidence")}
        self.assertEqual(self.call("export", request)[0], 2)
        self.assertFalse(output.exists())
        review = self.completed_review(partial)
        review["coverage"]["complete_capture"] = False
        self.assertEqual(self.save(partial, review)[0], 2)
        self.assertEqual(self.call("export", request)[0], 2)

    def test_draft_hash_races_and_owned_lock_preserve_saved_review(self):
        result = self.start()
        code, updated = self.save(result)
        self.assertEqual(code, 0, updated)
        before = Path(updated["review_path"]).read_bytes()
        self.assertEqual(self.save(result)[0], 1)
        self.assertEqual(Path(updated["review_path"]).read_bytes(), before)
        lock = self.work / ".review.json.lock"
        lock.write_text("another-writer", encoding="ascii")
        self.assertEqual(self.save(updated)[0], 1)
        self.assertEqual(lock.read_text(encoding="ascii"), "another-writer")
        self.assertEqual(Path(updated["review_path"]).read_bytes(), before)

    def test_immutable_context_and_invalid_identity_edits_are_rejected(self):
        result = self.start()
        before = Path(result["review_path"]).read_bytes()
        for mode in ("binding", "order", "raw_ocr", "baseline", "star", "sid", "namespace", "reason"):
            review = self.completed_review(result)
            if mode == "binding": review["bindings"]["model_sha256"] = "0" * 64
            elif mode == "order": review["rows"].reverse()
            elif mode == "raw_ocr": review["rows"][0]["raw_ocr"] = "edited OCR"
            elif mode == "baseline": review["rows"][0]["baseline_sid"] = 0
            elif mode == "star": review["rows"][0]["star"] = 4
            elif mode == "sid": review["rows"][0]["app_sid"] = 1
            elif mode == "namespace": review["rows"][0]["factor_group_id"] = 102
            elif mode == "reason": review["rows"][0]["observed_name"] = "가·○"
            with self.subTest(mode=mode):
                self.assertEqual(self.save(result, review)[0], 1)
                self.assertEqual(Path(result["review_path"]).read_bytes(), before)

    def test_manual_master_selection_succeeds_with_empty_ocr_candidates(self):
        self.inference.return_value = [("", .0)] * 3
        result = self.start()
        self.assertTrue(all(not r["candidates"] for r in result["rows"]))
        code, ready = self.save(result)
        self.assertEqual(code, 0, ready)
        self.assertTrue(ready["ready_to_export"])
        self.assertFalse(ready["completed"])
        self.assertEqual(self.call("validate-review")[0], 0)

    def test_export_full_shape_failure_replacement_guard_and_protected_inputs(self):
        result = self.start()
        self.assertEqual(self.save(result)[0], 0)
        output, evidence = self.fixture.root / "output/record-kr.json", self.fixture.root / "evidence"
        request = {**self.request, "output": str(output), "evidence_output": str(evidence)}
        code, exported = self.call("export", request)
        self.assertEqual(code, 0, exported)
        self.assertEqual(exported["status"], "completed")
        self.assertTrue(exported["completed"])
        derived = exporter.read_json(output)
        exporter.validate_allowed_changes(self.fixture.record, derived)
        self.assertEqual(derived["factors"], {g: [{"id": 0, "star": 2}] for g in kr.GROUPS})
        self.assertEqual(exported["output_sha256"], kr.digest(output))
        before = output.read_bytes()
        again = {**request, "evidence_output": str(self.fixture.root / "evidence2")}
        self.assertEqual(self.call("export", again)[0], 1)
        self.assertEqual(self.call("export", {**again, "replace_sha256": "0" * 64})[0], 1)
        self.assertEqual(output.read_bytes(), before)
        self.assertEqual({p: kr.digest(p) for p in self.fixture.source.iterdir()}, self.before)
        bad = {**again, "output": str(self.fixture.source / "record.json")}
        self.assertEqual(self.call("export", bad)[0], 1)
        # Explicit matching replacement pin is the only supported replacement route.
        self.assertEqual(self.call("export", {**again, "replace_sha256": kr.digest(output)})[0], 0)

    def test_stale_sources_and_wrong_model_never_return_success(self):
        result = self.start()
        source = self.fixture.source / "factor.png"
        source.write_bytes(source.read_bytes() + b"changed")
        self.assertEqual(self.call("load")[0], 1)
        self.assertEqual(self.save(result)[0], 1)
        self.assertEqual(self.call("lookup", {**self.request, "schema_version": True})[0], 1)
        self.assertEqual(self.call("load", {**self.request, "model": str(source)})[0], 1)

    def test_run_refuses_inputs_existing_work_and_relative_paths(self):
        self.assertEqual(self.call("run", {**self.request, "working_dir": str(self.fixture.source)})[0], 1)
        self.assertEqual(self.call("run", {**self.request, "working_dir": "relative-run"})[0], 1)
        self.assertEqual(self.call("run", {**self.request, "factor_info_sha256": "x"})[0], 1)
        self.assertEqual({p: kr.digest(p) for p in self.fixture.source.iterdir()}, self.before)

    def test_cli_malformed_requests_have_one_json_error_line(self):
        script = Path(app.__file__)
        for content in ('{"schema_version":1,"schema_version":1}', '{"value":NaN}', '[1]', '{bad'):
            path = self.fixture.root / "malformed.json"
            path.write_text(content, encoding="utf-8")
            process = subprocess.run([sys.executable, "-B", str(script), "lookup", "--request", str(path)],
                                     capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(process.returncode, 1)
            self.assertEqual(len(process.stdout.splitlines()), 1)
            self.assertEqual(json.loads(process.stdout)["status"], "error")


if __name__ == "__main__":
    unittest.main()
