// Metro configuration for Kyros patient app.
//
// On web builds, native-only libraries (victory-native, @shopify/react-native-skia)
// are redirected to empty stubs. This lets the web bundle compile even when a route
// file imports them — the .web.tsx platform-specific file takes over at runtime.

const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

const config = getDefaultConfig(__dirname);

// Workspace root — needed so Metro can resolve shared packages (design-tokens)
const workspaceRoot = path.resolve(__dirname, '..');
config.watchFolders = [workspaceRoot];
config.resolver.nodeModulesPaths = [
  path.resolve(__dirname, 'node_modules'),
  path.resolve(workspaceRoot, 'node_modules'),
];

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
