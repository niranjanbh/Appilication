'use client';

import { useRef, useEffect, useState, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Environment } from '@react-three/drei';
import Model from './ForHim';

export function BodySchematic() {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const el = wrapperRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) setSize({ width, height });
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const cameraConfig = useMemo(() => {
    const mobile = size.width > 0 && size.width < 900;
    return mobile
      ? { position: [0, 0, 8] as [number, number, number], fov: 56 }
      : { position: [0, 0, 5] as [number, number, number], fov: 48 };
  }, [size.width]);

  return (
    <div
      ref={wrapperRef}
      style={{ position: 'absolute', inset: 0 }}
      className="flex items-center justify-center"
    >
      {size.width > 0 && size.height > 0 && (
        <Canvas
          style={{
            width: typeof window !== 'undefined' && window.innerWidth < 1000 ? '200px' : '100%',
            height: size.height,
            display: 'block',
          }}
          camera={cameraConfig}
          gl={{ powerPreference: 'high-performance' }}
        >
          <ambientLight intensity={1} />
          <directionalLight position={[5, 5, 5]} intensity={2} color="green" />
          <directionalLight position={[-5, 5, 5]} intensity={2} />
          <Environment preset="studio" />
          <Model />
          <OrbitControls
            enableRotate
            enablePan={false}
            minPolarAngle={Math.PI / 2}
            maxPolarAngle={Math.PI / 2}
            autoRotate
            autoRotateSpeed={1.5}
            enableDamping
            dampingFactor={0.05}
          />
        </Canvas>
      )}
    </div>
  );
}
