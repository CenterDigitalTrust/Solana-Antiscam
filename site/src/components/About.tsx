'use client';
import { useTranslations } from 'next-intl';

export default function About() {
  const t = useTranslations('About');

  const principles = [
    t('p_1'),
    t('p_2'),
    t('p_3'),
    t('p_4')
  ];

  return (
    <section id="about" className="w-full max-w-6xl mx-auto px-4 md:px-8 py-16 border-t border-rule">
      
      <div className="font-mono text-xs text-ink-faint tracking-widest uppercase mb-12">
        05 — ABOUT
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-16">
        
        {/* Left Column */}
        <div className="flex flex-col">
          <h2 className="font-serif text-3xl md:text-4xl text-ink leading-tight mb-8">
            &quot;Safety isn&apos;t a feature of this product. It&apos;s the only reason it exists.&quot;
          </h2>
          
          <div className="font-sans text-sm text-ink-soft leading-relaxed space-y-4">
            <p>{t.rich('desc_1', { strong: (chunks) => <strong>{chunks}</strong> })}</p>
            <p>{t('desc_2')}</p>
          </div>
        </div>

        {/* Right Column */}
        <div className="flex flex-col">
          <div className="font-mono text-[10px] text-ink-faint uppercase tracking-widest mb-4">
            PRINCIPLES
          </div>
          <div className="flex flex-col border-t border-rule">
            {principles.map((principle, idx) => (
              <div key={idx} className="flex justify-between items-center py-4 border-b border-rule">
                <span className="font-sans text-sm text-ink">{principle}</span>
                <span className="font-mono text-[10px] text-ink-faint">0{idx + 1}</span>
              </div>
            ))}
          </div>

          <div className="mt-12 bg-paper border border-rule p-6 flex flex-col gap-4">
            <div>
              <div className="font-mono text-[9px] text-ink-faint uppercase tracking-widest mb-1">ORGANIZATION</div>
              <div className="font-sans text-sm text-ink">{t('org_name')}</div>
            </div>
            <div>
              <div className="font-mono text-[9px] text-ink-faint uppercase tracking-widest mb-1">NETWORK</div>
              <div className="font-sans text-sm text-ink">{t('org_network')}</div>
            </div>
            <div>
              <div className="font-mono text-[9px] text-ink-faint uppercase tracking-widest mb-1">STATUS</div>
              <div className="font-sans text-sm text-ink">{t('org_status')}</div>
            </div>
          </div>
        </div>

      </div>

    </section>
  );
}
