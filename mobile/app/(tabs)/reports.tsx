import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Ionicons } from '@expo/vector-icons';
import {
  FlatList,
  Platform,
  RefreshControl,
  ScrollView,
  SectionList,
  StyleSheet,
  Text,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';
import { useRouter } from 'expo-router';
import { listLabReports, type Biomarker, type LabReport } from '../../lib/api/lab-reports';
import { listBiomarkers, type BiomarkerSummary } from '../../lib/api/biomarker-trends';
import { listPrescriptions, type Prescription } from '../../lib/api/prescriptions';
import { apiFetch } from '../../lib/api/client';
import { AmbientBackground } from '../../components/ui/AmbientBackground';
import { EmptyState } from '../../components/ui/EmptyState';
import { TAB_DOCK_CLEARANCE } from '../../components/ui/GlassTabBar';
import { HapticPressable } from '../../components/ui/HapticPressable';
import { GlassCard } from '../../components/ui/GlassCard';
import { SkeletonCards } from '../../components/ui/Skeleton';
import { Button } from '../../components/Button';
import {
  borderRadius,
  colors,
  fontFamily,
  fontSize,
  spacing,
  withAlpha,
} from '../../lib/design-tokens';
import { useTheme, type AppPalette } from '../../lib/theme';

// ── Types ───────────────────────────────────────────────────────────────────────

type ConsultationStatus =
  | 'requested' | 'scheduled' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled' | 'no_show';

interface Consultation {
  id: string;
  doctor_id: string | null;
  condition_category: string;
  consultation_type: string;
  scheduled_start_at: string | null;
  scheduled_end_at: string | null;
  status: ConsultationStatus;
}

interface ConsultationListResponse {
  items: Consultation[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

type TabKey = 'all' | 'next' | 'rx';
type ViewMode = 'dashboard' | 'list';

interface FlaggedValue {
  name: string;
  value: string;
  unit: string;
  flag: 'high' | 'low';
}

interface ReportSection {
  title: string;
  data: LabReport[];
}

// ── Status config ─────────────────────────────────────────────────────────────

const STATUS_LABEL: Record<string, string> = {
  upload_pending:        'Upload pending',
  ocr_pending:           'Processing…',
  ocr_processing:        'Processing…',
  ocr_complete:          'Ready',
  ocr_failed:            'Processing failed',
  patient_review_needed: 'Needs your review',
};

const STATUS_COLOR: Record<string, string> = {
  upload_pending:        colors.stone,
  ocr_pending:           colors.saffron,
  ocr_processing:        colors.saffron,
  ocr_complete:          colors.jade,
  ocr_failed:            colors.alert,
  patient_review_needed: colors.saffron,
};

const UPCOMING_CONSULT: ConsultationStatus[] = ['requested', 'scheduled', 'confirmed', 'in_progress'];

const CONDITION_LABEL: Record<string, string> = {
  weight: 'Weight Management',
  pcos: 'PCOS',
  thyroid: 'Thyroid',
  skin_hair: 'Skin & Hair',
  mens_intimate: 'Sexual & Intimate Health',
  hormones_trt: 'Hormones & TRT',
  longevity: 'Longevity',
};

// ── Helpers ──────────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
}

function monthLabel(iso: string): string {
  return new Date(iso).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });
}

