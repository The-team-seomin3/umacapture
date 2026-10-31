import 'package:easy_localization/easy_localization.dart';
// ignore: depend_on_referenced_packages
import 'package:easy_logger/easy_logger.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:logger/logger.dart';

import '/src/core/utils.dart';

extension LevelMessagesExtension on LevelMessages {
  Level get asLoggerLevel {
    switch (this) {
      case LevelMessages.debug:
        return Level.debug;
      case LevelMessages.info:
        return Level.info;
      case LevelMessages.warning:
        return Level.warning;
      case LevelMessages.error:
        return Level.error;
    }
  }
}

void _easyLocalizationPrinter(Object object, {String? name, StackTrace? stackTrace, LevelMessages? level}) {
  final loggerLevel = level?.asLoggerLevel ?? EasyLocalization.logger.defaultLevel.asLoggerLevel;
  final message = "$name: ${object.toString()}";
  if (stackTrace == null) {
    logger.log(loggerLevel, message);
  } else {
    logger.log(loggerLevel, message, "EasyLocalizationError", stackTrace);
  }
}

Future<void> setupLocalization() async {
  EasyLocalization.logger = EasyLogger(
    name: "Easy Localization",
    printer: _easyLocalizationPrinter,
    enableLevels: [
      // LevelMessages.debug,
      LevelMessages.info,
      LevelMessages.error,
      LevelMessages.warning,
    ],
  );
  await EasyLocalization.ensureInitialized();
}

/// Both startup surfaces use the same locale policy. Windows is the Korean UI build.
class AppLocalization extends StatelessWidget {
  const AppLocalization({super.key, required this.child});

  final Widget child;

  static Locale initialLocaleFor(TargetPlatform platform, {required bool isWeb}) =>
      !isWeb && platform == TargetPlatform.windows ? const Locale('ko') : const Locale('ja');

  @override
  Widget build(BuildContext context) => EasyLocalization(
    path: 'assets/translations',
    useOnlyLangCode: true,
    useFallbackTranslations: true,
    supportedLocales: const [Locale('ko'), Locale('ja')],
    startLocale: initialLocaleFor(defaultTargetPlatform, isWeb: kIsWeb),
    fallbackLocale: const Locale('ja'),
    saveLocale: false,
    child: Builder(
      builder: (context) {
        final initial = initialLocaleFor(defaultTargetPlatform, isWeb: kIsWeb);
        // easy_localization 3.0.8 can prefer the device locale when a saved locale
        // exists, even with saveLocale disabled. Resolve that before mounting UI.
        if (context.locale != initial) {
          return FutureBuilder<void>(
            future: context.setLocale(initial),
            builder: (context, snapshot) {
              if (snapshot.hasError) return ErrorWidget(snapshot.error!);
              return snapshot.connectionState == ConnectionState.done ? child : const SizedBox.shrink();
            },
          );
        }
        return child;
      },
    ),
  );
}
