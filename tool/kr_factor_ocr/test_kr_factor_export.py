"""Actual saved-output contract tests; all OCR/pixels here are synthetic."""
import argparse
from contextlib import closing, redirect_stdout
import copy
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

import kr_factor_ocr as kr
import kr_factor_export as exporter
from test_kr_factor_ocr import capture


class VerifiedExport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        fixture = Path(__file__).resolve().parents[2] / "test/fixtures/chara_detail_record.json"
        self.record = kr.read_json(fixture)
        _, prediction, geometry = capture()
        self.record["factors"] = {g: [{"id": 9, "star": 2}] for g in kr.GROUPS}
        for row in prediction["factor_tab"]:
            if row["model"] == "factor":
                row["prediction"]["label"] = 9
        self.record["metadata"]["format_version"] = "1.0.0"
        self.record["metadata"]["region"] = "JPN"
        self.record["future_extension"] = {"copied": [True, None, {"number": 2.0}]}
        module = {key: self.record["metadata"][key] for key in ("region", "recognizer_version")}
        for name, value in (("record.json", self.record), ("prediction.json", prediction),
                            ("factor.json", geometry), ("version_info.json", module),
                            ("factor_info.json", [{"sid": 0, "gid": 101}, {"sid": 9, "gid": 201}])):
            (self.source / name).write_bytes(exporter.encoded(value))
        cv2.imwrite(str(self.source / "factor.png"), np.zeros((150, 100, 3), dtype=np.uint8))
        (self.source / "model.onnx").write_bytes(b"mock inference")
        (self.root / "master").mkdir()
        self.master = self.root / "master/master.sqlite3"
        with closing(sqlite3.connect(self.master)) as db, db:
            db.execute("CREATE TABLE factor(factor_id, factor_group_id, stars, name_ko)")
            db.executemany("INSERT INTO factor VALUES(?,?,?,?)", [
                (101, 1, 1, "가○"), (102, 1, 2, "가○"), (103, 1, 3, "가○"),
                (201, 2, 1, "다른"), (202, 2, 2, "다른"),
            ])
            db.execute("CREATE TABLE master_snapshot(schema_version)")
            db.execute("INSERT INTO master_snapshot VALUES(1)")
        self.diagnostics = self.root / "diagnostics"
        ocr_args = argparse.Namespace(capture=self.source, factor_info=self.source / "factor_info.json",
            module_version=self.source / "version_info.json", model=self.source / "model.onnx",
            master=self.master, master_sha256=kr.digest(self.master),
            factor_info_sha256=kr.digest(self.source / "factor_info.json"), output=self.diagnostics)
        with patch.object(kr, "recognize", return_value=[("가ㅇ", .8)] * 3), redirect_stdout(io.StringIO()):
            self.assertEqual(kr.run(ocr_args), 2)
        # Model inference is mocked; use the supported model identity in this synthetic diagnostic.
        diagnostic_path = self.diagnostics / "diagnostic.json"
        diagnostic = kr.read_json(diagnostic_path)
        diagnostic["inputs_sha256"]["model"] = kr.MODEL_SHA256
        diagnostic_path.write_bytes(exporter.encoded(diagnostic))
        self.args = argparse.Namespace(capture=self.source, diagnostics=self.diagnostics, master=self.master,
            master_sha256=kr.digest(self.master), factor_info=self.source / "factor_info.json",
            factor_info_sha256=kr.digest(self.source / "factor_info.json"),
            module_version=self.source / "version_info.json", review=self.root / "review.json",
            output=self.root / "final" / "record-kr.json", evidence_output=self.root / "export-evidence",
            replace_sha256=None)
        self.ctx = exporter.load_context(self.args)
        self.review = exporter.review_template(self.ctx)
        self.review["reviewer"] = "Synthetic independent pixel reviewer"
        self.review["coverage"] = {**{key: True for key in exporter.COVERAGE},
                                   "evidence": "Synthetic full-image/group/completeness fixture inspected"}
        for row in self.review["rows"]:
            row.update(decision="verified", observed_name="가○", master_name="가○", star=2,
                       app_sid=0, factor_id=102, factor_group_id=1,
                       evidence="Synthetic row name and two stars independently checked")
        self.save_review()

    def save_review(self, review=None):
        self.args.review.write_bytes(exporter.encoded(self.review if review is None else review))

    def prior_output(self):
        self.args.output.parent.mkdir(exist_ok=True)
        self.args.output.write_bytes(b"previous validated output bytes")
        self.args.replace_sha256 = kr.digest(self.args.output)
        return self.args.output.read_bytes()

    def test_full_output_sid_zero_legacy_and_unknown_fields_preserved(self):
        before = {p: kr.digest(p) for p in self.source.iterdir()}
        result = exporter.export(self.args)
        self.assertTrue(result["completed"])
        self.assertEqual(result["verified_rows"], 3)
        derived = exporter.read_json(self.args.output)
        expected = copy.deepcopy(self.record)
        expected["metadata"]["region"] = "KR"
        expected["factors"] = {g: [{"id": 0, "star": 2}] for g in kr.GROUPS}
        self.assertEqual(exporter.canonical(derived), exporter.canonical(expected))
        self.assertEqual(derived["metadata"]["format_version"], "1.0.0")
        self.assertEqual({p: kr.digest(p) for p in self.source.iterdir()}, before)
        receipt = exporter.read_json(self.args.evidence_output / "comparison.json")
        self.assertEqual(receipt["comparison_counts"], {"matched": 0, "corrected": 3, "unresolved": 0, "error": 0})
        self.assertEqual(receipt["output_sha256"], kr.digest(self.args.output))
        self.assertTrue(all(r["kr"]["id"] == 0 for r in receipt["rows"]))
        self.assertFalse(kr.read_json(self.diagnostics / "diagnostic.json")["completed"])

    def test_preparation_is_unreviewed_and_refuses_reuse(self):
        self.args.review = self.root / "new-review.json"
        result = exporter.prepare_review(self.args)
        self.assertFalse(result["completed"])
        pending = exporter.read_json(self.args.review)
        self.assertTrue(all(r["decision"] == "unreviewed" for r in pending["rows"]))
        with self.assertRaises(ValueError):
            exporter.export(self.args)
        with self.assertRaises(FileExistsError):
            exporter.prepare_review(self.args)
        self.assertFalse(self.args.output.exists())

    def test_missing_duplicate_reordered_unreviewed_and_uncovered_rows_refused(self):
        prior = self.prior_output()
        for mode in ("missing", "extra", "duplicate", "reorder", "unreviewed", "coverage", "reviewer", "evidence"):
            bad = copy.deepcopy(self.review)
            if mode == "missing":
                bad["rows"].pop()
            elif mode == "extra":
                bad["rows"].append(copy.deepcopy(bad["rows"][0]))
            elif mode == "duplicate":
                bad["rows"][1] = copy.deepcopy(bad["rows"][0])
            elif mode == "reorder":
                bad["rows"].reverse()
            elif mode == "unreviewed":
                bad["rows"][0]["decision"] = "unreviewed"
            elif mode == "coverage":
                bad["coverage"]["group_boundaries"] = False
            elif mode == "reviewer":
                bad["reviewer"] = ""
            else:
                bad["rows"][0]["evidence"] = ""
            self.save_review(bad)
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                exporter.export(self.args)
            self.assertEqual(self.args.output.read_bytes(), prior)

    def test_semantic_id_star_and_alias_guards(self):
        for key, value in (("star", 0), ("star", 4), ("star", True), ("app_sid", -1), ("app_sid", 9),
                           ("factor_id", 101), ("factor_group_id", 2), ("master_name", "가ㅇ"),
                           ("observed_name", "가ㅇ")):
            bad = copy.deepcopy(self.review)
            bad["rows"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                exporter.verify_review(self.ctx, bad)

    def test_explicit_per_row_typography_observation_does_not_create_alias_policy(self):
        self.review["rows"][0].update(observed_name="다른 표기", name_difference_reason="Explicit synthetic pixel/master difference reviewed")
        _, rows = exporter.verify_review(self.ctx, self.review)
        self.assertEqual(rows[0]["observed_name"], "다른 표기")
        self.assertEqual(rows[0]["master_name"], "가○")
        self.assertEqual(kr.Resolver(list(self.ctx.factors.values()), [{"sid": 0, "gid": 101}]).candidates("가ㅇ", 2)[1], "unresolved")

    def test_stale_or_mixed_bindings_and_coordinates_refused(self):
        for mode in ("source", "diagnostic", "tool", "coords", "crop"):
            bad = copy.deepcopy(self.review)
            if mode == "source":
                bad["bindings"]["inputs_sha256"]["record.json"] = "0" * 64
            elif mode == "diagnostic":
                bad["bindings"]["diagnostic_sha256"] = "0" * 64
            elif mode == "tool":
                bad["bindings"]["tool_sha256"]["kr_factor_export.py"] = "0" * 64
            elif mode == "coords":
                bad["rows"][0]["name_rect"][0] += 1
            else:
                bad["rows"][0]["name_crop_sha256"] = "0" * 64
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                exporter.verify_review(self.ctx, bad)

    def test_source_and_pixel_mutations_refused(self):
        for name in ("record.json", "factor.png"):
            path = self.source / name
            original = path.read_bytes()
            path.write_bytes(original + b"changed")
            with self.subTest(name=name), self.assertRaises(ValueError):
                exporter.load_context(self.args)
            path.write_bytes(original)
        crop = self.diagnostics / "crops/self-001-name.png"
        cv2.imwrite(str(crop), np.ones((10, 20, 3), dtype=np.uint8))
        with self.assertRaisesRegex(ValueError, "pixels differ"):
            exporter.load_context(self.args)

    def test_pins_required_and_ambiguous_sid_refused(self):
        old = self.args.master_sha256
        self.args.master_sha256 = "0" * 64
        with self.assertRaises(ValueError):
            exporter.load_context(self.args)
        self.args.master_sha256 = old
        self.args.factor_info_sha256 = "0" * 64
        with self.assertRaises(ValueError):
            exporter.load_context(self.args)
        self.ctx.resolver.sids[1].append(7)
        with self.assertRaises(ValueError):
            exporter.verify_review(self.ctx, self.review)

    def test_existing_output_requires_exact_replacement_pin(self):
        prior = self.prior_output()
        for pin in (None, "0" * 64):
            self.args.replace_sha256 = pin
            with self.subTest(pin=pin), self.assertRaises(ValueError):
                exporter.export(self.args)
            self.assertEqual(self.args.output.read_bytes(), prior)
        self.args.replace_sha256 = kr.digest(self.args.output)
        self.assertTrue(exporter.export(self.args)["completed"])
        self.assertNotEqual(self.args.output.read_bytes(), prior)

    def test_disk_flush_failure_preserves_prior_output(self):
        prior = self.prior_output()
        with patch.object(exporter.os, "fsync", side_effect=OSError("injected disk failure")):
            with self.assertRaises(OSError):
                exporter.export(self.args)
        self.assertEqual(self.args.output.read_bytes(), prior)
        self.assertFalse(list(self.args.output.parent.glob(".record-kr-stage-*")))

    def test_staged_readback_failure_preserves_prior_output(self):
        prior = self.prior_output()
        original = exporter.read_json
        def broken_stage(path):
            return {} if Path(path).name.startswith(".record-kr-stage-") else original(path)
        with patch.object(exporter, "read_json", side_effect=broken_stage):
            with self.assertRaises(ValueError):
                exporter.export(self.args)
        self.assertEqual(self.args.output.read_bytes(), prior)

    def test_replace_failure_preserves_prior_output(self):
        prior = self.prior_output()
        with patch.object(exporter.os, "replace", side_effect=PermissionError("injected replace failure")):
            with self.assertRaises(PermissionError):
                exporter.export(self.args)
        self.assertEqual(self.args.output.read_bytes(), prior)
        self.assertFalse(list(self.args.output.parent.glob(".record-kr-stage-*")))
        self.assertTrue((self.args.evidence_output / "comparison.json").exists())

    def test_evidence_write_failure_preserves_prior_output(self):
        prior = self.prior_output()
        original = Path.open
        def broken_evidence(path, *args, **kwargs):
            if path.name == "comparison.json" and "x" in (args[0] if args else kwargs.get("mode", "r")):
                raise PermissionError("injected evidence failure")
            return original(path, *args, **kwargs)
        with patch.object(Path, "open", broken_evidence):
            with self.assertRaises(PermissionError):
                exporter.export(self.args)
        self.assertEqual(self.args.output.read_bytes(), prior)

    def test_lock_collision_refuses_second_writer(self):
        prior = self.prior_output()
        lock = self.args.output.with_name(".record-kr.json.lock")
        lock.write_text("other writer", encoding="ascii")
        with self.assertRaises(FileExistsError):
            exporter.export(self.args)
        self.assertEqual(lock.read_text(encoding="ascii"), "other writer")
        self.assertEqual(self.args.output.read_bytes(), prior)

    def test_commit_rechecks_source_review_and_output(self):
        for mode in ("source", "review", "output"):
            prior = self.prior_output()
            self.args.evidence_output = self.root / ("evidence-" + mode)
            original_unchanged = self.ctx.unchanged
            def race():
                if mode == "source":
                    path = self.source / "record.json"
                    path.write_bytes(path.read_bytes() + b" ")
                elif mode == "review":
                    self.args.review.write_bytes(self.args.review.read_bytes() + b" ")
                else:
                    self.args.output.write_bytes(b"another writer result")
                original_unchanged()
            with patch.object(exporter, "load_context", return_value=self.ctx), patch.object(self.ctx, "unchanged", side_effect=race):
                with self.subTest(mode=mode), self.assertRaises(ValueError):
                    exporter.export(self.args)
            expected = b"another writer result" if mode == "output" else prior
            self.assertEqual(self.args.output.read_bytes(), expected)
            (self.source / "record.json").write_bytes(exporter.encoded(self.record))
            self.save_review()

    def test_unapproved_paths_shapes_types_and_upgrade_refused(self):
        good = exporter.derived_record(self.ctx, exporter.verify_review(self.ctx, self.review)[0])
        for mode in ("format", "nonfactor", "extra", "count", "type"):
            bad = copy.deepcopy(good)
            if mode == "format":
                bad["metadata"]["format_version"] = "2.0.0"
            elif mode == "nonfactor":
                bad["future_extension"]["copied"][0] = False
            elif mode == "extra":
                bad["provenance"] = {}
            elif mode == "count":
                bad["factors"]["self"].append({"id": 0, "star": 2})
            else:
                bad["factors"]["self"][0]["id"] = False
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                exporter.validate_allowed_changes(self.record, bad)

    def test_reviewed_star_changes_use_actual_selected_star_row(self):
        self.review["rows"][0].update(star=1, factor_id=101)
        self.review["rows"][1].update(star=3, factor_id=103)
        accepted, comparison = exporter.verify_review(self.ctx, self.review)
        derived = exporter.derived_record(self.ctx, accepted)
        self.assertEqual([derived["factors"][g][0]["star"] for g in kr.GROUPS], [1, 3, 2])
        self.assertTrue(all(r["status"] == "corrected" for r in comparison))

    def test_duplicate_keys_nonfinite_and_incomplete_source_refused(self):
        path = self.root / "malformed.json"
        for data in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            path.write_text(data, encoding="utf-8")
            with self.subTest(data=data), self.assertRaises(ValueError):
                exporter.read_json(path)
        bad = copy.deepcopy(self.record)
        del bad["status"]
        with self.assertRaises(ValueError):
            exporter.full_record(bad)
        for malformed in ([], {**self.review, "coverage": None},
                          {**self.review, "rows": [None] * 3}, {**self.review, "rows": {}}):
            with self.subTest(malformed=type(malformed).__name__), self.assertRaises(ValueError):
                exporter.verify_review(self.ctx, malformed)

    def test_output_and_evidence_destinations_refuse_inputs(self):
        for target in (self.source / "record.json", self.diagnostics / "record-kr.json", self.source / "nested/record-kr.json"):
            self.args.output = target
            with self.subTest(target=target), self.assertRaises(ValueError):
                exporter.export(self.args)
        self.args.output = self.root / "final/record-kr.json"
        self.args.evidence_output = self.diagnostics / "new-evidence"
        with self.assertRaises(ValueError):
            exporter.export(self.args)


if __name__ == "__main__":
    unittest.main()
