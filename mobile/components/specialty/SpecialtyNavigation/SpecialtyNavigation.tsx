import { Ionicons } from '@expo/vector-icons';
import { ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { HapticPressable } from '../../ui/HapticPressable';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
  withAlpha,
} from '../../../lib/design-tokens';
import { useTheme } from '../../../lib/theme';
import type {
  DoctorCardData,
  SpecialtyNavigationProps,
  VerticalId,
} from './SpecialtyNavigation.types';

type IoniconName = React.ComponentProps<typeof Ionicons>['name'];

// Locked set — 8 verticals, never reconfigured at runtime.
// Icons are approximate: Ionicons has no clinical-specialty icons.
// Flag if a purpose-built clinical icon set becomes available.
const VERTICALS: { id: VerticalId; label: string; icon: IoniconName }[] = [
  { id: 'weight',          label: 'Weight',    icon: 'body-outline' },
  { id: 'thyroid',         label: 'Thyroid',   icon: 'pulse-outline' },
  { id: 'pcos',            label: 'PCOS',      icon: 'medical-outline' },
  { id: 'skin-hair',       label: 'Skin & Hair', icon: 'sparkles-outline' },
  { id: 'intimate-health', label: 'Intimate',  icon: 'shield-outline' },
  { id: 'hormones-trt',    label: 'Hormones',  icon: 'flask-outline' },
  { id: 'longevity',       label: 'Longevity', icon: 'leaf-outline' },
  { id: 'conditions',      label: 'Conditions', icon: 'fitness-outline' },
] as const;

function getInitials(name: string): string {
  return name
    .trim()
    .split(/\s+/)
    .map(n => n[0] ?? '')
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

// ── Vertical tab ───────────────────────────────────────────────────────────────

function VerticalTab({
  id, label, icon, selected, onPress,
}: { id: VerticalId; label: string; icon: IoniconName; selected: boolean; onPress: () => void }) {
  const t = useTheme();
  const strokeColor = selected
    ? (t.isDark ? colors.jadeGlow : colors.forest)
    : t.textSub;

  return (
    <HapticPressable
      haptic="selection"
      scaleTo={0.95}
      onPress={onPress}
      accessibilityLabel={label}
      containerStyle={tab.wrap}
    >
      <View style={[
        tab.container,
        selected && { borderBottomWidth: 2, borderBottomColor: t.isDark ? colors.jadeGlow : colors.forest },
      ]}>
        <Ionicons name={icon} size={22} color={strokeColor} />
        <Text style={[tab.label, { color: strokeColor }]} numberOfLines={1}>{label}</Text>
      </View>
    </HapticPressable>
  );
}

const tab = StyleSheet.create({
  wrap:      { alignItems: 'center' },
  container: {
    alignItems: 'center',
    gap: spacing[1],
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
    minWidth: 64,
  },
  label: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    fontWeight: '500',
  },
});

// ── Doctor card ────────────────────────────────────────────────────────────────

function DoctorCard({ doctor, onBook }: { doctor: DoctorCardData; onBook: () => void }) {
  const t        = useTheme();
  const initials = getInitials(doctor.name);

  return (
    <View style={[card.container, { backgroundColor: t.surface }]}>
      <View style={card.header}>
        {/* Initials avatar — no face photos per platform rule */}
        <View style={[card.avatar, { backgroundColor: withAlpha(t.isDark ? colors.jadeGlow : colors.forest, 0.15) }]}>
          <Text style={[card.avatarText, { color: t.isDark ? colors.jadeGlow : colors.forest }]}>
            {initials}
          </Text>
        </View>

        <View style={card.info}>
          <Text style={[card.name, { color: t.text }]}>{doctor.name}</Text>
          <Text style={[card.qual, { color: t.textSub }]}>{doctor.qualification}</Text>
          <Text style={[card.nmc, { color: t.textSub }]}>NMC Reg: {doctor.nmcRegistration}</Text>
        </View>
      </View>

      <View style={[card.divider, { backgroundColor: t.border }]} />

      <View style={card.footer}>
        <View style={card.availability}>
          <Ionicons name="time-outline" size={14} color={t.textSub} />
          <Text style={[card.availText, { color: t.textSub }]}>{doctor.nextAvailability}</Text>
        </View>

        <HapticPressable
          haptic="medium"
          scaleTo={0.97}
          onPress={onBook}
          accessibilityLabel={`Book consultation with ${doctor.name}`}
        >
          <View style={[card.cta, { backgroundColor: colors.saffron }]}>
            <Text style={card.ctaText}>Book</Text>
          </View>
        </HapticPressable>
      </View>
    </View>
  );
}