function formatCat(cat: string): string {
  return CONDITION_LABEL[cat] ?? cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function isProcessing(report: LabReport): boolean {
  return report.status === 'ocr_pending'
    || report.status === 'ocr_processing'
    || report.status === 'upload_pending';
}

function biomarkerCount(report: LabReport): number {
  return report.parsed_json?.biomarkers?.length ?? 0;
}

function flagArrow(flag: 'high' | 'low'): string {
  return flag === 'high' ? '↑' : '↓';
}

/** Flagged biomarkers for a single report — abnormal values the patient should notice. */
function flaggedForReport(report: LabReport): FlaggedValue[] {
  const markers = report.parsed_json?.biomarkers ?? [];
  return markers
    .filter((b): b is Biomarker & { flag: 'high' | 'low' } => b.flag === 'high' || b.flag === 'low')
    .map(b => ({ name: b.name, value: b.value, unit: b.unit, flag: b.flag }));
}

function hasDoctorCommentary(report: LabReport): boolean {
  const c = report.doctor_commentary;
  return c != null && typeof c === 'object' && Object.keys(c).length > 0;
}

/** Group reports into month/year sections, newest first. */
function groupByMonth(reports: LabReport[]): ReportSection[] {
  const sorted = [...reports].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
  const sections: ReportSection[] = [];
  for (const report of sorted) {
    const title = monthLabel(report.created_at);
    const last = sections[sections.length - 1];
    if (last && last.title === title) {
      last.data.push(report);
    } else {
      sections.push({ title, data: [report] });
    }
  }
  return sections;
}

function shadowStyle(isDark: boolean): StyleProp<ViewStyle> {
  return Platform.select<ViewStyle>({
    web: { boxShadow: isDark ? '0 2px 8px rgba(0,0,0,0.4)' : '0 2px 8px rgba(13,59,42,0.08)' },
    default: {
      shadowColor: isDark ? colors.ink : colors.forest,
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: isDark ? 0.4 : 0.08,
      shadowRadius: 8,
      elevation: 3,
    },
  });
}

// ── Shared report card (list mode) ──────────────────────────────────────────────

function ReportCard({ report, onPress, t }: { report: LabReport; onPress: () => void; t: AppPalette }) {
  const sColor = STATUS_COLOR[report.status] ?? colors.stone;
  const sLabel = STATUS_LABEL[report.status] ?? report.status;
  const isPdf = report.content_type === 'application/pdf';

  return (
    <HapticPressable
      scaleTo={0.97}
      onPress={onPress}
      accessibilityLabel={`View ${report.original_filename}`}
    >
      <GlassCard unpadded>
        <View style={styles.simpleCard}>
          <View style={[styles.fileIcon, { backgroundColor: withAlpha(sColor, 0.1) }]}>
            <Text style={[styles.fileIconText, { color: sColor }]}>{isPdf ? 'PDF' : 'IMG'}</Text>
          </View>
          <View style={styles.simpleBody}>
            <Text style={[styles.filename, { color: t.text }]} numberOfLines={1}>
              {report.original_filename}
            </Text>
            {report.lab_name ? (
              <Text style={[styles.metaLine, { color: t.textSub }]} numberOfLines={1}>{report.lab_name}</Text>
            ) : null}
            <Text style={[styles.metaSmall, { color: t.textSub }]}>{formatDate(report.created_at)}</Text>
          </View>
          <View style={styles.simpleRight}>
            <View style={[styles.statusPill, { backgroundColor: withAlpha(sColor, 0.1) }]}>
              <Text style={[styles.statusText, { color: sColor }]}>{sLabel}</Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color={t.textSub} />
          </View>
        </View>
      </GlassCard>
    </HapticPressable>
  );
}

// ── Two-section report card (dashboard mode) ────────────────────────────────────

function ReportCardRich({ report, onPress, t }: { report: LabReport; onPress: () => void; t: AppPalette }) {
  const sColor = STATUS_COLOR[report.status] ?? colors.stone;
  const sLabel = STATUS_LABEL[report.status] ?? report.status;
  const isPdf = report.content_type === 'application/pdf';
  const count = biomarkerCount(report);
  const flagged = flaggedForReport(report);

  let footerIcon: React.ReactNode;
  let footerText: string;
  let footerColor: string;
  if (isProcessing(report)) {
    footerIcon = <Text style={[styles.footerSymbol, { color: colors.saffron }]}>⏳</Text>;
    footerText = 'Processing… check back soon';
    footerColor = colors.saffron;
  } else if (report.status === 'ocr_failed') {
    footerIcon = <Ionicons name="alert-circle-outline" size={14} color={colors.alert} />;
    footerText = 'Processing failed · download original';
    footerColor = colors.alert;
  } else if (flagged.length > 0) {
    footerIcon = <Ionicons name="warning-outline" size={14} color={colors.saffron} />;
    footerText = flagged
      .slice(0, 3)
      .map(f => `${f.name} ${flagArrow(f.flag)} ${f.value}`)
      .join(' · ');
    footerColor = colors.saffron;
  } else if (hasDoctorCommentary(report)) {
    footerIcon = <Ionicons name="chatbubble-ellipses-outline" size={14} color={colors.forest} />;
    footerText = 'Doctor commented';
    footerColor = t.isDark ? colors.jadeGlow : colors.forest;
  } else {
    footerIcon = <Text style={[styles.footerSymbol, { color: colors.jade }]}>✓</Text>;
    footerText = 'All values in normal range';
    footerColor = colors.jade;
  }

  return (
    <HapticPressable
      scaleTo={0.98}
      onPress={onPress}
      accessibilityLabel={`View ${report.original_filename}`}
      containerStyle={styles.richCardSpacing}
    >
      <GlassCard unpadded>
        {/* Top section */}
        <View style={styles.richTop}>
          <View style={[styles.fileIcon, { backgroundColor: withAlpha(sColor, 0.1) }]}>
            <Text style={[styles.fileIconText, { color: sColor }]}>{isPdf ? 'PDF' : 'IMG'}</Text>
          </View>
          <View style={styles.richBody}>
            <Text style={[styles.filename, { color: t.text }]} numberOfLines={1}>
              {report.original_filename}
            </Text>
            <Text style={[styles.metaLine, { color: t.textSub }]} numberOfLines={1}>
              {report.lab_name ? `${report.lab_name} · ` : ''}{formatDate(report.created_at)}
            </Text>
            {count > 0 ? (
              <Text style={[styles.metaSmall, { color: t.textSub }]}>
                {count} biomarker{count === 1 ? '' : 's'}
              </Text>
            ) : null}
          </View>
          <View style={[styles.statusPill, { backgroundColor: withAlpha(sColor, 0.1) }]}>
            <Text style={[styles.statusText, { color: sColor }]}>{sLabel}</Text>
          </View>
        </View>

        {/* Dashed divider */}
        <View style={[styles.dashedDivider, { borderColor: withAlpha(t.textSub, 0.25) }]} />

        {/* Bottom section */}
        <View style={styles.richBottom}>
          <View style={styles.richFooterLeft}>
            {footerIcon}
            <Text style={[styles.footerText, { color: footerColor }]} numberOfLines={1}>
              {footerText}
            </Text>
          </View>
          <Ionicons name="chevron-forward" size={18} color={t.textSub} />
        </View>
      </GlassCard>
    </HapticPressable>
  );
}

// ── Attention flags banner ──────────────────────────────────────────────────────

function AttentionBanner({ flags, t }: { flags: FlaggedValue[]; t: AppPalette }) {
  if (flags.length === 0) return null;
  return (
    <GlassCard style={[styles.banner, { borderColor: withAlpha(colors.saffron, 0.4) }]}>
      <View style={styles.bannerHeader}>
        <Ionicons name="warning-outline" size={18} color={colors.saffron} />
        <Text style={[styles.bannerTitle, { color: t.text }]}>
          {flags.length} value{flags.length === 1 ? '' : 's'} need attention
        </Text>
      </View>
      <Text style={[styles.bannerBody, { color: t.textSub }]} numberOfLines={3}>
        {flags
          .map(f => `${f.name} ${flagArrow(f.flag)} ${f.value}${f.unit ? ` ${f.unit}` : ''}`)
          .join('  ·  ')}
      </Text>
    </GlassCard>
  );
}

// ── Key biomarkers card ─────────────────────────────────────────────────────────

function biomarkerStatus(flag: BiomarkerSummary['flag']): { symbol: string; color: string } {
  if (flag === 'high') return { symbol: '↑', color: colors.saffron };
  if (flag === 'low') return { symbol: '↓', color: colors.saffron };
  return { symbol: '✓', color: colors.jade };
}

function KeyBiomarkers({
  biomarkers,
  onPressBiomarker,
  t,
}: {
  biomarkers: BiomarkerSummary[];
  onPressBiomarker: (name: string) => void;
  t: AppPalette;
}) {
  if (biomarkers.length === 0) return null;
  const shown = biomarkers.slice(0, 6);
  return (
    <GlassCard style={styles.keyCard}>
      <Text style={[styles.sectionHeading, { color: t.text }]}>Key Biomarkers</Text>
      <View style={styles.keyList}>
        {shown.map((b, i) => {
          const status = biomarkerStatus(b.flag);
          return (
            <HapticPressable
              key={b.name}
              haptic="selection"
              scaleTo={0.98}
              onPress={() => onPressBiomarker(b.name)}
              accessibilityLabel={`View trend for ${b.name}`}
              style={[
                styles.keyRow,
                i < shown.length - 1 && { borderBottomWidth: StyleSheet.hairlineWidth, borderColor: withAlpha(t.textSub, 0.15) },
              ]}
            >
              <Text style={[styles.keyName, { color: t.text }]} numberOfLines={1}>{b.name}</Text>
              <View style={styles.keyValueWrap}>
                <Text style={[styles.keyValue, { color: t.textSub }]}>
                  {b.latest_value != null ? b.latest_value : '—'}{b.unit ? ` ${b.unit}` : ''}
                </Text>
                <Text style={[styles.keySymbol, { color: status.color }]}>{status.symbol}</Text>
                <Ionicons name="chevron-forward" size={14} color={t.textSub} />
              </View>
            </HapticPressable>
          );
        })}
      </View>
    </GlassCard>
  );
}

// ── Sub-tabs bar ─────────────────────────────────────────────────────────────────

const TABS: { key: TabKey; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'next', label: 'Next Consult' },
  { key: 'rx', label: 'Rx' },
];

