import { useEffect, useState } from 'react';
import { Platform } from 'react-native';
import NetInfo, { NetInfoState } from '@react-native-community/netinfo';

export interface NetworkStatus {
  isConnected: boolean;
  isInternetReachable: boolean | null;
}

// We intentionally do NOT override NetInfo's reachability target. Probing our
// own backend (`/healthz`) conflated two different things — "the device is
// offline" and "the Kyros API is down" — so a reachable phone pointed at an
// unreachable backend (e.g. localhost on a physical device, or an API outage)
// showed a permanent "No internet connection" banner. NetInfo's default
// reachability check hits a neutral connectivity endpoint, which is what the
// offline banner actually wants to know.

function useWebNetworkStatus(): NetworkStatus {
  const [online, setOnline] = useState(
    typeof navigator !== 'undefined' ? navigator.onLine : true,
  );

  useEffect(() => {
    // Both web and native hooks run unconditionally (rules of hooks), so this
    // effect executes on native too — where the global `window` exists but has
    // no DOM event APIs. Guard before touching addEventListener.
    if (typeof window === 'undefined' || typeof window.addEventListener !== 'function') {
      return;
    }
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener('online', goOnline);
    window.addEventListener('offline', goOffline);
    return () => {
      window.removeEventListener('online', goOnline);
      window.removeEventListener('offline', goOffline);
    };
  }, []);

  return { isConnected: online, isInternetReachable: online };
}

function useNativeNetworkStatus(): NetworkStatus {
  const [status, setStatus] = useState<NetworkStatus>({
    isConnected: true,
    isInternetReachable: true,
  });

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener((state: NetInfoState) => {
      setStatus({
        isConnected: state.isConnected ?? true,
        isInternetReachable: state.isInternetReachable,
      });
    });
    return unsubscribe;
  }, []);

  return status;
}

export function useNetworkStatus(): NetworkStatus {
  const web = useWebNetworkStatus();
  const native = useNativeNetworkStatus();
  return Platform.OS === 'web' ? web : native;
}
