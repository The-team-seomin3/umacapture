"""Conservative PR routing and explicit required-check gates (stdlib only)."""
from __future__ import annotations

import argparse
from hashlib import sha256
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
    "tool/kr_representative_identity/prepare_role_evidence.py",
    "tool/kr_representative_identity/test_prepare_role_evidence.py",
    "tool/kr_representative_identity/README.md",
}
GUIDANCE = {
    "AGENTS.md": {"Issue context and decision continuity"},
    "docs/agents/contracts.md": {"Research handoffs", "Local storage and worktree handoff"},
    "docs/agents/teams.md": {"Responsibility map", "Shared work and handoffs"},
}
# Ordinary manuals are document-only inputs. Policy guidance, evidence and the
# exact #42 companion document keep their existing specialized admissions.
PROTECTED_MANUALS = {"docs/fork-network-policy.md", "docs/korean-ui-localization.md"}
PROTECTED_MANUAL_TREES = ("docs/agents/", "docs/validation/")
MASTER_MIGRATIONS = {
    WORKFLOW: ("on:\n  pull_request:\n    branches: [develop]\n", "on:\n  pull_request:\n    branches: [master]\n"),
    WARM_WORKFLOW: ("on:\n  push:\n    branches: [develop]\n", "on:\n  push:\n    branches: [master]\n"),
    "AGENTS.md": (
        "PR to `develop`; no direct\n  `develop` commits/pushes.",
        "PR to `master`; no direct\n  `master` commits/pushes.",
    ),
}
# Exact before/after SHA-256 pairs for the reviewed #23 delta (#42).
# Require the entire delta, including its synthetic test and companion docs.
FLUTTER_ADMISSION = {
    "assets/translations/ja.json": (
        "9bd77bdf5ad26f1ca3df17f5d9030ed6d97d1efb0d5ef1fe960a8ae93cd8535a",
        "89e8b3b12c7030b6ca45c5482548ffa552b854d540878de392186951c9aa3394",
    ),
    "assets/translations/ko.json": (
        "9b8e56bac215a2254691845bf918ed739e0f9ced4321dfeeb908e03a94cf315b",
        "9067f9806978fc25624e2f68d7b3bbaffddd1866adca7d774ccbd07a9bd1b71e",
    ),
    "docs/korean-ui-localization.md": (
        "4b4b86e34bc157aed94caa260e66be338dfab5cbb2eb03df6e13d09f5815f50e",
        "805561fc8d43acf3cfe520fcbfa466102c5506260f912d0aa012e18064edf16b",
    ),
    "lib/src/gui/statistics.dart": (
        "b90dac977a1a30ec87176bc90a205ce721fc4bc66bad939773cb6eb357e069d2",
        "350075ee489ed7fa7a20339963af4215ca0600d10131f273d8a4f9857f59c8a9",
    ),
    "test/strategy_statistics_test.dart": (
        None,
        "fc8897489b359268af85046207d5473dd6b16615cc129eeb1224c64c91ce73d3",
    ),
}
FLUTTER_BOOTSTRAP_PATHS = {
    WORKFLOW, "tool/ci/pr_scope.py", "tool/ci/test_pr_scope.py", "tool/kr_factor_ocr/README.md",
}
FLUTTER_LANES = {"flutter", "flutter-bootstrap"}

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


def master_branch_baseline(before, after, path):
    """Recognize only the exact forward migration of canonical branch metadata."""
    old, new = MASTER_MIGRATIONS[path]
    if before.count(old) != 1 or after.count(new) != 1 or old in after:
        return before
    return before.replace(old, new, 1)


def ordinary_manual(path):
    """Recognize canonical ordinary docs Markdown, never executable/assets/policy."""
    if (not isinstance(path, str) or "\\" in path
            or any(ord(character) < 32 or ord(character) == 127 for character in path)):
        return False
    parts = path.split("/")
    return (len(parts) >= 2 and parts[0] == "docs" and path.endswith(".md")
            and all(part and not part.startswith(".") for part in parts)
            and parts[-1] != "AGENTS.md" and path not in PROTECTED_MANUALS
            and not path.startswith(PROTECTED_MANUAL_TREES))


