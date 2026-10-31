// Opt-in actual-widget screenshots; not part of the ordinary CI test selection.
import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:easy_localization/easy_localization.dart';
import 'package:flex_color_scheme/flex_color_scheme.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
// ignore: depend_on_referenced_packages
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:umacapture/main.dart';
import 'package:umacapture/src/core/path_entity.dart';
import 'package:umacapture/src/core/capture_preview.dart';
import 'package:umacapture/src/core/platform_channel.dart';
import 'package:umacapture/src/core/platform_controller.dart';
import 'package:umacapture/src/core/providers.dart';
import 'package:umacapture/src/core/video_import_ops.dart';
import 'package:umacapture/src/gui/app_fonts.dart';
import 'package:umacapture/src/gui/app_widget.dart';
import 'package:umacapture/src/gui/capture.dart';
import 'package:umacapture/src/gui/common.dart';
import 'package:umacapture/src/gui/toast.dart';
import 'package:umacapture/src/preference/notifier.dart';

import '../../test/support/hive.dart';
import '../../test/support/localization.dart';
import '../../test/support/riverpod.dart';
import 'korean_visual_surfaces.dart';

const output = String.fromEnvironment('KOREAN_VISUAL_OUTPUT');
const captureKey = ValueKey('korean-visual-capture');
final scaffoldKey = GlobalKey<ScaffoldState>();

ThemeData previewTheme(WidgetRef ref, bool dark) {
  final base = dark
      ? FlexThemeData.dark(
          scheme: FlexScheme.blue,
          surfaceMode: FlexSurfaceMode.highScaffoldLowSurface,
          blendLevel: 15,
          subThemesData: const FlexSubThemesData(outlinedButtonOutlineSchemeColor: SchemeColor.primary),
          visualDensity: FlexColorScheme.comfortablePlatformDensity,
          useMaterial3: true,
          fontFamily: koreanUiFontFamily,
        )
      : FlexThemeData.light(
          scheme: FlexScheme.blue,
          surfaceMode: FlexSurfaceMode.highScaffoldLowSurface,
          blendLevel: 20,
          subThemesData: const FlexSubThemesData(outlinedButtonOutlineSchemeColor: SchemeColor.primary),
          visualDensity: FlexColorScheme.comfortablePlatformDensity,
          useMaterial3: true,
          fontFamily: koreanUiFontFamily,
        );
  // This is the same production theme modifier, including the user's default bold setting.
  return ApplicationWidgetState().modifyTheme(ref, base);
}

Future<void> loadRealFonts() async {
  final manifest = jsonDecode(await rootBundle.loadString('FontManifest.json')) as List;
  expect(manifest.where((e) => e['family'] == koreanUiFontFamily), hasLength(1));
  for (final family in manifest) {
    final loader = FontLoader(family['family'] as String);
    for (final font in family['fonts'] as List) {
      loader.addFont(rootBundle.load(font['asset'] as String));
    }
    await loader.load();
  }
  expect(await rootBundle.loadString(koreanUiFontLicenseAsset), contains('SIL OPEN FONT LICENSE'));
}

String titleFor(String surface) {
  if (surface.startsWith('capture')) return 'pages.capture.title'.tr();
  if (surface.startsWith('settings')) return 'pages.settings.title'.tr();
  if (surface == 'storage') return 'pages.storage.title'.tr();
  return 'pages.chara_detail.title'.tr();
}

class PreviewHost extends ConsumerWidget {
  const PreviewHost({super.key, required this.surface, required this.dark, required this.wide, required this.body});
  final String surface;
  final bool dark;
  final bool wide;
  final Widget body;