function SubTabs({ active, onChange, t }: { active: TabKey; onChange: (k: TabKey) => void; t: AppPalette }) {
  return (
    <View style={styles.tabBar}>
      {TABS.map(tab => {
        const isActive = tab.key === active;
        return (
          <HapticPressable
            key={tab.key}
            haptic="selection"
            scaleTo={0.96}
            onPress={() => onChange(tab.key)}
            accessibilityLabel={`Show ${tab.label}`}
            style={styles.tabItem}
          >
            <Text
              style={[
                styles.tabLabel,
                { color: isActive ? (t.isDark ? colors.jadeGlow : colors.forest) : colors.stone },
              ]}
            >
              {tab.label}
            </Text>
            <View
              style={[
                styles.tabUnderline,
                { backgroundColor: isActive ? (t.isDark ? colors.jadeGlow : colors.forest) : 'transparent' },
              ]}
            />
          </HapticPressable>
        );
      })}
    </View>
  );
}

// ── Prescription card ───────────────────────────────────────────────────────────

function PrescriptionCard({ rx, t }: { rx: Prescription; t: AppPalette }) {
  const sColor = rx.status === 'dispensed' ? colors.jade : colors.forest;
  const sLabel = rx.status === 'dispensed' ? 'Dispensed' : 'Signed';
  const medCount = rx.items.length;
  return (
    <HapticPressable
      scaleTo={0.98}
      onPress={() => undefined}
      accessibilityLabel={`Prescription, ${medCount} medication${medCount === 1 ? '' : 's'}`}
      containerStyle={styles.richCardSpacing}
    >
      <GlassCard unpadded>
        <View style={styles.rxCard}>
          <View style={styles.rxHeader}>
            <View style={styles.rxIcon}>
              <Ionicons name="medkit-outline" size={18} color={t.isDark ? colors.jadeGlow : colors.forest} />
            </View>
            <Text style={[styles.rxDiagnosis, { color: t.text }]} numberOfLines={2}>
              {rx.diagnosis_note?.trim() || 'Prescription'}
            </Text>
            <View style={[styles.statusPill, { backgroundColor: withAlpha(sColor, 0.1) }]}>
              <Text style={[styles.statusText, { color: sColor }]}>{sLabel}</Text>
            </View>
          </View>
          <Text style={[styles.rxMeta, { color: t.textSub }]}>
            {medCount} medication{medCount === 1 ? '' : 's'}
            {rx.signed_at ? ` · ${formatDate(rx.signed_at)}` : ''}
          </Text>
        </View>
      </GlassCard>
    </HapticPressable>
  );
}

