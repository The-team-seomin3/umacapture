import 'dart:async';

import 'package:auto_route/auto_route.dart';
import 'package:flutter/material.dart';
import 'package:material_symbols_icons/symbols.dart';

import '/src/core/providers.dart';
import '/src/core/utils.dart';
import '/src/gui/theme_extensions.dart';

final _plainToastEvent = EventStreamProvider<ToastData>();
final plainToastEventProvider = _plainToastEvent.provider;

enum ToastType { success, info, warning, error }

class ToastData {
  final ToastType type;
  final String? description;
  final Widget? label;
  final Duration? duration;
  final VoidCallback? onTap;
  final PageRouteInfo? navigateOnTab;

  ToastData({required this.type, this.description, this.label, this.duration, this.onTap, this.navigateOnTab});

  ToastData.success({this.description, this.label, this.duration, this.onTap, this.navigateOnTab})
    : type = ToastType.success;

  ToastData.info({this.description, this.label, this.duration, this.onTap, this.navigateOnTab}) : type = ToastType.info;

  ToastData.warning({this.description, this.label, this.duration, this.onTap, this.navigateOnTab})
    : type = ToastType.warning;

  ToastData.error({this.description, this.label, this.duration, this.onTap, this.navigateOnTab})
    : type = ToastType.error;
}

class Toaster {
  static void show(ToastData data) {
    assert(data.description != null || data.label != null);
    _plainToastEvent.add(data);
  }

  final double narrowWidth;
  final Map<ToastType, Duration> durationMap = {
    ToastType.success: const Duration(seconds: 5),
    ToastType.info: const Duration(seconds: 5),
    ToastType.warning: const Duration(seconds: 10),
    ToastType.error: const Duration(seconds: 15),
  };
  final Map<ToastType, IconData> iconMap = {
    ToastType.success: Symbols.check_circle_rounded,
    ToastType.info: Symbols.info_rounded,
    ToastType.warning: Symbols.warning_rounded,
    ToastType.error: Symbols.dangerous_rounded,
  };
  Toaster({this.narrowWidth = 600.0});

  Color _backgroundColor(AppSemanticColors semantic, ToastType type) => switch (type) {
    ToastType.success => semantic.success,
    ToastType.info => semantic.info,
    ToastType.warning => semantic.warning,
    ToastType.error => semantic.danger,
  };

  double _contrast(Color foreground, Color background) {
    final a = foreground.computeLuminance();
    final b = background.computeLuminance();
    return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
  }

  Color _foregroundColor(ThemeData theme, Color background) {
    // Semantic accents become lighter in dark mode. Choose among existing theme
    // roles rather than assuming their filled backgrounds always need white text.
    final candidates = [theme.semantic.onAccent, theme.colorScheme.onSurface, theme.colorScheme.surface];
    return candidates.reduce((a, b) => _contrast(a, background) >= _contrast(b, background) ? a : b);
  }

  void showToast(BuildContext context, ToastData data) {
    final messenger = ScaffoldMessenger.of(context);
    final theme = Theme.of(context);
    final semantic = theme.semantic;
    final background = _backgroundColor(semantic, data.type);
    final onAccent = _foregroundColor(theme, background);
    final parentSize = MediaQuery.of(context).size;
    final barWidth = Math.min(parentSize.width - 20.0, narrowWidth);
    final isNarrow = barWidth < narrowWidth;
    final duration = data.duration ?? durationMap[data.type]!;
    // Capture the tab router now, while [context] is valid. The SnackBar lives
    // for up to 15s; resolving AutoTabsRouter.of(context) inside onPressed would
    // throw if the originating widget has unmounted by the time it is tapped.
    final tabsRouter = data.navigateOnTab != null ? AutoTabsRouter.of(context) : null;

    final controller = messenger.showSnackBar(
      SnackBar(
        width: barWidth,
        padding: const EdgeInsets.symmetric(vertical: 10),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(5)),
        backgroundColor: background,
        behavior: SnackBarBehavior.floating,
        dismissDirection: isNarrow ? DismissDirection.horizontal : DismissDirection.down,
        duration: duration,
        action: isNarrow
            ? null
            : SnackBarAction(
                textColor: onAccent,
                label: MaterialLocalizations.of(context).closeButtonLabel,
                onPressed: () {},
              ),
        content: TextButton.icon(
          icon: Icon(iconMap[data.type], color: onAccent),
          label: Padding(
            padding: const EdgeInsets.only(left: 10),
            child: Align(
              heightFactor: 1,
              alignment: Alignment.centerLeft,
              child: data.label ?? Text(data.description!, style: TextStyle(color: onAccent, fontSize: 16)),
            ),
          ),
          style: ButtonStyle(overlayColor: WidgetStateProperty.all<Color>(Colors.transparent)),
          onPressed: () {
            messenger.hideCurrentSnackBar(reason: SnackBarClosedReason.action);
            data.onTap?.call();
            if (data.navigateOnTab != null) {
              tabsRouter?.navigate(data.navigateOnTab!);
            }
          },
        ),
      ),
    );

    // ScaffoldMessenger only schedules its built-in auto-dismiss timer when the
    // messenger's enclosing route isCurrent (see ScaffoldMessengerState.build);
    // in this app that condition is not met, so the SnackBar would otherwise
    // stay until manually closed. Drive the dismissal ourselves so [duration] is
    // always honored, cancelling if the user dismisses it first.
    Timer? autoDismiss;
    autoDismiss = Timer(duration, () {
      try {
        controller.close();
      } catch (_) {
        // Already removed (manual dismiss or queue reordering); nothing to do.
      }
    });
    controller.closed.then((_) => autoDismiss?.cancel());
  }
}
