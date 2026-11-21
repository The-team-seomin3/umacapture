import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:umacapture/src/core/kr_factor_workflow.dart';
import 'package:umacapture/src/gui/kr_factor_workflow.dart';

class HandoffFixture extends KrFactorAdapter {
  HandoffFixture() : super(LocalKrCommandTransport());
  final nameHash = 'a' * 64;
  final starHash = 'b' * 64;
  final groups = ['self', 'parent1', 'parent2'];
  late final rows = [
    for (final group in groups)
      {
        'group': group,
        'index': 0,
        'raw_text': 'OCR $group',
        'star': 1,
        'name_crop': '$group-name.png',
        'star_crop': '$group-star.png',
      },
  ];
  late final question = {
    'group': 'parent2',
    'index': 0,
    'name_crop_sha256': nameHash,
    'star_crop_sha256': starHash,
    'question': 'How many stars?',
    'reason': 'Obscured edge',
    'answer': null,
  };
  late Map<String, dynamic> review = {
    'rows': [
      for (final group in groups)
        {
          'group': group,
          'index': 0,
          'name_crop_sha256': nameHash,
          'star_crop_sha256': starHash,
          'decision': group == 'parent1' ? 'verified' : 'unreviewed',
        },
    ],
    'coverage': {},
    'owner_handoff': {
      'version': 1,
      'agent_review_complete': false,
      'requests': [question],
    },
  };
  var revision = 0;
  bool ready = false;
  final commands = <String>[];
  Map<String, dynamic> get response => {
    'rows': rows,
    'review': review,
    'source_image': 'source.png',
    'review_sha256': 'rev-$revision',
    'review_issues': ['Review self/0', 'Review parent2/0'],
    'ready_to_export': ready,
  };
  @override
  Future<KrAdapterResponse> execute({
    required String interpreter,
    required String adapter,
    required String command,
    required Map<String, dynamic> request,
  }) async {
    commands.add(command);
    if (command == 'save-review') {
      expect(request['expected_review_sha256'], 'rev-$revision');
      review = jsonDecode(jsonEncode(request['review'])) as Map<String, dynamic>;
      revision++;
    } else {
      expect(command, 'load');
    }
    return KrAdapterResponse(response);
  }
}

void main() {
  testWidgets('only outstanding owner requests appear and saving an answer preserves row decisions', (tester) async {
    tester.view.physicalSize = const Size(1400, 3000);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final fixture = HandoffFixture();
    final originalRows = jsonEncode(fixture.review['rows']);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [krFactorAdapterProvider.overrideWithValue(fixture)],
        child: const MaterialApp(
          home: Scaffold(body: KrFactorWorkflowPanel(dataRoot: '.', loadSettings: false)),
        ),
      ),
    );
    Future<void> tap(String text) async {
      final target = find.text(text);
      await tester.ensureVisible(target);
      await tester.tap(target);
      await tester.pumpAndSettle();
    }

    bool exportEnabled() => tester.widget<FilledButton>(find.byKey(const ValueKey('kr_export'))).onPressed != null;
    await tap('기존 작업 재개');
    expect(find.textContaining('OCR self'), findsNothing);
    expect(find.textContaining('OCR parent1'), findsNothing);
    expect(find.text('Review self/0'), findsNothing);
    expect(find.textContaining('Obscured edge'), findsOneWidget);
    await tap('전체 검토 기록 보기');
    expect(find.text('Review self/0'), findsOneWidget);
    expect(find.textContaining('OCR parent1'), findsOneWidget);
    await tap('전체 검토 기록 보기');
    await tap('How many stars?');
    expect(tester.widgetList<KrPixelImage>(find.byType(KrPixelImage)).map((w) => w.path), [
      'parent2-name.png',
      'parent2-star.png',
    ]);
    final input = find.descendant(of: find.byType(AlertDialog), matching: find.byType(TextField));
    expect(tester.widget<FilledButton>(find.widgetWithText(FilledButton, '답변 저장')).onPressed, isNull);
    await tester.enterText(input, 'Two stars');
    await tester.pump();
    await tap('답변 저장');
    expect(jsonEncode(fixture.review['rows']), originalRows);
    expect(fixture.review['owner_handoff']['requests'].single['answer'], 'Two stars');
    await tap('기존 작업 재개');
    expect(find.text('How many stars?'), findsNothing);
    expect(find.textContaining('에이전트 검토 미완료'), findsOneWidget);
    expect(exportEnabled(), isFalse);
    fixture.review['owner_handoff']['agent_review_complete'] = true;
    await tap('기존 작업 재개');
    expect(find.textContaining('에이전트 검토 완료'), findsOneWidget);
    expect(exportEnabled(), isFalse);
    expect(fixture.commands, ['load', 'save-review', 'load', 'load']);
  });

  test('missing, malformed, duplicate or misbound handoffs cannot present a ready queue', () {
    final fixture = HandoffFixture()..ready = true;
    final request = fixture.question;
    final handoff = fixture.review.remove('owner_handoff') as Map;
    expect(KrReviewSession.fromResponse(fixture.response).ready, isFalse);
    for (final invalid in [
      null,
      {...handoff, 'version': 2},
      {...handoff, 'agent_review_complete': 'yes'},
      for (final requests in [
        [request, request],
        [
          {...request, 'star_crop_sha256': 'c' * 64},
        ],
        [
          {...request, 'group': 'missing'},
        ],
        [
          {...request, 'answer': ' '},
        ],
        [
          {...request, 'reason': ''},
        ],
      ])
        {...handoff, 'requests': requests},
    ]) {
      fixture.review['owner_handoff'] = invalid;
      expect(() => KrReviewSession.fromResponse(fixture.response), throwsA(isA<KrAdapterException>()));
    }
    fixture.review['owner_handoff'] = {...handoff, 'agent_review_complete': true};
    expect(KrReviewSession.fromResponse(fixture.response).ready, isFalse);
    fixture.review['owner_handoff']['requests'] = [
      {...request, 'answer': 'Two stars'},
    ];
    expect(KrReviewSession.fromResponse(fixture.response).ready, isFalse);
    for (final row in fixture.review['rows']) {
      row['decision'] = 'verified';
    }
    expect(KrReviewSession.fromResponse(fixture.response).ready, isTrue);
  });
}
