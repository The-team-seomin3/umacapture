import 'dart:convert';
import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider_platform_interface/path_provider_platform_interface.dart';
import 'package:plugin_platform_interface/plugin_platform_interface.dart';
import 'package:umacapture/src/core/app_variant.dart';
import 'package:umacapture/src/core/bootstrap.dart';
import 'package:umacapture/src/core/path_entity.dart';
import 'package:umacapture/src/core/providers.dart';
import 'package:umacapture/src/core/version_check.dart';

class _Dirs extends PathProviderPlatform with MockPlatformInterfaceMixin {
  _Dirs(this.root);
  final String root;
  @override
  Future<String?> getApplicationSupportPath() async => p.join(root, 'support');
  @override
  Future<String?> getApplicationDocumentsPath() async => p.join(root, 'documents');
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Directory root;
  setUp(() {
    root = Directory.systemTemp.createTempSync('kr-variant-');
    Directory(p.join(root.path, 'support')).createSync();
    Directory(p.join(root.path, 'documents')).createSync();
  });
  tearDown(() => root.deleteSync(recursive: true));

  test('KR startup selects the dedicated bootstrap before stores open', () async {
    PathProviderPlatform.instance = _Dirs(root.path);
    final actual = await readDataRootOverride();
    expect(actual, isNotNull);
    expect(actual, endsWith('kr-factor-app'));
    expect(resolvedDataRoot, actual);
    File(p.join(root.path, 'support', koreanBootstrapFileName)).writeAsStringSync('{broken');
    await expectLater(readDataRootOverride(), throwsA(isA<KoreanDataRootException>()));
    expect(resolvedDataRoot, isNull);
  }, skip: !isKoreanFactorApp);

  test('KR uses a compatible local capture module without consulting an update service', () async {
    final data = DirectoryPath(root.path);
    final paths = PathInfo(documentDir: data, supportDir: data, executableDir: data, downloadDir: data, dataRoot: data);
    Directory(p.join(root.path, 'modules')).createSync();
    File(p.join(root.path, 'modules', 'version_info.json')).writeAsStringSync(
      jsonEncode({
        'format_version': '1.0',
        'region': 'JP',
        'recognizer_version': '2026-01-01T00:00:00+0900',
        'minimum_version': '2021-02-24T00:00:00+0900',
        'application_version': '0.3.0',
        'pin_version': false,
      }),
    );
    final container = ProviderContainer(
      overrides: [
        pathInfoLoader.overrideWith((_) async => paths),
        packageInfoLoader.overrideWith(
          (_) async => PackageInfo(appName: 'umacapture', packageName: 'test', version: '0.3.0', buildNumber: '1'),
        ),
        appVersionCheckLoader.overrideWith((_) => throw StateError('KR must not run the JP update path')),
      ],
    );
    addTearDown(container.dispose);
    final version = await container.read(moduleVersionLoader.future);
    expect(version?.recognizerVersion, DateTime.parse('2026-01-01T00:00:00+0900'));
  }, skip: !isKoreanFactorApp);
}
