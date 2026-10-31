# /// script
# requires-python = ">=3.11"
# dependencies = ["rapidocr==3.10.0", "onnxruntime==1.31.1", "opencv-python-headless==4.13.0.92", "numpy==2.5.4"]
# ///
"""Independent KR factor candidate diagnostics. Never emits a completed game record."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import closing
import difflib
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unicodedata

GROUPS = ("self", "parent1", "parent2")
MODEL_SHA256 = "cd6e2ea50f6943ca7271eb8c56a877a5a90720b7047fe9c41a2e541a25773c9b"


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError("Expected a non-negative integer")
    return value


def normalize(text):
    # Candidate lookup only; punctuation is deliberately retained.
    return "".join(unicodedata.normalize("NFC", text).split()).casefold()


def rect_pixels(rect, width, height):
    points = [rect["top_left"], rect["bottom_right"]]
    for p in points:
        if p["anchor"] != {"h": "ScreenStart", "v": "ScreenStart"}:
            raise ValueError("Only absolute ScreenStart geometry is supported")
        integer(p["x"])
        integer(p["y"])
    x, y = points[0]["x"], points[0]["y"]
    right, bottom = points[1]["x"], points[1]["y"]
    if not (x < right <= width and y < bottom <= height):
        raise ValueError("Empty or out-of-bounds crop")
    return [x, y, right, bottom]


def capture_rows(record, prediction, geometry, width, height):
    if rect_pixels(geometry["intersection"], width, height) != [0, 0, width, height]:
        raise ValueError("Unsupported non-full-image factor intersection")
    factors = record["factors"]
    if set(factors) != set(GROUPS):
        raise ValueError("Expected exactly three factor groups")
    entries = [p for p in prediction["factor_tab"] if p["model"] in ("factor", "factor_rank")]
    total = sum(len(factors[g]) for g in GROUPS)
    if len(entries) != 2 * total or any(not factors[g] for g in GROUPS):
        raise ValueError("Missing/extra predictions or empty factor group")
    rows, seen = [], set()
    previous = None
    offset = 0
    for group in GROUPS:
        for index, baseline in enumerate(factors[group], 1):
            name, rank = entries[2 * offset:2 * offset + 2]
            offset += 1
            if name["model"] != "factor" or rank["model"] != "factor_rank":
                raise ValueError("Unexpected prediction pairing/order")
            sid = integer(baseline["id"])
            star = integer(baseline["star"], 1)
            if star > 3 or name["prediction"]["label"] != sid or rank["prediction"]["label"] != star - 1:
                raise ValueError("Record/prediction identity or star mismatch")
            nr = rect_pixels(name["rect"], width, height)
            sr = rect_pixels(rank["rect"], width, height)
            if tuple(nr) in seen:
                raise ValueError("Duplicated factor crop")
            seen.add(tuple(nr))
            if not (sr[1] >= nr[3] and sr[0] >= nr[0] and sr[2] <= nr[2]):
                raise ValueError("Name/star geometry mismatch")
            position = (nr[1], nr[0])
            if previous is not None and position <= previous:
                raise ValueError("Reordered factor rows")
            previous = position
            rows.append({"group": group, "index": index, "baseline_sid": sid, "star": star,
                         "name_rect": nr, "star_rect": sr})
    return rows


def load_master(path, expected_hash):
    """Query a stable private byte copy; never open the original DB with SQLite."""
    path = path.resolve()
    def state():
        files = [path] + [p for p in (Path(str(path) + "-wal"), Path(str(path) + "-shm")) if p.exists()]
        return {str(p): digest(p) for p in files}

    before = state()
    sources = [Path(p) for p in before]
    wal = Path(str(path) + "-wal")
    if wal.exists() and wal.stat().st_size:
        raise ValueError("Use a stable master snapshot with no pending WAL; never checkpoint the source")
    if before[str(path)] != expected_hash.lower():
        raise ValueError("Master SHA256 mismatch")
    with tempfile.TemporaryDirectory(prefix="umacapture-kr-master-") as tmp:
        copied = Path(tmp) / path.name
        for p in sources:
            shutil.copyfile(p, Path(tmp) / p.name)
        if before != state():
            raise ValueError("Master changed during copy")
        for p in sources:
            if digest(Path(tmp) / p.name) != before[str(p)]:
                raise ValueError("Master copy hash mismatch")
        with closing(sqlite3.connect(copied.as_uri() + "?mode=ro", uri=True)) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            factors = [dict(r) for r in db.execute(
                "SELECT factor_id,factor_group_id,stars,name_ko FROM factor ORDER BY factor_id")]
            snapshot = [dict(r) for r in db.execute("SELECT * FROM master_snapshot")]
    if before != state():
        raise ValueError("Master changed during query")
    if not factors or not snapshot:
        raise ValueError("Master factors or snapshot provenance missing")
    return factors, {"files": {Path(p).name: h for p, h in before.items()}, "snapshot": snapshot}


class Resolver:
    def __init__(self, factors, app):
        self.names = defaultdict(list)
        by_id = {}
        for f in factors:
            fid = integer(f["factor_id"])
            integer(f["factor_group_id"])
            if not 1 <= integer(f["stars"], 1) <= 3 or not isinstance(f["name_ko"], str):
                raise ValueError("Invalid master factor")
            if fid in by_id:
                raise ValueError("Duplicate master factor ID")
            by_id[fid] = f
            self.names[normalize(f["name_ko"])].append(f)
        self.sids = defaultdict(list)
        seen = set()
        for a in app:
            sid, gid = integer(a["sid"]), integer(a["gid"])
            if sid in seen:
                raise ValueError("Duplicate app SID")
            seen.add(sid)
            representative = by_id.get(gid)
            if representative is not None and representative["stars"] == 1:
                self.sids[representative["factor_group_id"]].append(sid)

    def candidates(self, text, star):
        key = normalize(text)
        exact = self.names.get(key, [])
        keys = [key] if exact else difflib.get_close_matches(key, self.names, n=5, cutoff=0.55)
        candidates = []
        for k in keys:
            for f in self.names[k]:
                if f["stars"] != star:
                    continue
                sids = self.sids.get(f["factor_group_id"], [])
                candidates.append({
                    "name_ko": f["name_ko"], "factor_id": f["factor_id"],
                    "factor_group_id": f["factor_group_id"], "star": star,
                    "app_sids": sids, "match": "normalized_exact" if k == key else "suggestion",
                })
        unique = (len(candidates) == 1 and candidates[0]["match"] == "normalized_exact"
                  and len(candidates[0]["app_sids"]) == 1)
        return candidates, "candidate_only" if unique else "unresolved"


def recognize(crops, model):
    if digest(model) != MODEL_SHA256:
        raise ValueError("Model differs from pinned Korean PP-OCRv5 artifact")
    if importlib.metadata.version("rapidocr") != "3.10.0":
        raise ValueError("RapidOCR 3.10.0 is required")
    from rapidocr import EngineType, LangRec, ModelType, OCRVersion
    from rapidocr.main import DEFAULT_CFG_PATH
    from rapidocr.ch_ppocr_rec import TextRecognizer, TextRecInput

    # Instantiate the recognition component directly. RapidOCR() also constructs
    # detector/classifier components and may download their models.
    from rapidocr.utils.parse_parameters import ParseParams
    cfg = ParseParams.load(DEFAULT_CFG_PATH)
    params = {
        "Rec.engine_type": EngineType.ONNXRUNTIME, "Rec.lang_type": LangRec.KOREAN,
        "Rec.model_type": ModelType.MOBILE, "Rec.ocr_version": OCRVersion.PPOCRV5,
        "Rec.model_path": str(model.resolve()), "Rec.rec_batch_num": 6,
        "EngineConfig.onnxruntime.intra_op_num_threads": 1,
        "EngineConfig.onnxruntime.inter_op_num_threads": 1,
    }
    cfg = ParseParams.update_batch(cfg, params)
    cfg.Rec.font_path = None
    cfg.Rec.engine_cfg = cfg.EngineConfig.onnxruntime
    cfg.Rec.model_root_dir = str(model.parent.resolve())
    output = TextRecognizer(cfg.Rec)(TextRecInput(img=crops, return_word_box=False))
    if len(output.txts) != len(crops) or len(output.scores) != len(crops):
        raise ValueError("OCR result count mismatch")
    return list(zip(output.txts, map(float, output.scores)))


def run(args):
    import cv2
    import numpy as np

    capture = args.capture.resolve()
    paths = {n: capture / n for n in ("record.json", "prediction.json", "factor.json", "factor.png")}
    paths.update({"factor_info.json": args.factor_info.resolve(), "version_info.json": args.module_version.resolve(),
                  "model": args.model.resolve()})
    output = args.output.resolve()
    protected = [capture, args.master.resolve().parent, args.factor_info.resolve().parent,
                 args.module_version.resolve().parent, args.model.resolve().parent]
    if any(output == p or p in output.parents for p in protected):
        raise ValueError("Output must be outside input directories")
    if output.exists():
        raise FileExistsError("Use a new private output directory")
    before = {n: digest(p) for n, p in paths.items()}
    if before["factor_info.json"] != args.factor_info_sha256.lower():
        raise ValueError("App factor metadata SHA256 mismatch")
    record = read_json(paths["record.json"])
    module = read_json(paths["version_info.json"])
    for key in ("region", "recognizer_version"):
        if module[key] != record["metadata"][key]:
            raise ValueError("Module/record version mismatch")
    image = cv2.imdecode(np.frombuffer(paths["factor.png"].read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Cannot decode factor.png")
    height, width = image.shape[:2]
    rows = capture_rows(record, read_json(paths["prediction.json"]), read_json(paths["factor.json"]), width, height)
    master, provenance = load_master(args.master, args.master_sha256)
    resolver = Resolver(master, read_json(paths["factor_info.json"]))
    crops = [image[r["name_rect"][1]:r["name_rect"][3], r["name_rect"][0]:r["name_rect"][2]].copy()
             for r in rows]
    observations = recognize(crops, args.model)
    for row, (text, score) in zip(rows, observations):
        if not isinstance(text, str) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Invalid OCR observation")
        candidates, status = resolver.candidates(text, row["star"])
        row.update(raw_text=text, score=score, candidates=candidates, status=status, verified=False)
        row["jp_comparison"] = (
            "candidate_sid_matches" if status == "candidate_only"
            and candidates[0]["app_sids"][0] == row["baseline_sid"]
            else "candidate_sid_differs" if status == "candidate_only" else "unresolved")
        row["crop"] = f"crops/{row['group']}-{row['index']:03d}-name.png"
        row["star_crop"] = f"crops/{row['group']}-{row['index']:03d}-star.png"
    if before != {n: digest(p) for n, p in paths.items()}:
        raise ValueError("Input changed during processing")
    report = {
        "diagnostic_version": 1, "completed": False, "verified_rows": 0,
        "limitations": [
            "All rows require independent pixel/group/star verification; candidates are not accepted IDs.",
            "Group boundaries and stars are reused from saved predictions, not independently inferred.",
            "Missing/duplicated content or wrong groups in a self-consistent capture require pixel review.",
            "No confirmation UX, automatic correction, record-kr.json or consumer contract is implemented.",
            "A dictionary match and JP agreement are not evidence of Korean recognition correctness.",
        ],
        "inputs_sha256": before, "source_metadata": record["metadata"], "module": module,
        "master": provenance, "model_sha256": MODEL_SHA256,
        "packages": {n: importlib.metadata.version(n) for n in
                     ("rapidocr", "onnxruntime", "opencv-python-headless", "numpy")},
        "counts": dict(Counter(r["status"] for r in rows)),
        "groups": {g: sum(r["group"] == g for r in rows) for g in GROUPS}, "rows": rows,
    }
    # Reserve a fresh destination; never overwrite any prior diagnostic or game record.
    output.mkdir(parents=True, exist_ok=False)
    (output / "crops").mkdir()
    for row, crop in zip(rows, crops):
        if not cv2.imwrite(str(output / row["crop"]), crop):
            raise OSError("Failed to write name crop")
        x, y, right, bottom = row["star_rect"]
        if not cv2.imwrite(str(output / row["star_crop"]), image[y:bottom, x:right]):
            raise OSError("Failed to write star crop")
    report_path = output / "diagnostic.json"
    with report_path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    if read_json(report_path) != report:
        raise ValueError("Diagnostic read-back failed")
    print(json.dumps({"completed": False, "rows": len(rows), "counts": report["counts"],
                      "groups": report["groups"]}))
    return 2  # Deliberately incomplete: no independently accepted result.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("capture", "master", "factor-info", "module-version", "model", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--master-sha256", required=True)
    parser.add_argument("--factor-info-sha256", required=True)
    args = parser.parse_args()
    try:
        return run(args)
    except (ValueError, KeyError, TypeError, OSError, sqlite3.Error, ImportError) as error:
        # Details stay local; no raw OCR or personal metadata is logged.
        print(f"KR diagnostics failed: {type(error).__name__}: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
