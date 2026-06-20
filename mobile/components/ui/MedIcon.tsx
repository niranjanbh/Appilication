import { Canvas, Circle, Group, LinearGradient, RoundedRect, vec, Line as SkiaLine } from '@shopify/react-native-skia';
import { StyleSheet, View } from 'react-native';
import { colors } from '../../lib/design-tokens';

type MedForm = 'capsule' | 'tablet' | 'softgel' | 'injection';

interface MedIconProps {
  form: MedForm;
  size?: number;
  accessibilityLabel?: string;
}

export function MedIcon({ form, size = 34, accessibilityLabel }: MedIconProps) {
  return (
    <View
      style={[styles.container, { width: size, height: size }]}
      accessibilityLabel={accessibilityLabel ?? form}
    >
      <Canvas style={{ width: size, height: size }}>
        {form === 'capsule' && <CapsuleIcon size={size} />}
        {form === 'tablet' && <TabletIcon size={size} />}
        {form === 'softgel' && <SoftgelIcon size={size} />}
        {form === 'injection' && <InjectionIcon size={size} />}
      </Canvas>
    </View>
  );
}

function CapsuleIcon({ size }: { size: number }) {
  const w = size * 0.82;
  const h = size * 0.44;
  const x = (size - w) / 2;
  const y = (size - h) / 2;
  const r = h / 2;
  const midX = size / 2;

  return (
    <Group>
      <RoundedRect x={x} y={y} width={w / 2} height={h} r={r} color="#F4F1E8" />
      <RoundedRect x={midX} y={y} width={w / 2} height={h} r={r} color={colors.terracotta} />
      <RoundedRect
        x={x}
        y={y}
        width={w}
        height={h}
        r={r}
        color="transparent"
        style="stroke"
        strokeWidth={0.5}
      >
        <LinearGradient
          start={vec(x, y)}
          end={vec(x, y + h)}
          colors={['rgba(255,255,255,0.4)', 'rgba(0,0,0,0.08)']}
        />
      </RoundedRect>
    </Group>
  );
}

function TabletIcon({ size }: { size: number }) {
  const r = size * 0.36;
  const cx = size / 2;
  const cy = size / 2;

  return (
    <Group>
      <Circle cx={cx} cy={cy} r={r}>
        <LinearGradient
          start={vec(cx - r * 0.6, cy - r * 0.6)}
          end={vec(cx + r, cy + r)}
          colors={['#FFFFFF', '#E6DFD0']}
        />
      </Circle>
      <SkiaLine
        p1={vec(cx - r * 0.6, cy)}
        p2={vec(cx + r * 0.6, cy)}
        color="#CDC6B4"
        strokeWidth={0.8}
      />
      <Circle
        cx={cx}
        cy={cy}
        r={r}
        color="transparent"
        style="stroke"
        strokeWidth={0.5}
      >
        <LinearGradient
          start={vec(cx, cy - r)}
          end={vec(cx, cy + r)}
          colors={['rgba(255,255,255,0.5)', 'rgba(0,0,0,0.10)']}
        />
      </Circle>
    </Group>
  );
}

function SoftgelIcon({ size }: { size: number }) {
  const r = size * 0.36;
  const cx = size / 2;
  const cy = size / 2;

  return (
    <Group>
      <Circle cx={cx} cy={cy} r={r}>
        <LinearGradient
          start={vec(cx - r * 0.6, cy - r * 0.6)}
          end={vec(cx + r, cy + r)}
          colors={['#F3C87C', '#C2891F']}
        />
      </Circle>
      <Circle cx={cx - r * 0.25} cy={cy - r * 0.25} r={r * 0.15} color="rgba(255,230,171,0.45)" />
      <Circle
        cx={cx}
        cy={cy}
        r={r}
        color="transparent"
        style="stroke"
        strokeWidth={0.5}
      >
        <LinearGradient
          start={vec(cx, cy - r)}
          end={vec(cx, cy + r)}
          colors={['rgba(255,255,255,0.3)', 'rgba(0,0,0,0.12)']}
        />
      </Circle>
    </Group>
  );
}

function InjectionIcon({ size }: { size: number }) {
  const cx = size / 2;
  const cy = size / 2;
  const bodyW = size * 0.18;
  const bodyH = size * 0.52;
  const needleH = size * 0.18;
  const plungerH = size * 0.12;

  const bodyX = cx - bodyW / 2;
  const bodyY = cy - bodyH / 2 + plungerH / 2;

  return (
    <Group transform={[{ rotate: -0.785 }]} origin={vec(cx, cy)}>
      <RoundedRect x={bodyX} y={bodyY} width={bodyW} height={bodyH} r={bodyW * 0.2}>
        <LinearGradient
          start={vec(bodyX, bodyY)}
          end={vec(bodyX + bodyW, bodyY)}
          colors={['#F6F3EA', '#FFFDF8', '#E6DFD0']}
        />
      </RoundedRect>
      <SkiaLine
        p1={vec(cx, bodyY + bodyH)}
        p2={vec(cx, bodyY + bodyH + needleH)}
        color={colors.terracotta}
        strokeWidth={1.5}
        strokeCap="round"
      />
      <RoundedRect
        x={cx - bodyW * 0.35}
        y={bodyY - plungerH}
        width={bodyW * 0.7}
        height={plungerH}
        r={2}
        color={colors.terracotta}
      />
    </Group>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: 'center', justifyContent: 'center' },
});
