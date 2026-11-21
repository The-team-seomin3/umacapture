import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:umacapture/const.dart';
import 'package:umacapture/src/core/bootstrap.dart';

void main() {
  late Directory root;
  late Directory support;
  late Directory jpSupport;
  late Directory documents;
  setUp(() {
    root = Directory.systemTemp.createTempSync('kr-bootstrap-');
    final company = Directory(p.join(root.path, 'Roaming', 'umasagashi'))..createSync(recursive: true);
    support = Directory(p.join(company.path, 'umacapture Korean Factor OCR'))..createSync();
    jpSupport = Directory(p.join(company.path, 'umacapture'))..createSync();
    documents = Directory(p.join(root.path, 'documents'))..createSync();
  });
  tearDown(() => root.deleteSync(recursive: true));
  Future<String> read([Map<String, String> env = const {}]) =>
      readKoreanDataRoot(supportDirectory: support, documentsDirectory: documents, environment: env);
  test('default KR root ignores JP bootstrap and process override', () async {
    final jp = Directory(p.join(root.path, 'jp'))..createSync();
    final file = File(p.join(jpSupport.path, bootstrapFileName))..writeAsStringSync(sampleBootstrapContent(jp.path));
    final before = file.readAsBytesSync();
    final actual = await read({dataRootOverrideEnvVar: jp.path});
    expect(actual, p.join(support.resolveSymbolicLinksSync(), 'kr-factor-app'));
    expect(resolvedDataRoot, actual);
    expect(file.readAsBytesSync(), before);
    expect(jp.listSync(), isEmpty);
  });
  test('missing configured KR root stops instead of creating or falling back', () async {
    final missing = p.join(root.path, 'missing');
    await expectLater(read({koreanDataRootEnvVar: missing}), throwsA(isA<KoreanDataRootException>()));
    expect(resolvedDataRoot, isNull);
    expect(dataRootDegraded, isTrue);
    expect(Directory(missing).existsSync(), isFalse);
  });
  test('malformed KR config refuses startup without opening the default', () async {
    File(p.join(support.path, koreanBootstrapFileName)).writeAsStringSync('{broken');
    await expectLater(read(), throwsA(isA<KoreanDataRootException>()));
    expect(resolvedDataRoot, isNull);
    expect(Directory(p.join(support.path, 'kr-factor-app')).existsSync(), isFalse);
  });
  test('configured root cannot equal, contain or nest in JP storage', () async {
    final jp = Directory(p.join(documents.path, 'umacapture'))..createSync();
    final child = Directory(p.join(jp.path, 'child'))..createSync();
    for (final path in [jp.path, child.path, documents.path]) {
      await expectLater(read({koreanDataRootEnvVar: path}), throwsA(isA<KoreanDataRootException>()));
      expect(resolvedDataRoot, isNull);
    }
  });
  test('rejects overlap with a relocated JP root before making a default KR directory', () async {
    await expectLater(read({dataRootOverrideEnvVar: support.path}), throwsA(isA<KoreanDataRootException>()));
    expect(Directory(p.join(support.path, 'kr-factor-app')).existsSync(), isFalse);
  });
  test('reads the JP product pointer and rejects equal, nested and enclosing KR roots', () async {
    final relocated = Directory(p.join(root.path, 'relocated', 'jp'))..createSync(recursive: true);
    final child = Directory(p.join(relocated.path, 'nested'))..createSync();
    final sentinel = File(p.join(relocated.path, 'settings.bin'))..writeAsStringSync('JP settings');
    final pointer = File(p.join(jpSupport.path, bootstrapFileName))
      ..writeAsStringSync(sampleBootstrapContent(relocated.path));
    final pointerBefore = pointer.readAsBytesSync();
    expect(File(p.join(support.path, bootstrapFileName)).existsSync(), isFalse);
    for (final path in [relocated.path, child.path, relocated.parent.path]) {
      await expectLater(read({koreanDataRootEnvVar: path}), throwsA(isA<KoreanDataRootException>()));
      expect(resolvedDataRoot, isNull);
      expect(dataRootDegraded, isTrue);
      expect(pointer.readAsBytesSync(), pointerBefore);
      expect(sentinel.readAsStringSync(), 'JP settings');
      expect(
        relocated.listSync().map((entity) => p.basename(entity.path)),
        unorderedEquals(['settings.bin', 'nested']),
      );
      expect(child.listSync(), isEmpty);
    }
  });
  test('rejects a saved KR path in the JP product module directory', () async {
    final modules = Directory(p.join(jpSupport.path, 'modules'))..createSync();
    File(p.join(support.path, koreanBootstrapFileName)).writeAsStringSync(sampleBootstrapContent(modules.path));
    await expectLater(read(), throwsA(isA<KoreanDataRootException>()));
    expect(resolvedDataRoot, isNull);
    expect(modules.listSync(), isEmpty);
  });
  test('existing disjoint KR root resolves without changing JP settings', () async {
    final kr = Directory(p.join(root.path, 'kr'))..createSync();
    File(p.join(support.path, koreanBootstrapFileName)).writeAsStringSync(sampleBootstrapContent(kr.path));
    expect(await read(), kr.resolveSymbolicLinksSync());
    expect(dataRootDegraded, isFalse);
  });
}
