'use client';
import { useTokens } from '@/hooks/useTokens';
import { useTranslations } from 'next-intl';

export default function GrowthTable() {
  const t = useTranslations('Growth');
  const allTokens = useTokens();
  const passedStates = ['MONITORING', 'READY_TO_ENTER', 'OPEN', 'CLOSED', 'WATCH'];
  const tokens = allTokens.filter(t => passedStates.includes(t.status));

  const tokensWithGrowth = tokens.map(token => {
    const initPrice = Number(token.initial_price_usd || token.price_usd || 0);
    const currPrice = Number(token.price_usd || 0);
    const diff = currPrice - initPrice;
    const growthPct = initPrice > 0 ? (diff / initPrice) * 100 : 0;
    return { ...token, growthPct, currPrice };
  });

  const todayStr = new Date().toDateString();
  const getDailyScore = (address: string) => {
    let hash = 0;
    const str = address + todayStr;
    for (let i = 0; i < str.length; i++) {
      hash = (hash << 5) - hash + str.charCodeAt(i);
      hash |= 0;
    }
    return hash;
  };

  // Sort by stable daily hash so the 3 leaders stay the same all day
  const topLeaders = [...tokensWithGrowth]
    .sort((a, b) => getDailyScore(b.token_address) - getDailyScore(a.token_address))
    .slice(0, 3);

  const formatAge = (discoveredAt: string) => {
    const diff = Math.floor((Date.now() - new Date(discoveredAt).getTime()) / 1000);
    if (diff < 60) return `${diff} sec ago`;
    return `${Math.floor(diff / 60)} min ago`;
  };

  return (
    <section id="growth" className="w-full max-w-6xl mx-auto px-4 md:px-8 py-16 border-t border-rule bg-[#F5F0E6]">
      
      <div className="flex flex-col xl:flex-row justify-between items-start mb-12 gap-8">
        <div className="mb-6 xl:mb-0 max-w-md shrink-0">
          <div className="font-mono text-xs text-ink-faint tracking-widest uppercase mb-4">
            03 — СУТОЧНЫЕ ЛИДЕРЫ
          </div>
          <h2 className="font-serif text-4xl text-ink leading-tight">
            {t('title')}
          </h2>
          <div className="mt-4 font-sans text-sm text-ink-soft leading-relaxed">
            {t('subtitle')}
          </div>
        </div>

        {/* Top 4 Leaders Cards */}
        <div className="flex flex-wrap md:flex-nowrap gap-4 w-full xl:w-auto xl:justify-end">
          {topLeaders.map(leader => (
            <div key={leader.token_address} className="w-[48%] md:w-auto md:min-w-[140px] flex-shrink-0 bg-paper border border-olive p-4 flex flex-col justify-between shadow-sm">
              <div className="font-mono font-bold text-lg text-ink mb-2">${leader.ticker}</div>
              <div className="font-mono text-xl md:text-2xl text-olive font-bold mb-2">
                +{leader.growthPct.toFixed(1)}%
              </div>
              <div className="font-mono text-[10px] text-ink-faint uppercase">
                {formatAge(leader.discovered_at)}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="w-full overflow-x-auto border border-rule" style={{ backgroundColor: '#F1F0E3' }}>
        <table className="w-full text-left border-collapse min-w-[700px]">
          <thead>
            <tr className="border-b border-rule font-mono text-[10px] uppercase text-ink-faint">
              <th className="p-4 font-normal">TOKEN</th>
              <th className="p-4 font-normal">DISCOVERED</th>
              <th className="p-4 font-normal">SCORE</th>
              <th className="p-4 font-normal">PRICE USD</th>
              <th className="p-4 font-normal">STATUS</th>
            </tr>
          </thead>
          <tbody className="font-mono text-sm">
            {tokens.map((token) => {
              const currPrice = Number(token.price_usd || 0);

              return (
                <tr key={token.token_address} className="border-b border-rule/50">
                  <td className="p-4 font-bold text-ink">${token.ticker}</td>
                  <td className="p-4 text-ink-soft">{formatAge(token.discovered_at)}</td>
                  <td className="p-4 text-ink">{token.score || 0}</td>
                  <td className="p-4 font-bold text-ink">${currPrice.toFixed(6)}</td>
                  <td className="p-4">
                    <span className="text-[10px] uppercase px-2 py-1 border text-olive border-olive">
                      {token.status}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

    </section>
  );
}
