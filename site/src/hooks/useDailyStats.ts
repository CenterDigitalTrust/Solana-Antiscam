
'use client';
import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

export type DailyStats = {
  scanned_today: number;
  rejected_today: number;
  passed_today: number;
  daily_pnl_usd: number;
};

export function useDailyStats() {
  const [stats, setStats] = useState<DailyStats>({ scanned_today: 0, rejected_today: 0, passed_today: 0, daily_pnl_usd: 0 });

  useEffect(() => {
    const fetchInitial = async () => {
      const { data, error } = await supabase.from('daily_stats').select('*').eq('id', 1).single();
      if (!error && data) {
        setStats(data as DailyStats);
      }
    };
    fetchInitial();

    const channel = supabase.channel(`stats-changes-${Math.random()}`)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'daily_stats' }, (payload) => {
        setStats(payload.new as DailyStats);
      }).subscribe();

    return () => { supabase.removeChannel(channel); };
  }, []);

  return stats;
}