const card = StyleSheet.create({
  container: {
    borderRadius: borderRadius.xl,
    padding: spacing[4],
    gap: spacing[3],
  },
  header:   { flexDirection: 'row', alignItems: 'center', gap: spacing[3] },
  avatar:   {
    width: 52,
    height: 52,
    borderRadius: 26,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  avatarText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '700',
  },
  info:     { flex: 1, gap: 3 },
  name: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '600',
  },
  qual: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },
  nmc: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
  },
  divider:  { height: 1 },
  footer:   { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  availability: { flexDirection: 'row', alignItems: 'center', gap: spacing[1] },
  availText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },
  cta: {
    borderRadius: borderRadius.full,
    paddingHorizontal: spacing[5],
    paddingVertical: spacing[2],
  },
  ctaText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '700',
    color: colors.ivoryText,
  },
});

// ── SpecialtyNavigation ────────────────────────────────────────────────────────

export function SpecialtyNavigation({
  selectedVertical,
  onSelectVertical,
  doctors,
  onBookConsultation,
  searchQuery = '',
  onSearchChange,
}: SpecialtyNavigationProps) {
  const t = useTheme();

  const filtered = searchQuery.trim()
    ? doctors.filter(d => d.name.toLowerCase().includes(searchQuery.toLowerCase()))
    : doctors;

  return (
    <View style={nav.container}>
      {/* Horizontal vertical tabs */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={nav.tabRow}
      >
        {VERTICALS.map(v => (
          <VerticalTab
            key={v.id}
            id={v.id}
            label={v.label}
            icon={v.icon}
            selected={selectedVertical === v.id}
            onPress={() => onSelectVertical(v.id)}
          />
        ))}
      </ScrollView>

      {/* Search — scoped to name within the selected vertical */}
      {onSearchChange ? (
        <View style={[nav.searchWrap, { backgroundColor: t.surface }]}>
          <Ionicons name="search-outline" size={16} color={t.textSub} />
          <TextInput
            style={[nav.searchInput, { color: t.text }]}
            value={searchQuery}
            onChangeText={onSearchChange}
            placeholder="Search by doctor name…"
            placeholderTextColor={t.textSub}
            returnKeyType="search"
            accessibilityLabel="Search doctors by name"
          />
        </View>
      ) : null}

      {/* Doctor cards */}
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={nav.doctorList}>
        {filtered.length === 0 ? (
          <View style={nav.empty}>
            <Ionicons name="person-outline" size={32} color={t.textSub} />
            <Text style={[nav.emptyText, { color: t.textSub }]}>No doctors found</Text>
          </View>
        ) : (
          filtered.map(doctor => (
            <DoctorCard
              key={doctor.id}
              doctor={doctor}
              onBook={() => onBookConsultation(doctor)}
            />
          ))
        )}
      </ScrollView>
    </View>
  );
}

const nav = StyleSheet.create({
  container:  { flex: 1 },
  tabRow: {
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[2],
    gap: spacing[1],
  },
  searchWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: spacing[4],
    marginVertical: spacing[2],
    borderRadius: borderRadius.xl,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    gap: spacing[2],
  },
  searchInput: {
    flex: 1,
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    padding: 0,
  },
  doctorList: {
    paddingHorizontal: spacing[4],
    paddingTop: spacing[3],
    gap: spacing[3],
  },
  empty:     { alignItems: 'center', gap: spacing[3], paddingVertical: spacing[10] },
  emptyText: { fontFamily: fontFamily.body, fontSize: fontSize.body },
});
