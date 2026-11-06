"""Routing/gate regressions: no Windows tools, network or third-party packages."""
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

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


class ScopeTests(unittest.TestCase):
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


class GateTests(unittest.TestCase):
    def needs(self, lane, context):
        return {"scope": {"result": "success", "outputs": {"lane": lane}},
                "cli-tests": {"result": "success"},
                **{name: {"result": "skipped" if lane == "portable" else "success"}
                   for name in pr_scope.WINDOWS_JOBS[context]}}

    def test_both_lanes_and_contexts_have_explicit_honest_success(self):
        for context in pr_scope.WINDOWS_JOBS:
            self.assertIn("not applicable", pr_scope.verify_gate(self.needs("portable", context), context))
            self.assertIn("Windows work", pr_scope.verify_gate(self.needs("windows", context), context))

    def test_failed_missing_cancelled_or_skipped_prerequisites_fail(self):
        for lane in ("portable", "windows"):
            for context in pr_scope.WINDOWS_JOBS:
                for name in ("scope", "cli-tests", *pr_scope.WINDOWS_JOBS[context]):
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
        self.assertIn("on:\n  push:\n    branches: [develop]", header)
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
            self.assertEqual(needs, {"scope", "cli-tests", *pr_scope.WINDOWS_JOBS[context]})
            self.assertIn("    if: always()", lines)
            self.assertIn("    runs-on: ubuntu-latest", lines)
            self.assertIn(f"        run: python3 tool/ci/pr_scope.py gate --context {context}", lines)
        scope = "\n".join(blocks["scope"])
        self.assertRegex(scope, r"uses: actions/checkout@[^\n]+\n        with:\n          fetch-depth: 0")


if __name__ == "__main__":
    unittest.main()