// ── Header ───────────────────────────────────────────────────────────────────────

function Header({
  total,
  viewMode,
  onToggle,
  showToggle,
  t,
  isDark,
}: {
  total: number;
  viewMode: ViewMode;
  onToggle: (m: ViewMode) => void;
  showToggle: boolean;
  t: AppPalette;
  isDark: boolean;
}) {
  const activeColor = isDark ? colors.forestInk : colors.white;
  const activeBg = isDark ? colors.jadeGlow : colors.forest;
  return (
    <View style={styles.header}>
      <View style={styles.headerText}>
        <Text style={[styles.title, { color: t.text }]}>Lab Reports</Text>
        <Text style={[styles.subtitle, { color: t.textSub }]}>
          {total > 0 ? `${total} report${total === 1 ? '' : 's'}` : 'No reports yet'}
        </Text>
      </View>
      {showToggle ? (
        <View style={[styles.toggle, { borderColor: withAlpha(t.textSub, 0.2) }, shadowStyle(isDark)]}>
          <HapticPressable
            haptic="selection"
            onPress={() => onToggle('dashboard')}
            accessibilityLabel="Dashboard view"
            style={[styles.toggleBtn, viewMode === 'dashboard' && { backgroundColor: activeBg }]}
          >
            <Ionicons
              name="grid-outline"
              size={16}
              color={viewMode === 'dashboard' ? activeColor : t.textSub}
            />
          </HapticPressable>
          <HapticPressable
            haptic="selection"
            onPress={() => onToggle('list')}
            accessibilityLabel="List view"
            style={[styles.toggleBtn, viewMode === 'list' && { backgroundColor: activeBg }]}
          >
            <Ionicons
              name="list-outline"
              size={18}
              color={viewMode === 'list' ? activeColor : t.textSub}
            />
          </HapticPressable>
        </View>
      ) : null}
    </View>
  );
}