  @override
  Widget build(BuildContext context, WidgetRef ref) => RepaintBoundary(
    key: captureKey,
    child: MaterialApp(
      debugShowCheckedModeBanner: false,
      locale: const Locale('ko'),
      supportedLocales: const [Locale('ko'), Locale('ja')],
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      theme: surface == 'waiting'
          ? ThemeData(brightness: dark ? Brightness.dark : Brightness.light, fontFamily: koreanUiFontFamily)
          : previewTheme(ref, dark),
      home: surface == 'waiting'
          ? body
          : DialogLayer(
              child: Scaffold(
                key: scaffoldKey,
                appBar: AppBar(title: Text(titleFor(surface))),
                drawer: wide ? null : AppNavigationDrawer(onSelected: (_) {}),
                body: Row(
                  children: [
                    if (wide)
                      AppNavigationRail(
                        selectedIndex: surface.startsWith('capture')
                            ? 1
                            : (surface.startsWith('settings') || surface == 'storage' ? 4 : 2),
                        onSelected: _ignore,
                      ),
                    Expanded(child: body),
                  ],
                ),
              ),
            ),
    ),
  );
}

void _ignore(int _) {}

Future<void> renderFrame(WidgetTester tester) async {
  // Start newly-mounted drawer/snack-bar animations before advancing their clock.
  await tester.pump();
  // Synthetic file enumeration and asset reads need a real event-loop turn.
  await tester.runAsync(() => Future<void>.delayed(const Duration(milliseconds: 80)));
  await tester.pump(const Duration(milliseconds: 350));
  await tester.pump();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  if (output.isEmpty) {
    test('visual preview requires KOREAN_VISUAL_OUTPUT', () {}, skip: 'Opt-in; see tool/visual/README.md');
    return;
  }
  useStorageBoxForTest();
  setUpAll(() async {
    loadAppTranslations(locale: const Locale('ko'));
    await loadRealFonts();
    Directory(output).createSync(recursive: true);
  });
  setUp(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(
      PlatformChannel.channel,
      (call) async => null,
    );
  });
  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger.setMockMethodCallHandler(
      PlatformChannel.channel,
      null,
    );
  });

  const surfaces = [
    'navigation',
    'capture_unavailable',
    'capture_ready',
    'capture_waiting',
    'capture_importing',
    'records_empty',
    'settings_top',
    'settings_middle',
    'settings_bottom',
    'storage',
    'delete_confirmation',
    'error',
    'notification_success',
    'notification_error',
    'waiting',
  ];
  for (final dark in [false, true]) {
    for (final wide in [true, false]) {
      for (final surface in surfaces) {
        final name = '${dark ? 'dark' : 'light'}_${wide ? 'normal' : 'narrow'}_$surface';
        testWidgets(name, (tester) async {
          await tester.binding.setSurfaceSize(Size(wide ? 1280 : 480, 900));
          addTearDown(() => tester.binding.setSurfaceSize(null));
          final temp = Directory.systemTemp.createTempSync('umacapture-visual-');
          addTearDown(() => temp.deleteSync(recursive: true));
          final layout = PathInfo(
            documentDir: DirectoryPath('${temp.path}/documents'),
            supportDir: DirectoryPath('${temp.path}/support'),
            executableDir: DirectoryPath('${temp.path}/exe'),
            downloadDir: DirectoryPath('${temp.path}/downloads'),
          );
          for (final path in [
            layout.documentDir.path,
            layout.supportDir.path,
            layout.executableDir.path,
            layout.downloadDir.path,
          ]) {
            Directory(path).createSync(recursive: true);
          }
          final controllerReady = surface != 'capture_unavailable';
          final container = createVisualContainer(
            layout,
            additionalOverrides: [
              capturingStateProvider.overrideWith((ref) => surface == 'capture_waiting'),
              platformControllerProvider.overrideWith((ref) {
                if (!controllerReady) return null;
                final controller = PlatformController(ref, const {});
                ref.onDispose(controller.dispose);
                return controller;
              }),
              capturePreviewEnabledProvider.overrideWith(() => BooleanNotifier(entryKey: null, defaultValue: true)),
            ],
          );
          final import = ValueNotifier<VideoImportState>(
            surface == 'capture_importing'
                ? const VideoImportState(phase: VideoImportPhase.importing, fileName: 'synthetic-korean-preview.mkv')
                : VideoImportState.idle,
          );
          addTearDown(import.dispose);
          Widget body;
          if (surface.startsWith('capture')) {
            body = SingleChildScrollView(
              child: CaptureControlGroup(
                importState: import,
                importAvailable: true,
                frameGrabAvailable: true,
                captureSupported: true,
              ),
            );
          } else if (surface.startsWith('settings')) {
            body = settingsVisualBody();
          } else if (surface == 'storage') {
            body = storageVisualBody();
          } else if (surface == 'error') {
            body = errorVisualBody();
          } else if (surface == 'waiting') {
            body = const AppInstanceWaitingScreen();
          } else {
            body = recordsVisualBody();
          }
          await pumpWithContainer(tester, container, PreviewHost(surface: surface, dark: dark, wide: wide, body: body));
          await renderFrame(tester);
          if (surface == 'capture_waiting') {
            container.read(charaDetailCaptureStateProvider.notifier).started('synthetic-visual-record');
            await renderFrame(tester);
          }
          if (surface == 'navigation' && !wide) {
            scaffoldKey.currentState!.openDrawer();
            await renderFrame(tester);
            expect(scaffoldKey.currentState!.isDrawerOpen, isTrue);
          }
          if (surface == 'delete_confirmation') {
            await showDeleteVisual(container);
            await renderFrame(tester);
          }
          if (surface.startsWith('settings') && surface != 'settings_top') {
            final scroll = tester.state<ScrollableState>(
              find.descendant(of: find.byType(ListTilePageRootWidget), matching: find.byType(Scrollable)).first,
            );
            for (var i = 0; i < 4; i++) {
              scroll.position.jumpTo(scroll.position.maxScrollExtent * (surface == 'settings_middle' ? 0.5 : 1));
              await renderFrame(tester);
            }
          }
          if (surface.startsWith('notification')) {
            Toaster().showToast(
              scaffoldKey.currentContext!,
              surface == 'notification_success'
                  ? ToastData.success(description: 'toast.clipboard.success_file'.tr())
                  : ToastData.error(description: 'app.record_store_blocked'.tr()),
            );
            await renderFrame(tester);
          }
          if (surface == 'storage') {
            final calculating = find.text('pages.storage.status.calculating'.tr());
            for (var attempt = 0; attempt < 50 && calculating.evaluate().isNotEmpty; attempt++) {
              await renderFrame(tester);
            }
            expect(calculating, findsNothing, reason: 'capture completed synthetic storage totals');
          }
          if (surface.startsWith('notification')) {
            expect(find.byType(SnackBar), findsOneWidget);
            expect(tester.getRect(find.byType(SnackBar)).top, lessThan(900));
          }
          final errors = <String>[];
          Object? error;
          while ((error = tester.takeException()) != null) {
            errors.add(error.toString());
          }
          final boundary = tester.renderObject<RenderRepaintBoundary>(find.byKey(captureKey));
          await tester.runAsync(() async {
            final image = await boundary.toImage(pixelRatio: 1);
            final bytes = (await image.toByteData(format: ui.ImageByteFormat.png))!;
            await File('$output/$name.png').writeAsBytes(bytes.buffer.asUint8List());
            image.dispose();
            await File('$output/$name.json').writeAsString(
              jsonEncode({
                'surface': surface,
                'theme': dark ? 'dark' : 'light',
                'width': wide ? 1280 : 480,
                'height': 900,
                'font': koreanUiFontFamily,
                'synthetic': true,
                'frameworkErrors': errors,
              }),
            );
          });
          if (surface.startsWith('notification')) {
            ScaffoldMessenger.of(scaffoldKey.currentContext!).removeCurrentSnackBar();
            await tester.pump();
          }
          await tester.pumpWidget(const SizedBox.shrink());
          await tester.pump();
          expect(errors, isEmpty, reason: name);
        }, variant: TargetPlatformVariant.only(TargetPlatform.windows));
      }
    }
  }
}
