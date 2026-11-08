"""Conservative PR routing and explicit required-check gates (stdlib only)."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import posixpath
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

WORKFLOW = ".github/workflows/ci.yml"
WARM_WORKFLOW = ".github/workflows/warm-caches.yml"
ROUTED_WORKFLOWS = {WORKFLOW, WARM_WORKFLOW}
WARM_CONCURRENCY = "concurrency:\n  group: warm-caches-${{ github.ref }}\n  cancel-in-progress: true\n"
PORTABLE = {
    "tool/kr_factor_ocr/kr_factor_app.py", "tool/kr_factor_ocr/kr_factor_cli.py",
    "tool/kr_factor_ocr/test_kr_factor_app.py", "tool/kr_factor_ocr/test_kr_factor_cli.py",
    "tool/kr_factor_ocr/kr_factor_ocr.py", "tool/kr_factor_ocr/kr_factor_export.py",
    "tool/kr_factor_ocr/test_kr_factor_ocr.py", "tool/kr_factor_ocr/test_kr_factor_export.py",
    "tool/kr_factor_ocr/APP_PROTOCOL.md", "tool/kr_factor_ocr/README.md",
    "test/fixtures/chara_detail_record.json", "tool/ci/pr_scope.py", "tool/ci/test_pr_scope.py",
}
GUIDANCE = {
    "AGENTS.md": {"Issue context and decision continuity"},
    "docs/agents/contracts.md": {"Research handoffs", "Local storage and worktree handoff"},
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


def warm_job_concurrency(text):
    """Normalize the original warm workflow's exact concurrency block to job scope."""
    header, jobs, body = text.partition("\njobs:\n")
    if ("\n" + WARM_CONCURRENCY.rstrip() + "\n") in ("\n" + header + "\n"):
        job_block = "".join("    " + line for line in WARM_CONCURRENCY.splitlines(keepends=True))
        header = (header + "\n").replace("\n" + WARM_CONCURRENCY, "\n", 1)
        body = re.sub(r"^  warm:\n", "  warm:\n" + job_block, body, count=1, flags=re.MULTILINE)
        text = header.rstrip("\n") + jobs + body
    return text


def unfenced_lines(lines):
    """Yield original positions and text outside canonical Markdown fences."""
    fence = None
    visible = []
    for index, line in enumerate(lines):
        stripped = line.rstrip("\n")
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", stripped)
        if fence is not None:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            continue
        if marker:
            fence = marker[1]
            continue
        visible.append((index, line))
    if fence is not None:
        raise ValueError("Unclosed guidance code fence")
    return visible


def guidance_sections(text, path):
    """Return protected text and allowed sections for canonical ATX guidance."""
    if not isinstance(text, str) or "\r" in text or "\x00" in text or text.startswith("\ufeff"):
        raise ValueError("Guidance must be UTF-8/LF text without a BOM or NUL")
    lines = text.splitlines(keepends=True)
    headings, seen, title_count = [], set(), 0
    for index, line in unfenced_lines(lines):
        stripped = line.rstrip("\n")
        if re.fullmatch(r" {0,3}(?:=+|-+)\s*", stripped) or re.match(r"^ {1,3}#{1,6}(?:\s|$)", stripped):
            raise ValueError("Unsupported guidance heading")
        if re.match(r"^#(?:\s|$)", stripped):
            title_count += 1
        if re.match(r"^##(?:\s|$)", stripped):
            match = re.fullmatch(r"## ([^#\n]+)", stripped)
            if not match or match[1].strip() != match[1] or match[1] in seen:
                raise ValueError("Ambiguous guidance section")
            seen.add(match[1])
            headings.append((index, match[1]))
    if title_count != 1:
        raise ValueError("Ambiguous document title")
    protected = lines[:headings[0][0]] if headings else list(lines)
    sections = {}
    for position, (start, name) in enumerate(headings):
        end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        content = "".join(lines[start:end])
        if name in GUIDANCE[path]:
            sections[name] = content
        else:
            protected.extend(lines[start:end])
    return "".join(protected).rstrip("\n"), sections


