/// Bootstrap layer that resolves the user-configurable data root BEFORE the app
/// has any access to its own settings.
///
/// The settings database (Hive) is itself relocatable, so the chosen location
/// cannot live inside it — we would need the location before the database is
/// open. Instead a tiny JSON file is kept at a fixed, OS-managed path
/// ([getApplicationSupportDirectory]) that is never relocated. It records the
/// override root and is read at the very start of `main()`, before Hive and
/// before any provider resolves a path.
///
/// When no override is recorded (the default), every path keeps its current
/// native location, so behavior is unchanged for existing installs.
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '/src/core/app_logger.dart';
import '/src/core/app_variant.dart';

/// Current on-disk schema version of [bootstrapFileName].
const int _bootstrapVersion = 1;

/// Name of the fixed bootstrap file that records the data root override.
///
/// Public so the settings UI can show its location, letting a user hand-edit the
/// data root if the in-app change ever fails to write it.
const String bootstrapFileName = "data_root.json";

/// Environment variable that overrides the data root, taking precedence over
/// [bootstrapFileName].
///
/// Unlike the file, this is process-scoped (set only in the launching
/// process's environment) and leaves no state behind if the process is killed,
/// which is what makes it safe for an automated test harness to use instead of
/// the file — see the doc comment at the top of this library.
const String dataRootOverrideEnvVar = "UMACAPTURE_DATA_ROOT";

const String _versionKey = "version";

const String _dataRootKey = "data_root";

/// The override root resolved during [readDataRootOverride], cached for the
/// lifetime of the process.
///
/// `pathInfoLoader` reads this synchronously so the path layer and the Hive
/// layer agree on the same root without re-reading the bootstrap file. `null`
/// means "no override" (use native defaults). Defaults to `null` until
/// [readDataRootOverride] runs in `main()`.
String? resolvedDataRoot;

/// Whether a data root was recorded but could not be used this launch.
///
/// Set when the bootstrap file names a root that cannot be created (e.g. an
/// external drive that is currently unplugged). In that case the app falls back
/// to the native defaults; the UI can surface this so the user understands why
/// their data appears to be missing.
bool dataRootDegraded = false;

/// The data root as recorded in the bootstrap file, regardless of whether it is
/// usable this launch.
///
/// Unlike [resolvedDataRoot] (which is nulled out when the root is unusable),
/// this keeps the recorded path so the settings UI can name the location that is
/// currently unreachable — telling the user *which* drive to reconnect — and
/// offer to clear the stale pointer. `null` means no override is recorded.
String? configuredDataRoot;

/// Returns a sample `data_root.json` body pointing at [examplePath].
///
/// Built with the same encoder, schema version, and keys the app itself writes
/// (see [writeDataRootOverride]), so the sample shown in the settings UI can
/// never drift from the real format. The encoder escapes backslashes, so a
/// Windows [examplePath] comes out correctly JSON-escaped for the user to copy.
String sampleBootstrapContent(String examplePath) =>
    const JsonEncoder.withIndent("  ").convert({_versionKey: _bootstrapVersion, _dataRootKey: examplePath});

/// Returns the fixed bootstrap file, independent of any override.
Future<File> _bootstrapFile() async {
  final supportDir = await getApplicationSupportDirectory();
  return File(p.join(supportDir.path, isKoreanFactorApp ? koreanBootstrapFileName : bootstrapFileName));
}

const String koreanBootstrapFileName = 'data_root_kr.json';
const String koreanDataRootEnvVar = 'UMACAPTURE_KR_DATA_ROOT';

class KoreanDataRootException implements Exception {
  const KoreanDataRootException(this.message);
  final String message;
  @override
  String toString() => message;
}

/// KR never reads JP's override as its own root. Read it only to refuse overlap.
/// A missing default KR directory may be created; a configured missing drive may not.
Future<String> readKoreanDataRoot({
  required Directory supportDirectory,
  required Directory documentsDirectory,
  required Map<String, String> environment,
}) async {
  resolvedDataRoot = null;
  configuredDataRoot = null;
  dataRootDegraded = false;
  try {
    final file = File(p.join(supportDirectory.path, koreanBootstrapFileName));
    var createDefault = false;
    var root = environment[koreanDataRootEnvVar];
    if (root == null || root.trim().isEmpty) {
      if (file.existsSync()) {
        final value = jsonDecode(file.readAsStringSync());
        if (value is! Map ||
            value['version'] != 1 ||
            value['data_root'] is! String ||
            (value['data_root'] as String).trim().isEmpty) {
          throw const FormatException('KR 데이터 경로 설정 형식이 올바르지 않습니다.');
        }
        root = value['data_root'] as String;
      } else {
        root = p.join(supportDirectory.path, 'kr-factor-app');
        createDefault = true;
      }
    }
    configuredDataRoot = root;
    if (!p.isAbsolute(root) || (!createDefault && !_ensureUsable(root))) {
      throw const FormatException('KR 데이터 경로가 없거나 절대 경로가 아닙니다. 드라이브와 권한을 확인하세요.');
    }
    final actual = Directory(root).existsSync()
        ? Directory(root).resolveSymbolicLinksSync()
        : p.join(supportDirectory.resolveSymbolicLinksSync(), 'kr-factor-app');
    final protected = <String>[p.join(documentsDirectory.path, 'umacapture'), p.join(supportDirectory.path, 'modules')];
    final jpEnv = environment[dataRootOverrideEnvVar];
    if (jpEnv != null && jpEnv.trim().isNotEmpty) protected.add(jpEnv);
    final jpFile = File(p.join(supportDirectory.path, bootstrapFileName));
    if (jpFile.existsSync()) {
      final jp = jsonDecode(jpFile.readAsStringSync());
      if (jp is Map && jp['data_root'] is String) protected.add(jp['data_root'] as String);
    }
    for (final source in protected) {
      if (!p.isAbsolute(source)) continue;
      final target = Directory(source).existsSync()
          ? Directory(source).resolveSymbolicLinksSync()
          : p.normalize(source);
      if (p.equals(actual, target) || p.isWithin(target, actual) || p.isWithin(actual, target)) {
        throw const FormatException('KR 데이터 경로가 JP 저장소와 겹칩니다. 별도 폴더를 선택하세요.');
      }
    }
    if (createDefault) Directory(actual).createSync(recursive: true);
    final probe = Directory(actual).createTempSync('.kr-startup-probe-');
    probe.deleteSync();
    resolvedDataRoot = actual;
    return actual;
  } catch (error) {
    dataRootDegraded = true;
    throw KoreanDataRootException('KR 저장소를 열지 않았습니다. JP 경로로 전환하지 않습니다.\n$error');
  }
}

