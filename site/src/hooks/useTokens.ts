'use client';
import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

export type TokenData = {
  token_address: string;
  ticker: string;
  score: number;
  status: string;
  price_usd: number;
  initial_price_usd?: number;
  liquidity_usd: number;
  market_cap_usd: number;
  mint_authority_active: boolean;
  freeze_authority_active: boolean;
  top10_holder_pct: number;
  discovered_at: string;
  updated_at: string;
  status_reason: string;
};

export function useTokens() {
  const [tokens, setTokens] = useState<TokenData[]>([]);

  useEffect(() => {
    // 1. Fetch initial active tokens (last 100)
    const fetchInitial = async () => {
      const { data, error } = await supabase
        .from('tokens')
        .select('*')
        .order('updated_at', { ascending: false })
        .limit(100);
      
      if (!error && data) {
        setTokens(data);
      }
    };
    
    fetchInitial();

    // 2. Subscribe to realtime updates
    const channelId = `tokens-changes-${Math.random().toString(36).substring(7)}`;
    const channel = supabase
      .channel(channelId)
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'tokens' },
        (payload) => {
          setTokens((current) => {
            const newToken = payload.new as TokenData;
            const existsIndex = current.findIndex(t => t.token_address === newToken.token_address);
            
            if (payload.eventType === 'DELETE') {
               return current.filter(t => t.token_address !== payload.old.token_address);
            }

            if (existsIndex >= 0) {
              const updated = [...current];
              updated[existsIndex] = newToken;
              return updated.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
            } else {
              return [newToken, ...current].slice(0, 100); // Keep top 100 visible in cache
            }
          });
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  return tokens;
}
