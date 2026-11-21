import 'dart:convert';
import 'dart:io';

import 'package:auto_route/auto_route.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as p;
import 'package:uuid/uuid.dart';

import '/src/core/bootstrap.dart';
import '/src/core/kr_factor_workflow.dart';
import '/src/core/providers.dart';

class KoreanFactorWorkflowPage extends ConsumerWidget {
  const KoreanFactorWorkflowPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) => ref
      .watch(pathLayoutLoader)
      .when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => Center(child: SelectableText('KR 경로 확인 실패: $error')),
        data: (paths) => KrFactorWorkflowPanel(
          dataRoot: paths.dataRoot!.path,
          onOpenCapture: () => AutoTabsRouter.of(context).setActiveIndex(1),
        ),
      );
}

/// This screen owns no record loader: reviewed bytes stay in their separate path.
class KrFactorWorkflowPanel extends ConsumerStatefulWidget {
  const KrFactorWorkflowPanel({super.key, required this.dataRoot, this.onOpenCapture, this.loadSettings = true});
  final String dataRoot;
  final VoidCallback? onOpenCapture;
  final bool loadSettings;

  @override
  ConsumerState<KrFactorWorkflowPanel> createState() => _KrFactorWorkflowPanelState();
}

class _KrFactorWorkflowPanelState extends ConsumerState<KrFactorWorkflowPanel> {
  static const labels = {
    'interpreter': '로컬 Python 실행 파일',
    'adapter': '앱 어댑터 kr_factor_app.py',
    'capture': '완료된 3탭 캡처 폴더',
    'model': '한국어 PP-OCRv5 ONNX 모델',
    'master': '정규화된 Scout SQLite master',
    'master_sha256': 'master SHA256 핀',
    'factor_info': '캡처와 일치하는 factor_info.json',
    'factor_info_sha256': 'factor_info SHA256 핀',
    'module_version': '캡처와 일치하는 version_info.json',
    'working_dir': '새 OCR 작업 또는 재개할 작업 폴더',
    'output_root': '검토 결과를 저장할 전용 폴더',
  };
  final _fields = <String, TextEditingController>{};
  final _reviewer = TextEditingController();
  final _coverageEvidence = TextEditingController();
  KrReviewSession? _session;
  Map<String, dynamic>? _sessionRequest;
  Map<String, dynamic>? _export;
  bool _busy = false;
  bool _dirty = false;
  String _status = '준비 · 한국어 인자 OCR을 아직 실행하지 않았습니다.';
  String? _error;

  File get _settingsFile => File(p.join(widget.dataRoot, 'kr-workflow-settings.json'));

  @override
  void initState() {
    super.initState();
    final defaults = {
      'adapter': p.join(p.dirname(Platform.resolvedExecutable), 'tool', 'kr_factor_ocr', 'kr_factor_app.py'),
      'working_dir': _newWorkPath(),
      'output_root': p.join(widget.dataRoot, 'kr-results'),
    };
    for (final key in labels.keys) {
      _fields[key] = TextEditingController(text: defaults[key] ?? '');
    }
    if (widget.loadSettings) {
      try {
        if (_settingsFile.existsSync()) {
          final saved = jsonDecode(_settingsFile.readAsStringSync()) as Map<String, dynamic>;
          for (final key in labels.keys) {
            if (saved[key] is String) _fields[key]!.text = saved[key] as String;
          }
        }
      } catch (error) {
        _error = 'KR 작업 설정을 읽지 못했습니다. 경로를 다시 선택하세요. $error';
      }
    }
  }

  String _newWorkPath() => p.join(widget.dataRoot, 'kr-runs', const Uuid().v4());

  @override
  void dispose() {
    for (final field in _fields.values) {
      field.dispose();
    }
    _reviewer.dispose();
    _coverageEvidence.dispose();
    super.dispose();
  }

  Map<String, dynamic> get _request => {
    for (final key in [
      'capture',
      'model',
      'master',
      'master_sha256',
      'factor_info',
      'factor_info_sha256',
      'module_version',
      'working_dir',
    ])
      key: _fields[key]!.text.trim(),
  };

