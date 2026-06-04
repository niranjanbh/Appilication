/**
 * Background health sync task — registered at module load time so the OS can
 * wake the app every 4 hours and run a HealthKit / Health Connect sync.
 *
 * Requires a custom dev client (expo-background-fetch + expo-task-manager are
 * native modules; they are not available in Expo Go or on web).
 *
 * This file MUST be imported before the React tree mounts (i.e. in _layout.tsx)
 * so that TaskManager.defineTask is called before the OS triggers the task.
 */
import { Platform } from 'react-native';

export const HEALTH_SYNC_TASK = 'KYROS_HEALTH_SYNC';

if (Platform.OS !== 'web') {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const TaskManager = require('expo-task-manager');
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const BackgroundFetch = require('expo-background-fetch');

    TaskManager.defineTask(HEALTH_SYNC_TASK, async () => {
      try {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const { fetchHealthData } = require('./health-data') as typeof import('./health-data');
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const { postHealthSync } = require('../api/health-sync') as typeof import('../api/health-sync');

        const source = Platform.OS === 'ios' ? 'apple_health' : 'google_health_connect';
        const until = new Date();
        const since = new Date(until.getTime() - 7 * 24 * 60 * 60 * 1000);

        const datapoints = await fetchHealthData(source, since, until);
        if (datapoints.length > 0) {
          await postHealthSync({
            source,
            data_range_start: since.toISOString(),
            data_range_end: until.toISOString(),
            datapoints,
          });
        }

        return BackgroundFetch.BackgroundFetchResult.NewData;
      } catch {
        return BackgroundFetch.BackgroundFetchResult.Failed;
      }
    });
  } catch {
    // expo-task-manager / expo-background-fetch not available (Expo Go or missing prebuild)
  }
}

export async function registerHealthSyncTask(): Promise<void> {
  if (Platform.OS === 'web') return;
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const BackgroundFetch = require('expo-background-fetch');
    const status = await BackgroundFetch.getStatusAsync();
    if (
      status === BackgroundFetch.BackgroundFetchStatus.Restricted ||
      status === BackgroundFetch.BackgroundFetchStatus.Denied
    ) {
      return;
    }
    await BackgroundFetch.registerTaskAsync(HEALTH_SYNC_TASK, {
      minimumInterval: 4 * 60 * 60, // 4 hours in seconds
      stopOnTerminate: false,
      startOnBoot: true,
    });
  } catch {
    // Not available without custom dev client
  }
}
