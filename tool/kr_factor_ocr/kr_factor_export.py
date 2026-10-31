# /// script
# requires-python = ">=3.12"
# dependencies = ["opencv-python-headless==4.13.0.92", "numpy==2.5.4"]
# ///
"""Review saved KR factor evidence and export a source-preserving full record."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import copy
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import sqlite3
import tempfile
import uuid

import kr_factor_ocr as kr

REQUIRED_FIELDS = {
    "metadata": dict, "trainee": dict, "evaluation_value": int, "status": dict,
    "aptitudes": dict, "skills": list, "factors": dict, "support_cards": list,
    "family": dict, "fans": int, "scenario": dict, "trained_date": str, "races": list,
}
COVERAGE = ("complete_capture", "group_boundaries", "no_missing_or_duplicate_rows")
RECORD_TYPES = ("Standard", "InheritanceOnly", "FriendStandard", "FriendInheritance")


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def constant(_):
        raise ValueError("Non-finite JSON number")

    return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=pairs, parse_constant=constant)


def text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Review text, attribution and evidence must be nonempty")
    return value


def source_fields(value, required, path, optional=None):
    if type(value) is not dict:
        raise ValueError(f"Expected a source object: {path}")
    for key, kind in required.items():
        if key not in value or type(value[key]) is not kind:
            raise ValueError(f"Missing or invalid source field: {path}.{key}")
    for key, kind in (optional or {}).items():
        if key in value and value[key] is not None and type(value[key]) is not kind:
            raise ValueError(f"Invalid optional source field: {path}.{key}")


def source_character(value, path):
    source_fields(value, dict.fromkeys(("icon", "character", "card", "rank"), int), path,
                  {"record_type": str})
    if value.get("record_type") is not None and value["record_type"] not in RECORD_TYPES:
        raise ValueError(f"Unsupported source record type: {path}.record_type")


def full_record(record):
    # Required/optional shape follows native/src/chara_detail/chara_detail_record.h
    # and lib/src/chara_detail/chara_detail_record.dart; no values are defaulted or converted.
    source_fields(record, REQUIRED_FIELDS, "record")
    metadata = record["metadata"]
    source_fields(metadata, {**dict.fromkeys(("format_version", "region", "trainer_id", "captured_date",
                                             "recognizer_version", "stage"), str),
                             "record_id": dict, "strategy": int}, "metadata",
                  {"relation_bonus": int, "record_type": str})
    for key in ("format_version", "region", "recognizer_version"):
        text(metadata[key])
    if metadata["stage"] != "active":
        raise ValueError("Unsupported source record stage")
    if metadata.get("record_type") is not None and metadata["record_type"] not in RECORD_TYPES:
        raise ValueError("Unsupported source record type: metadata.record_type")
    source_fields(metadata["record_id"], {"self": str}, "metadata.record_id", {"parent1": str, "parent2": str})
    source_character(record["trainee"], "trainee")
    source_fields(record["status"], dict.fromkeys(("speed", "stamina", "power", "guts", "intelligence"), int),
                  "status")
    source_fields(record["aptitudes"], dict.fromkeys(("ground", "distance", "style"), dict), "aptitudes")
    for group, keys in (("ground", ("turf", "dirt")),
                        ("distance", ("short_range", "mile_range", "middle_range", "long_range")),
                        ("style", ("lead_pace", "with_pace", "off_pace", "late_charge"))):
        source_fields(record["aptitudes"][group], dict.fromkeys(keys, int), f"aptitudes.{group}")
    for i, skill in enumerate(record["skills"]):
        source_fields(skill, {"id": int}, f"skills[{i}]", {"level": int})
    source_fields(record["factors"], dict.fromkeys(kr.GROUPS, list), "factors")
    for group in kr.GROUPS:
        for i, factor in enumerate(record["factors"][group]):
            source_fields(factor, {"id": int, "star": int}, f"factors.{group}[{i}]")
    if len(record["support_cards"]) != 6:
        raise ValueError("Expected six original support-card entries")
    for i, card in enumerate(record["support_cards"]):
        source_fields(card, dict.fromkeys(("id", "rank", "level"), int), f"support_cards[{i}]")
    source_fields(record["family"], {"parent1": dict, "parent2": dict}, "family")
    for group in ("parent1", "parent2"):
        parent = record["family"][group]
        source_fields(parent, dict.fromkeys(("self", "parent1", "parent2"), dict), f"family.{group}",
                      {"rental": bool})
        for key in ("self", "parent1", "parent2"):
            source_character(parent[key], f"family.{group}.{key}")
    source_fields(record["scenario"], {"id": int}, "scenario")
    race_keys = ("title", "place", "ground", "distance", "variation", "weather", "strategy", "turn", "position")
    for i, race in enumerate(record["races"]):
        source_fields(race, dict.fromkeys(race_keys, int), f"races[{i}]")


def identity(row):
    return {key: row[key] for key in ("group", "index", "name_rect", "star_rect")}


@dataclass
class Context:
    record: dict
    rows: list
    resolver: kr.Resolver
    factors: dict
    bindings: dict
    paths: dict
    hashes: dict
    master: Path
    master_state: dict
    crop_paths: list
    input_dirs: list

    def unchanged(self):
        if self.hashes != {key: kr.digest(path) for key, path in self.paths.items()}:
            raise ValueError("An input or crop changed during export")
        if self.master_state != master_state(self.master):
            raise ValueError("Master changed during export")


def master_state(path):
    files = [path] + [p for p in (Path(str(path) + "-wal"), Path(str(path) + "-shm")) if p.exists()]
    return {str(p): kr.digest(p) for p in files}


def load_context(args):
    import cv2
    import numpy as np

    capture, diagnostics = args.capture.resolve(), args.diagnostics.resolve()
    paths = {n: capture / n for n in ("record.json", "prediction.json", "factor.json", "factor.png")}
    paths.update({"factor_info.json": args.factor_info.resolve(), "version_info.json": args.module_version.resolve()})
    hashes = {key: kr.digest(path) for key, path in paths.items()}
    if hashes["factor_info.json"] != args.factor_info_sha256.lower():
        raise ValueError("Module factor metadata pin mismatch")
    record = read_json(paths["record.json"])
    full_record(record)
    module = read_json(paths["version_info.json"])
    for key in ("region", "recognizer_version"):
        if module[key] != record["metadata"][key]:
            raise ValueError("Module/record identity mismatch")
    paths["diagnostic"] = diagnostics / "diagnostic.json"
    hashes["diagnostic"] = kr.digest(paths["diagnostic"])
    diagnostic = read_json(paths["diagnostic"])
    if type(diagnostic["diagnostic_version"]) is not int or diagnostic["diagnostic_version"] != 1:
        raise ValueError("Unsupported diagnostic version")
    for key in hashes:
        if key != "diagnostic" and diagnostic["inputs_sha256"].get(key) != hashes[key]:
            raise ValueError("Diagnostic/source pin mismatch")
    if (diagnostic["model_sha256"] != kr.MODEL_SHA256
            or diagnostic["inputs_sha256"].get("model") != kr.MODEL_SHA256):
        raise ValueError("Unsupported diagnostic OCR model")
    if canonical(diagnostic["source_metadata"]) != canonical(record["metadata"]):
        raise ValueError("Diagnostic record metadata mismatch")
    if canonical(diagnostic["module"]) != canonical(module):
        raise ValueError("Diagnostic module metadata mismatch")
    image = cv2.imdecode(np.frombuffer(paths["factor.png"].read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Cannot decode original factor image")
    height, width = image.shape[:2]
    rows = kr.capture_rows(record, read_json(paths["prediction.json"]), read_json(paths["factor.json"]), width, height)
    if len(diagnostic["rows"]) != len(rows):
        raise ValueError("Diagnostic row count mismatch")
    crop_paths = []
    row_bindings = []
    for row, observed in zip(rows, diagnostic["rows"]):
        for key in (*identity(row), "baseline_sid", "star"):
            if canonical(observed[key]) != canonical(row[key]):
                raise ValueError("Diagnostic alignment mismatch")
        if (not isinstance(observed["raw_text"], str) or type(observed["score"]) not in (int, float)
                or not math.isfinite(observed["score"]) or not 0 <= observed["score"] <= 1):
            raise ValueError("Invalid diagnostic OCR observation")
        row.update(raw_text=observed["raw_text"], score=observed["score"])
        binding = identity(row)
        for label, rect in (("name", row["name_rect"]), ("star", row["star_rect"])):
            relative = f"crops/{row['group']}-{row['index']:03d}-{label}.png"
            key = "crop" if label == "name" else "star_crop"
            if observed[key] != relative:
                raise ValueError("Unexpected diagnostic crop path")
            path = (diagnostics / relative).resolve()
            if diagnostics not in path.parents:
                raise ValueError("Crop escapes diagnostic directory")
            crop_key = relative
            paths[crop_key] = path
            hashes[crop_key] = kr.digest(path)
            saved = cv2.imdecode(np.frombuffer(path.read_bytes(), dtype=np.uint8), cv2.IMREAD_COLOR)
            x, y, right, bottom = rect
            if saved is None or not np.array_equal(saved, image[y:bottom, x:right]):
                raise ValueError("Diagnostic crop pixels differ from original")
            binding[label + "_crop_sha256"] = hashes[crop_key]
            crop_paths.append(path)
        row_bindings.append(binding)
    master_path = args.master.resolve()
    state = master_state(master_path)
    factors, provenance = kr.load_master(master_path, args.master_sha256)
    if provenance["snapshot"] != diagnostic["master"]["snapshot"]:
        raise ValueError("Diagnostic master snapshot mismatch")
    if args.master_sha256.lower() not in diagnostic["master"]["files"].values():
        raise ValueError("Diagnostic master pin mismatch")
    resolver = kr.Resolver(factors, read_json(paths["factor_info.json"]))
    bindings = {
        "inputs_sha256": {key: hashes[key] for key in diagnostic["inputs_sha256"] if key in hashes},
        "diagnostic_sha256": hashes["diagnostic"], "model_sha256": kr.MODEL_SHA256,
        "master_sha256": args.master_sha256.lower(), "master_snapshot": provenance["snapshot"],
        "tool_sha256": {"kr_factor_ocr.py": kr.digest(Path(kr.__file__)),
                        "kr_factor_export.py": kr.digest(Path(__file__))},
        "rows": row_bindings,
    }
    for name, path in (("kr_factor_ocr.py", Path(kr.__file__)), ("kr_factor_export.py", Path(__file__))):
        paths["tool:" + name] = path.resolve()
        hashes["tool:" + name] = bindings["tool_sha256"][name]
    ctx = Context(record, rows, resolver, {f["factor_id"]: f for f in factors}, bindings,
                  paths, hashes, master_path, state, crop_paths,
                  [capture, diagnostics, master_path.parent, paths["factor_info.json"].parent,
                   paths["version_info.json"].parent])
    ctx.unchanged()
    return ctx


def review_template(ctx):
    rows = []
    for source, binding in zip(ctx.rows, ctx.bindings["rows"]):
        rows.append({**binding, "decision": "unreviewed", "observed_name": None, "master_name": None,
                     "star": None, "app_sid": None, "factor_id": None, "factor_group_id": None,
                     "name_difference_reason": "", "evidence": "",
                     "raw_ocr": source["raw_text"], "baseline_sid": source["baseline_sid"],
                     "baseline_star": source["star"]})
    return {"review_version": 1, "bindings": ctx.bindings, "reviewer": "",
            "coverage": {**{key: False for key in COVERAGE}, "evidence": ""}, "rows": rows}


def verify_review(ctx, review):
    if not isinstance(review, dict) or not isinstance(review.get("coverage"), dict):
        raise ValueError("Review and coverage must be JSON objects")
    if type(review["review_version"]) is not int or review["review_version"] != 1:
        raise ValueError("Unsupported review version")
    if canonical(review["bindings"]) != canonical(ctx.bindings):
        raise ValueError("Stale or mixed-capture review bindings")
    reviewer = text(review["reviewer"])
    if any(review["coverage"].get(key) is not True for key in COVERAGE):
        raise ValueError("Capture completeness and group coverage require explicit review")
    text(review["coverage"]["evidence"])
    decisions = review["rows"]
    if not isinstance(decisions, list) or len(decisions) != len(ctx.rows):
        raise ValueError("Review has missing/extra rows")
    accepted, comparison = [], []
    for row, binding, decision in zip(ctx.rows, ctx.bindings["rows"], decisions):
        if not isinstance(decision, dict):
            raise ValueError("Each reviewed row must be a JSON object")
        for key, value in binding.items():
            if canonical(decision[key]) != canonical(value):
                raise ValueError("Review row/crop/order mismatch")
        if decision["decision"] not in ("verified", "confirmed"):
            raise ValueError("Every factor must be independently verified or explicitly confirmed")
        evidence = text(decision["evidence"])
        observed_name, master_name = text(decision["observed_name"]), text(decision["master_name"])
        if observed_name != master_name:
            text(decision["name_difference_reason"])
        sid, star = kr.integer(decision["app_sid"]), kr.integer(decision["star"], 1)
        fid, group = kr.integer(decision["factor_id"]), kr.integer(decision["factor_group_id"])
        if star > 3:
            raise ValueError("Reviewed stars must be 1 through 3")
        actual = ctx.factors.get(fid)
        if actual is None or (actual["factor_group_id"], actual["stars"], actual["name_ko"]) != (group, star, master_name):
            raise ValueError("Reviewed master name/star/ID chain is invalid")
        if ctx.resolver.sids.get(group) != [sid]:
            raise ValueError("Reviewed app SID is missing or ambiguous in the pinned mapping")
        matched = row["baseline_sid"] == sid and row["star"] == star
        accepted.append({"id": sid, "star": star})
        comparison.append({**identity(row), "status": "matched" if matched else "corrected",
                           "jp": {"id": row["baseline_sid"], "star": row["star"]},
                           "kr": {"id": sid, "star": star}, "raw_ocr": row["raw_text"],
                           "observed_name": observed_name, "master_name": master_name,
                           "factor_id": fid, "factor_group_id": group, "reviewer": reviewer,
                           "decision": decision["decision"], "evidence": evidence,
                           "name_difference_reason": decision["name_difference_reason"]})
    return accepted, comparison


def validate_allowed_changes(original, derived):
    def visit(a, b, path=()):
        allowed = (path == ("metadata", "region") or
                   len(path) == 4 and path[0] == "factors" and path[1] in kr.GROUPS
                   and type(path[2]) is int and path[3] in ("id", "star"))
        if type(a) is not type(b):
            raise ValueError("Derived record changed a source JSON type")
        if isinstance(a, dict):
            if a.keys() != b.keys():
                raise ValueError("Derived record changed source JSON keys")
            for key in a:
                visit(a[key], b[key], (*path, key))
        elif isinstance(a, list):
            if len(a) != len(b):
                raise ValueError("Derived record changed a source array length")
            for i, (left, right) in enumerate(zip(a, b)):
                visit(left, right, (*path, i))
        elif canonical(a) != canonical(b) and not allowed:
            raise ValueError("Derived record changed an unapproved source path")

    visit(original, derived)
    if derived["metadata"]["region"] != "KR":
        raise ValueError("Derived region must identify the adopted KR game source")


def derived_record(ctx, accepted):
    result = copy.deepcopy(ctx.record)
    result["metadata"]["region"] = "KR"
    offset = 0
    for group in kr.GROUPS:
        for factor in result["factors"][group]:
            factor.update(accepted[offset])
            offset += 1
    if offset != len(accepted):
        raise ValueError("Accepted row count mismatch")
    validate_allowed_changes(ctx.record, result)
    return result


@contextmanager
def output_lock(target):
    lock = target.with_name("." + target.name + ".lock")
    token = uuid.uuid4().hex
    with lock.open("x", encoding="ascii") as stream:
        stream.write(token)
    try:
        yield
    finally:
        try:
            if lock.read_text(encoding="ascii") == token:
                lock.unlink()
        except OSError:
            # A stale lock prevents later writers; it never justifies bypassing one.
            pass


def destination(args, ctx):
    raw = args.output.absolute()
    if raw.is_symlink():
        raise ValueError("A derived-file symlink is not a supported destination")
    target = raw.resolve()
    if target.name != "record-kr.json":
        raise ValueError("The derived filename must be record-kr.json")
    if any(target == p or p in target.parents for p in ctx.input_dirs[1:]):
        # The exact derived sibling is allowed even when module metadata accompanies the capture.
        if target.parent != args.capture.resolve():
            raise ValueError("Derived output must not be inside master/module/diagnostic directories")
    if args.capture.resolve() in target.parents and target.parent != args.capture.resolve():
        raise ValueError("Only the exact derived sibling is allowed inside capture inputs")
    if target in ctx.paths.values() or target == ctx.master or target == args.review.resolve():
        raise ValueError("Derived output would replace an input")
    return target


def export(args):
    ctx = load_context(args)
    review_path = args.review.resolve()
    review_hash = kr.digest(review_path)
    review = read_json(review_path)
    accepted, comparison = verify_review(ctx, review)
    derived = derived_record(ctx, accepted)
    target = destination(args, ctx)
    evidence = args.evidence_output.resolve()
    if any(evidence == p or p in evidence.parents for p in ctx.input_dirs):
        raise ValueError("Export evidence requires a new directory outside inputs")
    if evidence == target or evidence == target.parent or evidence == review_path or evidence.exists():
        raise FileExistsError("Use a fresh export-evidence directory")
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = None
    with output_lock(target):
        existing = kr.digest(target) if target.exists() else None
        expected = args.replace_sha256.lower() if args.replace_sha256 else None
        if existing != expected:
            raise ValueError("Existing output needs its exact --replace-sha256; absent output needs no replacement pin")
        try:
            fd, name = tempfile.mkstemp(prefix=".record-kr-stage-", suffix=".json", dir=target.parent)
            stage = Path(name)
            with os.fdopen(fd, "wb") as stream:
                stream.write(encoded(derived))
                stream.flush()
                os.fsync(stream.fileno())
            staged = read_json(stage)
            if canonical(staged) != canonical(derived):
                raise ValueError("Staged record read-back mismatch")
            validate_allowed_changes(ctx.record, staged)
            output_hash = kr.digest(stage)
            receipt = {
                "receipt_version": 1, "artifact_kind": "validated_export_receipt",
                "output_sha256": output_hash, "review_sha256": review_hash, "bindings": ctx.bindings,
                "source_metadata": ctx.record["metadata"], "output_region": "KR",
                "nonfactor_values": "Copied unchanged; unverified for Korean-client accuracy",
                "coverage": review["coverage"], "reviewer": review["reviewer"],
                "comparison_counts": {s: sum(r["status"] == s for r in comparison)
                                      for s in ("matched", "corrected", "unresolved", "error")},
                "rows": comparison,
                "publication_note": "This immutable receipt validates the bytes named by output_sha256. "
                                    "Its presence alone does not prove final-path publication; match the output hash.",
            }
            evidence.mkdir(parents=True, exist_ok=False)
            for filename, value in (("review.json", review), ("comparison.json", receipt)):
                path = evidence / filename
                with path.open("xb") as stream:
                    stream.write(encoded(value))
                    stream.flush()
                    os.fsync(stream.fileno())
                if canonical(read_json(path)) != canonical(value):
                    raise ValueError("Evidence read-back failed")
            ctx.unchanged()
            if kr.digest(review_path) != review_hash:
                raise ValueError("Review changed during export")
            if (kr.digest(target) if target.exists() else None) != existing:
                raise ValueError("Derived output changed during export")
            # Commit last: every source/decision/identity/shape and staged byte is checked.
            os.replace(stage, target)
            stage = None
        finally:
            if stage is not None:
                stage.unlink(missing_ok=True)
    return {"completed": True, "verified_rows": len(accepted), "output_sha256": output_hash,
            "comparison_counts": receipt["comparison_counts"]}


def prepare_review(args):
    ctx = load_context(args)
    target = args.review.resolve()
    if target in ctx.paths.values() or any(target == p or p in target.parents for p in ctx.input_dirs):
        raise ValueError("Review file must be outside input directories")
    value = review_template(ctx)
    ctx.unchanged()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(encoded(value))
    if canonical(read_json(target)) != canonical(value):
        raise ValueError("Review template read-back failed")
    return {"completed": False, "status": "unresolved", "review_rows": len(ctx.rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare-review", "export"):
        command = commands.add_parser(name)
        for option in ("capture", "diagnostics", "master", "factor-info", "module-version", "review"):
            command.add_argument("--" + option, type=Path, required=True)
        command.add_argument("--master-sha256", required=True)
        command.add_argument("--factor-info-sha256", required=True)
        if name == "export":
            command.add_argument("--output", type=Path, required=True)
            command.add_argument("--evidence-output", type=Path, required=True)
            command.add_argument("--replace-sha256")
    args = parser.parse_args()
    try:
        result = prepare_review(args) if args.command == "prepare-review" else export(args)
        print(json.dumps(result))
        return 2 if args.command == "prepare-review" else 0
    except (ValueError, KeyError, TypeError, IndexError, OSError, sqlite3.Error, ImportError) as error:
        print(json.dumps({"completed": False, "status": "error", "error_type": type(error).__name__,
                          "message": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
