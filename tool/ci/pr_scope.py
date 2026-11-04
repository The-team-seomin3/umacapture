"""Conservative PR routing and explicit required-check gates (stdlib only)."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

WORKFLOW = ".github/workflows/ci.yml"
PORTABLE = {
    "tool/kr_factor_ocr/kr_factor_app.py", "tool/kr_factor_ocr/kr_factor_cli.py",
    "tool/kr_factor_ocr/test_kr_factor_app.py", "tool/kr_factor_ocr/test_kr_factor_cli.py",
    "tool/kr_factor_ocr/kr_factor_ocr.py", "tool/kr_factor_ocr/kr_factor_export.py",
    "tool/kr_factor_ocr/test_kr_factor_ocr.py", "tool/kr_factor_ocr/test_kr_factor_export.py",
    "tool/kr_factor_ocr/APP_PROTOCOL.md", "tool/kr_factor_ocr/README.md",
    "test/fixtures/chara_detail_record.json", "tool/ci/pr_scope.py", "tool/ci/test_pr_scope.py",
}
WINDOWS_JOBS = {
    "native": ("native-tests-windows",),
    "flutter": ("flutter-test-shards", "flutter-static", "flutter-web", "browser-tests"),
}


def windows_contract(text):
    """Fingerprint the workflow header and supported Windows execution bodies.

    This is deliberately not a general YAML parser. Only literal Ubuntu/Windows
    runners and ordinary two-space job mappings qualify for portable routing.
    Job-level name/needs/if may change; root configuration and execution stay exact.
    """
    jobs, job, lines, seen_jobs, header, root_keys = {}, None, [], False, [], set()

    def save():
        if job is None:
            return
        meaningful = [line for line in lines if line.strip() and not line.lstrip().startswith("#")]
        runners = [line[13:].strip() for line in meaningful if line.startswith("    runs-on:")]
        if len(runners) != 1 or not re.fullmatch(r"(?:windows|ubuntu)-[A-Za-z0-9.]+", runners[0]):
            raise ValueError("Unsupported runner declaration")
        if not runners[0].startswith("windows-"):
            return
        retained, ignoring = [], False
        for line in meaningful:
            if re.match(r"^    (?:name|needs|if):", line):
                ignoring = True
                continue
            if re.match(r"^    \S", line):
                ignoring = False
            if not ignoring:
                retained.append(line.rstrip())
        key = "native-tests-windows" if job == "native-tests" else job
        if key in jobs:
            raise ValueError("Duplicate normalized Windows job")
        jobs[key] = retained

    job_ids = set()
    for line in text.splitlines():
        if line == "jobs:":
            if seen_jobs:
                raise ValueError("Duplicate jobs mapping")
            seen_jobs = True
            continue
        if not seen_jobs:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if "\t" in line:
                raise ValueError("Unsupported workflow header indentation")
            if not line.startswith(" "):
                root = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):", line)
                if not root or root[1] in root_keys:
                    raise ValueError("Unsupported or duplicate workflow root key")
                root_keys.add(root[1])
            elif not root_keys:
                raise ValueError("Workflow header has no root mapping")
            header.append(line.rstrip())
            continue
        match = re.fullmatch(r"  ([A-Za-z_][A-Za-z0-9_-]*):", line)
        if match:
            save()
            job, lines = match[1], []
            if job in job_ids:
                raise ValueError("Duplicate job")
            job_ids.add(job)
        elif line.strip() and not line.startswith(" ") and not line.startswith("#"):
            raise ValueError("Unsupported jobs mapping boundary")
        elif job is not None:
            lines.append(line)
    save()
    if not seen_jobs or not jobs:
        raise ValueError("No Windows jobs found")
    return {"__workflow_header__": header, **jobs}


def classify_paths(paths, before_workflow=None, after_workflow=None):
    paths = set(paths)
    unknown = paths - PORTABLE - {WORKFLOW}
    if not paths or unknown:
        return "windows"
    if WORKFLOW in paths:
        try:
            if windows_contract(before_workflow) != windows_contract(after_workflow):
                return "windows"
        except (AttributeError, TypeError, ValueError):
            return "windows"
    return "portable"


def git(*args):
    return subprocess.check_output(["git", *args])


def classify_refs(base, head):
    for ref in (base, head):
        if not re.fullmatch(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", ref):
            raise ValueError("Explicit full commit SHAs are required")
        git("cat-file", "-e", ref + "^{commit}")
    # Rename detection is disabled: a move from outside the allowlist stays visible.
    raw = git("diff", "--no-renames", "--name-only", "-z", base + "..." + head)
    paths = [p.decode("utf-8") for p in raw.split(b"\0") if p]
    before = after = None
    if WORKFLOW in paths:
        try:
            before = git("show", base + ":" + WORKFLOW).decode("utf-8")
            after = git("show", head + ":" + WORKFLOW).decode("utf-8")
        except (subprocess.CalledProcessError, UnicodeDecodeError):
            pass
    return classify_paths(paths, before, after), paths


def verify_gate(needs, context):
    if not isinstance(needs, dict) or context not in WINDOWS_JOBS:
        raise ValueError("Invalid gate input")
    for name in ("scope", "cli-tests"):
        if not isinstance(needs.get(name), dict) or needs[name].get("result") != "success":
            raise ValueError(f"{name} did not succeed")
    outputs = needs["scope"].get("outputs")
    if not isinstance(outputs, dict):
        raise ValueError("Missing or invalid scope outputs")
    lane = outputs.get("lane")
    if lane not in ("portable", "windows"):
        raise ValueError("Missing or unknown scope lane")
    expected = "skipped" if lane == "portable" else "success"
    for name in WINDOWS_JOBS[context]:
        if not isinstance(needs.get(name), dict) or needs[name].get("result") != expected:
            raise ValueError(f"{name} must be {expected} for {lane} routing")
    if lane == "portable":
        return "Portable CLI tests passed; Windows work is not applicable and was skipped."
    return f"Required {context} Windows work and Linux CLI tests passed."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    scope = commands.add_parser("classify")
    scope.add_argument("--base", required=True)
    scope.add_argument("--head", required=True)
    gate = commands.add_parser("gate")
    gate.add_argument("--context", required=True, choices=tuple(WINDOWS_JOBS))
    args = parser.parse_args()
    if args.command == "classify":
        lane, paths = classify_refs(args.base, args.head)
        print(json.dumps({"lane": lane, "changed_paths": paths}, sort_keys=True))
        if os.environ.get("GITHUB_OUTPUT"):
            with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as stream:
                stream.write(f"lane={lane}\nwindows={'true' if lane == 'windows' else 'false'}\n")
    else:
        message = verify_gate(json.loads(os.environ["NEEDS"]), args.context)
        print(message)
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as stream:
                stream.write(message + "\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print(f"CI routing/gate error: {error}", file=sys.stderr)
        raise SystemExit(1)