// ── Screen ─────────────────────────────────────────────────────────────────────

export default function ReportsScreen() {
  const router = useRouter();
  const t = useTheme();
  const isDark = t.isDark;

  const [tab, setTab] = useState<TabKey>('all');
  const [viewMode, setViewMode] = useState<ViewMode>('dashboard');

  const reportsQuery = useQuery({
    queryKey: ['lab-reports'],
    queryFn: () => listLabReports(1, 50),
    staleTime: 60_000,
  });
  const biomarkersQuery = useQuery({
    queryKey: ['biomarkers'],
    queryFn: listBiomarkers,
    staleTime: 60_000,
    enabled: tab === 'all' && viewMode === 'dashboard',
  });
  const prescriptionsQuery = useQuery({
    queryKey: ['prescriptions'],
    queryFn: () => listPrescriptions(1, 50),
    staleTime: 60_000,
    enabled: tab === 'rx',
  });
  const consultationsQuery = useQuery({
    queryKey: ['consultations'],
    queryFn: () => apiFetch<ConsultationListResponse>('/v1/clinic/patient/consultations?page_size=50'),
    staleTime: 60_000,
    enabled: tab === 'next',
  });

  const reports = reportsQuery.data?.items ?? [];
  const total = reportsQuery.data?.total ?? 0;

  const allFlagged = useMemo<FlaggedValue[]>(
    () => reports.flatMap(flaggedForReport),
    [reports],
  );

  const onRefresh = () => {
    reportsQuery.refetch();
    if (tab === 'all' && viewMode === 'dashboard') biomarkersQuery.refetch();
    if (tab === 'rx') prescriptionsQuery.refetch();
    if (tab === 'next') consultationsQuery.refetch();
  };

  const refreshing =
    (reportsQuery.isFetching && !reportsQuery.isLoading)
    || (tab === 'rx' && prescriptionsQuery.isFetching && !prescriptionsQuery.isLoading)
    || (tab === 'next' && consultationsQuery.isFetching && !consultationsQuery.isLoading);

  const headerBlock = (
    <>
      <Header
        total={total}
        viewMode={viewMode}
        onToggle={setViewMode}
        showToggle={tab === 'all'}
        t={t}
        isDark={isDark}
      />
      <SubTabs active={tab} onChange={setTab} t={t} />
    </>
  );

  const refreshControl = (
    <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={t.primary} />
  );

  // ── All tab — dashboard mode (SectionList) ──────────────────────────────────
  if (tab === 'all' && viewMode === 'dashboard') {
    const sections = groupByMonth(reports);
    return (
      <View style={[styles.container, { backgroundColor: t.background }]}>
        <AmbientBackground />
        {reportsQuery.isLoading ? (
          <View style={styles.scrollPad}>
            {headerBlock}
            <SkeletonCards count={4} />
          </View>
        ) : (
          <SectionList
            sections={sections}
            keyExtractor={item => item.id}
            contentContainerStyle={styles.scrollPad}
            stickySectionHeadersEnabled={false}
            refreshControl={refreshControl}
            ListHeaderComponent={
              <>
                {headerBlock}
                <AttentionBanner flags={allFlagged} t={t} />
                {!biomarkersQuery.isLoading && (
                  <KeyBiomarkers
                    biomarkers={biomarkersQuery.data?.biomarkers ?? []}
                    onPressBiomarker={name => router.push(`/biomarkers/${encodeURIComponent(name)}`)}
                    t={t}
                  />
                )}
              </>
            }
            renderSectionHeader={({ section }) => (
              <Text style={[styles.monthHeader, { color: t.textSub }]}>{section.title}</Text>
            )}
            renderItem={({ item }) => (
              <ReportCardRich
                report={item}
                t={t}
                onPress={() => router.push(`/reports/${item.id}`)}
              />
            )}
            ListEmptyComponent={
              reportsQuery.error ? (
                <EmptyState
                  icon="cloud-offline-outline"
                  tint="amber"
                  title="Could not load lab reports. Please try again."
                  body="Pull down to refresh, or try again in a moment. Your reports are safe."
                />
              ) : (
                <EmptyState
                  icon="flask-outline"
                  tint="green"
                  title="No reports yet"
                  body="Upload a lab report and we'll extract your biomarker results automatically."
                  ctaLabel="Upload report"
                  onCtaPress={() => router.push('/reports/upload')}
                />
              )
            }
          />
        )}
        <UploadFab router={router} />
      </View>
    );
  }

  // ── All tab — list mode (FlatList) ──────────────────────────────────────────
  if (tab === 'all') {
    return (
      <View style={[styles.container, { backgroundColor: t.background }]}>
        <AmbientBackground />
        {reportsQuery.isLoading ? (
          <View style={styles.scrollPad}>
            {headerBlock}
            <SkeletonCards count={4} />
          </View>
        ) : (
          <FlatList
            data={reports}
            keyExtractor={r => r.id}
            contentContainerStyle={styles.scrollPad}
            ItemSeparatorComponent={() => <View style={{ height: spacing[3] }} />}
            refreshControl={refreshControl}
            ListHeaderComponent={headerBlock}
            renderItem={({ item }) => (
              <ReportCard report={item} t={t} onPress={() => router.push(`/reports/${item.id}`)} />
            )}
            ListEmptyComponent={
              reportsQuery.error ? (
                <EmptyState
                  icon="cloud-offline-outline"
                  tint="amber"
                  title="Could not load lab reports. Please try again."
                  body="Pull down to refresh, or try again in a moment. Your reports are safe."
                />
              ) : (
                <EmptyState
                  icon="flask-outline"
                  tint="green"
                  title="No reports yet"
                  body="Upload a lab report and we'll extract your biomarker results automatically."
                  ctaLabel="Upload report"
                  onCtaPress={() => router.push('/reports/upload')}
                />
              )
            }
          />
        )}
        <UploadFab router={router} />
      </View>
    );
  }

  // ── Next Consult tab ────────────────────────────────────────────────────────
  if (tab === 'next') {
    return (
      <View style={[styles.container, { backgroundColor: t.background }]}>
        <AmbientBackground />
        <ScrollView contentContainerStyle={styles.scrollPad} refreshControl={refreshControl}>
          {headerBlock}
          <NextConsultPane
            consultations={consultationsQuery.data?.items ?? []}
            reports={reports}
            flagged={allFlagged}
            isLoading={consultationsQuery.isLoading}
            t={t}
            onBook={() => router.push('/consultations/book')}
            onOpenConsult={id => router.push(`/consultations/${id}`)}
            onOpenReport={id => router.push(`/reports/${id}`)}
          />
        </ScrollView>
      </View>
    );
  }

  // ── Rx tab ──────────────────────────────────────────────────────────────────
  return (
    <View style={[styles.container, { backgroundColor: t.background }]}>
      <AmbientBackground />
      {prescriptionsQuery.isLoading ? (
        <View style={styles.scrollPad}>
          {headerBlock}
          <SkeletonCards count={3} />
        </View>
      ) : (
        <FlatList
          data={prescriptionsQuery.data?.items ?? []}
          keyExtractor={rx => rx.id}
          contentContainerStyle={styles.scrollPad}
          refreshControl={refreshControl}
          ListHeaderComponent={headerBlock}
          renderItem={({ item }) => <PrescriptionCard rx={item} t={t} />}
          ListEmptyComponent={
            prescriptionsQuery.error ? (
              <EmptyState
                icon="cloud-offline-outline"
                tint="amber"
                title="Could not load prescriptions. Please try again."
                body="Pull down to refresh, or try again in a moment."
              />
            ) : (
              <EmptyState
                icon="document-text-outline"
                tint="sage"
                title="No prescriptions yet"
                body="After a consultation, your doctor's signed prescriptions will appear here for you to view anytime."
              />
            )
          }
        />
      )}
    </View>
  );
}