def navigation_table_baseline(text):
    """Remove only simple manual-link rows in AGENTS' existing navigation table.

    All heading/table scaffolding and other prose remain protected. This admits
    #70's added two-cell manual link without admitting arbitrary AGENTS sections.
    """
    lines = text.splitlines(keepends=True)
    removed, inside, table = set(), False, 0
    for index, line in unfenced_lines(lines):
        stripped = line.rstrip("\n")
        if stripped.startswith("## "):
            inside, table = stripped == "## Find the needed document", 0
            continue
        if not inside:
            continue
        if stripped == "| Need | Read next |":
            table = 1
            continue
        if table == 1:
            table = 2 if stripped == "| --- | --- |" else 0
            continue
        if table != 2:
            continue
        if not stripped.startswith("|"):
            table = 0
            continue
        row = re.fullmatch(r"\| ([^|`\[\]<>]{1,120}) \| \[([^|\[\]<>]{1,160})\]\(([^()\s<>]+)\) \|", stripped)
        if row:
            target = urlsplit(row[3])
            if (not target.scheme and not target.netloc and not target.query
                    and ordinary_manual(unquote(target.path))):
                removed.add(index)
    return "".join(line for index, line in enumerate(lines) if index not in removed)


def guidance_only(path, before, after):
    old_protected, old_sections = guidance_sections(before, path)
    new_protected, new_sections = guidance_sections(after, path)
    if path in MASTER_MIGRATIONS:
        old_protected = master_branch_baseline(old_protected, new_protected, path)
    navigation_changed = False
    if path == "AGENTS.md":
        old_navigation = navigation_table_baseline(old_protected)
        new_navigation = navigation_table_baseline(new_protected)
        navigation_changed = old_protected != new_protected and old_navigation == new_navigation
        old_protected, new_protected = old_navigation, new_navigation
    return ((bool(new_sections) or navigation_changed) and old_sections.keys() <= new_sections.keys()
            and old_protected == new_protected)


def classify_paths(paths, workflows=None, documents=None, flutter_blobs=None):
    paths = set(paths)
    manuals = {path for path in paths if ordinary_manual(path)}
    unknown = paths - PORTABLE - ROUTED_WORKFLOWS - GUIDANCE.keys() - FLUTTER_ADMISSION.keys() - manuals
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
            before = master_branch_baseline(before, after, path)
            if windows_contract(before) != windows_contract(after):
                return "windows"
        except (AttributeError, KeyError, TypeError, ValueError):
            return "windows"
    flutter_paths = paths & FLUTTER_ADMISSION.keys()
    if flutter_paths:
        # Do not combine admission with edits to its classifier, tests or workflows.
        if (flutter_paths != FLUTTER_ADMISSION.keys()
                or flutter_blobs != FLUTTER_ADMISSION
                or paths & (ROUTED_WORKFLOWS | {"tool/ci/pr_scope.py", "tool/ci/test_pr_scope.py"})):
            return "windows"
        return "flutter"
    if paths == FLUTTER_BOOTSTRAP_PATHS:
        return "flutter-bootstrap"
    return "docs" if paths <= GUIDANCE.keys() | manuals else "portable"


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


def regular_blob_digest(ref, path):
    entry = git("ls-tree", ref, "--", ":(literal)" + path)
    if not entry:
        return None
    if entry.split()[:2] != [b"100644", b"blob"]:
        raise ValueError(f"{path}: expected a non-executable regular file")
    # Unexpected read errors must propagate instead of becoming an absent file.
    return sha256(git("show", ref + ":" + path)).hexdigest()


