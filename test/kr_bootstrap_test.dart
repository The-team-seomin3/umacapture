import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:umacapture/src/core/bootstrap.dart';

void main() {
  late Directory root;
  late Directory support;
  late Directory documents;
  setUp(() {
    root = Directory.systemTemp.createTempSync('kr-bootstrap-');
    support = Directory(p.join(root.path, 'support'))..createSync();
    documents = Directory(p.join(root.path, 'documents'))..createSync();
  });
  tearDown(() => root.deleteSync(recursive: true));
  Future<String> read([Map<String, String> env = const {}]) =>
      readKoreanDataRoot(supportDirectory: support, documentsDirectory: documents, environment: env);
  test('default KR root ignores JP bootstrap and process override', () async {
    final jp = Directory(p.join(root.path, 'jp'))..createSync();
    final file = File(p.join(support.path, bootstrapFileName))..writeAsStringSync(sampleBootstrapContent(jp.path));
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
  test('existing disjoint KR root resolves without changing JP settings', () async {
    final kr = Directory(p.join(root.path, 'kr'))..createSync();
    File(p.join(support.path, koreanBootstrapFileName)).writeAsStringSync(sampleBootstrapContent(kr.path));
    expect(await read(), kr.resolveSymbolicLinksSync());
    expect(dataRootDegraded, isFalse);
  });
}
