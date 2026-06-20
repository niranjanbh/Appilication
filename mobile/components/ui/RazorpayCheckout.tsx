/**
 * RazorpayCheckout — WebView-based Razorpay Standard Checkout for Expo/RN.
 *
 * Razorpay does not ship a maintained native SDK for the current Expo SDK, so
 * we load Razorpay's hosted checkout.js inside a WebView. The page reports the
 * result back to native via `window.ReactNativeWebView.postMessage(...)`.
 *
 * Security notes:
 *  - The Razorpay key_id is a *publishable* key (safe on the client). The
 *    secret never leaves the backend; signature verification is server-side.
 *  - No PHI is passed into the page beyond the prefill contact details the
 *    patient already entered, and nothing is logged.
 */
import { useMemo } from 'react';
import { ActivityIndicator, Modal, StyleSheet, View } from 'react-native';
import { WebView, type WebViewMessageEvent } from 'react-native-webview';
import { colors } from '../../lib/design-tokens';

export interface RazorpayCheckoutProps {
  /** When false the modal is hidden and the WebView is unmounted. */
  visible: boolean;
  orderId: string;
  amountPaise: number;
  currency: string;
  keyId: string;
  prefill?: { name?: string; email?: string; contact?: string };
  /** Razorpay returned a successful, signed payment. */
  onSuccess: (data: {
    razorpay_payment_id: string;
    razorpay_order_id: string;
    razorpay_signature: string;
  }) => void;
  /** Razorpay reported a payment failure. */
  onFailure: (error: { code: string; description: string }) => void;
  /** Patient closed checkout without paying. */
  onDismiss: () => void;
}

interface WebMessage {
  event: 'success' | 'failure' | 'dismiss';
  payload?: Record<string, string>;
}

/** Escape a value for safe interpolation into a single-quoted JS string literal. */
function jsString(value: string | undefined): string {
  if (!value) return '';
  return value.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/[\r\n]/g, ' ');
}

function buildHtml(props: RazorpayCheckoutProps): string {
  const { orderId, amountPaise, currency, keyId, prefill } = props;
  return `<!DOCTYPE html>
<html>
  <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
  </head>
  <body style="margin:0;background:transparent;">
    <script>
      function post(msg) {
        if (window.ReactNativeWebView) {
          window.ReactNativeWebView.postMessage(JSON.stringify(msg));
        }
      }
      function launch() {
        try {
          var options = {
            key: '${jsString(keyId)}',
            order_id: '${jsString(orderId)}',
            amount: ${Number.isFinite(amountPaise) ? Math.trunc(amountPaise) : 0},
            currency: '${jsString(currency)}',
            name: 'Kyros Clinic',
            description: 'Consultation fee',
            prefill: {
              name: '${jsString(prefill && prefill.name)}',
              email: '${jsString(prefill && prefill.email)}',
              contact: '${jsString(prefill && prefill.contact)}'
            },
            theme: { color: '#1f3d2b' },
            modal: {
              ondismiss: function () { post({ event: 'dismiss' }); }
            },
            handler: function (response) {
              post({
                event: 'success',
                payload: {
                  razorpay_payment_id: response.razorpay_payment_id,
                  razorpay_order_id: response.razorpay_order_id,
                  razorpay_signature: response.razorpay_signature
                }
              });
            }
          };
          var rzp = new Razorpay(options);
          rzp.on('payment.failed', function (resp) {
            var err = (resp && resp.error) || {};
            post({
              event: 'failure',
              payload: {
                code: err.code || 'payment_failed',
                description: err.description || 'Payment could not be completed.'
              }
            });
          });
          rzp.open();
        } catch (e) {
          post({ event: 'failure', payload: { code: 'checkout_error', description: 'Could not open checkout.' } });
        }
      }
      if (window.Razorpay) { launch(); }
      else { window.addEventListener('load', launch); }
    </script>
  </body>
</html>`;
}

export function RazorpayCheckout(props: RazorpayCheckoutProps) {
  const { visible, onSuccess, onFailure, onDismiss } = props;

  // Rebuild the page only when the order parameters change.
  const html = useMemo(
    () => buildHtml(props),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [props.orderId, props.amountPaise, props.currency, props.keyId,
     props.prefill?.name, props.prefill?.email, props.prefill?.contact],
  );

  const handleMessage = (event: WebViewMessageEvent) => {
    let msg: WebMessage;
    try {
      msg = JSON.parse(event.nativeEvent.data) as WebMessage;
    } catch {
      return;
    }
    if (msg.event === 'success' && msg.payload) {
      onSuccess({
        razorpay_payment_id: msg.payload['razorpay_payment_id'] ?? '',
        razorpay_order_id: msg.payload['razorpay_order_id'] ?? '',
        razorpay_signature: msg.payload['razorpay_signature'] ?? '',
      });
    } else if (msg.event === 'failure') {
      onFailure({
        code: msg.payload?.['code'] ?? 'payment_failed',
        description: msg.payload?.['description'] ?? 'Payment could not be completed.',
      });
    } else if (msg.event === 'dismiss') {
      onDismiss();
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent={false}
      onRequestClose={onDismiss}
      accessibilityViewIsModal
    >
      <View style={styles.container}>
        {visible && (
          <WebView
            originWhitelist={['*']}
            source={{ html, baseUrl: 'https://checkout.razorpay.com' }}
            javaScriptEnabled
            domStorageEnabled
            onMessage={handleMessage}
            startInLoadingState
            renderLoading={() => (
              <View style={styles.loading}>
                <ActivityIndicator color={colors.jade} size="large" />
              </View>
            )}
            style={styles.webview}
          />
        )}
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.ivory },
  webview: { flex: 1, backgroundColor: colors.ivory },
  loading: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.ivory,
  },
});

export default RazorpayCheckout;
