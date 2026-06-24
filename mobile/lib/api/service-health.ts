/**
 * Backend service-health signal — distinct from device connectivity.
 *
 * `useNetworkStatus`/OfflineBanner answer "is the device online?". This store
 * answers "is the Kyros API reachable and healthy?", driven by the outcomes of
 * real API calls in `client.ts`:
 *   - a network-level failure (DNS / connection refused / timeout) or a 5xx
 *     response  → service 'unavailable'
 *   - any response the server actually produced (2xx, 3xx, even 4xx) → 'ok',
 *     because the server clearly answered.
 *
 * It's a tiny subscribable store so non-React code (the fetch client) can update
 * it and React can read it via `useSyncExternalStore`.
 */
export type ServiceHealth = 'ok' | 'unavailable';

let _state: ServiceHealth = 'ok';
const _subscribers = new Set<() => void>();

function emit(): void {
  _subscribers.forEach(cb => cb());
}

export function reportServiceUp(): void {
  if (_state !== 'ok') {
    _state = 'ok';
    emit();
  }
}

export function reportServiceDown(): void {
  if (_state !== 'unavailable') {
    _state = 'unavailable';
    emit();
  }
}

export function getServiceHealth(): ServiceHealth {
  return _state;
}

export function subscribeServiceHealth(cb: () => void): () => void {
  _subscribers.add(cb);
  return () => { _subscribers.delete(cb); };
}
