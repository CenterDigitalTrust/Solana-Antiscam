'use client';
import { TokenData } from '@/hooks/useTokens';
import { useTranslations } from 'next-intl';

export default function LiveFeed({ tokens }: { tokens: TokenData[] }) {
  const t = useTranslations('LiveFeed');

  const getStatusColor = (status: string) => {
    switch(status) {
      case 'QUARANTINE': return 'text-rust bg-rust/10 border-rust';
      case 'SUCCESS': return 'text-olive bg-olive/10 border-olive';
      case 'MONITORING': return 'text-ochre bg-ochre/10 border-ochre';
      case 'REJECT': return 'text-rust bg-rust/10 border-rust';
      default: return 'text-ink-soft bg-ink/5 border-rule';
    }
  };

  const displayTokens = tokens.slice(0, 15);

  return (
    <div className="w-full bg-paper border border-rule mt-8">
      <div className="p-4 border-b border-rule flex justify-between items-center bg-beige/50">
        <h3 className="font-serif text-xl font-medium text-ink">{t('title')}</h3>
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-olive opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-olive"></span>
          </span>
          <span className="font-mono text-xs uppercase tracking-wider text-ink-soft">{t('online')}</span>
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-beige/30 font-mono text-xs uppercase tracking-wider text-ink-soft">
              <th className="p-4 border-b border-rule font-medium">{t('col_time')}</th>
              <th className="p-4 border-b border-rule font-medium">{t('col_token')}</th>
              <th className="p-4 border-b border-rule font-medium">{t('col_score')}</th>
              <th className="p-4 border-b border-rule font-medium">{t('col_status')}</th>
              <th className="p-4 border-b border-rule font-medium">{t('col_reason')}</th>
            </tr>
          </thead>
          <tbody className="font-sans text-sm text-ink font-medium">
            {displayTokens.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-ink-faint italic font-serif">
                  {t('waiting')}
                </td>
              </tr>
            ) : (
              displayTokens.map((token) => (
                <tr key={token.token_address} className="hover:bg-beige/20 transition-colors">
                  <td className="p-4 border-b border-rule font-mono text-xs text-ink-faint">
                    {new Date(token.updated_at).toLocaleTimeString()}
                  </td>
                  <td className="p-4 border-b border-rule">
                    <div className="font-mono bg-ink/5 px-2 py-1 rounded inline-block">
                      ${token.ticker}
                    </div>
                  </td>
                  <td className="p-4 border-b border-rule font-mono text-lg">
                    {token.score}
                  </td>
                  <td className="p-4 border-b border-rule">
                    <span className={`font-mono text-xs px-2 py-1 border rounded uppercase ${getStatusColor(token.status)}`}>
                      {token.status}
                    </span>
                  </td>
                  <td className="p-4 border-b border-rule text-ink-soft max-w-[200px] truncate">
                    {token.status_reason || "-"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
