export type TokenState = 'monitoring' | 'quarantine' | 'entry_eligible' | 'closed';

export interface TokenMockData {
  id: string;
  token_address: string;
  ticker: string;
  discovered_at: string;
  state: TokenState;
  score: number;
  price_change_pct: number;
  liquidity_usd: number;
  top10_holder_pct: number;
  mint_authority_active: boolean;
  freeze_authority_active: boolean;
  status_reason: string;
  updated_at: string;
}

export const MOCK_TERMINAL_FEED: TokenMockData[] = [
  {
    id: '1', token_address: '111', ticker: 'WCAT', discovered_at: new Date(Date.now() - 4000).toISOString(),
    state: 'monitoring', score: 81, price_change_pct: 12.4, liquidity_usd: 15000, top10_holder_pct: 20,
    mint_authority_active: false, freeze_authority_active: false, status_reason: '', updated_at: new Date().toISOString()
  },
  {
    id: '2', token_address: '222', ticker: 'FROGG', discovered_at: new Date(Date.now() - 11000).toISOString(),
    state: 'quarantine', score: 22, price_change_pct: -3.1, liquidity_usd: 500, top10_holder_pct: 85,
    mint_authority_active: true, freeze_authority_active: false, status_reason: 'TOP10 >80%', updated_at: new Date().toISOString()
  },
  {
    id: '3', token_address: '333', ticker: 'NOVA', discovered_at: new Date(Date.now() - 41000).toISOString(),
    state: 'entry_eligible', score: 94, price_change_pct: 187.0, liquidity_usd: 50000, top10_holder_pct: 10,
    mint_authority_active: false, freeze_authority_active: false, status_reason: '', updated_at: new Date().toISOString()
  },
  {
    id: '4', token_address: '444', ticker: 'PLUME', discovered_at: new Date(Date.now() - 62000).toISOString(),
    state: 'monitoring', score: 63, price_change_pct: 4.0, liquidity_usd: 5000, top10_holder_pct: 25,
    mint_authority_active: false, freeze_authority_active: false, status_reason: '', updated_at: new Date().toISOString()
  },
  {
    id: '5', token_address: '555', ticker: 'RUGZ', discovered_at: new Date(Date.now() - 75000).toISOString(),
    state: 'quarantine', score: 8, price_change_pct: -71.2, liquidity_usd: 100, top10_holder_pct: 95,
    mint_authority_active: true, freeze_authority_active: true, status_reason: 'MINT ACTIVE', updated_at: new Date().toISOString()
  }
];

export const MOCK_GROWTH_LEADERS = MOCK_TERMINAL_FEED.filter(t => t.price_change_pct >= 50 && t.state !== 'quarantine');
export const MOCK_QUARANTINE = MOCK_TERMINAL_FEED.filter(t => t.state === 'quarantine');
