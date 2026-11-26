"""Routing/gate regressions: no Windows tools, network or third-party packages."""
import copy
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pr_scope


def workflow():
    text = "name: CI\njobs:\n"
    for name in ("native-tests", "native-coverage", "flutter-test-shards", "flutter-static", "flutter-web", "browser-tests"):
        text += (f"  {name}:\n    name: {name}\n    runs-on: windows-2022\n"
                 "    timeout-minutes: 20\n    steps:\n      - run: echo checked\n")
    return text


def routed_workflow():
    text = workflow().replace("  native-tests:\n", "  native-tests-windows:\n")
    return text.replace("    runs-on:", "    needs: scope\n    if: needs.scope.outputs.windows == 'true'\n    runs-on:") + (
        "  scope:\n    runs-on: ubuntu-latest\n    steps:\n      - run: python3 tool/ci/pr_scope.py classify\n"
    )


def classify_workflow(before, after, path=pr_scope.WORKFLOW):
    return pr_scope.classify_paths([path], {path: (before, after)})


def warm_workflow():
    return (
        "name: Warm caches\non:\n  push:\n    branches: [develop]\n"
        + pr_scope.WARM_CONCURRENCY
        + "jobs:\n  warm:\n    runs-on: windows-2022\n    steps:\n      - run: echo warmed\n"
    )


def guidance_text(path="AGENTS.md", value="Guidance before"):
    if path == "AGENTS.md":
        return "# Agent guidance\n\n## Protected rules\nKeep product checks.\n\n## Issue context and decision continuity\n" + value + "\n"
    if path == "docs/agents/teams.md":
        return ("# Team responsibilities\n\n## Responsibility map\n" + value +
                "\n\n## Shared work and handoffs\nRecord requests.\n\n"
                "## Validation and staffing\nKeep product checks.\n")
    return ("# Contracts\n\n## Scope and contracts\nKeep product contracts.\n\n"
            "## Research handoffs\n" + value + "\n\n## Local storage and worktree handoff\nKeep private storage.\n")


