# /// script
# requires-python = ">=3.12"
# dependencies = ["rapidocr==3.10.0", "onnxruntime==1.31.1", "opencv-python-headless==4.13.0.92", "numpy==2.5.4"]
# ///
"""JSON process boundary for the Korean factor review application. See APP_PROTOCOL.md."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import sys
import tempfile

import kr_factor_export as exporter
import kr_factor_ocr as kr

SCHEMA_VERSION = 1
COMMANDS = ("run", "load", "lookup", "save-review", "validate-review", "export")
EDITABLE_ROW = {"decision", "observed_name", "master_name", "star", "app_sid", "factor_id",
                "factor_group_id", "name_difference_reason", "evidence"}
LIMITATIONS = [
    "Candidates are unverified; every row needs independent pixel review or explicit confirmation.",
    "Confirm full capture coverage, group boundaries, and no missing or duplicate rows.",
    "Only factors are recognized in Korean; copied non-factor values remain unverified.",
    "The original Japanese record and recognition path are preserved.",
]


def absolute_path(request, key):
    value = request.get(key)
    if not isinstance(value, str) or not value.strip() or not Path(value).is_absolute():
        raise ValueError(f"{key} must be an explicit absolute local path")
    return Path(value).resolve()


def no_links(path):
    # Writes must not follow a redirected file/directory into another input/run.
    for part in (path, *path.parents):
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise ValueError("Writable paths must not contain symbolic links or junctions")


def pinned_hash(request, key):
    value = request.get(key)
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdefABCDEF" for c in value):
        raise ValueError(f"{key} must be a SHA256 hex string")
    return value.lower()


def common_args(request):
    paths = {key: absolute_path(request, key) for key in
             ("capture", "master", "factor_info", "module_version", "model", "working_dir")}
    # Check the original spelling as well as the resolved writable path.
    no_links(Path(request["working_dir"]))
    work = paths.pop("working_dir")
    protected = [paths["capture"], *(paths[key].parent for key in
                  ("master", "factor_info", "module_version", "model"))]
    if any(work == p or p in work.parents or work in p.parents for p in protected):
        raise ValueError("working_dir must be separate from capture/master/module/model inputs")
    if kr.digest(paths["model"]) != kr.MODEL_SHA256:
        raise ValueError("Model differs from the pinned Korean PP-OCRv5 artifact")
    args = argparse.Namespace(**paths, master_sha256=pinned_hash(request, "master_sha256"),
                              factor_info_sha256=pinned_hash(request, "factor_info_sha256"),
                              diagnostics=work / "diagnostics", review=work / "review.json")
    no_links(args.diagnostics)
    no_links(args.review)
    return args, work


def review_issues(ctx, review):
    """Reject corrupt drafts; return missing confirmations without inventing any."""
    template = exporter.review_template(ctx)
    if type(review) is not dict or set(review) != set(template):
        raise ValueError("Review fields differ from the prepared template")
    for key in ("review_version", "bindings"):
        if exporter.canonical(review[key]) != exporter.canonical(template[key]):
            raise ValueError("Review bindings are immutable; reload this capture")
    if not isinstance(review["reviewer"], str):
        raise ValueError("Reviewer must be text")
    coverage = review["coverage"]
    if type(coverage) is not dict or set(coverage) != set(template["coverage"]):
        raise ValueError("Coverage fields differ from the prepared template")
    if any(type(coverage[key]) is not bool for key in exporter.COVERAGE):
        raise ValueError("Coverage confirmations must be booleans")
    if not isinstance(coverage["evidence"], str):
        raise ValueError("Coverage evidence must be text")
    rows = review["rows"]
    if type(rows) is not list or len(rows) != len(template["rows"]):
        raise ValueError("Review has missing or extra rows")
    issues = []
    if not review["reviewer"].strip():
        issues.append("Provide reviewer attribution")
    for key in exporter.COVERAGE:
        if not coverage[key]:
            issues.append(f"Confirm capture coverage: {key}")
    if not coverage["evidence"].strip():
        issues.append("Provide capture coverage evidence")
    for row, source in zip(rows, template["rows"]):
        if type(row) is not dict or set(row) != set(source):
            raise ValueError("Review row fields differ from the prepared template")
        for key in set(source) - EDITABLE_ROW:
            if exporter.canonical(row[key]) != exporter.canonical(source[key]):
                raise ValueError("Review row/crop/order and original observations are immutable")
        if row["decision"] not in ("unreviewed", "verified", "confirmed"):
            raise ValueError("Unsupported row decision")
        for key in ("observed_name", "master_name", "name_difference_reason", "evidence"):
            if row[key] is not None and not isinstance(row[key], str):
                raise ValueError("Draft row text must be text or null")
        for key in ("star", "app_sid", "factor_id", "factor_group_id"):
            if row[key] is not None:
                kr.integer(row[key])
        if row["star"] is not None and not 1 <= row["star"] <= 3:
            raise ValueError("Draft stars must be 1 through 3")
        if row["decision"] == "unreviewed":
            issues.append(f"Review {row['group']}/{row['index']}")
            continue
        # Drafts may be partial, but an explicitly selected identity must be real.
        for key in ("observed_name", "master_name", "evidence"):
            exporter.text(row[key])
        if row["observed_name"] != row["master_name"]:
            exporter.text(row["name_difference_reason"])
        sid, star = kr.integer(row["app_sid"]), kr.integer(row["star"], 1)
        fid, group = kr.integer(row["factor_id"]), kr.integer(row["factor_group_id"])
        actual = ctx.factors.get(fid)
        if star > 3 or actual is None or (actual["factor_group_id"], actual["stars"], actual["name_ko"]) != (
                group, star, row["master_name"]):
            raise ValueError("Selected master name/star/ID chain is invalid")
        if ctx.resolver.sids.get(group) != [sid]:
            raise ValueError("Selected module SID is missing or ambiguous")
    if not issues:
        # The existing exporter remains authoritative for a completed review.
        exporter.verify_review(ctx, review)
    return issues


def session(ctx, args, work, review=None):
    review_hash = kr.digest(args.review)
    review = exporter.read_json(args.review) if review is None else review
    if kr.digest(args.review) != review_hash:
        raise ValueError("Review changed during read; reload")
    issues = review_issues(ctx, review)
    rows = []
    for row in ctx.rows:
        candidates, status = ctx.resolver.candidates(row["raw_text"], row["star"])
        rows.append({**row, "candidates": candidates, "status": status, "verified": False,
                     "name_crop": str(args.diagnostics / f"crops/{row['group']}-{row['index']:03d}-name.png"),
                     "star_crop": str(args.diagnostics / f"crops/{row['group']}-{row['index']:03d}-star.png")})
    ctx.unchanged()
    if kr.digest(args.review) != review_hash:
        raise ValueError("Review changed during validation; reload")
    return {"status": "needs_review" if issues else "ok", "completed": False,
            "working_dir": str(work), "diagnostics": str(args.diagnostics), "review_path": str(args.review),
            "review_sha256": review_hash, "source_image": str(args.capture / "factor.png"),
            "rows": rows, "review": review, "review_issues": issues, "ready_to_export": not issues,
            "limitations": LIMITATIONS}


def save_review(ctx, args, work, request):
    review = request.get("review")
    review_issues(ctx, review)
    expected = pinned_hash(request, "expected_review_sha256")
    staged = None
    with exporter.output_lock(args.review):
        if kr.digest(args.review) != expected:
            raise ValueError("Review draft changed; reload before saving")
        try:
            fd, name = tempfile.mkstemp(prefix=".review-stage-", suffix=".json", dir=work)
            staged = Path(name)
            with os.fdopen(fd, "wb") as stream:
                stream.write(exporter.encoded(review))
                stream.flush()
                os.fsync(stream.fileno())
            if exporter.canonical(exporter.read_json(staged)) != exporter.canonical(review):
                raise ValueError("Staged review read-back failed")
            ctx.unchanged()
            if kr.digest(args.review) != expected:
                raise ValueError("Review draft changed during save")
            os.replace(staged, args.review)
            staged = None
        finally:
            if staged is not None:
                staged.unlink(missing_ok=True)
    return session(ctx, args, work)


def lookup(request):
    master, module = absolute_path(request, "master"), absolute_path(request, "factor_info")
    if kr.digest(module) != pinned_hash(request, "factor_info_sha256"):
        raise ValueError("Module factor metadata pin mismatch")
    factors, _ = kr.load_master(master, pinned_hash(request, "master_sha256"))
    resolver = kr.Resolver(factors, exporter.read_json(module))
    query = request.get("query", "")
    if not isinstance(query, str):
        raise ValueError("query must be text")
    star = request.get("star")
    if star is not None and (type(star) is not int or not 1 <= star <= 3):
        raise ValueError("star must be 1 through 3")
    offset, limit = request.get("offset", 0), request.get("limit", 50)
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError("Invalid lookup offset/limit")
    query = kr.normalize(query)
    matches = []
    for f in factors:
        if query not in kr.normalize(f["name_ko"]) or star is not None and f["stars"] != star:
            continue
        sids = resolver.sids.get(f["factor_group_id"], [])
        matches.append({"name_ko": f["name_ko"], "factor_id": f["factor_id"],
                        "factor_group_id": f["factor_group_id"], "star": f["stars"],
                        "app_sids": sids, "selectable": len(sids) == 1})
    if kr.digest(module) != pinned_hash(request, "factor_info_sha256"):
        raise ValueError("Module factor metadata changed during lookup")
    return {"status": "ok", "completed": False, "matches": matches[offset:offset + limit],
            "total": len(matches), "offset": offset, "limit": limit}


def dispatch(command, request):
    if type(request) is not dict:
        raise ValueError("Request must be a JSON object")
    version = request.get("schema_version", SCHEMA_VERSION)
    if type(version) is not int or version != SCHEMA_VERSION:
        raise ValueError("Unsupported request schema_version")
    if command not in COMMANDS:
        raise ValueError("Unsupported command")
    if command == "lookup":
        return lookup(request)
    args, work = common_args(request)
    if command == "run":
        # Reserve a fresh run. Failed/cancelled runs remain evidence, never reused.
        work.mkdir(parents=True, exist_ok=False)
        with redirect_stdout(sys.stderr):
            result = kr.run(argparse.Namespace(**vars(args), output=args.diagnostics))
            if result != 2:
                raise ValueError("Diagnostic producer did not return needs-review")
            exporter.prepare_review(args)
    ctx = exporter.load_context(args)
    if command == "save-review":
        return save_review(ctx, args, work, request)
    value = session(ctx, args, work)
    if command != "export" or not value["ready_to_export"]:
        return value
    output, evidence = absolute_path(request, "output"), absolute_path(request, "evidence_output")
    no_links(Path(request["output"]))
    no_links(Path(request["evidence_output"]))
    if output == args.review or evidence == work or evidence in work.parents:
        raise ValueError("Export must preserve the review working directory")
    args.output, args.evidence_output = output, evidence
    args.replace_sha256 = pinned_hash(request, "replace_sha256") if request.get("replace_sha256") else None
    result = exporter.export(args)
    if not result.get("completed") or kr.digest(output) != result["output_sha256"]:
        raise ValueError("Published derived output hash mismatch")
    receipt = exporter.read_json(evidence / "comparison.json")
    if receipt["output_sha256"] != result["output_sha256"]:
        raise ValueError("Published receipt hash mismatch")
    exporter.validate_allowed_changes(ctx.record, exporter.read_json(output))
    return {**result, "status": "completed", "output": str(output), "evidence_output": str(evidence)}


class JsonParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main(argv=None):
    command = None
    try:
        parser = JsonParser(description=__doc__)
        parser.add_argument("command", choices=COMMANDS)
        parser.add_argument("--request", type=Path, required=True)
        args = parser.parse_args(argv)
        command = args.command
        request = exporter.read_json(args.request)
        with redirect_stdout(sys.stderr):
            value = dispatch(command, request)
        code = 2 if value["status"] == "needs_review" else 0
    except Exception as error:
        value = {"status": "error", "completed": False, "error_type": type(error).__name__, "message": str(error)}
        code = 1
    value.update(schema_version=SCHEMA_VERSION, command=command)
    print(json.dumps(value, ensure_ascii=False, allow_nan=False))
    return code


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
