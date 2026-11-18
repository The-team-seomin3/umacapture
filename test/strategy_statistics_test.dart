import 'package:dart_mappable/dart_mappable.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_symbols_icons/symbols.dart';
import 'package:umacapture/src/chara_detail/chara_detail_record.dart';
import 'package:umacapture/src/chara_detail/spec/base.dart';
import 'package:umacapture/src/chara_detail/spec/loader.dart';
import 'package:umacapture/src/chara_detail/storage.dart';
import 'package:umacapture/src/core/mapper_init.dart';
import 'package:umacapture/src/gui/statistics.dart';
import 'package:umacapture/src/gui/theme_extensions.dart';

import 'support/localization.dart';
import 'support/records.dart' as fixtures;

const _labels = ['strategy zero', 'strategy one', 'strategy two', 'strategy three'];

CharaDetailRecord _record(
  String id, {
  int metadataStrategy = 0,
  List<int> raceStrategies = const [],
  RecordType type = RecordType.standard,
}) {
  final map = fixtures.makeRecord(id: id, card: 1, recordType: type).toMap();
  (map['metadata'] as Map<String, dynamic>)['strategy'] = metadataStrategy;
  map['races'] = [for (final strategy in raceStrategies) Race(0, 0, 0, 0, 0, 0, strategy, 0, 1).toMap()];
  return CharaDetailRecordMapper.fromMap(map);
}

ThemeData _theme() {
  final base = ThemeData();
  return base.copyWith(extensions: [AppChartColors.standard(), AppSemanticColors.light(base.colorScheme)]);
}

CountStrategyChartData _chart(List<CharaDetailRecord> records) =>
    CountStrategyChartData(records, _labels, AppChartColors.standard().categories);

Future<void> _pumpChart(WidgetTester tester, List<CharaDetailRecord> records, {double width = 400}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        statisticsInitialLoader.overrideWith((ref) async => []),
        charaDetailRecordStorageProvider.overrideWithValue(records),
        labelMapProvider.overrideWithValue({LabelKeys.raceStrategy: _labels}),
      ],
      child: MaterialApp(
        theme: _theme(),
        home: Scaffold(
          body: SizedBox(width: width, height: 300, child: const CountStrategyStatisticWidget()),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  setUpAll(initializeMappers);
  setUp(loadAppTranslations);

  test('a missing race is unknown while a genuine first-race strategy zero is counted', () {
    final chart = _chart([
      _record('missing'),
      _record('zero', raceStrategies: [0]),
      _record('one', metadataStrategy: 1, raceStrategies: [1]),
    ]);
    expect(chart.counts, [1, 1, 0, 0]);
    expect(chart.knownCount, 2);
    expect(chart.unknownCount, 1);
    final sections = chart.build(_theme(), 200).data.sections;
    expect(sections.where((section) => section.value > 0).map((section) => section.title), ['50 %', '50 %']);
  });

  test('invalid and inconsistent evidence is excluded rather than repaired or inferred', () {
    final records = [
      _record('negative', metadataStrategy: -1, raceStrategies: [-1]),
      _record('too-large', metadataStrategy: 4, raceStrategies: [4]),
      _record('unsupported-race', raceStrategies: [4]),
      _record('mismatch', metadataStrategy: 1, raceStrategies: [2]),
      _record('later-match', metadataStrategy: 1, raceStrategies: [2, 1]),
      _record('valid', metadataStrategy: 3, raceStrategies: [3, 2]),
    ];
    final before = records.map((record) => record.toRecordJsonBytes()).toList();
    final chart = _chart(records);
    expect(chart.counts, [0, 0, 0, 1]);
    expect(chart.knownCount, 1);
    expect(chart.unknownCount, 5);
    expect(chart.build(_theme(), 200).data.sections.singleWhere((section) => section.value > 0).title, '100 %');
    expect(records.map((record) => record.toRecordJsonBytes()).toList(), before);
  });

  test('unsupported inactive stages are rejected before chart records are constructed', () {
    final map = _record('inactive').toMap();
    (map['metadata'] as Map<String, dynamic>)['stage'] = 'inactive';
    expect(() => CharaDetailRecordMapper.fromMap(map), throwsA(isA<MapperException>()));
    expect(RecordStage.values, [RecordStage.active]);
  });

  testWidgets('mixed coverage uses known-only denominator and shows excluded count', (tester) async {
    await _pumpChart(tester, [
      _record('missing'),
      _record('one', metadataStrategy: 1, raceStrategies: [1]),
    ]);
    expect(find.text('集計対象 1件・未確認の除外 1件'), findsOneWidget);
    final chart = tester.widget<PieChart>(find.byType(PieChart));
    expect(chart.data.sections.singleWhere((section) => section.value > 0).title, '100 %');
    expect(tester.takeException(), isNull);
  });

  testWidgets('all-unknown and empty sets keep coverage visible without a percentage chart', (tester) async {
    await _pumpChart(tester, [
      _record('missing'),
      _record('invalid', metadataStrategy: 8, raceStrategies: [8]),
    ]);
    expect(find.text('集計対象 0件・未確認の除外 2件'), findsOneWidget);
    expect(find.text('-'), findsOneWidget);
    expect(find.byType(PieChart), findsNothing);
    expect(tester.takeException(), isNull);
    await _pumpChart(tester, []);
    expect(find.text('集計対象 0件・未確認の除外 0件'), findsOneWidget);
    expect(find.byType(PieChart), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('category switching recomputes both denominator and excluded records', (tester) async {
    await _pumpChart(tester, [
      _record('trained', raceStrategies: [0]),
      _record('inheritance', type: RecordType.inheritanceOnly),
      _record('friend', metadataStrategy: 2, raceStrategies: [2], type: RecordType.friendStandard),
      _record('friend-inheritance', type: RecordType.friendInheritance),
    ]);
    expect(find.text('集計対象 2件・未確認の除外 2件'), findsOneWidget);
    final next = find.byIcon(Symbols.keyboard_arrow_right_rounded);
    await tester.tap(next);
    await tester.pumpAndSettle();
    expect(find.text('集計対象 1件・未確認の除外 0件'), findsOneWidget);
    await tester.tap(next);
    await tester.pumpAndSettle();
    expect(find.text('集計対象 0件・未確認の除外 1件'), findsOneWidget);
    expect(find.byType(PieChart), findsNothing);
    await tester.tap(next);
    await tester.pumpAndSettle();
    expect(find.text('集計対象 1件・未確認の除外 1件'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Korean coverage fits a narrow tile with actual placeholders resolved', (tester) async {
    loadAppTranslations(locale: const Locale('ko'));
    await _pumpChart(tester, [_record('missing')], width: 240);
    expect(find.text('집계 기준 0건 · 미확인 제외 1건'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