// ── Next Consult pane ───────────────────────────────────────────────────────────

function NextConsultPane({
  consultations,
  reports,
  flagged,
  isLoading,
  t,
  onBook,
  onOpenConsult,
  onOpenReport,
}: {
  consultations: Consultation[];
  reports: LabReport[];
  flagged: FlaggedValue[];
  isLoading: boolean;
  t: AppPalette;
  onBook: () => void;
  onOpenConsult: (id: string) => void;
  onOpenReport: (id: string) => void;
}) {
  if (isLoading) return <SkeletonCards count={2} />;

  const upcoming = consultations.find(c => UPCOMING_CONSULT.includes(c.status));

  if (!upcoming) {
    return (
      <EmptyState
        icon="calendar-outline"
        tint="sage"
        title="No upcoming consultation"
        body="Book a consultation and we'll gather your latest reports and flagged values for your doctor."
        ctaLabel="Book a consultation"
        onCtaPress={onBook}
      />
    );
  }

  // Reports uploaded since the last completed consultation, else all reports.
  const lastCompleted = consultations
    .filter(c => c.status === 'completed' && c.scheduled_start_at)
    .sort((a, b) => new Date(b.scheduled_start_at!).getTime() - new Date(a.scheduled_start_at!).getTime())[0];
  const sinceTs = lastCompleted?.scheduled_start_at
    ? new Date(lastCompleted.scheduled_start_at).getTime()
    : 0;
  const relevantReports = reports
    .filter(r => new Date(r.created_at).getTime() >= sinceTs)
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  const pendingCorrections = reports.filter(r => r.status === 'patient_review_needed').length;

  return (
    <View style={styles.pane}>
      {/* Upcoming consultation summary */}
      <GlassCard style={styles.consultSummary}>
        <View style={styles.consultHeaderRow}>
          <Ionicons name="calendar-outline" size={18} color={t.isDark ? colors.jadeGlow : colors.forest} />
          <Text style={[styles.consultTitle, { color: t.text }]} numberOfLines={1}>
            {formatCat(upcoming.condition_category)}
          </Text>
        </View>
        <Text style={[styles.consultMeta, { color: t.textSub }]}>
          {upcoming.consultation_type === 'initial' ? 'Initial consultation' : 'Follow-up'}
        </Text>
        <Text style={[styles.consultWhen, { color: t.primary }]}>
          {upcoming.scheduled_start_at
            ? `${formatDate(upcoming.scheduled_start_at)} · ${formatTime(upcoming.scheduled_start_at)}`
            : 'Awaiting assignment'}
        </Text>
        <Button
          label="View consultation"
          variant="forest"
          onPress={() => onOpenConsult(upcoming.id)}
          accessibilityLabel="View consultation details"
          style={styles.consultBtn}
        />
      </GlassCard>

      {pendingCorrections > 0 ? (
        <GlassCard style={[styles.banner, { borderColor: withAlpha(colors.saffron, 0.4) }]}>
          <View style={styles.bannerHeader}>
            <Ionicons name="alert-circle-outline" size={18} color={colors.saffron} />
            <Text style={[styles.bannerTitle, { color: t.text }]}>
              {pendingCorrections} report{pendingCorrections === 1 ? '' : 's'} need your review
            </Text>
          </View>
          <Text style={[styles.bannerBody, { color: t.textSub }]}>
            Confirm the extracted values so your doctor sees accurate data.
          </Text>
        </GlassCard>
      ) : null}

      {flagged.length > 0 ? (
        <GlassCard style={styles.keyCard}>
          <Text style={[styles.sectionHeading, { color: t.text }]}>Flagged values for your doctor</Text>
          <Text style={[styles.bannerBody, { color: t.textSub }]} numberOfLines={4}>
            {flagged
              .map(f => `${f.name} ${flagArrow(f.flag)} ${f.value}${f.unit ? ` ${f.unit}` : ''}`)
              .join('  ·  ')}
          </Text>
        </GlassCard>
      ) : null}

      <Text style={[styles.sectionHeading, styles.paneSectionHeading, { color: t.text }]}>
        {sinceTs > 0 ? 'New reports since last visit' : 'Your reports'}
      </Text>
      {relevantReports.length > 0 ? (
        relevantReports.map(r => (
          <ReportCardRich key={r.id} report={r} t={t} onPress={() => onOpenReport(r.id)} />
        ))
      ) : (
        <Text style={[styles.emptyHint, { color: t.textSub }]}>
          No new reports yet. Upload one so your doctor has the latest before your visit.
        </Text>
      )}
    </View>
  );
}