  void _invalidate() {
    setState(() {
      _session = null;
      _sessionRequest = null;
      _export = null;
      _dirty = false;
      _status = '경로가 변경됐습니다. OCR 실행 또는 기존 작업 재개가 필요합니다.';
    });
  }

  Future<KrAdapterResponse> _invoke(String command, Map<String, dynamic> request) => ref
      .read(krFactorAdapterProvider)
      .execute(
        interpreter: _fields['interpreter']!.text.trim(),
        adapter: _fields['adapter']!.text.trim(),
        command: command,
        request: request,
      );

  void _acceptSession(KrAdapterResponse response) {
    final session = KrReviewSession.fromResponse(response.data);
    _session = session;
    _reviewer.text = session.review['reviewer'] as String? ?? '';
    _coverageEvidence.text = (session.review['coverage'] as Map)['evidence'] as String? ?? '';
    _dirty = false;
    _status = session.ready ? '검토 검증 통과 · 별도 출력으로 내보낼 수 있습니다.' : '검토 필요 · 행별 픽셀과 전체 캡처를 확인하세요.';
  }

  Future<void> _perform(Future<void> Function() action) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
    } catch (error) {
      if (mounted) {
        setState(() {
          _error = '$error';
          _status = '완료하지 못했습니다. 기존 입력과 출력은 보존됩니다.';
        });
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _start(String command) => _perform(() async {
    final request = _request;
    final response = await _invoke(command, request);
    if (!mounted) return;
    setState(() {
      _sessionRequest = request;
      _export = null;
      _acceptSession(response);
    });
  });

  Future<void> _save({bool validate = false}) => _perform(() async {
    final session = _session!;
    final response = await _invoke('save-review', {
      ..._sessionRequest!,
      'review': session.review,
      'expected_review_sha256': session.reviewSha256,
    });
    if (!mounted) return;
    setState(() => _acceptSession(response));
    if (validate) {
      final checked = await _invoke('validate-review', _sessionRequest!);
      if (mounted) setState(() => _acceptSession(checked));
    }
  });

  Future<void> _exportRecord() => _perform(() async {
    final root = _fields['output_root']!.text.trim();
    if (!p.isAbsolute(root)) throw const KrAdapterException('결과 저장 폴더의 절대 경로를 선택하세요.');
    // Every attempt gets new paths. No replacement/lock bypass is exposed.
    final destination = p.join(root, const Uuid().v4());
    final response = await _invoke('export', {
      ..._sessionRequest!,
      'output': p.join(destination, 'record-kr.json'),
      'evidence_output': p.join(destination, 'evidence'),
    });
    if (!mounted) return;
    setState(() {
      if (response.completed) {
        _export = response.data;
        _status = '검토된 record-kr.json 저장 및 SHA256 확인 완료';
      } else {
        _status = '검토 필요 · 출력 완료가 아닙니다.';
        _export = null;
      }
    });
  });

  Future<void> _pick(String key) async {
    final directory = {'capture', 'working_dir', 'output_root'}.contains(key);
    String? selected;
    if (directory) {
      selected = await FilePicker.getDirectoryPath();
    } else {
      selected = (await FilePicker.pickFile())?.path;
    }
    if (selected != null && mounted) {
      _fields[key]!.text = selected;
      _invalidate();
    }
  }

  Future<void> _saveSettings() => _perform(() async {
    await _settingsFile.writeAsString(
      jsonEncode({for (final e in _fields.entries) e.key: e.value.text.trim()}),
      flush: true,
    );
    if (mounted) setState(() => _status = 'KR 전용 경로 설정을 저장했습니다.');
  });

  void _editCoverage(String key, dynamic value) {
    setState(() {
      (_session!.review['coverage'] as Map)[key] = value;
      _session!.data['ready_to_export'] = false;
      _dirty = true;
      _export = null;
    });
  }

  Future<void> _reviewRow(int index) async {
    final session = _session!;
    final edit = await showDialog<Map<String, dynamic>>(
      context: context,
      barrierDismissible: false,
      builder: (_) => KrFactorRowReviewDialog(
        row: session.rows[index],
        decision: session.decisions[index],
        lookup: (query, star, offset) async => (await _invoke('lookup', {
          ..._sessionRequest!,
          'query': query,
          'star': star,
          'offset': offset,
          'limit': 30,
        })).data,
      ),
    );
    if (edit != null && mounted) {
      setState(() {
        session.updateRow(index, edit);
        _dirty = true;
        _export = null;
      });
    }
  }

  Widget _section(String title, List<Widget> children) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          ...children,
        ],
      ),
    ),
  );

  @override
  Widget build(BuildContext context) {
    final session = _session;
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        _section('한국어 인자 OCR · Phase 1', [
          const Text(
            '실제 한국어 인자 OCR → 픽셀·master 검토 → 별도 record-kr.json. '
            '후보는 확인 전까지 미검증입니다. 비인자 항목은 JP 기준 원본에서 복사되며 한국어 정확성을 보증하지 않습니다.',
          ),
          const SizedBox(height: 8),
          SelectableText(
            '실행 파일: ${Platform.resolvedExecutable}\nKR 데이터: ${widget.dataRoot}\n'
            '설정: ${_settingsFile.path}\n캡처 저장소: ${p.join(widget.dataRoot, 'storage', 'chara_detail', 'active')}\n'
            '로컬 캡처 모듈: ${p.join(widget.dataRoot, 'modules')}\nbootstrap: $koreanBootstrapFileName',
          ),
          const Text(
            '캡처 화면에서 기존 3탭 수집을 사용하세요. 새 KR 저장소에는 설정 화면의 로컬 모듈 ZIP 가져오기로 '
            '기존 캡처용 모듈을 설치해야 합니다. 한국어 모델·master·Python은 아래에서 로컬 파일로 지정합니다. 자동 다운로드하지 않습니다.',
          ),
          Align(
            alignment: Alignment.centerLeft,
            child: OutlinedButton.icon(
              onPressed: _busy ? null : widget.onOpenCapture,
              icon: const Icon(Icons.videocam_outlined),
              label: const Text('기존 3탭 캡처 화면'),
            ),
          ),
        ]),
        _section('1 · 로컬 입력과 경로', [
          for (final entry in labels.entries)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: TextField(
                key: ValueKey('kr_${entry.key}'),
                controller: _fields[entry.key],
                enabled: !_busy,
                onChanged: (_) => _invalidate(),
                decoration: InputDecoration(
                  labelText: entry.value,
                  border: const OutlineInputBorder(),
                  suffixIcon: entry.key.endsWith('sha256')
                      ? null
                      : IconButton(
                          onPressed: _busy ? null : () => _pick(entry.key),
                          icon: const Icon(Icons.folder_open),
                          tooltip: '로컬 경로 선택',
                        ),
                ),
              ),
            ),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              OutlinedButton(onPressed: _busy ? null : _saveSettings, child: const Text('KR 경로 설정 저장')),
              OutlinedButton(
                onPressed: _busy
                    ? null
                    : () {
                        _fields['working_dir']!.text = _newWorkPath();
                        _invalidate();
                      },
                child: const Text('새 작업 경로'),
              ),
              FilledButton(
                key: const ValueKey('kr_run'),
                onPressed: _busy ? null : () => _start('run'),
                child: const Text('한국어 OCR 실행'),
              ),
              OutlinedButton(onPressed: _busy ? null : () => _start('load'), child: const Text('기존 작업 재개')),
            ],
          ),
        ]),
        _section('작업 상태', [
          Text(_status, key: const ValueKey('kr_status')),
          if (_busy) ...[
            const LinearProgressIndicator(),
            TextButton(onPressed: () => ref.read(krFactorAdapterProvider).cancel(), child: const Text('현재 프로세스 취소')),
          ],
          if (_error != null) SelectableText(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          const Text(
            '취소·실패한 작업 폴더와 잠금은 자동 삭제하지 않습니다. 새 작업 경로로 재시도하거나 기존 작업을 재개하세요. '
            '경로 변경 시 메모리의 미저장 검토는 해제됩니다. 재개는 마지막 저장본을 읽습니다.',
          ),
        ]),
        if (session != null) ...[
          _section('2 · 전체 캡처와 행별 확인', [
            SelectableText(
              '작업: ${session.data['working_dir']}\n검토: ${session.data['review_path']}\n'
              '검토 해시: ${session.reviewSha256}\n확인: ${session.confirmedCount}/${session.rows.length}'
              '${_dirty ? ' · 미저장 변경 있음' : ''}',
            ),
            TextButton(
              onPressed: _busy
                  ? null
                  : () => showDialog<void>(
                      context: context,
                      builder: (_) =>
                          Dialog(child: KrPixelImage(path: session.data['source_image'] as String, fullImage: true)),
                    ),
              child: const Text('전체 factor.png 열기 · 시작/끝/그룹 경계 확인'),
            ),
            TextField(
              controller: _reviewer,
              enabled: !_busy,
              decoration: const InputDecoration(labelText: '독립 검토/명시적 확인자'),
              onChanged: (value) => setState(() {
                session.review['reviewer'] = value;
                session.data['ready_to_export'] = false;
                _dirty = true;
                _export = null;
              }),
            ),
            for (final entry in const {
              'complete_capture': '수집 시작부터 끝까지 완전한 캡처임을 확인',
              'group_boundaries': 'self → parent1 → parent2 순서와 그룹 경계 확인',
              'no_missing_or_duplicate_rows': '누락 또는 중복된 인자 행이 없음을 확인',
            }.entries)
              CheckboxListTile(
                title: Text(entry.value),
                value: (session.review['coverage'] as Map)[entry.key] == true,
                onChanged: _busy ? null : (v) => _editCoverage(entry.key, v == true),
              ),
            TextField(
              controller: _coverageEvidence,
              enabled: !_busy,
              maxLines: 2,
              decoration: const InputDecoration(labelText: '전체 캡처 범위/그룹/행 수를 확인한 근거'),
              onChanged: (v) => _editCoverage('evidence', v),
            ),
            for (var index = 0; index < session.rows.length; index++)
              ListTile(
                title: Text(
                  '${session.rows[index]['group']} [${session.rows[index]['index']}] '
                  '${session.rows[index]['raw_text']}',
                ),
                subtitle: Text(
                  'JP SID ${session.rows[index]['baseline_sid']} · 별 ${session.rows[index]['star']} · '
                  'KR ${session.decisions[index]['master_name'] ?? '미선택'} · ${session.decisions[index]['decision']}',
                ),
                trailing: const Icon(Icons.zoom_in),
                onTap: _busy ? null : () => _reviewRow(index),
              ),
          ]),
          _section('3 · 검토 저장·검증·안전 출력', [
            for (final issue in session.issues) Text(issue),
            for (final limit in (session.data['limitations'] as List? ?? [])) Text('$limit'),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                OutlinedButton(onPressed: _busy ? null : () => _save(), child: const Text('검토 초안 저장')),
                FilledButton(onPressed: _busy ? null : () => _save(validate: true), child: const Text('저장 후 전체 검증')),
                FilledButton(
                  key: const ValueKey('kr_export'),
                  onPressed: !_busy && !_dirty && session.ready ? _exportRecord : null,
                  child: const Text('검토된 record-kr.json 내보내기'),
                ),
              ],
            ),
            const Text(
              '매번 새 출력 폴더를 사용합니다. 원본 record.json과 이전 결과는 교체하지 않습니다. '
              '파생 결과를 기존 통계/목록에 자동 삽입하거나 upgradeFormat으로 재직렬화하지 않습니다.',
            ),
            if (_export != null)
              SelectableText(
                '출력: ${_export!['output']}\nSHA256: ${_export!['output_sha256']}\n'
                '비교·검토 증거: ${_export!['evidence_output']}\nJP/KR 비교: ${_export!['comparison_counts']}',
              ),
          ]),
        ],
      ],
    );
  }
}

