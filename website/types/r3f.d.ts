// Bridge @react-three/fiber JSX types into React's JSX namespace.
// @types/react@19 uses React.JSX; R3F v8 augments the global JSX namespace.
// This file makes Three.js elements (ambientLight, mesh, etc.) valid JSX.
import type { ThreeElements } from '@react-three/fiber';

declare module 'react' {
  namespace JSX {
    interface IntrinsicElements extends ThreeElements {}
  }
}