// ── Upload FAB ───────────────────────────────────────────────────────────────────

function UploadFab({ router }: { router: ReturnType<typeof useRouter> }) {
  return (
    <View style={styles.fab}>
      <Button
        label="Upload report"
        variant="forest"
        onPress={() => router.push('/reports/upload')}
        accessibilityLabel="Upload lab report"
      />
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1 },
  scrollPad: {
    paddingHorizontal: spacing[4],
    paddingTop: spacing[2],
    paddingBottom: TAB_DOCK_CLEARANCE + 72,
  },

  // Header
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    paddingVertical: spacing[4],
  },
  headerText: { flex: 1, gap: spacing[1] },
  title: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h2,
    fontWeight: '600',
  },
  subtitle: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },

  // View toggle
  toggle: {
    flexDirection: 'row',
    borderRadius: borderRadius.full,
    borderWidth: 1,
    padding: 2,
    gap: 2,
  },
  toggleBtn: {
    width: 36,
    height: 32,
    borderRadius: borderRadius.full,
    alignItems: 'center',
    justifyContent: 'center',
  },

  // Sub-tabs
  tabBar: {
    flexDirection: 'row',
    gap: spacing[5],
    marginBottom: spacing[4],
  },
  tabItem: { alignItems: 'center', gap: spacing[2] },
  tabLabel: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  tabUnderline: {
    height: 2,
    width: '100%',
    borderRadius: 1,
  },

  // File icon + status (shared)
  fileIcon: {
    width: 48,
    height: 48,
    borderRadius: borderRadius.xl,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  fileIconText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  filename: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  metaLine: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },
  metaSmall: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
  },
  statusPill: {
    paddingHorizontal: spacing[2],
    paddingVertical: 3,
    borderRadius: borderRadius.full,
    alignSelf: 'flex-start',
  },
  statusText: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.caption,
    fontWeight: '700',
  },

  // Simple (list-mode) card
  simpleCard: {
    padding: spacing[4],
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
  },
  simpleBody: { flex: 1, gap: 3 },
  simpleRight: { alignItems: 'flex-end', gap: spacing[2] },

  // Rich (dashboard-mode) card
  richCardSpacing: { marginBottom: spacing[3] },
  richTop: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[3],
    padding: spacing[4],
    paddingBottom: spacing[3],
  },
  richBody: { flex: 1, gap: 3 },
  dashedDivider: {
    borderTopWidth: 1,
    borderStyle: 'dashed',
    marginHorizontal: spacing[4],
  },
  richBottom: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing[2],
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
  },
  richFooterLeft: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2],
  },
  footerText: {
    flex: 1,
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '600',
  },
  footerSymbol: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    fontWeight: '700',
  },

  // Month header
  monthHeader: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.xs,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginTop: spacing[4],
    marginBottom: spacing[3],
  },

  // Attention banner
  banner: { marginBottom: spacing[4], gap: spacing[2] },
  bannerHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  bannerTitle: {
    flex: 1,
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '700',
  },
  bannerBody: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    lineHeight: 19,
  },

  // Key biomarkers
  keyCard: { marginBottom: spacing[4] },
  sectionHeading: {
    fontFamily: fontFamily.display,
    fontSize: fontSize.h3,
    fontWeight: '600',
    marginBottom: spacing[2],
  },
  keyList: { gap: 0 },
  keyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing[3],
    paddingVertical: spacing[3],
  },
  keyName: {
    flex: 1,
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '500',
  },
  keyValueWrap: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  keyValue: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },
  keySymbol: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '700',
  },

  // Rx card
  rxCard: { padding: spacing[4], gap: spacing[2] },
  rxHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing[3] },
  rxIcon: {
    width: 40,
    height: 40,
    borderRadius: borderRadius.xl,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    backgroundColor: withAlpha(colors.forest, 0.1),
  },
  rxDiagnosis: {
    flex: 1,
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '600',
  },
  rxMeta: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },

  // Next consult pane
  pane: { gap: 0 },
  consultSummary: { marginBottom: spacing[4], gap: spacing[1] },
  consultHeaderRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  consultTitle: {
    flex: 1,
    fontFamily: fontFamily.body,
    fontSize: fontSize.bodyLg,
    fontWeight: '700',
  },
  consultMeta: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
  },
  consultWhen: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.body,
    fontWeight: '700',
    marginTop: spacing[1],
  },
  consultBtn: { marginTop: spacing[3] },
  paneSectionHeading: { marginTop: spacing[2] },
  emptyHint: {
    fontFamily: fontFamily.body,
    fontSize: fontSize.sm,
    lineHeight: 19,
  },

  // FAB
  fab: {
    position: 'absolute',
    bottom: TAB_DOCK_CLEARANCE - spacing[6],
    left: spacing[6],
    right: spacing[6],
  },
});
