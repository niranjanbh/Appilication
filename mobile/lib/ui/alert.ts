/**
 * Cross-platform Alert shim.
 *
 * react-native-web ships `Alert` as a no-op (`class Alert { static alert() {} }`),
 * so every `Alert.alert(...)` call silently does nothing on the web portal —
 * confirmation dialogs (withdraw request, cancel, delete account…) and error
 * toasts never appear, making the triggering buttons look broken.
 *
 * On native we delegate to the real RN Alert. On web we map to the browser's
 * `confirm`/`alert` and dispatch the matching button's `onPress`, so existing
 * call sites keep working unchanged — they just import `Alert` from here instead
 * of from 'react-native'.
 *
 * Covers the common 1- and 2-button cases (the only shapes used in this app).
 * For 3 buttons the non-cancel/destructive action maps to "OK".
 */
import { Alert as RNAlert, Platform, type AlertButton, type AlertOptions } from 'react-native';

function webAlert(title: string, message?: string, buttons?: AlertButton[]) {
  const text = [title, message].filter(Boolean).join('\n\n');

  if (!buttons || buttons.length <= 1) {
    window.alert(text);
    buttons?.[0]?.onPress?.();
    return;
  }

  const confirmed = window.confirm(text);
  const cancelBtn = buttons.find(b => b.style === 'cancel');
  const actionBtn =
    buttons.find(b => b.style === 'destructive') ??
    buttons.find(b => b.style !== 'cancel') ??
    buttons[buttons.length - 1];

  (confirmed ? actionBtn : cancelBtn)?.onPress?.();
}

export const Alert = {
  alert(title: string, message?: string, buttons?: AlertButton[], options?: AlertOptions) {
    if (Platform.OS === 'web') {
      webAlert(title, message, buttons);
    } else {
      RNAlert.alert(title, message, buttons, options);
    }
  },
};
