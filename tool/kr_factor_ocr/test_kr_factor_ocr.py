"""Deterministic integrity checks; synthetic names are not OCR accuracy evidence."""
import copy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import kr_factor_ocr as kr


def rect(x, y, width=20, height=10):
    anchor = {"h": "ScreenStart", "v": "ScreenStart"}
    return {"top_left": {"x": x, "y": y, "anchor": anchor},
            "bottom_right": {"x": x + width, "y": y + height, "anchor": anchor}}


def capture():
    record = {"factors": {g: [{"id": 0, "star": 2}] for g in kr.GROUPS}}
    entries = []
    for i in range(3):
        entries.extend([
            {"model": "factor", "rect": rect(10, 10 + 40*i), "prediction": {"label": 0}},
            {"model": "factor_rank", "rect": rect(15, 21 + 40*i, 10), "prediction": {"label": 1}},
        ])
    return record, {"factor_tab": entries}, {"intersection": rect(0, 0, 100, 150)}


class InputIntegrity(unittest.TestCase):
    def check(self, data):
        return kr.capture_rows(*data, 100, 150)

    def test_sid_zero_and_groups(self):
        rows = self.check(capture())
        self.assertEqual([r["group"] for r in rows], list(kr.GROUPS))
        self.assertTrue(all(r["baseline_sid"] == 0 and r["star"] == 2 for r in rows))

    def test_missing_extra_or_reordered_predictions(self):
        for mode in ("missing", "extra", "reordered"):
            data = capture()
            entries = data[1]["factor_tab"]
            if mode == "missing":
                entries.pop()
            elif mode == "extra":
                entries.extend(copy.deepcopy(entries[:2]))
            else:
                entries[0], entries[1] = entries[1], entries[0]
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.check(data)

    def test_duplicates_out_of_bounds_anchors_and_group_order(self):
        for mode in ("duplicate", "bounds", "anchor", "order", "rank_geometry"):
            data = capture()
            entries = data[1]["factor_tab"]
            if mode == "duplicate":
                entries[2]["rect"] = copy.deepcopy(entries[0]["rect"])
            elif mode == "bounds":
                entries[0]["rect"]["bottom_right"]["x"] = 101
            elif mode == "anchor":
                entries[0]["rect"]["top_left"]["anchor"]["h"] = "ScreenEnd"
            elif mode == "order":
                entries[2:4], entries[4:6] = entries[4:6], entries[2:4]
            else:
                entries[1]["rect"]["top_left"]["y"] = 1
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.check(data)

    def test_rank_and_record_transfer_fail_closed(self):
        for value in (0, 4, True, 1.5):
            data = capture()
            data[0]["factors"]["self"][0]["star"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.check(data)
        data = capture()
        data[0]["factors"]["self"][0]["id"] = 999
        with self.assertRaises(ValueError):
            self.check(data)

    def test_partial_intersection_and_empty_group(self):
        data = capture()
        data[2]["intersection"] = rect(0, 0, 99, 150)
        with self.assertRaises(ValueError):
            self.check(data)
        data = capture()
        data[0]["factors"]["self"] = []
        with self.assertRaises(ValueError):
            self.check(data)


class Identity(unittest.TestCase):
    def setUp(self):
        self.factors = [
            {"factor_id": 101, "factor_group_id": 1, "stars": 1, "name_ko": "가○"},
            {"factor_id": 102, "factor_group_id": 1, "stars": 2, "name_ko": "가○"},
            {"factor_id": 201, "factor_group_id": 2, "stars": 1, "name_ko": "가○＋"},
        ]
        self.app = [{"sid": 0, "gid": 101}, {"sid": 7, "gid": 201}]

    def test_explicit_star_group_and_sid_zero(self):
        candidates, status = kr.Resolver(self.factors, self.app).candidates(" 가 ○ ", 2)
        self.assertEqual(status, "candidate_only")
        self.assertEqual(candidates[0]["app_sids"], [0])
        self.assertEqual(candidates[0]["factor_id"], 102)
        self.assertEqual(candidates[0]["factor_group_id"], 1)

    def test_symbols_never_silently_corrected(self):
        resolver = kr.Resolver(self.factors, self.app)
        for name in ("가", "가ㅇ", "가O", "가○+", "가(○", "가·○"):
            with self.subTest(name=name):
                candidates, status = resolver.candidates(name, 1)
                self.assertEqual(status, "unresolved")
                self.assertTrue(all(c["match"] == "suggestion" for c in candidates))
        candidates, _ = resolver.candidates("가○＋", 1)
        self.assertEqual(candidates[0]["app_sids"], [7])

    def test_ambiguous_missing_and_duplicate_ids(self):
        app = self.app + [{"sid": 9, "gid": 101}]
        self.assertEqual(kr.Resolver(self.factors, app).candidates("가○", 1)[1], "unresolved")
        self.assertEqual(kr.Resolver(self.factors, []).candidates("가○", 1)[1], "unresolved")
        self.assertEqual(kr.Resolver(self.factors, self.app).candidates("가○", 3)[1], "unresolved")
        with self.assertRaises(ValueError):
            kr.Resolver(self.factors + self.factors[:1], self.app)
        with self.assertRaises(ValueError):
            kr.Resolver(self.factors, self.app + self.app[:1])


class MasterPreservation(unittest.TestCase):
    def test_read_only_copy_and_hash_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "master.sqlite3"
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("CREATE TABLE factor(factor_id, factor_group_id, stars, name_ko)")
                db.execute("INSERT INTO factor VALUES(101,1,1,'가')")
                db.execute("CREATE TABLE master_snapshot(schema_version)")
                db.execute("INSERT INTO master_snapshot VALUES(1)")
            before = kr.digest(path)
            rows, provenance = kr.load_master(path, before)
            self.assertEqual(rows[0]["factor_id"], 101)
            self.assertEqual(kr.digest(path), before)
            self.assertEqual(provenance["snapshot"], [{"schema_version": 1}])
            with self.assertRaises(ValueError):
                kr.load_master(path, "0" * 64)

    def test_model_hash_rejected_before_import_or_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / "wrong.onnx"
            model.write_bytes(b"wrong")
            with self.assertRaisesRegex(ValueError, "pinned"):
                kr.recognize([], model)



class DiagnosticDelivery(unittest.TestCase):
    def test_diagnostic_only_readback_and_existing_output_protection(self):
        import argparse
        import cv2
        import numpy as np
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "inputs"
            source.mkdir()
            record, prediction, geometry = capture()
            module = {"region": "JPN", "recognizer_version": "test"}
            record["metadata"] = module.copy()
            record["unverified_nonfactor"] = {"value": 77}
            for name, data in (("record.json", record), ("prediction.json", prediction),
                               ("factor.json", geometry), ("version_info.json", module),
                               ("factor_info.json", [{"sid": 0, "gid": 101}])):
                (source / name).write_text(json.dumps(data), encoding="utf-8")
            cv2.imwrite(str(source / "factor.png"), np.zeros((150, 100, 3), dtype=np.uint8))
            (source / "model.onnx").write_bytes(b"mock model")
            (source / "record-kr.json").write_bytes(b"previous good result")
            originals = {p: kr.digest(p) for p in source.iterdir()}
            args = argparse.Namespace(
                capture=source, factor_info=source / "factor_info.json",
                module_version=source / "version_info.json", model=source / "model.onnx",
                master=source / "unused.sqlite3", master_sha256="unused",
                factor_info_sha256=kr.digest(source / "factor_info.json"), output=root / "diagnostics")
            master = [{"factor_id": 101, "factor_group_id": 1, "stars": 1, "name_ko": "가"},
                      {"factor_id": 102, "factor_group_id": 1, "stars": 2, "name_ko": "가"}]
            with patch.object(kr, "load_master", return_value=(master, {})), patch.object(
                    kr, "recognize", return_value=[("가", 0.9)] * 3):
                self.assertEqual(kr.run(args), 2)
                report = kr.read_json(args.output / "diagnostic.json")
                self.assertFalse(report["completed"])
                self.assertEqual(report["verified_rows"], 0)
                self.assertTrue(all(not r["verified"] for r in report["rows"]))
                self.assertEqual(report["rows"][0]["candidates"][0]["app_sids"], [0])
                self.assertEqual(len(list((args.output / "crops").glob("*.png"))), 6)
                self.assertFalse((args.output / "record-kr.json").exists())
                before_report = kr.digest(args.output / "diagnostic.json")
                with self.assertRaises(FileExistsError):
                    kr.run(args)
                self.assertEqual(kr.digest(args.output / "diagnostic.json"), before_report)
                args.output = source / "nested-output"
                with self.assertRaises(ValueError):
                    kr.run(args)
                args.output = root / "bad-provenance"
                args.factor_info_sha256 = "0" * 64
                with self.assertRaises(ValueError):
                    kr.run(args)
                self.assertFalse(args.output.exists())
            self.assertEqual({p: kr.digest(p) for p in source.iterdir()}, originals)

    def test_pending_wal_refused_without_modification(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "master.sqlite3"
            path.write_bytes(b"not opened")
            wal = Path(str(path) + "-wal")
            wal.write_bytes(b"pending")
            with self.assertRaisesRegex(ValueError, "WAL"):
                kr.load_master(path, kr.digest(path))
            self.assertEqual(wal.read_bytes(), b"pending")



class MasterRace(unittest.TestCase):
    def test_new_wal_during_copy_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "master.sqlite3"
            path.write_bytes(b"synthetic source")
            copyfile = kr.shutil.copyfile

            def racing_copy(source, target):
                result = copyfile(source, target)
                Path(str(path) + "-wal").write_bytes(b"new concurrent WAL")
                return result

            with patch.object(kr.shutil, "copyfile", side_effect=racing_copy):
                with self.assertRaisesRegex(ValueError, "changed during copy"):
                    kr.load_master(path, kr.digest(path))


if __name__ == "__main__":
    unittest.main()
