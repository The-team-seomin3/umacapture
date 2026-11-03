import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:umacapture/src/gui/kr_factor_workflow.dart';
import 'package:umacapture/src/gui/kr_data_root_recovery.dart';

void main() {
  late Directory root;
  late String pixels;
  setUp(() {
    root = Directory.systemTemp.createTempSync('kr-widget-');
    pixels = p.join(root.path, 'synthetic.png');
    File(pixels).writeAsBytesSync(
      base64Decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='),
    );
  });
  tearDown(() => root.deleteSync(recursive: true));

  testWidgets('workflow explains actual OCR ownership and retains the capture entry', (tester) async {
    var captureOpened = false;
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: KrFactorWorkflowPanel(
              dataRoot: root.path,
              loadSettings: false,
              onOpenCapture: () => captureOpened = true,
            ),
          ),
        ),
      ),
    );
    expect(find.text('한국어 인자 OCR · Phase 1'), findsOneWidget);
    expect(find.textContaining('비인자 항목은 JP'), findsOneWidget);
    await tester.tap(find.text('기존 3탭 캡처 화면'));
    expect(captureOpened, isTrue);
    expect(tester.takeException(), isNull);
  });

  testWidgets('recovery paints without any settings/provider and retries without a store', (tester) async {
    var retried = false;
    await tester.pumpWidget(KoreanDataRootRecoveryApp(message: 'JP fallback refused', onRetry: () => retried = true));
    expect(find.text('JP fallback refused'), findsOneWidget);
    await tester.tap(find.text('다시 확인'));
    expect(retried, isTrue);
    expect(tester.takeException(), isNull);
  });

  testWidgets('manual master lookup supports SID zero and requires individual pixel confirmation', (tester) async {
    tester.view.physicalSize = const Size(1200, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    Map<String, dynamic>? applied;
    var queries = 0;
    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (context) => Scaffold(
            body: TextButton(
              onPressed: () async {
                applied = await showDialog<Map<String, dynamic>>(
                  context: context,
                  builder: (_) => KrFactorRowReviewDialog(
                    row: {
                      'group': 'self',
                      'index': 0,
                      'star': 1,
                      'baseline_sid': 19,
                      'name_crop': pixels,
                      'star_crop': pixels,
                      'raw_text': 'unknown',
                      'score': 0.95,
                      'candidates': <dynamic>[],
                    },
                    decision: {'decision': 'unreviewed'},
                    lookup: (query, star, offset) async {
                      queries++;
                      expect(query, 'speed');
                      expect(star, 1);
                      expect(offset, 0);
                      return {
                        'total': 1,
                        'offset': 0,
                        'matches': [
                          {
                            'name_ko': '스피드',
                            'star': 1,
                            'app_sids': [0],
                            'factor_id': 101,
                            'factor_group_id': 12,
                            'selectable': true,
                          },
                        ],
                      };
                    },
                  ),
                );
              },
              child: const Text('review'),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('review'));
    await tester.pumpAndSettle();
    var check = tester.widget<CheckboxListTile>(find.byKey(const ValueKey('kr_confirm_row')));
    expect(check.value, isFalse);
    expect(check.onChanged, isNull);
    await tester.enterText(find.byKey(const ValueKey('kr_master_query')), 'speed');
    await tester.ensureVisible(find.text('master 검색'));
    await tester.tap(find.text('master 검색'));
    await tester.pumpAndSettle();
    expect(queries, 1);
    await tester.ensureVisible(find.text('스피드 · 별 1'));
    await tester.tap(find.text('스피드 · 별 1'));
    await tester.pumpAndSettle();
    expect(tester.widget<CheckboxListTile>(find.byKey(const ValueKey('kr_confirm_row'))).value, isFalse);
    await tester.ensureVisible(find.byKey(const ValueKey('kr_observed_name')));
    await tester.enterText(find.byKey(const ValueKey('kr_observed_name')), '스피드');
    await tester.ensureVisible(find.byKey(const ValueKey('kr_row_evidence')));
    await tester.enterText(find.byKey(const ValueKey('kr_row_evidence')), 'Synthetic row independently checked');
    await tester.pump();
    check = tester.widget<CheckboxListTile>(find.byKey(const ValueKey('kr_confirm_row')));
    expect(check.onChanged, isNotNull);
    expect(check.value, isFalse);
    await tester.ensureVisible(find.byKey(const ValueKey('kr_confirm_row')));
    await tester.tap(find.byKey(const ValueKey('kr_confirm_row')));
    await tester.pump();
    await tester.tap(find.text('행 검토 적용'));
    await tester.pumpAndSettle();
    expect(applied?['app_sid'], 0);
    expect(applied?['decision'], 'confirmed');
    expect(applied?['observed_name'], '스피드');
    expect(applied?['factor_id'], 101);
  });
}
