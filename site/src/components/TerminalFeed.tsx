'use client';
import { useTokens } from '@/hooks/useTokens';

export default function TerminalFeed() {
  const tokens = useTokens();

  const formatAge = (discoveredAt: string) => {
    const diff = Math.floor((Date.now() - new Date(discoveredAt).getTime()) / 1000);
    if (diff < 60) return `${diff}s ago`;
    return `${Math.floor(diff / 60)}m ${diff % 60}s ago`;
  };

  const formatStatus = (token: any) => {
    if (token.status === 'QUARANTINE' || token.status === 'REJECT') return <span className="text-rust">QUARANTINED — {token.status_reason}</span>;
    if (token.status === 'SUCCESS') return <span className="text-olive">GROWTH LEADER</span>;
    return <span className="text-ink-soft">MONITORING</span>;
  };

  const formatPrice = (val: number) => {
    // We don't have price_change_pct in the python bot right now, using price_usd as mock indicator
    const prefix = val > 0 ? '+' : '';
    const color = val > 0 ? 'text-olive' : 'text-ink-soft';
    return <span className={color}>{prefix}${val.toFixed(6)}</span>;
  };

  return (
    <section className="w-full max-w-6xl mx-auto px-4 md:px-8 -mt-6 relative z-20">
      <div className="bg-ink text-paper w-full shadow-none font-mono text-[10px] md:text-xs">
        {/* Terminal Header */}
        <div className="flex justify-between items-center px-4 py-2 border-b border-ink-soft">
          <div className="text-ink-faint">DAEMON — LIVE OUTPUT · discovery.py</div>
          <div className="flex gap-1">
            <div className="w-2 h-2 rounded-full bg-ink-soft"></div>
            <div className="w-2 h-2 rounded-full bg-ink-soft"></div>
            <div className="w-2 h-2 rounded-full bg-ink-soft"></div>
          </div>
        </div>
        {/* Terminal Body */}
        <div className="p-4 overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[600px]">
            <thead>
              <tr className="text-ink-faint border-b border-ink-soft/30">
                <th className="pb-2 font-normal">TOKEN</th>
                <th className="pb-2 font-normal">DISCOVERED</th>
                <th className="pb-2 font-normal">SCORE</th>
                <th className="pb-2 font-normal">Δ PRICE</th>
                <th className="pb-2 font-normal">STATUS</th>
                <th className="pb-2 font-normal">TIME</th>
                <th className="pb-2 font-normal">DATE</th>
              </tr>
            </thead>
            <tbody>
              {tokens.map((token: any) => {
                const dateObj = new Date(token.discovered_at);
                return (
                <tr key={token.token_address} className="border-b border-ink-soft/10">
                  <td className="py-2">${token.ticker}</td>
                  <td className="py-2 text-ink-faint">{formatAge(token.discovered_at)}</td>
                  <td className="py-2">{token.score}</td>
                  <td className="py-2">{formatPrice(token.price_usd)}</td>
                  <td className="py-2 uppercase">{formatStatus(token)}</td>
                  <td className="py-2 text-ink-faint">{dateObj.toLocaleTimeString('ru-RU')}</td>
                  <td className="py-2 text-ink-faint">{dateObj.toLocaleDateString('ru-RU')}</td>
                </tr>
              )})}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
