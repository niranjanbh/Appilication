'use client';

import dynamic from 'next/dynamic';
import { useState, useEffect, useRef } from 'react';
import { HealthOverlay } from './HealthOverlay';
import { LoadingLines } from '../ui/LoadingLines';

// Three.js reads window/document on import — ssr:false prevents server crashes
// and isolates the WebGL chunk from hot-module replacement cycles.
const BodySchematic = dynamic(
  () => import('./BodySchematic').then((m) => ({ default: m.BodySchematic })),
  {
    ssr: false,
    loading: () => (
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'rgba(244, 239, 230, 0.7)',
          backdropFilter: 'blur(4px)',
          borderRadius: '12px',
          gap: '8px',
        }}
      >
        <LoadingLines />
        <p
          style={{
            fontFamily: "var(--font-body, system-ui)",
            fontSize: '11px',
            color: '#9B9B98',
            letterSpacing: '0.06em',
            marginTop: '4px',
          }}
        >
          Preparing your model…
        </p>
      </div>
    ),
  },
);

export function DashboardSection() {
  const [canvasHeight, setCanvasHeight] = useState<string>('clamp(400px, 75vw, 520px)');
  // Defer Three.js until the section is close to the viewport.
  // rootMargin: '300px' starts loading ~300 px before the section enters view,
  // so the model is ready by the time the user scrolls to it.
  const [isInView, setIsInView] = useState(false);
  const sectionRef = useRef<HTMLElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsInView(true);
          observer.disconnect();
        }
      },
      { rootMargin: '300px' },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    function measure() {
      const lg = window.innerWidth >= 1024;
      if (lg) {
        setCanvasHeight('100%');
      } else {
        const vh = window.innerHeight;
        const vw = window.innerWidth;
        const natural = Math.min(vw * 0.85, vh * 0.6);
        setCanvasHeight(`${Math.max(380, Math.min(520, natural))}px`);
      }
    }
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, []);

  return (
    <section ref={sectionRef} className="py-16 lg:py-5 border-t border-forest/10 bg-ivory">
      <div className="max-w-7xl lg:h-[920px] mx-auto px-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 lg:h-full gap-8 lg:gap-12 items-center">

          {/* Left: copy */}
          <div>
            <p className="font-body text-caption uppercase tracking-widest text-stone mb-3">
              Your dashboard
            </p>
            <h2 className="font-display text-h2 font-medium text-forest leading-tight mb-5">
              Every consultation<br />builds on the last.
            </h2>
            <p className="font-body text-body text-stone mb-4 leading-relaxed">
              Your dashboard tracks each body system across time. Lab results sit alongside
              your doctor&apos;s interpretation. Prescription changes are visible — including
              dosage adjustments.
            </p>
            <p className="font-body text-body text-stone mb-6 leading-relaxed">
              When you next consult your doctor, they walk in already knowing what&apos;s
              changed. That&apos;s how chronic conditions are supposed to be managed.
            </p>
            <div className="border-l-2 border-forest/30 pl-4">
              <p className="font-display italic text-body-lg text-forest leading-relaxed">
                &ldquo;One place, where your health lives.&rdquo;
              </p>
            </div>
          </div>

          {/* Right: 3D model — only mounted once the section is near the viewport */}
          <div
            ref={containerRef}
            className="relative w-full"
            style={{ height: canvasHeight }}
          >
            {isInView ? (
              <>
                <BodySchematic />
                <HealthOverlay />
              </>
            ) : (
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'rgba(244, 239, 230, 0.7)',
                  borderRadius: '12px',
                }}
              >
                <LoadingLines />
              </div>
            )}
          </div>

        </div>
      </div>
    </section>
  );
}
