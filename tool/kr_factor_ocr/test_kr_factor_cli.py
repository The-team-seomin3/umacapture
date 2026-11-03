"""Synthetic explicit-config/preflight/report regressions; no owner inputs or inference."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import unittest
from unittest.mock import patch

import kr_factor_app as app
import kr_factor_cli as cli
import kr_factor_ocr as kr
import test_kr_factor_app as fixtures


class CliWorkflow(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.AppAdapter()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.root = self.f.fixture.root
        self.request = dict(self.f.request)
        self.config = self.root / "settings.json"
        self.override = self.root / "overrides.json"
        self.config.write_text(json.dumps({**self.request, "interpreter": sys.executable,
                                          "adapter": str(Path(app.__file__).resolve()),
                                          "output_root": str(self.root / "results")}))
        self.override.write_text('{}')
        # Metadata availability is tested independently of this test runner's installed wheels.
        self.versions = {k: v[0] for k, v in cli.PINS.items()}
        self.patch_version = patch.object(cli.importlib.metadata, "version", side_effect=self.versions.__getitem__)
        self.patch_spec = patch.object(cli.importlib.util, "find_spec", return_value=object())
        self.patch_version.start()
        self.patch_spec.start()
        self.addCleanup(self.patch_version.stop)
        self.addCleanup(self.patch_spec.stop)

    def call(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = app.main(list(args))
        self.assertEqual(len(stdout.getvalue().splitlines()), 1)
        return code, json.loads(stdout.getvalue())

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): ("directory" if p.is_dir() else p.read_bytes())
                for p in self.root.rglob('*')}

    def preflight(self, target="run"):
        return self.call("preflight", "--for", target, "--config", str(self.config))

    def test_config_reuses_actual_flat_settings_with_explicit_request_precedence(self):
        self.override.write_text(json.dumps({"working_dir": str(self.root / "selected-run")}))
        saved = self.config.read_bytes()
        code, value = self.call("run", "--config", str(self.config), "--request", str(self.override))
        self.assertEqual(code, 2, value)
        self.assertEqual(value["working_dir"], str(self.root / "selected-run"))
        self.assertFalse(self.f.work.exists())
        self.assertEqual(self.config.read_bytes(), saved)
        self.assertEqual(self.f.call("load", {**self.request, "working_dir": value["working_dir"]})[0], 2)

    def test_request_merge_is_deterministic_without_mutating_inputs(self):
        config = {"capture": str(self.root), "master_sha256": "A" * 64}
        override = {"working_dir": str(self.root / "new")}
        a = cli.build_request(config, override, "run")
        b = cli.build_request(dict(reversed(list(config.items()))), override, "run")
        self.assertEqual(list(a), sorted(a))
        self.assertEqual(a, b)
        self.assertEqual(config["master_sha256"], "A" * 64)

    def test_strict_schema_types_paths_unknown_keys_and_bad_json(self):
        for bad in ({"schema_version": True}, {"schema_version": 2}, {"capture": 4},
                    {"capture": "relative"}, {"master_sha256": "oops"}, {"secret": "never-store"}):
            self.override.write_text(json.dumps(bad))
            code, value = self.call("run", "--config", str(self.config), "--request", str(self.override))
            self.assertEqual(code, 1, value)
            self.assertEqual(value["stage"], "configuration")
            self.assertTrue(value["issues"])
            self.assertFalse(self.f.work.exists())
        for text in ('{"capture": "a", "capture":"b"}', '{"schema_version":NaN}', '[]', '{bad'):
            self.override.write_text(text)
            self.assertEqual(self.call("run", "--config", str(self.override))[0], 1)
        for data in ({"star": True}, {"offset": -1}, {"limit": 0}, {"query": None}):
            with self.assertRaises(cli.ConfigurationError):
                cli.build_request({}, data, "lookup")

    def test_preflight_success_has_zero_mutations_and_no_inference_or_database_loader(self):
        before = self.snapshot()
        with patch.object(kr, "run", side_effect=AssertionError("No inference")), \
             patch.object(kr, "load_master", side_effect=AssertionError("No database copy/query")):
            code, value = self.preflight()
        self.assertEqual(code, 0, value)
        self.assertEqual(value["failed_checks"], 0)
        self.assertFalse(value["completed"])
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.f.work.exists())
        self.assertTrue(value["not_tested"])
        self.f.inference.assert_not_called()

    def test_multiple_failures_aggregate_paths_pins_module_and_runtime(self):
        data = json.loads(self.config.read_text())
        data.update(model=str(self.root / "absent.onnx"), master_sha256="0" * 64,
                    module_version=str(self.root / "absent-module.json"))
        self.config.write_text(json.dumps(data))
        self.versions['rapidocr'] = '0.0.0'
        before = self.snapshot()
        code, value = self.preflight()
        self.assertEqual(code, 1)
        self.assertGreaterEqual(value["failed_checks"], 4)
        failures = [c for c in value["checks"] if c["status"] == "failed"]
        self.assertTrue(all(c["action"] for c in failures))
        self.assertIn("rapidocr", {c['field'] for c in failures})
        self.assertEqual(before, self.snapshot())

    def test_runtime_discovery_failure_is_not_a_pass(self):
        self.patch_spec.stop()
        with patch.object(cli.importlib.util, "find_spec", return_value=None):
            code, result = self.preflight()
        self.assertEqual(code, 1)
        self.assertTrue(any(c['stage'] == 'runtime' and c['status'] == 'failed' for c in result['checks']))

    def test_fresh_resume_partial_and_lock_states_are_nonmutating(self):
        self.assertEqual(self.preflight("load")[0], 1)
        self.f.start()
        before = self.snapshot()
        self.assertEqual(self.preflight()[0], 1)
        self.assertEqual(self.preflight("load")[0], 0)
        self.assertEqual(before, self.snapshot())
        lock = self.f.work / '.review.json.lock'
        lock.write_text('retain')
        before = self.snapshot()
        self.assertEqual(self.preflight("load")[0], 1)
        self.assertEqual(before, self.snapshot())
        partial = self.root / "partial"
        partial.mkdir()
        self.override.write_text(json.dumps({"working_dir": str(partial)}))
        self.assertEqual(self.call("preflight", "--for", "load", "--config", str(self.config),
                                   "--request", str(self.override))[0], 1)

    def test_preflight_metadata_wal_and_corrupt_capture_fail_without_changes(self):
        module = Path(self.request['module_version'])
        data = json.loads(module.read_text()); data['region'] = 'incompatible'
        module.write_text(json.dumps(data))
        Path(self.request['master'] + '-wal').write_bytes(b'pending')
        (Path(self.request['capture']) / 'factor.png').write_bytes(b'broken')
        before = self.snapshot()
        code, result = self.preflight()
        self.assertEqual(code, 1)
        self.assertGreaterEqual(result['failed_checks'], 3)
        self.assertEqual(before, self.snapshot())

    def test_preflight_rejects_redirected_work_and_protected_overlap(self):
        redirected = self.root / 'redirect'
        redirected.symlink_to(self.f.fixture.source, target_is_directory=True)
        for path in (redirected, self.f.fixture.source):
            self.override.write_text(json.dumps({'working_dir': str(path)}))
            before = self.snapshot()
            self.assertEqual(self.call('preflight', '--config', str(self.config), '--request', str(self.override))[0], 1)
            self.assertEqual(before, self.snapshot())

    def test_preflight_export_checks_existing_output_and_evidence_without_writes(self):
        self.f.start()
        output = self.root / 'result' / 'record-kr.json'
        output.parent.mkdir(); output.write_text('keep-output')
        evidence = self.root / 'evidence'
        evidence.mkdir()
        self.override.write_text(json.dumps({'output': str(output), 'evidence_output': str(evidence)}))
        before = self.snapshot()
        code, value = self.call('preflight', '--for', 'export', '--config', str(self.config), '--request', str(self.override))
        self.assertEqual(code, 1)
        self.assertTrue({'output', 'evidence_output'} <= {c['field'] for c in value['checks'] if c['status'] == 'failed'})
        self.assertEqual(before, self.snapshot())

    def test_report_exclusive_private_hash_receipt_has_no_raw_request_or_unknown_values(self):
        reports = self.root / 'reports'; reports.mkdir()
        report = reports / 'run.json'
        request = self.root / 'request.json'
        request.write_text(json.dumps({**self.request, 'unrelated_token': 'TOP_SECRET'}))
        code, value = self.call('run', '--request', str(request), '--report', str(report))
        self.assertEqual(code, 2, value)
        receipt = json.loads(report.read_text())
        self.assertEqual(receipt['exit_code'], 2)
        self.assertIn('adapter', receipt['files'])
        self.assertEqual(len(receipt['request_sha256']), 64)
        self.assertNotIn('TOP_SECRET', report.read_text())
        self.assertEqual(stat.S_IMODE(report.stat().st_mode), 0o600)
        before = self.snapshot()
        self.assertEqual(self.call('run', '--request', str(request), '--report', str(report))[0], 1)
        self.assertEqual(before, self.snapshot())

    def test_preflight_export_accepts_valid_destinations_without_accepting_review(self):
        self.f.start()
        output = self.f.fixture.source / 'record-kr.json'
        self.override.write_text(json.dumps({'output': str(output), 'evidence_output': str(self.root/'new-evidence')}))
        before = self.snapshot()
        code, value = self.call('preflight', '--for', 'export', '--config', str(self.config), '--request', str(self.override))
        self.assertEqual(code, 0, value)
        self.assertFalse(value['completed'])
        self.assertNotIn('ready_to_export', value)
        self.assertEqual(before, self.snapshot())

    def test_preflight_lookup_needs_only_lookup_inputs_and_does_not_write(self):
        self.override.write_text(json.dumps({k: self.request[k] for k in
                                           ('master', 'master_sha256', 'factor_info', 'factor_info_sha256')}))
        before = self.snapshot()
        code, value = self.call('preflight', '--for', 'lookup', '--request', str(self.override))
        self.assertEqual(code, 0, value)
        self.assertEqual(before, self.snapshot())

    def test_save_preflight_requires_current_review_hash_without_changing_draft(self):
        result = self.f.start()
        self.assertEqual(self.preflight('save-review')[0], 1)
        data = {'review': result['review'], 'expected_review_sha256': result['review_sha256']}
        for pin, expected in ((result['review_sha256'], 0), ('0' * 64, 1), (True, 1)):
            self.override.write_text(json.dumps({**data, 'expected_review_sha256': pin}))
            before = self.snapshot()
            code, value = self.call('preflight', '--for', 'save-review', '--config', str(self.config), '--request', str(self.override))
            self.assertEqual(code, expected, value)
            self.assertEqual(before, self.snapshot())

    def test_report_refuses_input_work_symlink_and_preflight_destinations(self):
        for path in (self.f.fixture.source / 'record.json', self.f.work / 'report.json',
                     self.root / 'results' / 'report.json', self.config):
            before = self.snapshot()
            self.assertEqual(self.call('run', '--config', str(self.config), '--report', str(path))[0], 1)
            self.assertEqual(before, self.snapshot())
        reports = self.root / 'reports'; reports.mkdir()
        linked = self.root / 'linked'; linked.symlink_to(reports, target_is_directory=True)
        self.assertEqual(self.call('run', '--config', str(self.config), '--report', str(linked/'report.json'))[0], 1)
        self.assertEqual(self.call('preflight', '--config', str(self.config), '--report', str(reports/'report.json'))[0], 1)
        self.assertEqual(list(reports.iterdir()), [])

    def test_report_records_failure_and_write_failure_does_not_change_completed_operation(self):
        reports = self.root / 'reports'; reports.mkdir()
        report = reports / 'failure.json'
        self.f.work.mkdir()
        code, result = self.call('run', '--config', str(self.config), '--report', str(report))
        self.assertEqual(code, 1)
        self.assertEqual(result['stage'], 'dispatch')
        self.assertEqual(json.loads(report.read_text())['exit_code'], 1)
        summary = json.loads(report.read_text())['diagnostic']
        self.assertEqual(summary['error_type'], 'FileExistsError')
        self.assertEqual(summary['error_code'], 'dispatch_failed')
        self.assertEqual(summary['action'], result['action'])
        with patch.object(cli, 'report_value', side_effect=OSError('disk failure')), \
             patch.object(app, 'dispatch', return_value={'status': 'completed', 'completed': True}):
            code, result = self.call('export', '--config', str(self.config), '--report', str(reports/'partial.json'))
        self.assertEqual(code, 0)
        self.assertTrue(result['completed'])
        self.assertIn('report_error', result)

    def test_real_cli_subprocess_preflight_json_and_nonmutation(self):
        self.override.write_text(json.dumps({k: self.request[k] for k in
                                           ('master', 'master_sha256', 'factor_info', 'factor_info_sha256')}))
        before = self.snapshot()
        result = subprocess.run([sys.executable, str(Path(app.__file__)), 'preflight', '--for', 'lookup',
                                 '--request', str(self.override)], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(len(result.stdout.splitlines()), 1)
        self.assertEqual(json.loads(result.stdout)['command'], 'preflight')
        self.assertEqual(before, self.snapshot())
        self.override.write_text(json.dumps(self.request))
        before = self.snapshot()
        result = subprocess.run([sys.executable, str(Path(app.__file__)), 'preflight', '--for', 'run',
                                 '--request', str(self.override)], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 1)
        value = json.loads(result.stdout)
        # The subprocess retains the production pin; the synthetic model is intentionally rejected.
        self.assertEqual([c['field'] for c in value['checks'] if c['status'] == 'failed'], ['model_sha256'])
        for c in value['checks']:
            if c['field'] in cli.PINS:
                self.assertEqual(c['status'], 'passed', c)
        self.assertEqual(before, self.snapshot())


if __name__ == '__main__':
    unittest.main()
