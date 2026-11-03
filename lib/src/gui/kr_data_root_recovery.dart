import 'package:flutter/material.dart';

import '/src/core/bootstrap.dart';
import '/src/gui/app_fonts.dart';

/// Has no Hive/provider/localization dependency: no store has opened yet.
class KoreanDataRootRecoveryApp extends StatefulWidget {
  const KoreanDataRootRecoveryApp({super.key, required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;

  @override
  State<KoreanDataRootRecoveryApp> createState() => _KoreanDataRootRecoveryAppState();
}

class _KoreanDataRootRecoveryAppState extends State<KoreanDataRootRecoveryApp> {
  final _path = TextEditingController(text: configuredDataRoot ?? '');
  String? _error;
  bool _busy = false;

  @override
  void dispose() {
    _path.dispose();
    super.dispose();
  }

  Future<void> _save(String? root) async {
    setState(() => _busy = true);
    try {
      await writeKoreanDataRoot(root);
      widget.onRetry();
    } catch (error) {
      if (mounted) setState(() => _error = '$error');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner: false,
    theme: ThemeData(fontFamily: koreanUiFontFamily),
    home: Scaffold(
      appBar: AppBar(title: const Text('umacapture KR · 저장소 복구')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          SelectableText(widget.message),
          const SizedBox(height: 16),
          const Text(
            'JP와 겹치지 않는 기존 폴더를 선택하거나 KR 기본 경로로 복구하세요. 파일을 이동하거나 삭제하지 않습니다. '
            'UMACAPTURE_KR_DATA_ROOT가 설정되어 있다면 해당 환경 변수를 먼저 수정하고 다시 시작하세요.',
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _path,
            enabled: !_busy,
            decoration: const InputDecoration(labelText: 'KR 전용 절대 경로'),
          ),
          if (_error != null) Text(_error!),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              FilledButton(onPressed: _busy ? null : () => _save(_path.text.trim()), child: const Text('경로 저장 후 재시도')),
              OutlinedButton(onPressed: _busy ? null : () => _save(null), child: const Text('KR 기본 경로로 복구')),
              TextButton(onPressed: _busy ? null : widget.onRetry, child: const Text('다시 확인')),
            ],
          ),
        ],
      ),
    ),
  );
}
