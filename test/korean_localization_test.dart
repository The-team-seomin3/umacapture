import 'dart:io';

import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
// ignore: depend_on_referenced_packages
import 'package:shared_preferences/shared_preferences.dart';
import 'package:umacapture/main.dart';
import 'package:umacapture/src/app/pages.dart';
import 'package:umacapture/src/core/localization_util.dart';
import 'package:umacapture/src/gui/app_widget.dart';

import 'support/localization.dart';

Map<String, String> leaves(Map<String, dynamic> json, [String prefix = '']) => {
  for (final entry in json.entries)
    if (entry.value is Map<String, dynamic>)
      ...leaves(entry.value as Map<String, dynamic>, '$prefix${entry.key}.')
    else
      '$prefix${entry.key}': entry.value as String,
};

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('Korean preserves every key, placeholder, intentional blank and line break', () {
    final ja = leaves(localeJson('assets/translations/ja.json'));
    final ko = leaves(localeJson('assets/translations/ko.json'));
    expect(ko.keys.toSet(), ja.keys.toSet());
    final placeholder = RegExp(r'\{[^{}]*\}');
    for (final key in ja.keys) {
      final source = key == 'pages.addon.dialog.copy_placeholder_hint'
          ? ja[key]!.replaceAll('{プレースホルダー}', '{자리표시자}')
          : ja[key]!;
      final translated = ko[key]!;
      List<String> tokens(String text) => placeholder.allMatches(text).map((m) => m[0]!).toList()..sort();
      expect(tokens(translated), tokens(source), reason: key);
      expect(translated.isEmpty, source.isEmpty, reason: key);
      expect('\n'.allMatches(translated).length, '\n'.allMatches(source).length, reason: key);
      expect(RegExp(r'[ぁ-ゖァ-ヺ]').hasMatch(translated), isFalse, reason: key);
    }
  });

  test('platform policy confines Korean default to Windows desktop', () {
    expect(AppLocalization.initialLocaleFor(TargetPlatform.windows, isWeb: false), const Locale('ko'));
    expect(AppLocalization.initialLocaleFor(TargetPlatform.windows, isWeb: true), const Locale('ja'));
    expect(AppLocalization.initialLocaleFor(TargetPlatform.android, isWeb: false), const Locale('ja'));
  });

  testWidgets('Windows overrides saved Japanese before rendering waiting screen and narrow navigation', (tester) async {
    debugDefaultTargetPlatformOverride = TargetPlatform.windows;
    addTearDown(() => debugDefaultTargetPlatformOverride = null);
    SharedPreferences.setMockInitialValues({'locale': 'ja'});
    await EasyLocalization.ensureInitialized();
    await tester.binding.setSurfaceSize(const Size(360, 640));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(AppLocalization(
      child: Builder(builder: (context) => MaterialApp(
        locale: context.locale,
        supportedLocales: context.supportedLocales,
        localizationsDelegates: context.localizationDelegates,
        home: const AppInstanceWaitingScreen(),
      )),
    ));
    await tester.pumpAndSettle();
    final ko = localeJson('assets/translations/ko.json');
    expect(find.text((ko['app'] as Map)['single_tab']['waiting'] as String), findsOneWidget);
    expect(tester.takeException(), isNull);
    expect(Pages.labels.first.label, '대시보드');
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: AppNavigationDrawer(onSelected: (_) {}))));
    await tester.pumpAndSettle();
    for (final label in Pages.labels) {
      expect(find.text(label.label), findsOneWidget);
    }
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox.shrink());
    loadAppTranslations();
  });

  test('both shipped locale resources remain nonempty UTF-8 JSON', () {
    for (final path in appLocaleFiles()) {
      expect(File(path).readAsStringSync(), isNotEmpty);
      expect(localeJson(path), isNotEmpty);
    }
  });
}
