'use client';
import { useTranslations } from 'next-intl';

export default function MethodologyGrid() {
  const t = useTranslations('Methodology');

  const cards = [
    { weight: '25%', code: 'SECURITY', key: 'security' },
    { weight: '20%', code: 'LIQUIDITY', key: 'liquidity' },
    { weight: '20%', code: 'MOMENTUM', key: 'momentum' },
    { weight: '15%', code: 'MARKET', key: 'market' },
    { weight: '15%', code: 'WALLET', key: 'wallet' },
    { weight: '5%', code: 'DATA QUALITY', key: 'data' },
  ];

  return (
    <section id="methodology" className="w-full max-w-6xl mx-auto px-4 md:px-8 py-16 border-t border-rule">
      
      <div className="flex flex-col md:flex-row justify-between items-start mb-12">
        <div className="mb-6 md:mb-0 max-w-md">
          <div className="font-mono text-xs text-ink-faint tracking-widest uppercase mb-4">
            01 — METHODOLOGY
          </div>
          <h2 className="font-serif text-4xl text-ink leading-tight">
            {t('title')}
          </h2>
        </div>
        <div className="max-w-xs font-sans text-sm text-ink-soft leading-relaxed">
          {t('subtitle')}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 border-l border-t border-rule bg-paper">
        {cards.map((card) => (
          <div key={card.key} className="border-r border-b border-rule p-6 flex flex-col relative h-[250px]">
            <div className="flex justify-between items-start mb-4">
              <span className="font-serif text-3xl text-ink">{card.weight}</span>
              <span className="font-mono text-[10px] uppercase border border-rule px-2 py-1 text-ink-faint">
                {card.code}
              </span>
            </div>
            <h3 className="font-sans font-semibold text-ink text-base mb-2">
              {t(`${card.key}.title`)}
            </h3>
            <p className="font-sans text-xs text-ink-soft leading-relaxed flex-grow">
              {t(`${card.key}.desc`)}
            </p>
            {/* Weight indicator bar */}
            <div className="absolute bottom-0 left-0 h-1 bg-rule/30 w-full">
              <div 
                className="h-full bg-ink" 
                style={{ width: card.weight }}
              ></div>
            </div>
          </div>
        ))}
      </div>

    </section>
  );
}