def classify_refs(base, head, *, push=False):
    paths = changed_paths(base, head, push=push)
    comparison_base = base if push else git("merge-base", base, head).decode().strip()
    # Check both existing sides: additions/deletions of ordinary manuals are
    # eligible, but executable modes, symlinks, submodules and mode changes are not.
    for path in paths:
        if ordinary_manual(path) or path in GUIDANCE or path in PORTABLE or path in ROUTED_WORKFLOWS:
            for ref in (comparison_base, head):
                entry = git("ls-tree", ref, "--", ":(literal)" + path)
                if entry:
                    if entry.split()[:2] != [b"100644", b"blob"]:
                        return "windows", paths
                    if ordinary_manual(path):
                        try:
                            git("show", ref + ":" + path).decode("utf-8")
                        except UnicodeDecodeError:
                            return "windows", paths
    workflows = changed_texts(set(paths) & ROUTED_WORKFLOWS, comparison_base, head)
    documents = changed_texts(set(paths) & GUIDANCE.keys(), comparison_base, head)
    flutter_blobs = {}
    for path in set(paths) & FLUTTER_ADMISSION.keys():
        try:
            flutter_blobs[path] = tuple(regular_blob_digest(ref, path) for ref in (comparison_base, head))
        except ValueError:
            return "windows", paths
    return classify_paths(paths, workflows, documents, flutter_blobs), paths


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


