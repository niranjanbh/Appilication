// Metro configuration for Kyros patient app.
//
// On web builds, native-only libraries (victory-native, @shopify/react-native-skia)
// are redirected to empty stubs. This lets the web bundle compile even when a route
// file imports them — the .web.tsx platform-specific file takes over at runtime.

const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

const config = getDefaultConfig(__dirname);

// Workspace root — needed so Metro can resolve shared packages (design-tokens).
// Spread the Expo defaults so expo-doctor's watchFolders check passes; the
// workspace root supersedes them but they must be present in the array.
const workspaceRoot = path.resolve(__dirname, '..');
config.watchFolders = [workspaceRoot, ...(config.watchFolders ?? [])];
config.resolver.nodeModulesPaths = [
  path.resolve(__dirname, 'node_modules'),
  path.resolve(workspaceRoot, 'node_modules'),
];

// ── pnpm monorepo: block stray react-native versions ─────────────────────────
//
// The website package depends on @react-three/fiber, which pulls expo@56 as a
// peer dependency. expo@56 requires react-native@0.85.3, which lands in the
// shared pnpm store. Metro, watching the workspace root, finds that tree and
// tries to transform VirtualViewExperimentalNativeComponent.js — a 0.85.x file
// that uses an event format @react-native/codegen@0.81.5 cannot parse.
//
// Two-pronged fix:
//   1. blockList — Metro never reads any file from the 0.85.x pnpm-store path.
//   2. resolveRequest redirect — any import of 'react-native' from a package
//      that would otherwise resolve to the 0.85.x copy is redirected to the
//      app's own node_modules (0.81.5).

const existingBlockList = Array.isArray(config.resolver.blockList)
  ? config.resolver.blockList
  : config.resolver.blockList
  ? [config.resolver.blockList]
  : [];

config.resolver.blockList = [
  ...existingBlockList,
  // Block every pnpm-store react-native that is NOT 0.81.x.
  /\.pnpm[\\/]react-native@(?!0\.81\.)/,
  // Block the website's react@18.x from leaking into the mobile bundle.
  /\.pnpm[\\/]react@(?!19\.)/,
];

// Force core packages to always resolve to the copies installed under
// mobile/node_modules.  Without this, packages whose pnpm-store subtree
// points at a different version (e.g. expo@56 → react-native@0.85.3, website
// → react@18.x) cause "multiple copies" runtime crashes.
config.resolver.extraNodeModules = {
  'react': path.resolve(__dirname, 'node_modules/react'),
  'react/jsx-runtime': path.resolve(__dirname, 'node_modules/react/jsx-runtime'),
  'react/jsx-dev-runtime': path.resolve(__dirname, 'node_modules/react/jsx-dev-runtime'),
  'react-native': path.resolve(__dirname, 'node_modules/react-native'),
};

// Stub native-only modules when bundling for web so the static renderer doesn't
// error out on route files that import them.  The actual web screens (.web.tsx)
// don't import these modules at all.
const nativeOnlyStub = path.resolve(__dirname, 'lib/native/web-stub.js');

config.resolver.resolveRequest = (context, moduleName, platform) => {
  if (platform === 'web') {
    const nativeOnly = [
      'victory-native',
      '@shopify/react-native-skia',
      '@livekit/react-native',
      '@livekit/react-native-webrtc',
    ];
    for (const pkg of nativeOnly) {
      if (moduleName === pkg || moduleName.startsWith(pkg + '/')) {
        return { filePath: nativeOnlyStub, type: 'sourceFile' };
      }
    }
  }

  return context.resolveRequest(context, moduleName, platform);
};

module.exports = config;
