import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as p;

import '/src/core/app_logger.dart';

typedef KrProcessOutput = ({int exitCode, String stdout, String stderr});

abstract interface class KrCommandTransport {
  Future<KrProcessOutput> execute(String executable, List<String> arguments);
  Future<void> cancel();
}

class LocalKrCommandTransport implements KrCommandTransport {
  Process? _process;
  bool _cancelled = false;

  @override
  Future<KrProcessOutput> execute(String executable, List<String> arguments) async {
    if (_process != null) throw StateError('이미 실행 중입니다.');
    _cancelled = false;
    final process = await Process.start(executable, arguments, runInShell: false);
    _process = process;
    if (_cancelled) process.kill();
    try {
      final stdout = utf8.decoder.bind(process.stdout).join();
      final stderr = utf8.decoder.bind(process.stderr).join();
      final code = await process.exitCode;
      final result = (exitCode: code, stdout: await stdout, stderr: await stderr);
      if (_cancelled) throw StateError('작업을 취소했습니다. 저장된 산출물은 보존됩니다. 새 작업 폴더로 재시도하세요.');
      return result;
    } finally {
      _process = null;
    }
  }

  @override
  Future<void> cancel() async {
    _cancelled = true;
    _process?.kill();
    await _process?.exitCode;
  }
}

final krFactorAdapterProvider = Provider<KrFactorAdapter>((ref) {
  final adapter = KrFactorAdapter(LocalKrCommandTransport());
  ref.onDispose(() => adapter.cancel());
  return adapter;
});

class KrAdapterException implements Exception {
  const KrAdapterException(this.message);
  final String message;
  @override
  String toString() => message;
}

/// The response envelope is checked before any result is presented as success.
class KrAdapterResponse {
  KrAdapterResponse(this.data);
  final Map<String, dynamic> data;
  bool get needsReview => data['status'] == 'needs_review';
  bool get completed => data['status'] == 'completed' && data['completed'] == true;
}

class KrFactorAdapter {
  KrFactorAdapter(this.transport);
  final KrCommandTransport transport;
  bool _busy = false;

  Future<void> cancel() => transport.cancel();

  Future<KrAdapterResponse> execute({
    required String interpreter,
    required String adapter,
    required String command,
    required Map<String, dynamic> request,
  }) async {
    if (_busy) throw const KrAdapterException('다른 작업이 실행 중입니다.');
    if (!p.isAbsolute(interpreter) || !File(interpreter).existsSync()) {
      throw const KrAdapterException('로컬 Python 실행 파일의 절대 경로를 확인하세요. 자동 설치하지 않습니다.');
    }
    if (!p.isAbsolute(adapter) || !File(adapter).existsSync()) {
      throw const KrAdapterException('kr_factor_app.py 경로를 확인하세요.');
    }
    _busy = true;
    Directory? temporary;
    try {
      temporary = await Directory.systemTemp.createTemp('umacapture-kr-request-');
      final file = File(p.join(temporary.path, 'request.json'));
      await file.writeAsString(jsonEncode({'schema_version': 1, ...request}), flush: true);
      final process = await transport.execute(interpreter, [adapter, command, '--request', file.path]);
      Map<String, dynamic> value;
      try {
        value = jsonDecode(process.stdout) as Map<String, dynamic>;
      } catch (_) {
        throw KrAdapterException(
          '어댑터가 유효한 JSON 응답을 보내지 않았습니다 (종료 ${process.exitCode}). '
          '${process.stderr}',
        );
      }
      final status = value['status'];
      if (value['schema_version'] != 1 ||
          value['command'] != command ||
          value['completed'] is! bool ||
          !((process.exitCode == 2 && status == 'needs_review' && value['completed'] == false) ||
              (process.exitCode == 0 && status == 'ok' && value['completed'] == false) ||
              (process.exitCode == 0 && status == 'completed' && value['completed'] == true && command == 'export'))) {
        throw KrAdapterException(
          '${value['message'] ?? '어댑터 응답 또는 종료 상태가 올바르지 않습니다.'} '
          '(종료 ${process.exitCode})',
        );
      }
      if (status == 'completed') {
        final output = value['output'];
        if (output is! String ||
            !p.equals(p.normalize(output), p.normalize(request['output'] as String)) ||
            p.basename(output) != 'record-kr.json' ||
            !File(output).existsSync()) {
          throw const KrAdapterException('완료 응답의 출력 파일을 확인할 수 없습니다.');
        }
        final actual = await sha256.bind(File(output).openRead()).first;
        if (actual.toString() != value['output_sha256']) {
          throw const KrAdapterException('출력 파일의 SHA256이 완료 응답과 다릅니다.');
        }
      }
      return KrAdapterResponse(value);
    } catch (error, stack) {
      logger.w('KR factor command failed: $command', error, stack);
      rethrow;
    } finally {
      _busy = false;
      if (temporary != null) await temporary.delete(recursive: true);
    }
  }
}

/// Keeps the adapter's complete immutable receipt. Only explicit editable fields
/// are changed by the review UI; bindings, coordinates, order and hashes survive.
class KrReviewSession {
  KrReviewSession._(this.data, this.review);
  final Map<String, dynamic> data;
  final Map<String, dynamic> review;

  factory KrReviewSession.fromResponse(Map<String, dynamic> data) {
    final review = jsonDecode(jsonEncode(data['review'])) as Map<String, dynamic>;
    final rows = data['rows'];
    if (rows is! List ||
        review['rows'] is! List ||
        rows.length != (review['rows'] as List).length ||
        data['review_sha256'] is! String ||
        data['source_image'] is! String) {
      throw const KrAdapterException('검토 세션 응답이 올바르지 않습니다.');
    }
    return KrReviewSession._(data, review);
  }

  List<Map<String, dynamic>> get rows => (data['rows'] as List).cast<Map<String, dynamic>>();
  List<Map<String, dynamic>> get decisions => (review['rows'] as List).cast<Map<String, dynamic>>();
  bool get ready => data['ready_to_export'] == true;
  String get reviewSha256 => data['review_sha256'] as String;
  List<String> get issues => (data['review_issues'] as List? ?? []).map((e) => '$e').toList();
  int get confirmedCount => decisions.where((r) => r['decision'] == 'verified' || r['decision'] == 'confirmed').length;

  void updateRow(int index, Map<String, dynamic> edit) {
    const editable = {
      'decision',
      'observed_name',
      'master_name',
      'star',
      'app_sid',
      'factor_id',
      'factor_group_id',
      'name_difference_reason',
      'evidence',
    };
    if (edit.keys.any((key) => !editable.contains(key))) throw ArgumentError('Immutable review field');
    decisions[index].addAll(edit);
    data['ready_to_export'] = false;
  }

  void selectMaster(int index, Map<String, dynamic> match) {
    final sids = match['app_sids'];
    if (sids is! List || sids.length != 1 || sids.single is! int || match['selectable'] == false) {
      throw const KrAdapterException('단일 module SID가 있는 master 항목만 선택할 수 있습니다.');
    }
    updateRow(index, {
      'master_name': match['name_ko'],
      'star': match['star'],
      'app_sid': sids.single,
      'factor_id': match['factor_id'],
      'factor_group_id': match['factor_group_id'],
      'decision': 'unreviewed',
    });
  }
}
