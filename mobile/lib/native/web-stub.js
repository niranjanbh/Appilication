// Empty stub for native-only modules on web builds.
// Metro redirects victory-native and @shopify/react-native-skia here when
// platform === 'web'. The actual web screens (.web.tsx) don't import these
// modules, so this stub is only reached by the .tsx route files that are
// included in the static renderer bundle but overridden at runtime.
module.exports = new Proxy(
  {},
  {
    get: (_, key) => {
      if (key === '__esModule') return true;
      if (key === 'default') return {};
      // Return a no-op function for any named export (hooks, components, etc.)
      return () => null;
    },
  },
);
