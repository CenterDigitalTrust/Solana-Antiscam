'use client';
import { useTokens } from '@/hooks/useTokens';
import { useTranslations } from 'next-intl';
import { useDailyStats } from '@/hooks/useDailyStats';

export default function QuarantineGrid() {
  const t = useTranslations('Quarantine');
  const allTokens = useTokens();
  const tokens = allTokens.filter(t => t.status === 'QUARANTINE' || t.status === 'REJECT');
  const stats = useDailyStats();

  const pnlColor = Number(stats?.daily_pnl_usd || 0) >= 0 ? "text-olive" : "text-red-500";
  const pnlSign = Number(stats?.daily_pnl_usd || 0) > 0 ? "+" : "";

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return `${d.toLocaleString('en-US', { month: 'short' }).toUpperCase()} ${d.getDate()}, ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')} UTC`;
  };

  const rotations = ['-rotate-[1.4deg]', 'rotate-[1deg]', '-rotate-[0.6deg]'];

  return (
    <section id="quarantine" className="w-full max-w-6xl mx-auto px-4 md:px-8 py-16 border-t border-rule">
      
      <div className="flex flex-col md:flex-row justify-between items-start mb-12">
        <div className="mb-6 md:mb-0 max-w-md">
          <div className="font-mono text-xs text-ink-faint tracking-widest uppercase mb-4">
            04 — QUARANTINE ZONE
          </div>
          <h2 className="font-serif text-4xl text-ink leading-tight">
            {t('title')}
          </h2>
        </div>
        <div className="max-w-xs font-sans text-sm text-ink-soft leading-relaxed">
          {t('subtitle')}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 pb-8">
        {tokens.slice(0, 3).map((token, idx) => (
          <div 
            key={token.token_address} 
            className={`bg-paper border border-ink p-6 flex flex-col relative h-[220px] shadow-none ${rotations[idx % 3]} transform origin-center`}
          >
            <div className="flex justify-between items-start mb-8">
              <div className="font-mono text-lg font-bold">${token.ticker}</div>
              <div className="font-mono text-[9px] uppercase text-ink-faint">
                {formatDate(token.discovered_at)}
              </div>
            </div>
            
            {/* REJECTED STAMP */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 -rotate-6 border-2 border-rust px-4 py-1 pointer-events-none opacity-90">
              <div className="font-mono text-xl text-rust tracking-widest uppercase font-bold">
                REJECTED
              </div>
            </div>

            <div className="mt-auto font-sans text-xs text-ink-soft leading-relaxed bg-paper relative z-10 pt-2 border-t border-rule/30">
              {token.status_reason || 'Unknown reason'}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 border border-rule bg-paper p-8 flex flex-col lg:flex-row justify-between items-start lg:items-center gap-8 shadow-none">
        <div className="max-w-xl">
          <div className="font-mono text-[10px] text-ink-faint tracking-widest uppercase mb-2 flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-olive opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-olive"></span>
            </span>
            DAEMON LIVE OUTPUT — PORTFOLIO SIMULATION
          </div>
          <div className="font-serif text-2xl text-ink leading-tight mb-4">Autonomous Target: +160% Take-Profit</div>
          <div className="font-sans text-sm text-ink-soft leading-relaxed">
            The system is actively scanning and trading in paper mode. With a starting <strong className="text-ink">deposit of $100</strong>, it allocates exactly <strong className="text-ink">$2 per token</strong> to every asset that clears all security and momentum filters. It targets a strict <strong className="text-olive">+160% take-profit</strong>, automatically closing positions upon reaching the target or hitting the dynamic -25% trailing stop-loss.
          </div>
        </div>
        <div className="flex flex-wrap gap-8 font-mono border-l-0 lg:border-l border-rule lg:pl-8">
          <div className="flex flex-col">
            <span className="text-[9px] text-ink-faint uppercase mb-1 tracking-widest">LIVE DEPOSIT</span>
            <span className="text-xl text-ink font-bold">$100.00</span>
          </div>
          <div className="flex flex-col">
            <span className="text-[9px] text-ink-faint uppercase mb-1 tracking-widest">BET SIZE</span>
            <span className="text-xl text-ink">$2.00</span>
          </div>
          <div className="flex flex-col">
            <span className="text-[9px] text-ink-faint uppercase mb-1 tracking-widest">EST. DAILY PnL</span>
            <span className={`text-xl font-bold ${pnlColor}`}>{pnlSign}{Number(stats?.daily_pnl_usd || 0).toFixed(2)}</span>
          </div>
        </div>
      </div>

    </section>
  );
}