class GuidanceTests(unittest.TestCase):
    def test_only_approved_sections_are_docs_and_mixtures_keep_product_checks(self):
        for path in pr_scope.GUIDANCE:
            before, after = guidance_text(path), guidance_text(path, "Changed guidance")
            documents = {path: (before, after)}
            self.assertEqual(pr_scope.classify_paths([path], documents=documents), "docs")
            self.assertEqual(pr_scope.classify_paths([path, "tool/kr_factor_ocr/kr_factor_cli.py"], documents=documents), "portable")
            self.assertEqual(pr_scope.classify_paths([path, "lib/main.dart"], documents=documents), "windows")
            after = after.replace("Keep product", "Changed product")
            self.assertEqual(pr_scope.classify_paths([path], documents={path: (before, after)}), "windows")

    def test_adding_issue_continuity_section_to_existing_agents_is_docs(self):
        before = "# Agent guidance\n\n## Existing rules\nPreserve these.\n"
        after = before + "\n## Issue context and decision continuity\nNew continuity rules.\n"
        self.assertEqual(pr_scope.classify_paths(["AGENTS.md"], documents={"AGENTS.md": (before, after)}), "docs")

    def test_docs_with_routing_workflow_are_portable_only_when_windows_unchanged(self):
        path = "AGENTS.md"
        documents = {path: (guidance_text(), guidance_text(value="Changed guidance"))}
        workflows = {pr_scope.WORKFLOW: (workflow(), routed_workflow())}
        self.assertEqual(pr_scope.classify_paths([path, pr_scope.WORKFLOW], workflows, documents), "portable")
        workflows[pr_scope.WORKFLOW] = (workflow(), routed_workflow().replace("echo checked", "echo changed"))
        self.assertEqual(pr_scope.classify_paths([path, pr_scope.WORKFLOW], workflows, documents), "windows")

    def test_unknown_or_consumed_markdown_is_never_docs(self):
        for path in ("README.md", "assets/news.md", "native/test/README.md", "docs/agents/new.md",
                     "docs/validation/new.md", "docs/fork-network-policy.md", "docs/korean-ui-localization.md",
                     "docs/nested/AGENTS.md", "docs/.private/new.md", "LICENSE.md"):
            with self.subTest(path=path):
                self.assertEqual(pr_scope.classify_paths([path]), "windows")
        for path in ("tool/kr_factor_ocr/README.md", "tool/kr_factor_ocr/APP_PROTOCOL.md"):
            self.assertEqual(pr_scope.classify_paths([path]), "portable")

    def test_missing_blobs_deleted_sections_and_ambiguous_structure_are_windows(self):
        before = guidance_text()
        variants = (
            None, "", before + "\n## Issue context and decision continuity\nDuplicate\n",
            before + "\n# New title\n", before + "\n```\nUnclosed example\n",
            before.replace("## Protected rules", "  ## Protected rules"),
            before.replace("## Protected rules", "Protected rules\n-------------"),
            before.split("## Issue context", 1)[0],
            before.replace("\n", "\r\n"),
        )
        for after in variants:
            with self.subTest(after=after):
                self.assertEqual(pr_scope.classify_paths(["AGENTS.md"], documents={"AGENTS.md": (before, after)}), "windows")
        self.assertEqual(pr_scope.classify_paths(["AGENTS.md"]), "windows")
        self.assertEqual(pr_scope.classify_paths(["AGENTS.md"], documents={"AGENTS.md": (None, before)}), "windows")

    def test_fenced_headings_and_link_templates_are_content(self):
        text = guidance_text(value="Example\n```text\n## Not a section\n[summary](<run-id>/SUMMARY.md)\n````")
        self.assertTrue(pr_scope.guidance_only("AGENTS.md", guidance_text(), text))
        pr_scope.check_guidance(text, "AGENTS.md", set())

    def test_reference_links_and_unsupported_syntax_are_not_silently_ignored(self):
        pr_scope.check_guidance(guidance_text(value="[guide][target]\n\n[target]: guide.md"), "AGENTS.md", {"guide.md"})
        for value in ("[guide][missing]", "[target]: missing.md", "[bad](missing file.md)",
                      "[bad](missing.md", '<a href="missing.md">bad</a>',
                      "[target]: missing.md\n[TARGET]: https://example.invalid"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    pr_scope.check_guidance(guidance_text(value=value), "AGENTS.md", set())

    def test_existing_guidance_links_and_issue37_section_addition_are_valid(self):
        root = Path(__file__).resolve().parents[2]
        raw = subprocess.check_output(["git", "ls-tree", "-r", "-t", "--name-only", "-z", "HEAD"], cwd=root)
        files = {p.decode() for p in raw.split(b"\0") if p}
        agents = (root / "AGENTS.md").read_text()
        if "## Issue context and decision continuity" not in agents:
            agents += "\n## Issue context and decision continuity\nUse verified current context.\n"
        pr_scope.check_guidance(agents, "AGENTS.md", files)
        pr_scope.check_guidance((root / "docs/agents/contracts.md").read_text(), "docs/agents/contracts.md", files)

    def test_local_links_use_document_directory_and_ignore_anchors_and_remote_urls(self):
        text = guidance_text("docs/agents/contracts.md", "[local](../../README.md#section) [self](#section) [remote](https://example.invalid/missing)")
        pr_scope.check_guidance(text, "docs/agents/contracts.md", {"README.md"})
        pr_scope.check_guidance(guidance_text(value="[directory](native/test)"), "AGENTS.md", {"native/test"})
        for target in ("missing.md", "../../../private.md", "/absolute.md", "../../missing%20name.md"):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    pr_scope.check_guidance(guidance_text(value=f"[bad]({target})"), "AGENTS.md", set())

    def test_checker_rejects_conflicts_whitespace_bad_encoding_structure_and_newline(self):
        for text in (guidance_text() + "<<<<<<< HEAD\n", guidance_text(value="bad "),
                     guidance_text().replace("\n", "\r\n"), "\ufeff" + guidance_text(),
                     guidance_text(value="bad\x00text"), guidance_text().rstrip("\n"),
                     guidance_text() + "## Protected rules\nDuplicate\n"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    pr_scope.check_guidance(text, "AGENTS.md", set())


class ScopeTests(unittest.TestCase):
    def test_exact_master_event_migration_is_directional(self):
        cases = (
            (pr_scope.WORKFLOW, workflow().replace("jobs:\n", "on:\n  pull_request:\n    branches: [develop]\njobs:\n")),
            (pr_scope.WARM_WORKFLOW, pr_scope.warm_job_concurrency(warm_workflow())),
        )
        for path, before in cases:
            after = before.replace("branches: [develop]", "branches: [master]")
            with self.subTest(path=path):
                self.assertEqual(classify_workflow(before, after, path), "portable")
                self.assertEqual(classify_workflow(after, before, path), "windows")
                for target in ("[main]", "[master, other]", "['master']"):
                    self.assertEqual(classify_workflow(before, after.replace("[master]", target), path), "windows")
                self.assertEqual(classify_workflow(before, after.replace("echo ", "echo changed "), path), "windows")
                self.assertEqual(classify_workflow(before, after.replace("on:\n", "permissions:\n  contents: write\non:\n"), path), "windows")

    def test_master_guidance_reference_does_not_allow_other_protected_edits(self):
        old, new = pr_scope.MASTER_MIGRATIONS["AGENTS.md"]
        before = guidance_text().replace("Keep product checks.", old)
        after = before.replace(old, new)
        documents = {"AGENTS.md": (before, after)}
        self.assertEqual(pr_scope.classify_paths(["AGENTS.md"], documents=documents), "docs")
        for previous, changed in ((after, before), (before, after.replace("no direct", "allow direct")),
                                  (before.replace(old, old + "\n" + old), after.replace(new, new + "\n" + new))):
            with self.subTest(previous=previous, changed=changed):
                self.assertEqual(pr_scope.classify_paths(["AGENTS.md"], documents={"AGENTS.md": (previous, changed)}), "windows")

    def test_representative_identity_admits_only_the_listed_paths(self):
        paths = {
            "tool/kr_representative_identity/prepare_role_evidence.py",
            "tool/kr_representative_identity/test_prepare_role_evidence.py",
            "tool/kr_representative_identity/README.md",
        }
        self.assertEqual(pr_scope.classify_paths(paths), "portable")
        self.assertEqual(pr_scope.classify_paths(paths | {"README.md"}), "windows")
        self.assertEqual(
            pr_scope.classify_paths(paths | {"tool/kr_representative_identity/unreviewed.py"}),
            "windows",
        )

    def test_portable_allowlist_and_empty_are_conservative(self):
        for path in pr_scope.PORTABLE:
            with self.subTest(path=path):
                self.assertEqual(pr_scope.classify_paths([path]), "portable")
        self.assertEqual(pr_scope.classify_paths([]), "windows")
        self.assertEqual(pr_scope.classify_paths(["README.md"]), "windows")

    def test_windows_native_dart_unknown_and_mixed_changes_require_windows(self):
        for path in ("windows/runner/main.cpp", "native/src/core/cli.cpp", "lib/main.dart",
                     "new-file.py", "tool/kr_factor_ocr/windows_helper.py", "test/fixtures/other.json"):
            with self.subTest(path=path):
                self.assertEqual(pr_scope.classify_paths(["tool/kr_factor_ocr/kr_factor_cli.py", path]), "windows")

    def test_only_workflow_routing_metadata_can_be_portable(self):
        self.assertEqual(classify_workflow(workflow(), routed_workflow()), "portable")
        self.assertEqual(pr_scope.windows_contract(workflow()), pr_scope.windows_contract(routed_workflow()))

    def test_windows_execution_changes_new_deleted_runner_or_matrix_require_windows(self):
        changes = [
            routed_workflow().replace("echo checked", "echo changed", 1),
            routed_workflow().replace("windows-2022", "windows-2025", 1),
            routed_workflow().replace("timeout-minutes: 20", "timeout-minutes: 30", 1),
            routed_workflow().replace("    timeout-minutes: 20", "    strategy:\n      matrix:\n        item: [1, 2]", 1),
            routed_workflow() + "  new-windows:\n    runs-on: windows-2022\n    steps:\n      - run: echo extra\n",
            routed_workflow().replace("windows-2022", "ubuntu-latest", 1),
            routed_workflow().replace("windows-2022", "${{ matrix.os }}", 1),
            routed_workflow().replace("    steps:\n", "    steps:\n      - if: false\n        run: echo changed\n", 1),
        ]
        for after in changes:
            with self.subTest(after=after):
                self.assertEqual(classify_workflow(workflow(), after), "windows")

    def test_workflow_failure_duplicate_job_or_missing_blob_is_not_portable(self):
        for after in (None, "jobs: {}", routed_workflow() + "  scope:\n    runs-on: ubuntu-latest\n"):
            self.assertEqual(classify_workflow(workflow(), after), "windows")
        self.assertEqual(classify_workflow(None, routed_workflow()), "windows")

    def test_job_routing_continuation_and_comments_do_not_change_execution(self):
        after = routed_workflow().replace("    needs: scope", "    needs:\n      - scope", 1)
        after = after.replace("    runs-on: windows-2022", "    # explanatory routing comment\n    runs-on: windows-2022", 1)
        self.assertEqual(pr_scope.windows_contract(workflow()), pr_scope.windows_contract(after))

    def test_root_env_defaults_permissions_events_and_concurrency_require_windows(self):
        additions = (
            "env:\n  WINDOWS_SETTING: changed\n",
            "defaults:\n  run:\n    shell: pwsh\n",
            "permissions:\n  contents: write\n",
            "on:\n  workflow_dispatch:\n",
            "concurrency:\n  group: changed\n  cancel-in-progress: true\n",
        )
        for header in additions:
            with self.subTest(header=header):
                after = routed_workflow().replace("jobs:\n", header + "jobs:\n", 1)
                self.assertEqual(classify_workflow(workflow(), after), "windows")
        before = workflow().replace("jobs:\n", "on:\n  pull_request:\n    branches: [develop]\nconcurrency:\n  group: ci\njobs:\n")
        after = before.replace("pull_request:", "workflow_dispatch:")
        self.assertEqual(classify_workflow(before, after), "windows")
        self.assertEqual(classify_workflow(before, before.replace("group: ci", "group: other")), "windows")

    def test_header_comments_and_blank_lines_remain_portable(self):
        after = "# Added explanation\n\n" + routed_workflow().replace("jobs:\n", "# Route by scope\n\njobs:\n", 1)
        self.assertEqual(classify_workflow(workflow(), after), "portable")

    def test_unsupported_or_duplicate_header_mapping_routes_windows(self):
        for header in ("? unsupported\n", "\tbad: value\n", "name: duplicate\n"):
            after = routed_workflow().replace("jobs:\n", header + "jobs:\n", 1)
            self.assertEqual(classify_workflow(workflow(), after), "windows")

    def test_only_warm_routing_preserves_the_windows_contract(self):
        before = warm_workflow()
        after = pr_scope.warm_job_concurrency(before)
        after = after.replace("    runs-on:", "    needs: scope\n    if: needs.scope.outputs.windows == 'true'\n    runs-on:")
        after += "  scope:\n    runs-on: ubuntu-latest\n    steps:\n      - run: classify\n"
        cli = "tool/kr_factor_ocr/kr_factor_cli.py"
        workflows = {pr_scope.WORKFLOW: (workflow(), routed_workflow()), pr_scope.WARM_WORKFLOW: (before, after)}
        self.assertEqual(pr_scope.classify_paths([cli, *workflows], workflows), "portable")
        self.assertEqual(pr_scope.classify_paths([cli, *workflows, "pubspec.lock"], workflows), "windows")
        for changed in (None, after.replace("echo warmed", "echo changed"),
                        after.replace("[develop]", "[main]"), after.replace("windows-2022", "windows-2025"),
                        after.replace("cancel-in-progress: true", "cancel-in-progress: false")):
            with self.subTest(changed=changed):
                self.assertEqual(classify_workflow(before, changed, pr_scope.WARM_WORKFLOW), "windows")


class GitScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git("init", "-q")
        (self.root / ".git/info/exclude").write_text("output\n")
        self.write("tool/kr_factor_ocr/README.md", "before\n")
        self.write("outside.txt", "move me\n")
        self.base = self.commit()

    def git(self, *args):
        return subprocess.check_output(["git", "-c", "user.name=Routing test", "-c", "user.email=test@example.invalid", *args], cwd=self.root).decode().strip()

    def write(self, name, value):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value)

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "Synthetic routing fixture")
        return self.git("rev-parse", "HEAD")

    def classify(self, head):
        output = self.root / "output"
        result = subprocess.run([sys.executable, "-B", str(Path(pr_scope.__file__).resolve()), "classify",
                                 "--base", self.base, "--head", head], cwd=self.root,
                                env={**os.environ, "GITHUB_OUTPUT": str(output)}, capture_output=True, text=True)
        return result, output

    def test_flutter_requires_the_full_reviewed_regular_file_delta(self):
        paths = list(pr_scope.FLUTTER_ADMISSION)
        old = {path: b"reviewed baseline\n" for path in paths[:-1]}
        new = {path: b"reviewed candidate\n" for path in paths}
        for path, data in old.items():
            self.write(path, data.decode())
        base = self.commit()
        for path, data in new.items():
            self.write(path, data.decode())
        head = self.commit()
        def pin(data):
            return sha256(data).hexdigest()

        pins = {p: (pin(old[p]) if p in old else None, pin(new[p])) for p in paths}

        def classify(base_ref, head_ref, *, push=False):
            return pr_scope.classify_refs(base_ref, head_ref, push=push)[0]

        with (patch.object(pr_scope, "FLUTTER_ADMISSION", pins),
              patch.object(pr_scope, "git", lambda *args: subprocess.check_output(["git", *args], cwd=self.root))):
            self.assertEqual(classify(base, head), "flutter")
            self.assertEqual(classify(base, head, push=True), "flutter")
            self.write("docs/ordinary-guide.md", "# Ordinary guide\n\nDocumentation companion.\n")
            with_manual = self.commit()
            self.assertEqual(classify(base, with_manual), "flutter")
            self.assertEqual(classify(base, with_manual, push=True), "flutter")
            self.write("tool/kr_factor_ocr/README.md", "portable companion\n")
            self.assertEqual(classify(base, self.commit()), "flutter")
            self.write("pubspec.lock", "dependency change\n")
            self.assertEqual(classify(base, self.commit()), "windows")

            self.git("checkout", "--detach", head)
            self.write(paths[0], "unreviewed edit\n")
            self.assertEqual(classify(base, self.commit()), "windows")

            self.git("checkout", "--detach", head)
            (self.root / paths[0]).chmod(0o755)
            self.assertEqual(classify(base, self.commit()), "windows")

            self.git("checkout", "--detach", head)
            (self.root / paths[-1]).rename(self.root / "outside_test.dart")
            self.assertEqual(classify(base, self.commit()), "windows")

            self.git("checkout", "--detach", head)
            (self.root / paths[-1]).unlink()
            self.assertEqual(classify(base, self.commit()), "windows")

            self.git("checkout", "--detach", base)
            self.write("outside.txt", "base branch drift\n")
            divergent = self.commit()
            self.assertEqual(classify(divergent, head), "flutter")
            self.assertEqual(classify(divergent, head, push=True), "windows")

    def test_bootstrap_requires_its_complete_support_diff_and_keeps_windows_contract(self):
        paths = pr_scope.FLUTTER_BOOTSTRAP_PATHS
        workflows = {pr_scope.WORKFLOW: (workflow(), routed_workflow())}
        self.assertEqual(pr_scope.classify_paths(paths, workflows), "flutter-bootstrap")
        self.assertEqual(pr_scope.classify_paths(paths - {"tool/ci/test_pr_scope.py"}, workflows), "portable")
        workflows[pr_scope.WORKFLOW] = (workflow(), routed_workflow().replace("echo checked", "echo changed"))
        self.assertEqual(pr_scope.classify_paths(paths, workflows), "windows")

    def test_actual_git_cli_outputs_and_deleted_portable_file(self):
        (self.root / "tool/kr_factor_ocr/README.md").unlink()
        result, output = self.classify(self.commit())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["lane"], "portable")
        self.assertEqual(output.read_text(), "lane=portable\nwindows=false\n")

    def test_rename_from_outside_stays_windows_with_no_rename_detection(self):
        self.git("mv", "outside.txt", "tool/kr_factor_ocr/kr_factor_cli.py")
        result, output = self.classify(self.commit())
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["lane"], "windows")
        self.assertIn("outside.txt", value["changed_paths"])
        self.assertIn("windows=true", output.read_text())

    def test_ref_arguments_are_full_commit_shas(self):
        with self.assertRaises(ValueError):
            pr_scope.classify_refs("--help", self.base)

    def test_push_compares_endpoint_trees_even_when_refs_diverge(self):
        self.write("tool/kr_factor_ocr/README.md", "after\n")
        portable_head = self.commit()
        self.git("checkout", "--detach", self.base)
        self.write("windows/runner.cpp", "mixed change\n")
        previous_push = self.commit()
        script = str(Path(pr_scope.__file__).resolve())
        args = [sys.executable, "-B", script, "classify", "--base", previous_push, "--head", portable_head]
        for flags, expected in (([], "portable"), (["--push"], "windows")):
            result = subprocess.check_output([*args, *flags], cwd=self.root)
            self.assertEqual(json.loads(result)["lane"], expected)

    def test_portable_merge_tree_skips_warming(self):
        branch = self.git("symbolic-ref", "--short", "HEAD")
        self.git("checkout", "-qb", "portable")
        self.write("tool/kr_factor_ocr/README.md", "after\n")
        self.commit()
        self.git("checkout", branch)
        self.git("merge", "--no-ff", "--no-edit", "portable")
        merge_sha = self.git("rev-parse", "HEAD")
        result = subprocess.check_output(
            [sys.executable, "-B", str(Path(pr_scope.__file__).resolve()), "classify",
             "--push", "--base", self.base, "--head", merge_sha], cwd=self.root)
        self.assertEqual(json.loads(result)["lane"], "portable")

    def test_docs_pr_push_merge_and_checker_use_the_exact_guidance_diff(self):
        self.write("AGENTS.md", guidance_text())
        self.base = self.commit()
        self.write("AGENTS.md", guidance_text(value="Updated continuity"))
        head = self.commit()
        result, output = self.classify(head)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["lane"], "docs")
        self.assertEqual(output.read_text(), "lane=docs\nwindows=false\n")
        script = str(Path(pr_scope.__file__).resolve())
        for command in ("classify", "check-docs"):
            value = subprocess.run([sys.executable, "-B", script, command, "--push", "--base", self.base,
                                    "--head", head], cwd=self.root, capture_output=True, text=True)
            self.assertEqual(value.returncode, 0, value.stderr)
        self.git("checkout", "-qb", "docs-target", self.base)
        self.git("merge", "--no-ff", "--no-edit", head)
        merge = self.git("rev-parse", "HEAD")
        value = subprocess.check_output([sys.executable, "-B", script, "classify", "--push", "--base", self.base,
                                         "--head", merge], cwd=self.root)
        self.assertEqual(json.loads(value)["lane"], "docs")

    def test_added_deleted_or_renamed_guidance_file_is_not_docs(self):
        self.write("AGENTS.md", guidance_text())
        added = self.commit()
        self.assertEqual(json.loads(self.classify(added)[0].stdout)["lane"], "windows")
        self.base = added
        self.git("mv", "AGENTS.md", "elsewhere.md")
        renamed = self.commit()
        self.assertEqual(json.loads(self.classify(renamed)[0].stdout)["lane"], "windows")
        self.git("checkout", "--detach", added)
        (self.root / "AGENTS.md").unlink()
        deleted = self.commit()
        self.assertEqual(json.loads(self.classify(deleted)[0].stdout)["lane"], "windows")

    def test_executable_guidance_is_not_docs(self):
        self.write("AGENTS.md", guidance_text())
        self.base = self.commit()
        self.git("update-index", "--chmod=+x", "AGENTS.md")
        self.git("commit", "-qm", "Executable Markdown fixture")
        head = self.git("rev-parse", "HEAD")
        self.assertEqual(json.loads(self.classify(head)[0].stdout)["lane"], "windows")

    def test_unrelated_product_whitespace_is_not_a_documentation_check(self):
        self.write("product.cpp", "trailing whitespace  \n")
        head = self.commit()
        result = subprocess.run([sys.executable, "-B", str(Path(pr_scope.__file__).resolve()), "check-docs",
                                 "--base", self.base, "--head", head], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("not applicable", result.stdout)

    def test_pr_blob_comparison_uses_merge_base_and_push_keeps_divergent_changes(self):
        self.write("AGENTS.md", guidance_text())
        common = self.commit()
        self.write("AGENTS.md", guidance_text(value="Docs branch"))
        head = self.commit()
        self.git("checkout", "--detach", common)
        self.write("AGENTS.md", guidance_text().replace("Keep product checks.", "Different protected rules."))
        self.base = self.commit()
        result, _ = self.classify(head)
        self.assertEqual(json.loads(result.stdout)["lane"], "docs")
        result = subprocess.check_output([sys.executable, "-B", str(Path(pr_scope.__file__).resolve()), "classify",
                                          "--push", "--base", self.base, "--head", head], cwd=self.root)
        self.assertEqual(json.loads(result)["lane"], "windows")

    def test_checker_reports_missing_link_and_invalid_utf8_without_network(self):
        self.write("AGENTS.md", guidance_text())
        self.base = self.commit()
        script = str(Path(pr_scope.__file__).resolve())
        for contents in (guidance_text(value="[bad](missing.md)").encode(), b"\xff"):
            (self.root / "AGENTS.md").write_bytes(contents)
            head = self.commit()
            result = subprocess.run([sys.executable, "-B", script, "check-docs", "--base", self.base,
                                     "--head", head], cwd=self.root, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_unavailable_and_empty_diff_do_not_claim_docs_success(self):
        result, _ = self.classify(self.base)
        self.assertEqual(json.loads(result.stdout)["lane"], "windows")
        result, _ = self.classify("f" * 40)
        self.assertNotEqual(result.returncode, 0)


    def docs_command(self, command, base, head, *, push=False):
        args = [sys.executable, "-B", str(Path(pr_scope.__file__).resolve()), command,
                "--base", base, "--head", head]
        return subprocess.run([*args, *(["--push"] if push else [])], cwd=self.root,
                              capture_output=True, text=True)

    def assert_docs_range(self, base, head):
        for push in (False, True):
            with self.subTest(push=push):
                result = self.docs_command("classify", base, head, push=push)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["lane"], "docs")
                checked = self.docs_command("check-docs", base, head, push=push)
                self.assertEqual(checked.returncode, 0, checked.stderr)
                self.assertNotIn("not applicable", checked.stdout)

    def navigation_text(self, target="docs/windows-ocr-variants.md"):
        return ("# Agent guidance\n\n## Working rules\nKeep product checks.\n\n"
                "## Find the needed document\n\n| Need | Read next |\n| --- | --- |\n"
                f"| Windows local delivery | [Variants]({target}) |\n\n"
                "## Issue context and decision continuity\nRefresh actual evidence.\n")

    def test_new_and_existing_ordinary_manuals_need_no_per_file_admission(self):
        self.write("docs/user-guide.md", "# User guide\n\n## Setup\nOriginal instructions.\n")
        base = self.commit()
        self.write("docs/user-guide.md", "# User guide\n\n## Setup\nUpdated instructions.\n")
        self.write("docs/new-folder/new-manual.md", "# New manual\n\n[Setup](../user-guide.md#setup)\n")
        head = self.commit()
        self.assert_docs_range(base, head)
        self.git("checkout", "-qb", "manual-merge-target", base)
        self.git("merge", "--no-ff", "--no-edit", head)
        self.assert_docs_range(base, self.git("rev-parse", "HEAD"))

    def test_issue70_navigation_and_manual_shape_uses_docs_in_pr_and_push(self):
        self.write("AGENTS.md", self.navigation_text())
        self.write("docs/windows-ocr-variants.md", "# Windows variants\n\n## Local builds\nBuild instructions.\n")
        base = self.commit()
        self.write("AGENTS.md", self.navigation_text("docs/windows-ocr-variants.md#local-delivery"))
        self.write("docs/windows-ocr-variants.md", "# Windows variants\n\n## Local builds\nBuild instructions.\n\n"
                   "## Local delivery\nCopy the complete package after verification.\n")
        head = self.commit()
        self.assert_docs_range(base, head)
        for value in (self.navigation_text().replace("Keep product checks.", "Skip product checks."),
                      self.navigation_text().replace("\n## Issue context", "\nAdditional permission outside the table.\n\n## Issue context"),
                      self.navigation_text("docs/wasm-toolchain/build.sh"),
                      self.navigation_text("docs/windows-ocr-variants.md?disable_checks=true")):
            self.write("AGENTS.md", value)
            changed = self.commit()
            result = self.docs_command("classify", base, changed)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["lane"], "windows")

    def test_agents_only_navigation_checks_fragment_in_unchanged_manual(self):
        self.write("AGENTS.md", self.navigation_text())
        self.write("docs/windows-ocr-variants.md", "# Variants\n\n## Local delivery\nInstructions.\n")
        base = self.commit()
        self.write("AGENTS.md", self.navigation_text("docs/windows-ocr-variants.md#missing-section"))
        broken = self.commit()
        for push in (False, True):
            classified = self.docs_command("classify", base, broken, push=push)
            self.assertEqual(json.loads(classified.stdout)["lane"], "docs")
            checked = self.docs_command("check-docs", base, broken, push=push)
            self.assertNotEqual(checked.returncode, 0)
        self.write("AGENTS.md", self.navigation_text("docs/windows-ocr-variants.md#local-delivery"))
        self.assert_docs_range(base, self.commit())

    def test_ordinary_manual_mixtures_retain_restricted_and_portable_routes(self):
        self.write("docs/user-guide.md", "# Guide\n\nOriginal prose.\n")
        base = self.commit()
        restricted = ("lib/main.dart", "native/src/producer.cpp", "pubspec.yaml", "README.md",
                      "docs/agents/new-policy.md", "docs/validation/evidence.md", "docs/evidence.json",
                      "docs/fork-network-policy.md", "docs/korean-ui-localization.md",
                      "docs/wasm-toolchain/build.sh", "docs/nested/AGENTS.md", "docs/.private/note.md")
        for path in restricted:
            with self.subTest(path=path):
                self.git("checkout", "--detach", base)
                self.write("docs/user-guide.md", "# Guide\n\nChanged prose.\n")
                self.write(path, "Restricted content.\n")
                head = self.commit()
                for push in (False, True):
                    result = self.docs_command("classify", base, head, push=push)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout)["lane"], "windows")
        self.git("checkout", "--detach", base)
        self.write("docs/user-guide.md", "# Guide\n\nChanged prose.\n")
        self.write("tool/kr_factor_ocr/README.md", "Portable companion.\n")
        head = self.commit()
        for push in (False, True):
            result = self.docs_command("classify", base, head, push=push)
            self.assertEqual(json.loads(result.stdout)["lane"], "portable")

    def test_ordinary_manual_modes_symlinks_invalid_utf8_and_hidden_paths_are_not_docs(self):
        self.write("docs/user-guide.md", "# Guide\n\nPlain prose.\n")
        base = self.commit()
        for mode in ("executable", "symlink", "invalid-utf8"):
            with self.subTest(mode=mode):
                self.git("checkout", "--detach", base)
                path = self.root / "docs/user-guide.md"
                if mode == "executable":
                    path.chmod(0o755)
                elif mode == "symlink":
                    path.unlink()
                    path.symlink_to("../outside.txt")
                else:
                    path.write_bytes(b"# Guide\n\xff\n")
                head = self.commit()
                for push in (False, True):
                    result = self.docs_command("classify", base, head, push=push)
                    self.assertTrue(result.returncode != 0 or json.loads(result.stdout)["lane"] == "windows")

    def test_submodule_shaped_document_never_enters_docs_lane(self):
        self.git("update-index", "--add", "--cacheinfo", f"160000,{self.base},docs/module.md")
        self.git("commit", "-qm", "Gitlink documentation fixture")
        head = self.git("rev-parse", "HEAD")
        for push in (False, True):
            result = self.docs_command("classify", self.base, head, push=push)
            self.assertTrue(result.returncode != 0 or json.loads(result.stdout)["lane"] == "windows")

    def test_manual_links_and_fragments_are_checked_at_the_actual_head(self):
        self.write("docs/target guide.md", "# Target\n\n## Local delivery\nKeep original.\n"
                   "\n## Repeated\nFirst.\n\n## Repeated\nSecond.\n")
        base = self.commit()
        self.write("docs/user-guide.md", "# User guide\n\n[Local](target%20guide.md#local-delivery)\n"
                   "[Duplicate heading][second]\n\n[second]: target%20guide.md#repeated-1\n\n"
                   "[Self](#user-guide) [Remote](https://example.invalid/unavailable#missing)\n")
        good = self.commit()
        self.assert_docs_range(base, good)
        for target in ("missing.md", "target%20guide.md#missing", "#missing", "../../outside.md", "/../docs/target%20guide.md"):
            with self.subTest(target=target):
                self.git("checkout", "--detach", good)
                self.write("docs/user-guide.md", f"# User guide\n\n[Broken]({target})\n")
                head = self.commit()
                for push in (False, True):
                    result = self.docs_command("check-docs", base, head, push=push)
                    self.assertNotEqual(result.returncode, 0)

    def test_nested_list_and_root_links_in_changed_and_unchanged_documents(self):
        self.write("docs/target.md", "# Target\n")
        base = self.commit()
        readers = (("- One\n  - Two\n    - [Target](target.md)\n", 10),
                   ("[Target](/docs/target.md#target)\n", 4))
        for source, code_indent in readers:
            with self.subTest(source=source):
                self.git("checkout", "--detach", base)
                example = " " * code_indent + "[Example](missing.md)\n"
                self.write("docs/reader.md", source + "\n" + example)
                good = self.commit()
                self.assert_docs_range(base, good)
                self.write("docs/reader.md", source.replace("target.md", "missing.md"))
                bad = self.commit()
                for push in (False, True):
                    check = self.docs_command("check-docs", good, bad, push=push)
                    self.assertIn("missing local link target", check.stderr)
                for operation in ("delete", "rename"):
                    self.git("checkout", "--detach", good)
                    if operation == "delete":
                        (self.root / "docs/target.md").unlink()
                    else:
                        self.git("mv", "docs/target.md", "docs/moved.md")
                    head = self.commit()
                    for push in (False, True):
                        check = self.docs_command("check-docs", good, head, push=push)
                        self.assertIn("missing local link target", check.stderr)

    def test_deletion_rename_and_heading_edits_check_affected_inbound_links(self):
        self.write("docs/target.md", "# Target\n\n## Existing section\nOriginal prose.\n")
        self.write("docs/source.md", "# Source\n\n[Target](target.md#existing-section)\n"
                   "[Pre-existing unrelated issue](unrelated-missing.md)\n")
        base = self.commit()
        for operation in ("delete", "rename", "remove-heading"):
            with self.subTest(operation=operation):
                self.git("checkout", "--detach", base)
                if operation == "delete":
                    (self.root / "docs/target.md").unlink()
                elif operation == "rename":
                    self.git("mv", "docs/target.md", "docs/renamed.md")
                else:
                    self.write("docs/target.md", "# Target\n\n## New section\nUpdated prose.\n")
                head = self.commit()
                for push in (False, True):
                    classified = self.docs_command("classify", base, head, push=push)
                    self.assertEqual(json.loads(classified.stdout)["lane"], "docs")
                    checked = self.docs_command("check-docs", base, head, push=push)
                    self.assertNotEqual(checked.returncode, 0)
                self.write("docs/source.md", "# Source\n\n" +
                           ("Target retired.\n" if operation == "delete" else
                            "[Target](renamed.md#existing-section)\n" if operation == "rename" else
                            "[Target](target.md#new-section)\n"))
                self.assert_docs_range(base, self.commit())

    def test_unchanged_inbound_sources_ignore_unrelated_preexisting_link_errors(self):
        self.write("docs/target.md", "# Target\n\n## Existing section\nOriginal prose.\n")
        self.write("README.md", "# Root\n\n[Target](docs/target.md#existing-section)\n"
                   "[Unrelated pre-existing issue](missing.md)\n")
        base = self.commit()
        self.write("docs/target.md", "# Target\n\n## Existing section\nUpdated prose.\n")
        self.assert_docs_range(base, self.commit())

    def test_ordinary_docs_pr_merge_base_and_complete_push_range_remain_distinct(self):
        self.write("docs/user-guide.md", "# Guide\n\nBaseline prose.\n")
        common = self.commit()
        self.write("docs/user-guide.md", "# Guide\n\nNew prose.\n")
        head = self.commit()
        self.git("checkout", "--detach", common)
        self.write("native/changed.cpp", "Restricted branch change.\n")
        base = self.commit()
        pr = self.docs_command("classify", base, head)
        push = self.docs_command("classify", base, head, push=True)
        self.assertEqual(json.loads(pr.stdout)["lane"], "docs")
        self.assertEqual(json.loads(push.stdout)["lane"], "windows")