/// Nearest-neighbor enlargement retains original pixels; zoom/pan is user controlled.
class KrPixelImage extends StatelessWidget {
  const KrPixelImage({super.key, required this.path, this.fullImage = false});
  final String path;
  final bool fullImage;
  @override
  Widget build(BuildContext context) => SizedBox(
    height: fullImage ? 600 : 125,
    width: fullImage ? 900 : double.infinity,
    child: InteractiveViewer(
      minScale: 0.1,
      maxScale: 16,
      constrained: false,
      child: Image.file(
        File(path),
        filterQuality: FilterQuality.none,
        scale: fullImage ? 1 : 0.5,
        errorBuilder: (_, error, _) => Text('픽셀 파일을 열 수 없습니다: $error'),
      ),
    ),
  );
}

typedef KrMasterLookup = Future<Map<String, dynamic>> Function(String query, int star, int offset);

class KrFactorRowReviewDialog extends StatefulWidget {
  const KrFactorRowReviewDialog({super.key, required this.row, required this.decision, required this.lookup});
  final Map<String, dynamic> row;
  final Map<String, dynamic> decision;
  final KrMasterLookup lookup;
  @override
  State<KrFactorRowReviewDialog> createState() => _KrFactorRowReviewDialogState();
}

class _KrFactorRowReviewDialogState extends State<KrFactorRowReviewDialog> {
  late final _observed = TextEditingController(text: widget.decision['observed_name'] as String? ?? '');
  late final _evidence = TextEditingController(text: widget.decision['evidence'] as String? ?? '');
  late final _difference = TextEditingController(text: widget.decision['name_difference_reason'] as String? ?? '');
  final _query = TextEditingController();
  late int _star = widget.decision['star'] as int? ?? widget.row['star'] as int;
  late Map<String, dynamic> _selected = Map.of(widget.decision);
  late bool _confirmed = {'confirmed', 'verified'}.contains(widget.decision['decision']);
  List<Map<String, dynamic>> _matches = [];
  int _offset = 0;
  int _total = 0;
  bool _searching = false;
  String? _error;

