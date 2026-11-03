import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:umacapture/src/core/kr_factor_workflow.dart';

class _Transport implements KrCommandTransport {
  late Future<KrProcessOutput> Function(String, List<String>) run;
  @override
  Future<KrProcessOutput> execute(String executable, List<String> arguments) => run(executable, arguments);
  @override
  Future<void> cancel() async {}
}

void main() {
  late Directory root;
  late File python;
  late File script;
  late _Transport transport;
  late KrFactorAdapter adapter;
  setUp(() {
    root = Directory.systemTemp.createTempSync('kr-service-');
    python = File(p.join(root.path, 'local python.exe'))..writeAsStringSync('synthetic');
    script = File(p.join(root.path, 'adapter & literal.py'))..writeAsStringSync('synthetic');
    transport = _Transport();
    adapter = KrFactorAdapter(transport);
  });
  tearDown(() => root.deleteSync(recursive: true));
  Future<KrAdapterResponse> invoke(String command, [Map<String, dynamic> request = const {}]) =>
      adapter.execute(interpreter: python.path, adapter: script.path, command: command, request: request);
  KrProcessOutput response(int code, Map<String, dynamic> data) =>
      (exitCode: code, stdout: jsonEncode(data), stderr: '');
  Map<String, dynamic> envelope(String command, String status) => {
    'schema_version': 1,
    'command': command,
    'status': status,
    'completed': status == 'completed',
  };

  test('preserves executable/argv and JSON paths; exit 2 is Needs review', () async {
    String? requestPath;
    transport.run = (exe, args) async {
      expect(exe, python.path);
      expect(args.take(3), [script.path, 'run', '--request']);
      requestPath = args.last;
      final request = jsonDecode(File(requestPath!).readAsStringSync());
      expect(request['capture'], r'C:\private folder\한글 & $name');
      return response(2, envelope('run', 'needs_review'));
    };
    final actual = await invoke('run', {'capture': r'C:\private folder\한글 & $name'});
    expect(actual.needsReview, isTrue);
    expect(actual.completed, isFalse);
    expect(File(requestPath!).existsSync(), isFalse);
  });
  test('nonzero error and malformed/mismatched JSON never signal completion', () async {
    for (final result in [
      response(1, {...envelope('run', 'error'), 'message': 'missing model'}),
      response(0, envelope('export', 'completed')),
      response(2, envelope('run', 'ok')),
      (exitCode: 0, stdout: 'not JSON', stderr: 'dependency error'),
    ]) {
      transport.run = (_, _) async => result;
      await expectLater(invoke('run'), throwsA(isA<KrAdapterException>()));
    }
  });
  test('missing interpreter is surfaced before invoking any process', () async {
    python.deleteSync();
    transport.run = (_, _) async => throw StateError('must not execute');
    await expectLater(invoke('run'), throwsA(isA<KrAdapterException>()));
  });
  test('export success requires the requested published bytes and exact SHA256', () async {
    final output = File(p.join(root.path, 'record-kr.json'))..writeAsStringSync('{"original_shape":true}');
    final before = output.readAsBytesSync();
    var reported = 'wrong';
    transport.run = (_, _) async =>
        response(0, {...envelope('export', 'completed'), 'output': output.path, 'output_sha256': reported});
    await expectLater(invoke('export', {'output': output.path}), throwsA(isA<KrAdapterException>()));
    expect(output.readAsBytesSync(), before);
    reported = sha256.convert(before).toString();
    expect((await invoke('export', {'output': output.path})).completed, isTrue);
    await expectLater(
      invoke('export', {'output': p.join(root.path, 'other', 'record-kr.json')}),
      throwsA(isA<KrAdapterException>()),
    );
    expect(output.readAsBytesSync(), before);
  });

  test('candidate selection preserves SID 0, immutable bindings and requires fresh confirmation', () {
    final dto = {
      'rows': [<String, dynamic>{}],
      'source_image': 'source.png',
      'review_sha256': 'hash',
      'ready_to_export': true,
      'review': {
        'bindings': {'hash': 'immutable'},
        'rows': [
          {'group': 'self', 'index': 0, 'name_crop_sha256': 'pixels', 'decision': 'confirmed'},
        ],
      },
    };
    final session = KrReviewSession.fromResponse(dto);
    session.selectMaster(0, {
      'name_ko': 'test',
      'star': 1,
      'app_sids': [0],
      'factor_id': 100,
      'factor_group_id': 7,
    });
    expect(session.decisions.single['app_sid'], 0);
    expect(session.decisions.single['decision'], 'unreviewed');
    expect(session.confirmedCount, 0);
    expect(session.ready, isFalse);
    expect(session.review['bindings'], {'hash': 'immutable'});
    expect(session.decisions.single['name_crop_sha256'], 'pixels');
    expect(() => session.updateRow(0, {'group': 'parent2'}), throwsArgumentError);
    expect(
      () => session.selectMaster(0, {
        'app_sids': [0, 1],
      }),
      throwsA(isA<KrAdapterException>()),
    );
  });

  test('cancellation settles a local process and permits a later invocation', () async {
    final config = jsonDecode(File('.dart_tool/package_config.json').readAsStringSync()) as Map;
    final flutter = (config['packages'] as List).cast<Map>().singleWhere((e) => e['name'] == 'flutter');
    final flutterPackage = Directory.fromUri(Uri.parse(flutter['rootUri'] as String));
    final dart = p.join(
      flutterPackage.parent.parent.path,
      'bin',
      'cache',
      'dart-sdk',
      'bin',
      Platform.isWindows ? 'dart.exe' : 'dart',
    );
    final local = LocalKrCommandTransport();
    final pending = local.execute(dart, ['--version']);
    // This test uses the test runner's Dart binary only, no shell or installed Python.
    final result = await pending;
    expect(result.exitCode, 0);
    final waitScript = File(p.join(root.path, 'wait.dart'))
      ..writeAsStringSync("import 'dart:io'; void main() { stdin.listen((_) {}); }");
    final running = local.execute(dart, [waitScript.path]);
    final expectation = expectLater(running, throwsStateError);
    await local.cancel();
    await expectation;
    expect((await local.execute(dart, ['--version'])).exitCode, 0);
  });
}
