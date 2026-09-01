'use client';
import { useTokens } from '@/hooks/useTokens';
import { useTranslations } from 'next-intl';

export default function MonitoringTable() {
  const t = useTranslations('Monitoring');
  const tokens = useTokens();

  const formatAge = (discoveredAt: string) => {
    const diff = Math.floor((Date.now() - new Date(discoveredAt).getTime()) / 1000);
    if (diff < 60) return `${diff} sec ago`;
    return `${Math.floor(diff / 60)} min ago`;
  };

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'QUARANTINE':
      case 'REJECT': return 'text-rust border-rust';
      case 'SUCCESS': return 'text-olive border-olive';
      case 'MONITORING': return 'text-ink-soft border-ink-soft/30';
      default: return 'text-ochre border-ochre';
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'QUARANTINE':
      case 'REJECT': return 'Quarantined';
      case 'SUCCESS': return 'Growth leader';
      case 'MONITORING': return 'Monitoring';
      default: return 'Watch';
    }
  };

  return (
    <section id="live-feed" className="w-full max-w-6xl mx-auto px-4 md:px-8 py-16 border-t border-rule">
      
      <div className="flex flex-col md:flex-row justify-between items-start mb-12">
        <div className="mb-6 md:mb-0 max-w-md">
          <div className="font-mono text-xs text-ink-faint tracking-widest uppercase mb-4">
            02 — MONITORING FEED
          </div>
          <h2 className="font-serif text-4xl text-ink leading-tight">
            {t('title')}
          </h2>
        </div>
        <div className="max-w-xs font-sans text-sm text-ink-soft leading-relaxed">
          {t('subtitle')}
        </div>
      </div>

      <div className="w-full overflow-x-auto bg-paper border border-rule">
        <table className="w-full text-left border-collapse min-w-[700px]">
          <thead>
            <tr className="border-b border-rule font-mono text-[10px] uppercase text-ink-faint">
              <th className="p-4 font-normal">Token</th>
              <th className="p-4 font-normal">Discovered</th>
              <th className="p-4 font-normal">Score</th>
              <th className="p-4 font-normal">Price USD</th>
              <th className="p-4 font-normal hidden md:table-cell">Status</th>
            </tr>
          </thead>
          <tbody className="font-mono text-sm">
            {tokens.map((token, idx) => (
              <tr key={token.token_address} className="border-b border-rule/50 hover:bg-beige-0/50 transition-colors">
                <td className="p-4 font-bold text-ink">
                  ${token.ticker}
                  {idx === 0 && (
                    <span className="ml-2 bg-rust text-paper text-[9px] px-1 py-0.5 rounded-none font-sans uppercase">
                      New
                    </span>
                  )}
                </td>
                <td className="p-4 text-ink-soft">{formatAge(token.discovered_at)}</td>
                <td className="p-4 font-bold">{token.score}</td>
                <td className="p-4 font-bold">
                  <span className={token.price_usd > 0 ? 'text-olive' : 'text-ink-soft'}>
                    ${token.price_usd?.toFixed(6) || 0}
                  </span>
                </td>
                <td className="p-4 hidden md:table-cell">
                  <span className={`text-[10px] px-2 py-1 border ${getStatusStyle(token.status)}`}>
                    {getStatusLabel(token.status)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

    </section>
  );
}
