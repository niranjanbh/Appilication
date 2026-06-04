/**
 * Print trigger button + print CSS injection for desktop web.
 *
 * Injects a <style> tag with @media print rules that hide navigation,
 * sidebars, and interactive controls, leaving a clean clinical document.
 *
 * Two variants:
 *  - "prescription": Kyros header, patient/doctor block, medication list
 *  - "lab-report": Kyros header, patient block, biomarker table
 *
 * Platform: web only — returns null on native.
 */

import { Platform, Pressable, StyleSheet, Text } from 'react-native';
import { useEffect } from 'react';
import { borderRadius, colors, fontFamily, fontSize, spacing } from '../../lib/design-tokens';

type PrintVariant = 'prescription' | 'lab-report';

interface PrintButtonProps {
  variant: PrintVariant;
  label?: string;
}

const PRINT_CSS = `
@media print {
  /* Hide all chrome */
  [data-kyros-sidebar],
  [data-kyros-tabs],
  [data-kyros-banner],
  [data-kyros-print-hide],
  button,
  [role="button"] {
    display: none !important;
  }

  /* Reset backgrounds for clean black-on-white output */
  body, * {
    background: white !important;
    color: black !important;
    font-family: 'Arial', sans-serif !important;
  }

  /* Clinic header block */
  [data-kyros-print-header] {
    display: block !important;
    border-bottom: 2px solid black;
    padding-bottom: 8px;
    margin-bottom: 16px;
  }

  /* Biomarker table / prescription table borders */
  table {
    border-collapse: collapse;
    width: 100%;
  }
  th, td {
    border: 1px solid #999;
    padding: 4px 8px;
    text-align: left;
    font-size: 11px;
  }
  th {
    background: #eee !important;
    font-weight: bold;
  }

  /* Page breaks */
  [data-kyros-print-section] {
    page-break-inside: avoid;
  }

  /* Footer */
  [data-kyros-print-footer] {
    display: block !important;
    border-top: 1px solid #ccc;
    margin-top: 24px;
    padding-top: 8px;
    font-size: 9px;
    color: #666 !important;
  }

  /* Ensure charts render as static — hide interactive overlays */
  svg {
    pointer-events: none;
  }
  [data-chart-overlay] {
    display: none !important;
  }
}
`;

const STYLE_ID = 'kyros-print-css';

function injectPrintCSS() {
  if (typeof document === 'undefined') return;
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement('style');
  style.id = STYLE_ID;
  style.textContent = PRINT_CSS;
  document.head.appendChild(style);
}

export function PrintButton({ variant, label }: PrintButtonProps) {
  useEffect(() => {
    if (Platform.OS === 'web') injectPrintCSS();
  }, []);

  if (Platform.OS !== 'web') return null;

  const buttonLabel = label ?? (variant === 'prescription' ? 'Print prescription' : 'Print report');

  const handlePrint = () => {
    if (typeof window !== 'undefined') {
      window.print();
    }
  };

  return (
    <Pressable
      onPress={handlePrint}
      style={styles.btn}
      accessibilityLabel={buttonLabel}
      data-kyros-print-hide
    >
      <Text style={styles.btnText}>🖨 {buttonLabel}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  btn: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.stone + '40',
    borderRadius: borderRadius.md,
    paddingVertical: spacing[2],
    paddingHorizontal: spacing[3],
    gap: spacing[1],
  },
  btnText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    color: colors.ink,
  },
});
