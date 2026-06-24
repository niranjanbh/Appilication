import type { Metadata } from 'next';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { PullQuote } from '../../components/ui/PullQuote';
import { Stat } from '../../components/ui/Stat';
import { Tag } from '../../components/ui/Tag';

export const metadata: Metadata = {
  title: 'Design System',
  robots: { index: false, follow: false },
};

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-16">
      <h2 className="font-body text-caption font-semibold text-stone uppercase tracking-widest mb-6 pb-2 border-b border-sage/30">
        {title}
      </h2>
      <div className="flex flex-wrap gap-4 items-start">{children}</div>
    </section>
  );
}

export default function DesignSystemPage() {
  return (
    <div className="min-h-screen bg-ivory">
      <header className="bg-forest text-ivory px-8 py-8">
        <h1 className="font-display text-h2 font-medium">Kyros Design System</h1>
        <p className="font-body text-body text-ivory/70 mt-1">Website — Primitive Showcase</p>
      </header>

      <main className="max-w-4xl mx-auto px-8 py-12">

        {/* Buttons */}
        <Section title="Button">
          <Button variant="forest">Book consultation</Button>
          <Button variant="saffron">Take the assessment</Button>
          <Button variant="outline">How it works</Button>
          <Button variant="ghost">Learn more</Button>
          <Button variant="forest" disabled>Disabled</Button>
        </Section>

        {/* Cards */}
        <Section title="Card">
          <Card variant="white" className="w-72">
            <p className="font-body text-caption text-stone mb-2">White on Ivory</p>
            <p className="font-body text-body text-ink">
              Clinical card background. Used for lab rows, prescription detail, consultation cards.
            </p>
          </Card>
          <div className="bg-peach-mist rounded-card p-3">
            <Card variant="ivory" className="w-72">
              <p className="font-body text-caption text-stone mb-2">Ivory on Peach Mist</p>
              <p className="font-body text-body text-ink">
                Warm section card. Used for welcome strips and condition pillar highlights.
              </p>
            </Card>
          </div>
        </Section>

        {/* Pull Quotes */}
        <Section title="PullQuote">
          <div className="w-full max-w-lg">
            <PullQuote accent="terracotta">
              "She thought she was just tired. For three years."
            </PullQuote>
          </div>
          <div className="w-full max-w-lg">
            <PullQuote accent="saffron">
              "The first honest conversation about your weight should be with someone who measures, not someone who sells."
            </PullQuote>
          </div>
        </Section>

        {/* Stats */}
        <Section title="Stat">
          <div className="bg-white rounded-card p-8">
            <Stat numeral="94%" caption="reduction in symptoms" color="forest" />
          </div>
          <div className="bg-white rounded-card p-8">
            <Stat numeral="2,400+" caption="consultations completed" color="saffron" />
          </div>
          <div className="bg-white rounded-card p-8">
            <Stat numeral="7" caption="hormonal conditions treated" color="forest" />
          </div>
        </Section>

        {/* Tags */}
        <Section title="Tag">
          <Tag variant="sage">In range</Tag>
          <Tag variant="saffron">Slightly off</Tag>
          <Tag variant="terracotta">Out of range</Tag>
          <Tag variant="forest">Thyroid</Tag>
        </Section>

        {/* Typography */}
        <Section title="Typography">
          <div className="w-full space-y-5">
            <p className="font-display text-h1 text-forest font-medium">
              H1 — Cormorant Garamond 42px Forest
            </p>
            <p className="font-display text-h2 text-forest font-medium">
              H2 — Cormorant Garamond 28px Forest
            </p>
            <p className="font-display text-h3 text-forest font-medium">
              H3 — Cormorant Garamond 22px Forest
            </p>
            <p className="font-display italic text-h3 text-forest">
              Pull-quote — Cormorant Garamond italic 22px Forest
            </p>
            <p className="font-body text-body text-ink">
              Body — DM Sans 14px Ink. Line height 1.6 for comfortable reading across condition pages and educational content.
            </p>
            <p className="font-body text-body-lg text-ink">
              Body Lg — DM Sans 15px Ink.
            </p>
            <p className="font-body text-caption text-stone">
              Caption — DM Sans 12px Stone. Timestamps, metadata, reference ranges.
            </p>
            <p className="font-hindi text-h3 text-forest">
              हिन्दी शीर्षक — Tiro Devanagari Hindi
            </p>
          </div>
        </Section>

        {/* Color Palette */}
        <Section title="Color Palette (11 tokens)">
          {(
            [
              ['bg-forest', 'Forest', 'text-ivory'],
              ['bg-jade', 'Jade', 'text-ivory'],
              ['bg-sage', 'Sage', 'text-forest'],
              ['bg-saffron', 'Saffron', 'text-forest'],
              ['bg-terracotta', 'Terracotta', 'text-ivory'],
              ['bg-ivory border border-stone/20', 'Ivory', 'text-ink'],
              ['bg-peach-mist', 'Peach Mist', 'text-ink'],
              ['bg-white border border-stone/20', 'White', 'text-ink'],
              ['bg-ink', 'Ink', 'text-ivory'],
              ['bg-stone', 'Stone', 'text-ivory'],
              ['bg-alert', 'Alert', 'text-ivory'],
            ] as [string, string, string][]
          ).map(([bgClass, label, textClass]) => (
            <div key={label} className={`w-24 h-24 rounded-card flex items-center justify-center ${bgClass}`}>
              <span className={`font-body text-caption font-medium ${textClass}`}>{label}</span>
            </div>
          ))}
        </Section>

      </main>
    </div>
  );
}
