'use client';
import { useTranslations } from 'next-intl';
import { useState } from 'react';
import { supabase } from '@/lib/supabase';

export default function Hero() {
  const t = useTranslations('Hero');
  const [searchValue, setSearchValue] = useState('');
  const [searchResult, setSearchResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleCheckToken = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchValue.trim()) return;
    
    setLoading(true);
    setSearchResult(null);
    
    try {
      const { data, error } = await supabase
        .from('tokens')
        .select('status, ticker, status_reason')
        .eq('token_address', searchValue.trim())
        .single();
        
      if (error || !data) {
        setSearchResult('TOKEN NOT FOUND IN DATABASE');
      } else {
        setSearchResult(`$${data.ticker} — ${data.status} ${data.status_reason ? `(${data.status_reason})` : ''}`);
      }
    } catch (err) {
      setSearchResult('SEARCH ERROR');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="relative w-full py-16 md:py-24 px-4 md:px-8 flex justify-center overflow-hidden border-b border-rule">
      
      {/* Decorative Radar Rings */}
      <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden flex items-center justify-center">
         <div className="radar-ring w-[300px] h-[300px]"></div>
         <div className="radar-ring w-[600px] h-[600px]"></div>
         <div className="radar-ring w-[900px] h-[900px]"></div>
         <div className="radar-ring w-[1200px] h-[1200px]"></div>
      </div>

      <div className="max-w-6xl w-full grid grid-cols-1 lg:grid-cols-12 gap-12 relative z-10">
        
        <div className="lg:col-span-8 flex flex-col items-start justify-center">
          <div className="font-mono text-xs text-ink-faint tracking-widest uppercase mb-6">
            {t('eyebrow')}
          </div>
          <h1 className="font-serif text-5xl md:text-[80px] leading-[1.1] text-ink mb-6">
            {t('h1_part1')} <br />
            {t('h1_part2')} <em className="text-rust italic font-semibold">{t('h1_italic')}</em>
          </h1>
          <p className="font-sans text-lg text-ink-soft max-w-[480px] leading-relaxed mb-8">
            {t('subtitle')}
          </p>

          <form onSubmit={handleCheckToken} className="w-full max-w-[480px]">
            <div className="flex w-full border border-rule bg-paper focus-within:border-ink transition-colors h-14">
              <input 
                type="text" 
                value={searchValue}
                onChange={(e) => setSearchValue(e.target.value)}
                placeholder={t('input_placeholder')}
                className="flex-grow bg-transparent px-4 outline-none font-mono text-sm text-ink placeholder:text-ink-faint rounded-none"
              />
              <button disabled={loading} type="submit" className="bg-ink text-paper font-mono text-sm px-8 hover:bg-ink-soft transition-colors whitespace-nowrap rounded-none disabled:opacity-50">
                {loading ? 'CHECKING...' : t('btn_check')}
              </button>
            </div>
            
            {searchResult && (
              <div className="mt-4 p-3 border border-ink bg-beige-0 font-mono text-xs uppercase text-ink">
                {searchResult}
              </div>
            )}

            <div className="font-mono text-[10px] text-ink-faint uppercase tracking-widest mt-3">
              {t('input_note')}
            </div>
          </form>
        </div>

        <div className="lg:col-span-4 flex items-center">
          <div className="bg-paper border border-rule p-6 md:p-8 w-full shadow-none">
            <div className="font-sans text-ink leading-relaxed mb-6 text-base">
              <strong>98.6%</strong> {t('stats_card_1')}
              <br/><br/>
              <strong>$151M+</strong> {t('stats_card_2')}
            </div>
            <div className="font-mono text-[10px] text-ink-faint uppercase tracking-widest leading-relaxed">
              {t('stats_source')}
            </div>
          </div>
        </div>

      </div>
    </section>
  );
}