  @override
  void dispose() {
    _observed.dispose();
    _evidence.dispose();
    _difference.dispose();
    _query.dispose();
    super.dispose();
  }

  Future<void> _search(int offset) async {
    setState(() {
      _searching = true;
      _error = null;
    });
    try {
      final result = await widget.lookup(_query.text, _star, offset);
      if (mounted) {
        setState(() {
          _matches = (result['matches'] as List).cast<Map<String, dynamic>>();
          _offset = result['offset'] as int;
          _total = result['total'] as int;
        });
      }
    } catch (error) {
      if (mounted) setState(() => _error = '$error');
    } finally {
      if (mounted) setState(() => _searching = false);
    }
  }

  bool get _hasSelection =>
      _selected['app_sid'] is int &&
      _selected['master_name'] is String &&
      _selected['factor_id'] is int &&
      _selected['factor_group_id'] is int &&
      _selected['star'] == _star;

  void _select(Map<String, dynamic> match) {
    final sids = match['app_sids'];
    if (sids is! List || sids.length != 1 || match['selectable'] == false) return;
    setState(() {
      _selected = {
        'master_name': match['name_ko'],
        'app_sid': sids.single,
        'factor_id': match['factor_id'],
        'factor_group_id': match['factor_group_id'],
        'star': match['star'],
      };
      _star = match['star'] as int;
      _confirmed = false;
    });
  }

