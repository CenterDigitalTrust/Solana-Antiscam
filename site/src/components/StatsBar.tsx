'use client';
import { useTranslations } from 'next-intl';
import { useDailyStats } from '@/hooks/useDailyStats';

export default function StatsBar() {
  const t = useTranslations('Stats');
  const stats = useDailyStats();

  return (
    <section className="w-full max-w-6xl mx-auto px-4 md:px-8 py-16">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-0">
        
        <div className="flex flex-col py-4 md:pr-8 border-b md:border-b-0 md:border-r border-rule">
          <div className="font-mono text-5xl font-bold text-ink tracking-tight mb-2">
            {stats ? Number(stats.scanned_today).toLocaleString() : '—'}
          </div>
          <div className="font-sans text-sm text-ink-soft">{t('scanned')}</div>
        </div>

        <div className="flex flex-col py-4 md:px-8 border-b md:border-b-0 md:border-r border-rule">
          <div className="font-mono text-5xl font-bold text-ink tracking-tight mb-2">
            {stats ? Number(stats.rejected_today).toLocaleString() : '—'}
          </div>
          <div className="font-sans text-sm text-ink-soft">{t('rejected')}</div>
        </div>

        <div className="flex flex-col py-4 md:pl-8">
          <div className="font-mono text-5xl font-bold text-ink tracking-tight mb-2">
            {stats ? Number(stats.passed_today).toLocaleString() : '—'}
          </div>
          <div className="font-sans text-sm text-ink-soft">{t('passed')}</div>
        </div>

      </div>
      
      <div className="mt-8 font-mono text-[10px] uppercase tracking-widest text-ink-faint">
        {t('footer_note')}
      </div>
    </section>
  );
}
