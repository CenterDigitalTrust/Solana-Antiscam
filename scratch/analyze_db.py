import sqlite3
import json

conn = sqlite3.connect('data/research_lab.db')
conn.row_factory = sqlite3.Row

with open('scratch/db_stats.txt', 'w', encoding='utf-8') as out:
    # 1. Total decisions
    cur = conn.execute('SELECT action, status, total_score, security_score, liquidity_score, momentum_score, wallet_score, primary_reason FROM decision_ledger')
    decisions = cur.fetchall()
    out.write(f'TOTAL DECISIONS IN LEDGER: {len(decisions)}\n')

    actions = {}
    statuses = {}
    reasons = {}
    scores = []
    sec_scores = []
    liq_scores = []
    wal_scores = []
    mom_scores = []

    for d in decisions:
        a = d['action']
        s = d['status']
        r = d['primary_reason']
        actions[a] = actions.get(a, 0) + 1
        statuses[s] = statuses.get(s, 0) + 1
        reasons[r] = reasons.get(r, 0) + 1
        if d['total_score'] is not None:
            scores.append(float(d['total_score']))
        if d['security_score'] is not None:
            sec_scores.append(float(d['security_score']))
        if d['liquidity_score'] is not None:
            liq_scores.append(float(d['liquidity_score']))
        if d['wallet_score'] is not None:
            wal_scores.append(float(d['wallet_score']))
        if d['momentum_score'] is not None:
            mom_scores.append(float(d['momentum_score']))

    out.write(f'\nACTIONS: {json.dumps(actions, indent=2)}\n')
    out.write(f'STATUSES: {json.dumps(statuses, indent=2)}\n')
    out.write(f'\nTOP PRIMARY REASONS:\n')
    for r, count in sorted(reasons.items(), key=lambda x: x[1], reverse=True)[:15]:
        out.write(f'  {count:>4}x: {r}\n')

    if scores:
        scores.sort()
        out.write(f'\nTOTAL SCORE STATS (count={len(scores)}):\n')
        out.write(f'  Min:    {min(scores):.2f}\n')
        out.write(f'  Max:    {max(scores):.2f}\n')
        out.write(f'  Mean:   {sum(scores)/len(scores):.2f}\n')
        out.write(f'  Median: {scores[len(scores)//2]:.2f}\n')
        out.write(f'  >= 70 (CANDIDATE): {sum(1 for s in scores if s >= 70.0)}\n')
        out.write(f'  40-70 (WATCH):     {sum(1 for s in scores if 40.0 <= s < 70.0)}\n')
        out.write(f'  < 40 (REJECT):     {sum(1 for s in scores if s < 40.0)}\n')

    if sec_scores:
        out.write(f'\nSECURITY SCORE STATS (count={len(sec_scores)}):\n')
        out.write(f'  Min:    {min(sec_scores):.2f}, Max: {max(sec_scores):.2f}, Mean: {sum(sec_scores)/len(sec_scores):.2f}\n')
    if mom_scores:
        out.write(f'MOMENTUM SCORE STATS (count={len(mom_scores)}):\n')
        out.write(f'  Min:    {min(mom_scores):.2f}, Max: {max(mom_scores):.2f}, Mean: {sum(mom_scores)/len(mom_scores):.2f}\n')
    if liq_scores:
        out.write(f'LIQUIDITY SCORE STATS (count={len(liq_scores)}):\n')
        out.write(f'  Min:    {min(liq_scores):.2f}, Max: {max(liq_scores):.2f}, Mean: {sum(liq_scores)/len(liq_scores):.2f}\n')
    if wal_scores:
        out.write(f'WALLET SCORE STATS (count={len(wal_scores)}):\n')
        out.write(f'  Min:    {min(wal_scores):.2f}, Max: {max(wal_scores):.2f}, Mean: {sum(wal_scores)/len(wal_scores):.2f}\n')

    # Check security_checks table
    cur = conn.execute('SELECT is_hard_reject, hard_reject_reasons, soft_security_score FROM security_checks')
    sec_checks = cur.fetchall()
    out.write(f'\nTOTAL SECURITY CHECKS: {len(sec_checks)}\n')
    hard_rejects = [c for c in sec_checks if c['is_hard_reject'] == 1]
    out.write(f'HARD REJECTS: {len(hard_rejects)}\n')
    hr_reasons = {}
    for c in hard_rejects:
        try:
            rs = json.loads(c['hard_reject_reasons'] or '[]')
            for r in rs:
                hr_reasons[r] = hr_reasons.get(r, 0) + 1
        except Exception:
            pass
    out.write(f'HARD REJECT REASONS: {json.dumps(hr_reasons, indent=2)}\n')

    # Check quarantine table / status in tokens
    cur = conn.execute('SELECT status, count(*) as cnt FROM tokens GROUP BY status')
    out.write(f'\nTOKENS BY STATUS: {dict(cur.fetchall())}\n')
