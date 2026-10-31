import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive_ce/hive.dart';
import 'package:umacapture/src/core/sentry_util.dart';
import 'package:umacapture/src/core/version_check.dart';
import 'package:umacapture/src/gui/common.dart';
import 'package:umacapture/src/gui/dashboard.dart';
import 'package:umacapture/src/gui/settings.dart';
import 'package:umacapture/src/gui/theme_extensions.dart';
import 'package:version/version.dart';

import 'support/hive.dart';
import 'support/localization.dart';

class _NoNetwork extends HttpOverrides {
  int attempts = 0;
  @override
  HttpClient createHttpClient(SecurityContext? context) {
    attempts++;
    throw StateError('Unexpected network request');
  }
}

ModuleVersionRawData _module(String requirement) =>
    ModuleVersionRawData('1.0.0', 'jp', '2026-08-01T00:00:00+0900', '2021-02-24T00:00:00+0900', requirement);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  useHiveForTest(['settings', 'telemetry_id', 'version_check']);
  setUp(() async {
    for (final box in ['settings', 'telemetry_id', 'version_check']) {
      await Hive.box(box).clear();
    }
    loadAppTranslations();
  });

  for (final consent in <bool?>[null, true, false]) {
    test('startup stays offline with persisted consent $consent, including restart', () async {
      if (consent != null) await Hive.box('settings').put('allowPostUserData', consent);
      final network = _NoNetwork();
      final previous = HttpOverrides.current;
      HttpOverrides.global = network;
      try {
        var starts = 0;
        for (var boot = 0; boot < 2; boot++) {
          await runWithSentry(() {
            starts++;
          });
          captureException(StateError('synthetic failure'), StackTrace.current);
          captureError('synthetic diagnostic');
          expect(await SentryRateLimit.download(), isNull);
          expect(isSentryAvailable(), isFalse);
        }
        expect(starts, 2);
        expect(network.attempts, 0);
        expect(Hive.box('telemetry_id').get('telemetry_id'), isNull);
        expect(Hive.box('settings').get('allowPostUserData'), consent);
      } finally {
        HttpOverrides.global = previous;
      }
    });
  }

  test('cached upstream version cannot enable app updates or request news', () async {
    await Hive.box(
      'version_check',
    ).putAll({'lastAppVersionChecked': DateTime.now(), 'localAppVersion': '1.0.0', 'latestAppVersion': '99.0.0'});
    final container = ProviderContainer.test(
      overrides: [localAppVersionLoader.overrideWith((ref) async => Version(1, 0, 0))],
    );
    final network = _NoNetwork();
    final previous = HttpOverrides.current;
    HttpOverrides.global = network;
    try {
      final result = await container.read(appVersionCheckLoader.future);
      expect(result.local, Version(1, 0, 0));
      expect(result.isUpdatable, isFalse);
      expect(await container.read(newsMarkdownLoader.future), isEmpty);
      expect(network.attempts, 0);
    } finally {
      HttpOverrides.global = previous;
      container.dispose();
    }
  });

  test('module fallback retains readable compatible local data only', () {
    expect(compatibleInstalledModule(_module('1.0.0'), Version(1, 2, 3)), isNotNull);
    expect(compatibleInstalledModule(_module('9.0.0'), Version(1, 2, 3)), isNull);
    expect(compatibleInstalledModule(_module('invalid'), Version(1, 2, 3)), isNull);
    expect(compatibleInstalledModule(null, Version(1, 2, 3)), isNull);
  });

  for (final locale in ['ja', 'ko']) {
    for (final brightness in Brightness.values) {
      for (final width in [540.0, 1000.0]) {
        testWidgets('locked controls keep layout: $locale $brightness $width', (tester) async {
          loadAppTranslations(locale: Locale(locale));
          if (const bool.fromEnvironment('FORK_UI_PREVIEW') && locale == 'ko') {
            final loader = FontLoader('NanumGothic')
              ..addFont(rootBundle.load('assets/fonts/nanum_gothic/NanumGothic-Regular.ttf'));
            await loader.load();
          }
          tester.view.physicalSize = Size(width, 900);
          tester.view.devicePixelRatio = 1;
          addTearDown(tester.view.resetPhysicalSize);
          addTearDown(tester.view.resetDevicePixelRatio);
          await Hive.box('settings').put('allowPostUserData', true);
          var pressed = 0;
          await tester.pumpWidget(
            ProviderScope(
              child: MaterialApp(
                theme: ThemeData(brightness: brightness, fontFamily: locale == 'ko' ? 'NanumGothic' : null).copyWith(
                  extensions: [
                    brightness == Brightness.dark
                        ? AppSemanticColors.dark(ColorScheme.fromSeed(seedColor: Colors.blue, brightness: brightness))
                        : AppSemanticColors.light(ColorScheme.fromSeed(seedColor: Colors.blue)),
                  ],
                ),
                home: Scaffold(
                  body: ListView(
                    children: [
                      const PrivacySettingsGroup(),
                      AppUpdaterGroup(version: Version(1, 0, 0)),
                      UnavailableFeature(
                        child: TextButton(
                          onPressed: () {
                            pressed++;
                          },
                          child: const Text('retired', style: TextStyle(decoration: TextDecoration.lineThrough)),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          );
          await tester.pumpAndSettle();
          expect(tester.takeException(), isNull);
          if (const bool.fromEnvironment('FORK_UI_PREVIEW') && locale == 'ko' && width == 540) {
            await tester.runAsync(() async {
              final boundary = tester.renderObject<RenderRepaintBoundary>(find.byType(RepaintBoundary).first);
              final image = await boundary.toImage();
              final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
              final file = File('.notes/issue15-ui/$locale-${brightness.name}-$width.png');
              await file.parent.create(recursive: true);
              await file.writeAsBytes(bytes!.buffer.asUint8List());
              image.dispose();
            });
          }
          expect(find.text('common.fork_feature_unavailable'), findsNothing);
          expect(find.text(locale == 'ko' ? '이 포크에서는 사용할 수 없습니다' : 'このフォークでは利用できません'), findsOneWidget);
          final toggle = tester.widget<Switch>(find.byType(Switch));
          expect(toggle.value, isFalse);
          expect(toggle.onChanged, isNull);
          await tester.tap(find.byType(Switch), warnIfMissed: false);
          await tester.tap(find.text('retired'), warnIfMissed: false);
          await tester.sendKeyEvent(LogicalKeyboardKey.tab);
          await tester.sendKeyEvent(LogicalKeyboardKey.enter);
          await tester.sendKeyEvent(LogicalKeyboardKey.space);
          await tester.pump();
          expect(pressed, 0);
          expect(Hive.box('settings').get('allowPostUserData'), isTrue);
          expect(tester.widget<Text>(find.text('retired')).style?.decoration, TextDecoration.lineThrough);
          expect(tester.takeException(), isNull);
        });
      }
    }
  }
}
