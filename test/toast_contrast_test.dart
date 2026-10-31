import 'package:flex_color_scheme/flex_color_scheme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:umacapture/src/gui/theme_extensions.dart';
import 'package:umacapture/src/gui/toast.dart';

void main() {
  for (final dark in [false, true]) {
    for (final type in ToastType.values) {
      testWidgets('${dark ? 'dark' : 'light'} $type toast uses readable text, icon and dismissal', (tester) async {
        final base = dark
            ? FlexThemeData.dark(scheme: FlexScheme.blue, useMaterial3: true)
            : FlexThemeData.light(scheme: FlexScheme.blue, useMaterial3: true);
        final theme = base.copyWith(
          extensions: [dark ? AppSemanticColors.dark(base.colorScheme) : AppSemanticColors.light(base.colorScheme)],
        );
        final key = GlobalKey<ScaffoldState>();
        await tester.pumpWidget(
          MaterialApp(
            theme: theme,
            home: Scaffold(key: key),
          ),
        );
        Toaster().showToast(key.currentContext!, ToastData(type: type, description: 'Contrast sample'));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 350));
        final snack = tester.widget<SnackBar>(find.byType(SnackBar));
        final text = tester.widget<Text>(find.text('Contrast sample'));
        final foreground = text.style!.color!;
        final a = foreground.computeLuminance();
        final b = snack.backgroundColor!.computeLuminance();
        final ratio = ((a > b ? a : b) + 0.05) / ((a < b ? a : b) + 0.05);
        expect(ratio, greaterThanOrEqualTo(4.5));
        expect(snack.action!.textColor, foreground);
        final icon = tester.widget<Icon>(find.descendant(of: find.byType(SnackBar), matching: find.byType(Icon)).first);
        expect(icon.color, foreground);
        ScaffoldMessenger.of(key.currentContext!).removeCurrentSnackBar();
        await tester.pump();
        await tester.pumpWidget(const SizedBox.shrink());
      });
    }
  }
}
