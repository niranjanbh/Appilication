'use client';

import { useState, useEffect } from 'react';

const SANS = "var(--font-body, 'DM Sans', system-ui, sans-serif)";

type Status = 'green' | 'amber' | 'red';

const STATUS_COLOR: Record<Status, string> = {
  green: '#2D7A4F',
  amber: '#C8A35E',
  red: '#B53A2B',
};

interface Point {
  id: string;
  label: string;
  value: string;
  status: Status;
  side: 'left' | 'right';
  y: number;
}

const POINTS: Point[] = [
  { id: 'hair',      label: 'Hair',     value: '65%',        status: 'red',   side: 'right', y: 10 },
  { id: 'thyroid',   label: 'Thyroid',  value: '3.8 mIU/L',  status: 'amber', side: 'right', y: 28 },
  { id: 'weight',    label: 'Weight',   value: 'BMI 27.0',   status: 'red',   side: 'right', y: 46 },
  { id: 'intimate',  label: 'Intimate', value: '8 / 10',     status: 'green', side: 'right', y: 64 },
  { id: 'skin',      label: 'Skin',      value: 'Sebum 58',   status: 'amber', side: 'left',  y: 16 },
  { id: 'longevity', label: 'Longevity', value: 'HbA1c 5.0%', status: 'green', side: 'left',  y: 40 },
  { id: 'hormonal',  label: 'Hormonal',  value: '280 ng/dL',  status: 'red',   side: 'left',  y: 62 },
];

export function HealthOverlay() {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 1023px)');
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', fontFamily: SANS }}>
      {POINTS.map((p) => {
        const color = STATUS_COLOR[p.status];
        const isRight = p.side === 'right';
        const outerEdge = isMobile ? '72%' : '80%';

        return (
          <div
            key={p.id}
            style={{
              position: 'absolute',
              top: `${p.y}%`,
              transform: 'translateY(-50%)',
              ...(isRight
                ? { left: outerEdge, right: 0 }
                : { left: 0, right: outerEdge }),
              padding: isMobile ? '0 6px' : '0 10px',
            }}
          >
            <p style={{
              margin: 0,
              fontSize: isMobile ? '9px' : '11px',
              fontWeight: 700,
              color: '#1A1A1A',
              letterSpacing: '0.02em',
              textAlign: isRight ? 'left' : 'right',
              lineHeight: 1.3,
              whiteSpace: 'nowrap',
            }}>
              {p.label}
            </p>
            <p style={{
              margin: '3px 0 0',
              fontSize: isMobile ? '8px' : '10px',
              fontWeight: 600,
              color,
              textAlign: isRight ? 'left' : 'right',
              whiteSpace: 'nowrap',
              lineHeight: 1.2,
            }}>
              {p.value}
            </p>
          </div>
        );
      })}
    </div>
  );
}