class GateTests(unittest.TestCase):
    def needs(self, lane, context):
        return {"scope": {"result": "success", "outputs": {"lane": lane}},
                "lightweight-checks": {"result": "success"},
                "cli-tests": {"result": "skipped" if lane == "docs" else "success"},
                **({"flutter-linux": {"result": "success" if lane in pr_scope.FLUTTER_LANES else "skipped"}}
                   if context == "flutter" else {}),
                **{name: {"result": "success" if lane == "windows" else "skipped"}
                   for name in pr_scope.WINDOWS_JOBS[context]}}

    def test_both_lanes_and_contexts_have_explicit_honest_success(self):
        for context in pr_scope.WINDOWS_JOBS:
            self.assertIn("not applicable", pr_scope.verify_gate(self.needs("portable", context), context))
            self.assertIn("Documentation checks passed", pr_scope.verify_gate(self.needs("docs", context), context))
            self.assertIn("Windows work", pr_scope.verify_gate(self.needs("windows", context), context))
        for lane in pr_scope.FLUTTER_LANES:
            self.assertIn("Linux Flutter", pr_scope.verify_gate(self.needs(lane, "flutter"), "flutter"))
            self.assertIn("native work is not applicable", pr_scope.verify_gate(self.needs(lane, "native"), "native"))

    def test_failed_missing_cancelled_or_skipped_prerequisites_fail(self):
        for lane in {"docs", "portable", "windows"} | pr_scope.FLUTTER_LANES:
            for context in pr_scope.WINDOWS_JOBS:
                for name in self.needs(lane, context):
                    expected = self.needs(lane, context)[name]["result"]
                    for state in (None, "failure", "cancelled", "skipped", "success"):
                        if state == expected:
                            continue
                        needs = self.needs(lane, context)
                        if state is None:
                            del needs[name]
                        else:
                            needs[name]["result"] = state
                        with self.subTest(lane=lane, context=context, name=name, state=state):
                            with self.assertRaises(ValueError):
                                pr_scope.verify_gate(needs, context)

    def test_unknown_route_and_invalid_gate_inputs_fail(self):
        needs = self.needs("portable", "native")
        for value in (None, [], "portable", {}, {"lane": "other"}):
            needs["scope"]["outputs"] = value
            with self.assertRaises(ValueError):
                pr_scope.verify_gate(needs, "native")
        with self.assertRaises(ValueError):
            pr_scope.verify_gate([], "native")

    def test_gate_subprocess_reads_needs_and_writes_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = Path(tmp) / "summary"
            result = subprocess.run([sys.executable, "-B", str(Path(pr_scope.__file__).resolve()), "gate", "--context", "flutter"],
                                    env={**os.environ, "NEEDS": json.dumps(self.needs("portable", "flutter")),
                                         "GITHUB_STEP_SUMMARY": str(summary)}, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("not applicable", summary.read_text())


class WorkflowWiringTests(unittest.TestCase):
    def test_cache_workflow_checks_push_scope_before_allocating_windows(self):
        path = Path(__file__).resolve().parents[2] / pr_scope.WARM_WORKFLOW
        header, jobs = path.read_text().split("\njobs:\n")
        self.assertIn("on:\n  push:\n    branches: [master]", header)
        self.assertNotIn("\nconcurrency:", header)
        scope, warm = jobs.split("\n  warm:\n")
        self.assertIn("    runs-on: ubuntu-latest", scope)
        self.assertIn("          fetch-depth: 0", scope)
        self.assertIn("          BEFORE_SHA: ${{ github.event.before }}", scope)
        self.assertIn("          AFTER_SHA: ${{ github.event.after }}", scope)
        self.assertIn('classify --push --base "$BEFORE_SHA" --head "$AFTER_SHA"', scope)
        self.assertIn("    needs: scope\n    if: needs.scope.outputs.windows == 'true'", warm)
        self.assertIn("    runs-on: windows-2022", warm)
        self.assertIn("    concurrency:\n      group: warm-caches-", warm)

    def test_actual_workflow_guards_every_windows_job_and_keeps_required_gates(self):
        path = Path(os.environ.get("CI_WORKFLOW_UNDER_TEST", Path(__file__).resolve().parents[2] / ".github/workflows/ci.yml"))
        self.assertIn("on:\n  pull_request:\n    branches: [master]", path.read_text())
        blocks, current = {}, None
        for line in path.read_text().splitlines():
            match = re.fullmatch(r"  ([A-Za-z_][A-Za-z0-9_-]*):", line)
            if match:
                current = match[1]
                self.assertNotIn(current, blocks)
                blocks[current] = []
            elif current is not None:
                blocks[current].append(line)
        windows = {key for key, lines in blocks.items() if any(line.startswith("    runs-on: windows-") for line in lines)}
        expected_windows = {"native-tests-windows", "native-coverage", *pr_scope.WINDOWS_JOBS["flutter"]}
        self.assertEqual(windows, expected_windows)
        for name in windows:
            with self.subTest(windows_job=name):
                self.assertIn("    needs: scope", blocks[name])
                self.assertIn("    if: needs.scope.outputs.windows == 'true'", blocks[name])
        for context, job in (("native", "native-tests"), ("flutter", "flutter-tests")):
            lines = blocks[job]
            name = "Native C++ tests (doctest)" if context == "native" else "Flutter unit/widget tests"
            self.assertIn(f"    name: {name}", lines)
            need_lines = [line for line in lines if line.startswith("    needs:")]
            self.assertEqual(len(need_lines), 1)
            needs = {item.strip() for item in need_lines[0].split(":", 1)[1].strip().strip("[]").split(",")}
            expected = {"scope", "lightweight-checks", "cli-tests", *pr_scope.WINDOWS_JOBS[context]}
            if context == "flutter":
                expected.add("flutter-linux")
            self.assertEqual(needs, expected)
            self.assertIn("    if: always()", lines)
            self.assertIn("    runs-on: ubuntu-latest", lines)
            self.assertIn(f"        run: python3 tool/ci/pr_scope.py gate --context {context}", lines)
        linux = "\n".join(blocks["flutter-linux"])
        self.assertIn("    runs-on: ubuntu-latest", linux)
        self.assertIn("    needs: scope", linux)
        self.assertIn("outputs.lane == 'flutter' || needs.scope.outputs.lane == 'flutter-bootstrap'", linux)
        scope = "\n".join(blocks["scope"])
        self.assertRegex(scope, r"uses: actions/checkout@[^\n]+\n        with:\n          fetch-depth: 0")
        lightweight = "\n".join(blocks["lightweight-checks"])
        self.assertIn("    needs: scope", lightweight)
        self.assertIn("          fetch-depth: 0", lightweight)
        self.assertIn('check-docs --base "$BASE_SHA" --head "$HEAD_SHA"', lightweight)
        self.assertIn("    needs: scope", blocks["cli-tests"])
        self.assertIn("    if: needs.scope.outputs.lane != 'docs'", blocks["cli-tests"])


if __name__ == "__main__":
    unittest.main()
