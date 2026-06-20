import { useEffect, useState } from 'react';
import { Platform } from 'react-native';
import NetInfo, { NetInfoState } from '@react-native-community/netinfo';

export interface NetworkStatus {
  isConnected: boolean;
  isInternetReachable: boolean | null;
}

if (Platform.OS !== 'web') {
  const API_BASE_URL = (process.env['EXPO_PUBLIC_API_BASE_URL'] ?? 'https://api.kyrosclinic.com').replace(/\/$/, '');
  NetInfo.configure({
    reachabilityUrl: `${API_BASE_URL}/healthz`,
    reachabilityTest: async (response) => response.status === 200,
    reachabilityLongTimeout: 60_000,
    reachabilityShortTimeout: 15_000,
    reachabilityRequestTimeout: 10_000,
  });
}

function useWebNetworkStatus(): NetworkStatus {
  const [online, setOnline] = useState(
    typeof navigator !== 'undefined' ? navigator.onLine : true,
  );

  useEffect(() => {
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
