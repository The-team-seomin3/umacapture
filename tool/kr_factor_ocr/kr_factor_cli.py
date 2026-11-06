"""Explicit local configuration, read-only preflight and opt-in diagnostic receipts."""
from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

import kr_factor_export as exporter
import kr_factor_ocr as kr

COMMON = {"capture", "master", "master_sha256", "factor_info", "factor_info_sha256",
          "module_version", "model", "working_dir"}
SETTINGS = {"interpreter", "adapter", "output_root"}
EXTRA = {"lookup": {"query", "star", "offset", "limit"},
         "save-review": {"review", "expected_review_sha256"},
         "export": {"output", "evidence_output", "replace_sha256"}}
PINS = {"rapidocr": ("3.10.0", "rapidocr"), "onnxruntime": ("1.31.1", "onnxruntime"),
        "opencv-python-headless": ("4.13.0.92", "cv2"), "numpy": ("2.5.4", "numpy")}


class ConfigurationError(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__("Invalid configuration/request: " + "; ".join(issues))


def object_json(path):
    value = exporter.read_json(path)
    if type(value) is not dict:
        raise ValueError("Expected a JSON object")
    return value


def build_request(config, override, command):
    """Deterministic allowlisted merge; never discovers or changes settings."""
    issues = []
    for label, value, allowed in (("config", config, COMMON | SETTINGS | {"schema_version"}),
                                  ("request", override, COMMON | EXTRA.get(command, set()) | {"schema_version"})):
        if type(value) is not dict:
            issues.append(f"{label} must be an object")
            continue
        for key in sorted(set(value) - allowed):
            # Do not echo arbitrary field values into diagnostics.
            issues.append(f"{label}: unknown field {key}")
        if "schema_version" in value and (type(value["schema_version"]) is not int or value["schema_version"] != 1):
            issues.append(f"{label}.schema_version must be integer 1")
        for key in sorted(set(value) & (COMMON | SETTINGS | {"output", "evidence_output", "replace_sha256", "expected_review_sha256"})):
            item = value[key]
            if not isinstance(item, str) or not item.strip():
                issues.append(f"{label}.{key} must be nonempty text")
            elif key.endswith("sha256"):
                if len(item) != 64 or any(c not in "0123456789abcdefABCDEF" for c in item):
                    issues.append(f"{label}.{key} must be SHA256 hex")
            elif not Path(item).is_absolute():
                issues.append(f"{label}.{key} must be an absolute local path")
        if "query" in value and not isinstance(value["query"], str):
            issues.append("query must be text")
        for key, minimum, maximum in (("star", 1, 3), ("offset", 0, sys.maxsize), ("limit", 1, 200)):
            if key in value and not (key == "star" and value[key] is None):
                if type(value[key]) is not int or not minimum <= value[key] <= maximum:
                    issues.append(f"{key} must be integer {minimum} through {maximum}")
        if "review" in value and type(value["review"]) is not dict:
            issues.append("review must be an object")
    if issues:
        raise ConfigurationError(issues)
    merged = {"schema_version": 1, **{k: v for k, v in config.items() if k in COMMON}, **override}
    return dict(sorted(merged.items()))


def preflight(app, request, command, settings=None):
    """No OCR, DB open/copy, runtime import, directory creation, lock or review writes."""
    checks, paths, hashes, parsed = [], {}, {}, {}

    def check(field, stage, action, operation):
        try:
            detail = operation()
            checks.append({"field": field, "stage": stage, "status": "passed", "detail": detail})
            return True
        except Exception as error:
            checks.append({"field": field, "stage": stage, "status": "failed",
                           "code": type(error).__name__, "message": str(error), "action": action})
            return False

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    required = {"master", "factor_info"} if command == "lookup" else {"capture", "master", "factor_info",
                                                                          "module_version", "model", "working_dir"}
    if command == "export":
        required |= {"output", "evidence_output"}
    for key in sorted(required):
        def path_check(key=key):
            paths[key] = app.absolute_path(request, key)
            if key in {"working_dir", "output", "evidence_output"}:
                app.no_links(Path(request[key]))
            elif key == "capture":
                require(paths[key].is_dir(), "Capture directory is missing")
            else:
                require(paths[key].is_file(), f"{key} file is missing")
            return "Absolute path checked"
        check(key, "paths", "Select an explicit existing input or separate local destination.", path_check)

    for key, pin in (("master", "master_sha256"), ("factor_info", "factor_info_sha256"), ("model", None)):
        if key not in required:
            continue
        def pin_check(key=key, pin=pin):
            expected = app.pinned_hash(request, pin) if pin else kr.MODEL_SHA256
            path = paths.get(key)
            require(path is not None and path.is_file(), f"Cannot check {key} identity without a readable file")
            hashes[key] = kr.digest(path)
            require(hashes[key] == expected, f"{key} SHA256 mismatch")
            return {"sha256": hashes[key]}
        check(pin or "model_sha256", "pins", "Provide the matching immutable input and exact expected pin.", pin_check)

    if "master" in paths:
        def master_check():
            master = paths["master"]
            with master.open("rb") as stream:
                require(stream.read(16) == b"SQLite format 3\x00", "Master is not a SQLite file")
            wal = Path(str(master) + "-wal")
            require(not wal.exists() or wal.stat().st_size == 0, "Master has pending WAL")
            return "SQLite header and no pending WAL checked; database not opened"
        check("master_snapshot", "metadata", "Select a stable standalone snapshot; do not checkpoint the original.", master_check)

    if "factor_info" in paths:
        def factor_check():
            data = exporter.read_json(paths["factor_info"])
            kr.Resolver([], data)
            return "Factor module JSON structure checked; master mapping is not validated"
        check("factor_info", "metadata", "Select factor_info.json from the matching capture module.", factor_check)

    if command != "lookup" and "capture" in paths:
        for name in ("record.json", "prediction.json", "factor.json", "factor.png"):
            def source_check(name=name):
                path = paths["capture"] / name
                hashes[name] = kr.digest(path)
                if name.endswith(".json"):
                    parsed[name] = object_json(path)
                    if name == "record.json":
                        exporter.full_record(parsed[name])
                else:
                    with path.open("rb") as stream:
                        header = stream.read(24)
                    require(len(header) == 24 and header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR",
                            "factor.png has no PNG/IHDR header")
                    parsed["dimensions"] = struct.unpack(">II", header[16:24])
                return {"sha256": hashes[name]}
            check(name, "capture", "Select a complete preserved three-tab capture.", source_check)
        if all(k in parsed for k in ("record.json", "prediction.json", "factor.json", "dimensions")):
            check("geometry", "capture", "Use matching record/prediction/geometry and full factor image.",
                  lambda: {"rows": len(kr.capture_rows(parsed["record.json"], parsed["prediction.json"],
                                                     parsed["factor.json"], *parsed["dimensions"]))})
        if "module_version" in paths:
            def module_check():
                module = object_json(paths["module_version"])
                record = parsed.get("record.json")
                require(record is not None, "Record metadata unavailable")
                for key in ("region", "recognizer_version"):
                    require(module[key] == record["metadata"][key], f"Module/record {key} mismatch")
                hashes["module_version"] = kr.digest(paths["module_version"])
                return "Module/record identity checked"
            check("module_version", "metadata", "Select version_info.json matching this original record.", module_check)

    if "working_dir" in paths:
        def work_check():
            work = paths["working_dir"]
            protected = [p if k == "capture" else p.parent for k, p in paths.items()
                         if k in {"capture", "master", "factor_info", "module_version", "model"}]
            require(not any(work == p or p in work.parents or work in p.parents for p in protected),
                    "working_dir overlaps protected inputs")
            if command == "run":
                require(not work.exists(), "Working path already exists; use load for an existing session or a fresh path")
            else:
                require(work.is_dir(), "Existing session directory is missing; run requires a fresh path")
                for relative in ("diagnostics/diagnostic.json", "review.json"):
                    app.no_links(work / relative)
                    object_json(work / relative)
                require(not (work / ".review.json.lock").exists(), "Review writer lock exists; preserve it")
            ancestor = work.parent
            while not ancestor.exists():
                ancestor = ancestor.parent
            require(ancestor.is_dir() and os.access(ancestor, os.W_OK | os.X_OK), "Working parent is not accessible/writable")
            return "Fresh path checked" if command == "run" else "Saved session presence/JSON checked; full validation deferred"
        check("working_dir", "session", "Resume only a matching complete session; preserve partial work and locks.", work_check)

    if command == "save-review":
        def draft_check():
            require(type(request.get("review")) is dict, "save-review requires an explicit review object")
            expected = app.pinned_hash(request, "expected_review_sha256")
            require("working_dir" in paths, "Existing working path unavailable")
            require(kr.digest(paths["working_dir"] / "review.json") == expected, "Saved review hash differs; reload")
            return "Draft presence and optimistic hash checked; full immutable/review validation deferred"
        check("review", "request", "Load the current session and supply its review plus exact last review hash.", draft_check)

    if command == "export":
        for key in ("output", "evidence_output"):
            if key not in paths:
                continue
            def output_check(key=key):
                p = paths[key]
                require(all(k in paths for k in ("capture", "master", "factor_info", "module_version", "working_dir")),
                        "Input/session paths unavailable for destination checks")
                work = paths["working_dir"]
                input_dirs = [paths["capture"], work / "diagnostics", paths["master"].parent,
                              paths["factor_info"].parent, paths["module_version"].parent]
                if key == "output":
                    inputs = {n: paths["capture"] / n for n in ("record.json", "prediction.json", "factor.json", "factor.png")}
                    inputs.update({k: v for k, v in paths.items() if k in {"master", "factor_info", "module_version", "model"}})
                    context = SimpleNamespace(input_dirs=input_dirs, paths=inputs, master=paths["master"])
                    exporter.destination(SimpleNamespace(output=p, capture=paths["capture"], review=work / "review.json"), context)
                    expected = app.pinned_hash(request, "replace_sha256") if request.get("replace_sha256") else None
                    actual = kr.digest(p) if p.exists() else None
                    require(actual == expected, "Existing output needs its exact pin; absent output needs no replacement pin")
                    require(not p.with_name(f".{p.name}.lock").exists(), "Output lock exists; preserve it")
                else:
                    require(not any(p == q or q in p.parents for q in input_dirs), "Evidence destination overlaps inputs")
                    require(not p.exists(), "Evidence output already exists")
                    output = paths.get("output")
                    require(output is None or p not in (output, output.parent), "Evidence conflicts with output")
                require(work is None or p != work and p not in work.parents, "Destination would replace session")
                return "Destination inspected without writing"
            check(key, "destinations", "Select separate destinations; do not remove locks or replace evidence.", output_check)

    check("python", "runtime", "Use a configured Python 3.12+ interpreter.",
          lambda: require(sys.version_info >= (3, 12), "Python 3.12+ required"))
    runtime = PINS if command == "run" else {k: v for k, v in PINS.items() if k in {"numpy", "opencv-python-headless"}}
    if command == "lookup":
        runtime = {}
    for package, (version, module) in runtime.items():
        def runtime_check(package=package, version=version, module=module):
            installed = importlib.metadata.version(package)
            require(installed == version, f"{package} requires {version}; installed {installed}")
            require(importlib.util.find_spec(module) is not None, f"{module} cannot be discovered")
            return {"version": installed, "module_discoverable": True, "loaded": False}
        check(package, "runtime", "Select the existing pinned runtime; preflight never installs packages.", runtime_check)
    for key, value in sorted((settings or {}).items()):
        if key not in SETTINGS:
            continue
        def setting_check(key=key, value=value):
            p = Path(value)
            if key == "interpreter":
                require(p.is_file() and os.access(p, os.X_OK), "Configured interpreter is unavailable")
                require(p.resolve() == Path(sys.executable).resolve(), "Invoke the configured interpreter explicitly")
            elif key == "adapter":
                require(p.is_file() and p.resolve() == Path(app.__file__).resolve(), "Invoke the configured adapter explicitly")
            return "Configured path inspected; output_root is not an export destination"
        check(key, "configuration", "Use explicit Linux-local configuration; settings are not repaired automatically.", setting_check)
    failed = sum(c["status"] == "failed" for c in checks)
    return {"status": "error" if failed else "ok", "completed": False, "target_command": command,
            "stage": "preflight", "checks": checks, "failed_checks": failed,
            "error_code": "prerequisites_failed" if failed else None,
            "action": "Inspect failed checks; preserve inputs and existing sessions/locks.",
            "error_type": "PreflightError" if failed else None,
            "message": f"{failed} prerequisite checks failed" if failed else "Read-only prerequisite checks passed",
            "request_sha256": hashlib.sha256(exporter.canonical(request).encode()).hexdigest(),
            "not_tested": ["native runtime loading/inference", "full image decode/crop-pixel checks",
                           "master SQL schema/provenance/mapping", "saved tool/crop/review bindings and export readiness"]}


def open_report(app, path, request, source_files, settings=None):
    """Reserve an explicit private report before any mutating operation."""
    raw = Path(path)
    if not raw.is_absolute():
        raise ValueError("report must be an explicit absolute local path")
    app.no_links(raw)
    target = raw.resolve()
    protected = [Path(kr.__file__).resolve().parent, Path(app.__file__).resolve().parent]
    if (settings or {}).get("output_root"):
        protected.append(Path(settings["output_root"]).resolve())
    for key in ("capture", "master", "factor_info", "module_version", "model", "working_dir", "output", "evidence_output"):
        if key in request:
            p = app.absolute_path(request, key)
            protected.append(p if key in {"capture", "working_dir", "evidence_output"} else p.parent)
    for source in source_files:
        if source is not None and target == Path(source).resolve():
            raise ValueError("Report cannot replace a configuration/request file")
    if any(target == p or p in target.parents or target in p.parents for p in protected):
        raise ValueError("Report must be separate from source/input/work/output locations")
    if not target.parent.is_dir():
        raise ValueError("Create/select a private report directory explicitly first")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    return os.fdopen(os.open(target, flags, 0o600), "w", encoding="utf-8")


def report_value(app, command, request, result, code):
    identities = {}
    candidates = {"adapter": Path(app.__file__), "cli": Path(__file__), "producer": Path(kr.__file__),
                  "exporter": Path(exporter.__file__)}
    for key in ("master", "model", "factor_info", "module_version", "output"):
        if isinstance(request.get(key), str):
            candidates[key] = Path(request[key])
    if isinstance(request.get("capture"), str):
        candidates.update({n: Path(request["capture"]) / n for n in ("record.json", "prediction.json", "factor.json", "factor.png")})
    for key, path in candidates.items():
        try:
            identities[key] = {"sha256": kr.digest(path)} if path.is_file() else {"status": "unavailable"}
        except OSError:
            identities[key] = {"status": "unreadable"}
    diagnostic = {k: result[k] for k in ("error_type", "error_code", "action") if isinstance(result.get(k), str)}
    return {"report_version": 1, "command": command, "exit_code": code, "diagnostic": diagnostic,
            "status": result["status"], "stage": result.get("stage", "dispatch"),
            "request_sha256": hashlib.sha256(exporter.canonical(request).encode()).hexdigest(),
            "python": sys.version.split()[0], "files": identities,
            "note": "Private local receipt. No raw request, review, OCR rows or arbitrary fields are retained."}
