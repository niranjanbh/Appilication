'use client';

import { useGLTF, useTexture } from '@react-three/drei';
import * as THREE from 'three';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export default function Model(props: any) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { nodes } = useGLTF('/models/For-Him.glb') as any;
  const texture = useTexture('/models/Material_him.png') as THREE.Texture;

  texture.flipY = false;
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.needsUpdate = true;

  return (
    <group {...props} dispose={null}>
      <mesh
        geometry={nodes.FinalBaseMesh.geometry}
        rotation={[Math.PI / 2, 0, 0]}
        position={[0, -2.6, 0]}
        scale={0.26}
      >
        <meshStandardMaterial map={texture} roughness={1} metalness={0} />
      </mesh>
    </group>
  );
}

useGLTF.preload('/models/For-Him.glb');
