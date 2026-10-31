// Production-widget surfaces for synthetic Korean visual verification.
// The caller owns localization, real-font loading, theme, Hive fixture and screenshots.
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart';
import 'package:version/version.dart';

import 'package:umacapture/src/chara_detail/chara_detail_record.dart';
import 'package:umacapture/src/chara_detail/spec/base.dart';
import 'package:umacapture/src/chara_detail/spec/loader.dart';
import 'package:umacapture/src/chara_detail/storage.dart';
import 'package:umacapture/src/core/providers.dart';
import 'package:umacapture/src/core/version_check.dart';
import 'package:umacapture/src/gui/chara_detail/data_table_widget.dart';
import 'package:umacapture/src/gui/chara_detail/delete_record_dialog.dart';
import 'package:umacapture/src/gui/common.dart';
import 'package:umacapture/src/gui/settings.dart';
import 'package:umacapture/src/gui/storage_tree.dart';

class _VisualRecords extends CharaDetailRecordStorage {
  _VisualRecords(this.syntheticRecords);
  final List<CharaDetailRecord> syntheticRecords;

  @override
  Future<List<CharaDetailRecord>> build() async => syntheticRecords;
}

class _VisualArchive extends CharaDetailArchiveStorage {
  @override
  Future<List<CharaDetailRecord>> build() async => const [];
}

/// Builds an isolated provider graph with no module/network checks or real store scan.
/// [layout] must point only to a newly-created synthetic temporary directory.
/// Pass [columns]/[records] and matching module-label overrides for populated grids.
/// Do not duplicate the default providers in [additionalOverrides].
ProviderContainer createVisualContainer(
  PathInfo layout, {
  List<CharaDetailRecord> records = const [],
  List<ColumnSpec> columns = const [],
  List<Override> additionalOverrides = const [],
}) {
  final version = Version(0, 0, 0);
  return ProviderContainer(
    retry: (_, _) => null,
    overrides: [
      pathLayoutLoader.overrideWith((ref) async => layout),
      pathInfoLoader.overrideWith((ref) async => layout),
      settingsOnWebProvider.overrideWithValue(false),
      storageOnWebProvider.overrideWithValue(false),
      appVersionCheckLoader.overrideWith((ref) async => AppVersionCheckResult(local: version, latest: version)),
      moduleVersionLoader.overrideWith((ref) async => null),
      charaDetailRecordStorageLoaderProvider.overrideWith(() => _VisualRecords(records)),
      charaDetailArchiveStorageLoaderProvider.overrideWith(_VisualArchive.new),
      displayedRecordsProvider.overrideWithValue(records),
      currentColumnSpecsProvider.overrideWithValue(columns),
      currentColumnSpecBrokenIdsProvider.overrideWithValue(const {}),
      charaDetailQuarantineCountProvider.overrideWith((ref) async => 0),
      charaDetailArchiveOutageProvider.overrideWithValue(null),
      charaDetailUnavailableRecordsProvider.overrideWithValue(const {}),
      ...additionalOverrides,
    ],
  );
}

/// Full production settings content; capture multiple scroll positions to see all groups.
Widget settingsVisualBody() => const SettingsPage();

/// Production record toolbar, column/filter chips and table/empty-state widgets.
/// The bootstrap loader is intentionally bypassed: only injected synthetic data is used.
Widget recordsVisualBody() => Consumer(
  builder: (context, ref, _) =>
      SingleTilePageRootWidget(child: const CharaDetailDataTableLoaderLayer().data(context, ref)),
);

/// Production storage tree; only the caller's synthetic [PathInfo] is enumerated.
Widget storageVisualBody() => const StorageTreeView();

/// Production error view with explicit synthetic diagnostics and localized product controls.
Widget errorVisualBody() => ErrorLogView(
  title: 'pages.chara_detail.loading_error'.tr(),
  message: StateError('Synthetic visual verification error; no user data.'),
  stackTrace: 'synthetic_visual_fixture.dart:1',
);

/// Opens the real bulk-delete confirmation but never confirms or writes anything.
/// The caller must mount [DialogLayer] and pump after calling this function.
Future<void> showDeleteVisual(ProviderContainer container) async {
  BulkDeleteRecordDialog.show(
    container.read(containerRefProvider),
    recordIds: const ['visual-synthetic-a', 'visual-synthetic-b'],
    source: RecordSource.active,
  );
}