def guidance_only(path, before, after):
    old_protected, old_sections = guidance_sections(before, path)
    new_protected, new_sections = guidance_sections(after, path)
    return bool(new_sections) and old_sections.keys() <= new_sections.keys() and old_protected == new_protected


def classify_paths(paths, workflows=None, documents=None):
    paths = set(paths)
    unknown = paths - PORTABLE - ROUTED_WORKFLOWS - GUIDANCE.keys()
    if not paths or unknown:
        return "windows"
    for path in paths & GUIDANCE.keys():
        try:
            if not guidance_only(path, *(documents or {})[path]):
                return "windows"
        except (KeyError, TypeError, ValueError):
            return "windows"
    for path in paths & ROUTED_WORKFLOWS:
        try:
            before, after = (workflows or {})[path]
            if path == WARM_WORKFLOW:
                before = warm_job_concurrency(before)
            if windows_contract(before) != windows_contract(after):
                return "windows"
        except (AttributeError, KeyError, TypeError, ValueError):
            return "windows"
    return "docs" if paths <= GUIDANCE.keys() else "portable"


def git(*args):
    return subprocess.check_output(["git", *args])


def changed_paths(base, head, *, push=False):
    for ref in (base, head):
        if not re.fullmatch(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", ref):
            raise ValueError("Explicit full commit SHAs are required")
        git("cat-file", "-e", ref + "^{commit}")
    # Rename detection is disabled: a move from outside the allowlist stays visible.
    diff_range = base + (".." if push else "...") + head
    raw = git("diff", "--no-renames", "--name-only", "-z", diff_range)
    return [p.decode("utf-8") for p in raw.split(b"\0") if p]


def changed_texts(paths, base, head):
    texts = {}
    for path in paths:
        try:
            before = git("show", base + ":" + path).decode("utf-8")
            after = git("show", head + ":" + path).decode("utf-8")
        except (subprocess.CalledProcessError, UnicodeDecodeError):
            continue
        texts[path] = (before, after)
    return texts


def classify_refs(base, head, *, push=False):
    paths = changed_paths(base, head, push=push)
    comparison_base = base if push else git("merge-base", base, head).decode().strip()
    workflows = changed_texts(set(paths) & ROUTED_WORKFLOWS, comparison_base, head)
    documents = changed_texts(set(paths) & GUIDANCE.keys(), comparison_base, head)
    for path in list(documents):
        if any(git("ls-tree", ref, "--", path).split()[0] != b"100644" for ref in (comparison_base, head)):
            del documents[path]
    return classify_paths(paths, workflows, documents), paths


def check_guidance(text, path, files):
    """Check text and local inline links without fetching URLs or reading evidence."""
    guidance_sections(text, path)
    if not text.endswith("\n"):
        raise ValueError(f"{path}: missing final newline")
    for number, line in enumerate(text.splitlines(), 1):
        if line.rstrip(" \t") != line or re.match(r"^(?:<{7}|={7}|>{7})(?:\s|$)", line):
            raise ValueError(f"{path}:{number}: whitespace or conflict marker")
    without_code = "".join(line for _, line in unfenced_lines(text.splitlines(keepends=True)))
    without_code = re.sub(r"`+[^`\n]*`+", "", without_code)
    if re.search(r"<(?:a|img)\b", without_code, re.IGNORECASE):
        raise ValueError(f"{path}: HTML links are outside the supported guidance syntax")
    links = list(re.finditer(r"\]\(([^)\n]*)\)", without_code))
    if without_code.count("](") != len(links):
        raise ValueError(f"{path}: unsupported inline link syntax")
    definitions = {}
    for label, value in re.findall(r"(?m)^ {0,3}\[([^\]\n]+)\]:[ \t]*(.*)$", without_code):
        key = " ".join(label.casefold().split())
        if key in definitions:
            raise ValueError(f"{path}: duplicate link reference {label}")
        definitions[key] = value
    destinations = [match[1] for match in links] + list(definitions.values())
    for label, reference in re.findall(r"\[([^\]\n]+)\]\[([^\]\n]*)\]", without_code):
        key = " ".join((reference or label).casefold().split())
        if key not in definitions:
            raise ValueError(f"{path}: undefined link reference {reference or label}")
    for raw in destinations:
        match = re.fullmatch(r"\s*(?:<([^>\n]+)>|([^\s<>]+))(?:\s+(?:\"[^\"\n]*\"|'[^'\n]*'))?\s*", raw)
        if not match:
            raise ValueError(f"{path}: unsupported link destination {raw}")
        destination = match[1] or match[2]
        url = urlsplit(destination)
        if url.scheme or url.netloc or not url.path:
            continue
        if any(character in destination for character in "\\()"):
            raise ValueError(f"{path}: unsupported local link destination {destination}")
        target = posixpath.normpath(posixpath.join(posixpath.dirname(path), unquote(url.path)))
        if target.startswith("../") or target.startswith("/") or target not in files:
            raise ValueError(f"{path}: missing or unsupported local link target {destination}")


def check_docs(base, head, *, push=False):
    paths = set(changed_paths(base, head, push=push)) & GUIDANCE.keys()
    if not paths:
        return "No changed guidance files; documentation checks are not applicable."
    git("diff", "--check", base + (".." if push else "...") + head, "--", *sorted(paths))
    files = {p.decode("utf-8") for p in git("ls-tree", "-r", "-t", "--name-only", "-z", head).split(b"\0") if p}
    for path in sorted(paths):
        try:
            text = git("show", head + ":" + path).decode("utf-8")
        except subprocess.CalledProcessError:
            # A deletion cannot select docs; product lanes retain their own checks.
            continue
        check_guidance(text, path, files)
    return "Changed guidance UTF-8/LF, structure, whitespace and local file links passed."


def verify_gate(needs, context):
    if not isinstance(needs, dict) or context not in WINDOWS_JOBS:
        raise ValueError("Invalid gate input")
    for name in ("scope", "lightweight-checks"):
        if not isinstance(needs.get(name), dict) or needs[name].get("result") != "success":
            raise ValueError(f"{name} did not succeed")
    outputs = needs["scope"].get("outputs")
    if not isinstance(outputs, dict):
        raise ValueError("Missing or invalid scope outputs")
    lane = outputs.get("lane")
    if lane not in ("docs", "portable", "windows"):
        raise ValueError("Missing or unknown scope lane")
    expected_cli = "skipped" if lane == "docs" else "success"
    if not isinstance(needs.get("cli-tests"), dict) or needs["cli-tests"].get("result") != expected_cli:
        raise ValueError(f"cli-tests must be {expected_cli} for {lane} routing")
    expected = "success" if lane == "windows" else "skipped"
    for name in WINDOWS_JOBS[context]:
        if not isinstance(needs.get(name), dict) or needs[name].get("result") != expected:
            raise ValueError(f"{name} must be {expected} for {lane} routing")
    if lane == "docs":
        return "Documentation checks passed; CLI and Windows product work are not applicable and were skipped."
    if lane == "portable":
        return "Portable CLI tests passed; Windows work is not applicable and was skipped."
    return f"Required {context} Windows work and Linux CLI tests passed."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    scope = commands.add_parser("classify")
    scope.add_argument("--base", required=True)
    scope.add_argument("--head", required=True)
    scope.add_argument("--push", action="store_true", help="Compare the before and after push trees directly")
    docs = commands.add_parser("check-docs")
    docs.add_argument("--base", required=True)
    docs.add_argument("--head", required=True)
    docs.add_argument("--push", action="store_true")
    gate = commands.add_parser("gate")
    gate.add_argument("--context", required=True, choices=tuple(WINDOWS_JOBS))
    args = parser.parse_args()
    if args.command == "classify":
        lane, paths = classify_refs(args.base, args.head, push=args.push)
        print(json.dumps({"lane": lane, "changed_paths": paths}, sort_keys=True))
        if os.environ.get("GITHUB_OUTPUT"):
            with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as stream:
                stream.write(f"lane={lane}\nwindows={'true' if lane == 'windows' else 'false'}\n")
    elif args.command == "check-docs":
        print(check_docs(args.base, args.head, push=args.push))
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