  Widget _candidate(Map<String, dynamic> match) {
    final sids = match['app_sids'];
    final selectable = sids is List && sids.length == 1 && match['selectable'] != false;
    return ListTile(
      dense: true,
      title: Text('${match['name_ko']} · 별 ${match['star']}'),
      subtitle: Text(
        'module SID $sids / Scout group ${match['factor_group_id']} / star-specific ID ${match['factor_id']}',
      ),
      enabled: selectable && !_searching,
      onTap: () => _select(match),
      trailing: Text(selectable ? '선택' : '매핑 불명확'),
    );
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Text('${widget.row['group']} [${widget.row['index']}] · 개별 픽셀 확인'),
    content: SizedBox(
      width: 850,
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('실제 이름과 별 픽셀을 확인하세요. OCR 신뢰도 또는 JP 일치만으로 확정하지 마세요.'),
            KrPixelImage(path: widget.row['name_crop'] as String),
            KrPixelImage(path: widget.row['star_crop'] as String),
            SelectableText(
              '원시 OCR: ${widget.row['raw_text']} · 점수 ${widget.row['score']}\n'
              'JP SID ${widget.row['baseline_sid']} / 별 ${widget.row['star']}',
            ),
            for (final c in (widget.row['candidates'] as List)) _candidate(Map<String, dynamic>.from(c as Map)),
            TextField(
              key: const ValueKey('kr_observed_name'),
              controller: _observed,
              decoration: const InputDecoration(labelText: '직접 관찰한 표시 이름'),
              onChanged: (_) => setState(() => _confirmed = false),
            ),
            DropdownButtonFormField<int>(
              key: ValueKey('kr_star_$_star'),
              initialValue: _star,
              decoration: const InputDecoration(labelText: '직접 관찰한 별'),
              items: [
                for (final s in [1, 2, 3]) DropdownMenuItem(value: s, child: Text('$s')),
              ],
              onChanged: _searching
                  ? null
                  : (v) => setState(() {
                      _star = v!;
                      _confirmed = false;
                      _matches = [];
                    }),
            ),
            const SizedBox(height: 12),
            const Text('후보가 없거나 틀리면 고정된 master에서 검색하세요. 빈 검색은 전체 목록입니다.'),
            TextField(
              key: const ValueKey('kr_master_query'),
              controller: _query,
              decoration: const InputDecoration(labelText: 'master 이름 검색'),
              onSubmitted: (_) => _search(0),
            ),
            Wrap(
              spacing: 8,
              children: [
                TextButton(onPressed: _searching ? null : () => _search(0), child: const Text('master 검색')),
                if (_offset > 0)
                  TextButton(
                    onPressed: _searching ? null : () => _search((_offset - 30).clamp(0, _total)),
                    child: const Text('이전'),
                  ),
                if (_offset + _matches.length < _total)
                  TextButton(onPressed: _searching ? null : () => _search(_offset + 30), child: const Text('다음')),
              ],
            ),
            if (_searching) const LinearProgressIndicator(),
            if (_error != null) Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            Text('검색 결과 $_total개 · 현재 $_offset부터 ${_matches.length}개'),
            for (final m in _matches) _candidate(m),
            SelectableText(
              '선택 master: ${_selected['master_name'] ?? '없음'} / 별 ${_selected['star']}\n'
              'module SID ${_selected['app_sid']} / Scout group ${_selected['factor_group_id']} / ID ${_selected['factor_id']}',
            ),
            TextField(
              controller: _difference,
              decoration: const InputDecoration(labelText: '관찰 이름과 master 이름이 다른 이유 (다르면 필수)'),
              onChanged: (_) => setState(() => _confirmed = false),
            ),
            TextField(
              key: const ValueKey('kr_row_evidence'),
              controller: _evidence,
              maxLines: 2,
              decoration: const InputDecoration(labelText: '이 행의 독립 관찰 또는 명시적 확인 근거'),
              onChanged: (_) => setState(() => _confirmed = false),
            ),
            CheckboxListTile(
              key: const ValueKey('kr_confirm_row'),
              title: const Text('이 행의 이름·별·master 연결을 직접 확인했습니다.'),
              value: _confirmed,
              onChanged:
                  _hasSelection &&
                      _observed.text.trim().isNotEmpty &&
                      _evidence.text.trim().isNotEmpty &&
                      (_observed.text == _selected['master_name'] || _difference.text.trim().isNotEmpty)
                  ? (v) => setState(() => _confirmed = v == true)
                  : null,
            ),
          ],
        ),
      ),
    ),
    actions: [
      TextButton(onPressed: _searching ? null : () => Navigator.pop(context), child: const Text('취소')),
      FilledButton(
        onPressed: _searching
            ? null
            : () => Navigator.pop(context, <String, dynamic>{
                for (final key in ['master_name', 'app_sid', 'factor_id', 'factor_group_id', 'star'])
                  key: _selected[key],
                'decision': _confirmed ? 'confirmed' : 'unreviewed',
                'observed_name': _observed.text,
                'evidence': _evidence.text,
                'name_difference_reason': _difference.text,
              }),
        child: const Text('행 검토 적용'),
      ),
    ],
  );
}