def manual_prose(text):
    """Exclude examples and comments from ordinary Markdown links/headings."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    visible = []
    # List indentation is relative to the start of the parent item's content.
    # Strip that container before distinguishing prose from a code example.
    content_columns = [0]
    fence = None
    for line in text.expandtabs(4).splitlines(keepends=True):
        if not line.strip():
            visible.append("\n")
            continue
        indent = len(line) - len(line.lstrip(" "))
        while len(content_columns) > 1 and indent < content_columns[-1]:
            content_columns.pop()
        content = line[content_columns[-1]:]
        if fence is None:
            item = re.match(r"^ {0,3}(?:[-*+]|[0-9]{1,9}[.)])(?: {1,4}(?! )| )", content)
            if item:
                content_columns.append(content_columns[-1] + item.end())
                content = content[item.end():]
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", content.rstrip("\n"))
        if fence is not None:
            if marker and marker[1].startswith(fence) and not marker[2].strip():
                fence = None
        elif marker:
            fence = marker[1]
        elif not content.startswith("    "):
            visible.append(content)
    if fence is not None:
        raise ValueError("Unclosed manual code fence")
    return "".join(visible)


def manual_destinations(text, path, *, strict=True):
    """Read inline/reference Markdown and HTML links without fetching URLs.

    Unsupported links fail changed manuals. Inbound checks tolerate unrelated
    syntax in unchanged documents and inspect only resolved affected targets.
    """
    from html import unescape

    try:
        prose = manual_prose(text)
    except ValueError:
        if strict:
            raise
        prose = text
    prose = re.sub(r"(`+).*?\1", "", prose, flags=re.DOTALL)
    destination = r'(?:<[^>\n]*>|(?:\\.|[^\s()<>]|\([^()\n]*\))*)'
    title = r'''(?:\s+(?:"[^"\n]*"|'[^'\n]*'|\([^()\n]*\)))?'''
    inline = list(re.finditer(r"(?<!\\)\]\(\s*(" + destination + title + r")\s*\)", prose))
    if strict and len(re.findall(r"(?<!\\)\]\(", prose)) != len(inline):
        raise ValueError(f"{path}: unsupported inline link syntax")
    references = {}
    for label, raw in re.findall(r"(?m)^ {0,3}\[([^\]\n]+)\]:[ \t]*(.*)$", prose):
        key = " ".join(label.casefold().split())
        if key in references:
            if strict:
                raise ValueError(f"{path}: duplicate link reference {label}")
            continue
        references[key] = raw
    for label, reference in re.findall(r"\[([^\]\n]+)\]\[([^\]\n]*)\]", prose):
        key = " ".join((reference or label).casefold().split())
        if strict and key not in references:
            raise ValueError(f"{path}: undefined link reference {reference or label}")
    raw_destinations = [match[1] for match in inline] + list(references.values())
    result = []
    for raw in raw_destinations:
        match = re.fullmatch(r"\s*(" + destination + r")" + title + r"\s*", raw)
        if not match:
            if strict:
                raise ValueError(f"{path}: unsupported link destination {raw}")
            continue
        result.append(unescape(re.sub(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~])", r"\1", match[1].strip("<>"))))
    result.extend(unescape(match[2]) for match in re.finditer(
        r'''<(?:a|img)\b[^>]*?\b(?:href|src)\s*=\s*(["'])(.*?)\1''', prose, re.IGNORECASE))
    return result


def manual_anchors(text):
    """GitHub-style heading slugs, duplicate suffixes and explicit HTML IDs."""
    from html import unescape

    prose = manual_prose(text)
    anchors = {unescape(match[2]) for match in re.finditer(
        r'''<[^>]*\b(?:id|name)\s*=\s*(["'])(.*?)\1''', prose, re.IGNORECASE)}
    used = set()
    previous = ""
    for line in prose.splitlines():
        match = re.match(r"^ {0,3}#{1,6}(?:[ \t]+|$)(.*)$", line)
        heading = None
        if match:
            heading = re.sub(r"[ \t]+#+[ \t]*$", "", match[1]).strip()
        elif previous.strip() and re.fullmatch(r" {0,3}(?:=+|-+)\s*", line):
            heading = previous.strip()
        previous = line
        if heading is None:
            continue
        heading = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", heading)
        heading = re.sub(r"<[^>]+>", "", heading)
        heading = unescape(heading).lower().replace("`", "")
        heading = re.sub(r"(?<!\w)_{1,2}([^_]+)_{1,2}(?!\w)", r"\1", heading)
        slug = "".join(character for character in heading if character.isalnum() or character in "_ -")
        slug = slug.replace(" ", "-")
        candidate, suffix = slug, 0
        while candidate in used:
            suffix += 1
            candidate = f"{slug}-{suffix}"
        used.add(candidate)
        anchors.add(candidate)
    return anchors


def local_manual_link(destination, path):
    url = urlsplit(destination)
    if url.scheme or url.netloc:
        return None
    decoded = unquote(url.path)
    if "\\" in decoded or "\x00" in decoded:
        raise ValueError(f"{path}: unsupported local link destination {destination}")
    if url.path.startswith("/"):
        target = posixpath.normpath(decoded[1:])
    else:
        target = posixpath.normpath(posixpath.join(posixpath.dirname(path), decoded)) if decoded else path
    if target == ".." or target.startswith(("../", "/")):
        raise ValueError(f"{path}: local link escapes the repository {destination}")
    return target, unquote(url.fragment)


def check_manual_link(destination, path, files, read_document, *, anchors=True):
    local = local_manual_link(destination, path)
    if local is None:
        return
    target, fragment = local
    if target not in files:
        raise ValueError(f"{path}: missing local link target {destination}")
    if anchors and fragment and target.lower().endswith(".md"):
        available = manual_anchors(read_document(target))
        if fragment not in available and fragment.removeprefix("user-content-") not in available:
            raise ValueError(f"{path}: missing local heading anchor {destination}")


def check_manual(text, path, files, read_document):
    """Check ordinary manuals without imposing the legacy guidance headings."""
    if "\r" in text or "\x00" in text or text.startswith("\ufeff") or not text.endswith("\n"):
        raise ValueError(f"{path}: expected UTF-8/LF text, no BOM/NUL and a final newline")
    for number, line in enumerate(text.splitlines(), 1):
        trailing = line[len(line.rstrip(" \t")):]
        if trailing not in ("", "  ") or re.match(r"^(?:<{7}|={7}|>{7})(?:\s|$)", line):
            raise ValueError(f"{path}:{number}: whitespace or conflict marker")
    for destination in manual_destinations(text, path):
        check_manual_link(destination, path, files, read_document)


def check_docs(base, head, *, push=False):
    from collections import Counter

    changed = set(changed_paths(base, head, push=push))
    manuals = {path for path in changed if ordinary_manual(path)}
    paths = (changed & GUIDANCE.keys()) | manuals
    if not paths:
        return "No changed guidance files; documentation checks are not applicable."
    git("diff", "--check", base + (".." if push else "...") + head, "--",
        *(":(literal)" + path for path in sorted(paths)))
    entries = {}
    for entry in git("ls-tree", "-r", "-t", "-z", head).split(b"\0"):
        if entry:
            metadata, name = entry.split(b"\t", 1)
            entries[name.decode("utf-8")] = metadata.split()[:2]
    files = set(entries)
    texts = {}

    def read_document(path):
        if path not in texts:
            texts[path] = git("show", head + ":" + path).decode("utf-8")
        return texts[path]

    for path in sorted(paths & files):
        if path in manuals and entries[path] != [b"100644", b"blob"]:
            continue
        text = read_document(path)
        if path in manuals:
            check_manual(text, path, files, read_document)
        else:
            check_guidance(text, path, files)
            if path == "AGENTS.md":
                comparison_base = base if push else git("merge-base", base, head).decode().strip()
                before = ""
                if git("ls-tree", comparison_base, "--", path):
                    before = git("show", comparison_base + ":" + path).decode("utf-8")
                added_links = Counter(manual_destinations(text, path, strict=False)) - Counter(
                    manual_destinations(before, path, strict=False))
                for destination in added_links:
                    local = local_manual_link(destination, path)
                    if local is not None and ordinary_manual(local[0]):
                        check_manual_link(destination, path, files, read_document)
    # Deleting/renaming a manual or changing its headings can break a reader that
    # did not change. Check only inbound references to affected manual paths.
    if manuals:
        for path, metadata in entries.items():
            if metadata not in ([b"100644", b"blob"], [b"100755", b"blob"]) or not path.lower().endswith(".md"):
                continue
            text = git("show", head + ":" + path).decode("utf-8", errors="replace")
            for destination in manual_destinations(text, path, strict=False):
                try:
                    local = local_manual_link(destination, path)
                except ValueError:
                    continue
                if local is not None and local[0] in manuals:
                    check_manual_link(destination, path, files, read_document)
    return "Changed documentation content, local file links, heading anchors and affected inbound references passed."


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
    if lane not in {"docs", "portable", "windows"} | FLUTTER_LANES:
        raise ValueError("Missing or unknown scope lane")
    expected_cli = "skipped" if lane == "docs" else "success"
    if not isinstance(needs.get("cli-tests"), dict) or needs["cli-tests"].get("result") != expected_cli:
        raise ValueError(f"cli-tests must be {expected_cli} for {lane} routing")
    if context == "flutter":
        expected_flutter = "success" if lane in FLUTTER_LANES else "skipped"
        linux_flutter = needs.get("flutter-linux")
        if not isinstance(linux_flutter, dict) or linux_flutter.get("result") != expected_flutter:
            raise ValueError(f"flutter-linux must be {expected_flutter} for {lane} routing")
    expected = "success" if lane == "windows" else "skipped"
    for name in WINDOWS_JOBS[context]:
        if not isinstance(needs.get(name), dict) or needs[name].get("result") != expected:
            raise ValueError(f"{name} must be {expected} for {lane} routing")
    if lane == "docs":
        return "Documentation checks passed; CLI and Windows product work are not applicable and were skipped."
    if lane == "portable":
        return "Portable CLI tests passed; Windows work is not applicable and was skipped."
    if lane in FLUTTER_LANES:
        if context == "native":
            return "Linux CLI and routing checks passed; Windows native work is not applicable and was skipped."
        suite = "bootstrap localization" if lane == "flutter-bootstrap" else "strategy and localization"
        return f"Linux Flutter {suite} checks and CLI tests passed; Windows Flutter work was skipped."
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