/// Recovery is available before settings or startup maintenance opens any store.
Future<void> writeKoreanDataRoot(String? root) async {
  final supportDir = await getApplicationSupportDirectory();
  final file = File(p.join(supportDir.path, koreanBootstrapFileName));
  if (root == null) {
    if (file.existsSync()) file.deleteSync();
  } else {
    if (!_ensureUsable(root)) throw const FormatException('존재하는 절대 경로를 선택하세요.');
    file.writeAsStringSync(sampleBootstrapContent(root), flush: true);
  }
}

/// Reads the configured data root and caches it in [resolvedDataRoot].
///
/// Returns the absolute override path, or `null` when no override is recorded,
/// the file is missing or malformed, or the recorded root is unusable. This
/// never throws: any failure degrades to the native defaults so a broken
/// bootstrap file can never block startup.
Future<String?> readDataRootOverride() async {
  dataRootDegraded = false;
  configuredDataRoot = null;
  // Web has no relocatable data root: OPFS is the storage root, and there is no
  // OS-managed support directory to hold the bootstrap file. Skip
  // the whole override concept so the path_provider call never runs on web.
  if (kIsWeb) {
    resolvedDataRoot = null;
    return null;
  }
  if (isKoreanFactorApp) {
    try {
      return await readKoreanDataRoot(
        supportDirectory: await getApplicationSupportDirectory(),
        documentsDirectory: await getApplicationDocumentsDirectory(),
        environment: Platform.environment,
      );
    } on KoreanDataRootException {
      rethrow;
    } catch (error) {
      resolvedDataRoot = null;
      dataRootDegraded = true;
      throw KoreanDataRootException('KR 저장소 기본 경로를 확인하지 못했습니다. JP 경로로 전환하지 않습니다.\n$error');
    }
  }
  final envRoot = Platform.environment[dataRootOverrideEnvVar];
  if (envRoot != null && envRoot.trim().isNotEmpty) {
    configuredDataRoot = envRoot;
    if (!_ensureUsable(envRoot)) {
      logger.w("Env-configured data root is not usable; falling back to defaults: $envRoot");
      dataRootDegraded = true;
      resolvedDataRoot = null;
      return null;
    }
    resolvedDataRoot = envRoot;
    return envRoot;
  }
  try {
    final file = await _bootstrapFile();
    if (!file.existsSync()) {
      resolvedDataRoot = null;
      return null;
    }
    final decoded = jsonDecode(file.readAsStringSync());
    final root = (decoded is Map) ? decoded[_dataRootKey] : null;
    if (root is! String || root.trim().isEmpty) {
      resolvedDataRoot = null;
      return null;
    }
    // Record the path before the usability check so the UI can still name an
    // unreachable root in the degraded branch below.
    configuredDataRoot = root;
    if (!_ensureUsable(root)) {
      logger.w("Configured data root is not usable; falling back to defaults: $root");
      dataRootDegraded = true;
      resolvedDataRoot = null;
      return null;
    }
    resolvedDataRoot = root;
    return root;
  } catch (error, stackTrace) {
    logger.e("Failed to read data root override; falling back to defaults.", error, stackTrace);
    resolvedDataRoot = null;
    return null;
  }
}

/// Writes (or clears) the configured data root.
///
/// Passing `null` removes the override so the next launch uses the native
/// defaults. Called by the migration flow after data has been copied to the new
/// location; the change only takes effect on the next launch.
Future<void> writeDataRootOverride(String? root) async {
  // The data-root override does not exist on web (see [readDataRootOverride]).
  if (kIsWeb) {
    return;
  }
  final file = await _bootstrapFile();
  if (root == null || root.trim().isEmpty) {
    if (file.existsSync()) {
      file.deleteSync();
    }
    resolvedDataRoot = null;
    // Drop any stale pointer and clear the degraded flag so the settings UI
    // stops warning about a location the user just abandoned.
    configuredDataRoot = null;
    dataRootDegraded = false;
    return;
  }
  final encoded = const JsonEncoder.withIndent("  ").convert({_versionKey: _bootstrapVersion, _dataRootKey: root});
  file.writeAsStringSync(encoded);
  resolvedDataRoot = root;
  configuredDataRoot = root;
}

/// Whether [root] is an absolute path that exists right now.
///
/// This only inspects the path; it never creates it. The migration flow is
/// responsible for creating the destination before it writes the override, so a
/// recorded root that is missing at startup means the location is genuinely
/// unavailable (e.g. an unplugged drive, or a drive letter now pointing at a
/// different volume) and must degrade rather than be silently re-created as an
/// empty data directory. Rejecting relative paths keeps a hand-edited bootstrap
/// file from resolving Hive against the process working directory.
bool _ensureUsable(String root) {
  try {
    return p.isAbsolute(root) && Directory(root).existsSync();
  } catch (_) {
    return false;
  }
}
