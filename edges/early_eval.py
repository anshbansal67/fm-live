"""14 Nov: score BOOK-EARLY LIVE paper picks (early_picks.jsonl). Close = Pinnacle no-vig at its last hourly snapshot before the start
(early_odds.jsonl), else the Betfair off mid from the recorder (last pre-off book within 30 min, teams matched through bf_rating.to_cs).
CLV = price x p_close - 1. Verdict per arm after 200 picks: CLV > 0 by >= 2 SE (fixture-clustered)."""
import os, sys, json, glob, numpy as np, pandas as pd
T = os.path.expanduser(os.environ.get('FM_T', '~/cricket-project/t20')); LV = T + '/output/markets/live/'
sys.path.insert(0, T + '/scratch/edge'); ACTIONS = os.environ.get('FM_ACTIONS') == '1'   # 15 Nov: the cloud job (LAPTOP_PROOF.md): no Betfair, results from ESPN
BR = None if ACTIONS else __import__('bf_rating')
import espn_result as ER
P = [json.loads(l) for l in open(LV + 'early_picks.jsonl')] if os.path.exists(LV + 'early_picks.jsonl') else []
if not P: print('BOOK-EARLY LIVE: no paper picks yet'); sys.exit(0)
import subprocess
now = pd.Timestamp.now(tz='UTC'); P = pd.DataFrame(P); P['start'] = pd.to_datetime(P.start, utc=True)
S = [json.loads(l) for l in open(LV + 'early_odds.jsonl')]
pin = {}
for s in S:
    if s.get('p_pin') and pd.Timestamp(s['ts']) < pd.Timestamp(s['start']): pin[s['fixture_id']] = s['p_pin']   # last one wins (file is in time order)
# 15 Nov (lane 2): the-odds-api picks (oa_picks.py): close = Pinnacle no-vig at the last snapshot before the start (the 10 min / start points)
if os.path.exists(T + '/output/markets/odds/oa/snaps.jsonl'):
    for l_ in open(T + '/output/markets/odds/oa/snaps.jsonl'):
        s_ = json.loads(l_); pb_ = s_['books'].get('pinnacle') or {}; tm_ = [s_['home'], s_['away']]
        if s_.get('mins', -1) >= 0 and all(pb_.get(t_) for t_ in tm_):
            q_ = [1 / pb_[t_] for t_ in tm_]; pin['oa:' + s_['id']] = [q_[0] / sum(q_), q_[1] / sum(q_)]
# 14 Nov: Pinnacle's true last pre-start price from the historical endpoint (hourly snapshots can be up to an hour stale); cached per fixture
HL = LV + 'pin_close/'; os.makedirs(HL, exist_ok=True)
def pin_close(fid, start):
    if str(fid).startswith('oa:'): return None   # the-odds-api picks: close from its own start snapshot (pin, below)
    f = HL + fid + '.json'
    if not os.path.exists(f):
        if now < start + pd.Timedelta(minutes=30): return None
        import early_picks as EP   # 15 Nov (lane 2): through the shared OddsPapi lock / cooldown
        d_ = EP.get('historical-odds', {'fixtureId': fid, 'bookmakers': 'pinnacle'}, 5.5)
        if d_ is None or ('_err' in d_ and d_['_err'] != 404): return None
        open(f, 'w').write(json.dumps({} if '_err' in d_ else d_))
    d = json.load(open(f)); m = (((d.get('bookmakers') or {}).get('pinnacle') or {}).get('markets') or {}).get('271')
    if not m: return None
    pr = []
    for oid in ('271', '272'):
        sn = [x for pl in ((m['outcomes'].get(oid) or {}).get('players') or {}).values() for x in pl if pd.Timestamp(x['createdAt']) <= start and x.get('price')]
        if not sn: return None
        pr.append(max(sn, key=lambda x: x['createdAt'])['price'])
    q = [1/pr[0], 1/pr[1]]; return [q[0]/sum(q), q[1]/sum(q)]
bf = BR.live_off() if BR else None
def bf_close(team, opp, start):
    if bf is None or not len(bf): return None
    a, b = BR.to_cs(team), BR.to_cs(opp); c = bf[(bf.t - start).abs() < pd.Timedelta(hours=2)]
    for x in c.itertuples():
        xa, xb = BR.to_cs(x.a), BR.to_cs(x.b)
        if (xa, xb) == (a, b): return x.qa
        if (xa, xb) == (b, a): return 1 - x.qa
    return None
# results: Betfair settlement of the match-odds market (results.jsonl), market found from the recorder's books by teams and start time
MO = {}
import glob as _g
for f in sorted(_g.glob(LV + '20??-??-??.jsonl')):
    for line in open(f):
        if '"Match Odds"' not in line: continue
        try: d = json.loads(line)
        except Exception: continue
        if len(d.get('runners', [])) == 2: MO[d['market_id']] = (pd.Timestamp(d['start']), [(r['id'], r['name']) for r in d['runners']])
RES = {}
if os.path.exists(LV + 'results.jsonl'):
    for line in open(LV + 'results.jsonl'):
        try: d = json.loads(line); RES[d['market_id']] = {r['id']: r['status'] for r in d['runners']}
        except Exception: pass
def result(team, opp, start, tournament=''):
    if BR is None: return ER.result(team, opp, start.isoformat(), tournament)   # cloud: ESPN
    a, b = BR.to_cs(team), BR.to_cs(opp)
    for mid, (st, rn) in MO.items():
        if abs(st - start) > pd.Timedelta(hours=3): continue
        cs = [BR.to_cs(n) for _, n in rn]
        if sorted(map(str, cs)) == sorted(map(str, [a, b])) and mid in RES:
            rid = rn[cs.index(a)][0]; st_ = RES[mid].get(rid)
            return 1.0 if st_ == 'WINNER' else 0.0 if st_ == 'LOSER' else None
    return None
rows = []
for x in P[P.start < now].itertuples():
    pc, src = None, None
    pcl = pin_close(x.fixture_id, x.start)
    if pcl: pc, src = pcl[x.side], 'pinnacle'
    elif x.fixture_id in pin: pc, src = pin[x.fixture_id][x.side], 'pinnacle (hourly)'
    else:
        q = bf_close(x.team, x.opp, x.start)
        if q is not None: pc, src = q, 'betfair'
    w = result(x.team, x.opp, x.start, x.tournament) if x.start < now - pd.Timedelta(hours=3) else None
    if w is None and BR is not None and x.start < now - pd.Timedelta(hours=3):   # 15 Nov: the Mac falls back to ESPN when Betfair has no settled market
        try: w = ER.result(x.team, x.opp, x.start.isoformat(), x.tournament)
        except Exception: w = None
    rows.append(dict(arm=x.arm, fixture_id=x.fixture_id, side=x.side, tournament=x.tournament, team=x.team, price=x.price, p_close=pc, src=src, clv=(x.price * pc - 1) if pc else np.nan, won=w))
R = pd.DataFrame(rows, columns=['arm', 'fixture_id', 'side', 'tournament', 'team', 'price', 'p_close', 'src', 'clv', 'won'])
print(f'BOOK-EARLY LIVE (paper): {len(P)} picks ({P.arm.value_counts().to_dict()}), {len(R)} started, {R.clv.notna().sum() if len(R) else 0} with a close')
for arm, g in (R.groupby('arm') if len(R) else []):
    g = g[g.clv.notna()]
    if not len(g): print(f'  {arm}: no closes yet'); continue
    se = g.clv.std() / np.sqrt(len(g)) if len(g) > 1 else np.nan
    print(f'  {arm}: {len(g)} scored | CLV {100*g.clv.mean():+.2f}% (SE {100*se:.2f}) | closes from {g.src.value_counts().to_dict()} | verdict waits for 200')

# ---- public feed (Ansh, 14 Nov: publish the picks, timestamped) -> output/markets/live/picks.json (+ ~/fm-live/picks.json with --publish)
ARM = {'A2': 'rating', 'A3': 'rating + home', 'B': 'above the sharp price', 'BT': 'above the sharp price, at the toss', 'TS': 'team sheet'}
sc = {(r.fixture_id, r.side, r.arm): r for r in R.itertuples()} if len(R) else {}
out = []
for x in P.sort_values('ts', ascending=False).itertuples():
    r = sc.get((x.fixture_id, x.side, x.arm))
    out.append(dict(posted=x.ts[:16] + 'Z', competition=x.tournament, match=f'{x.team} v {x.opp}', start=x.start.strftime('%Y-%m-%dT%H:%MZ'), pick=x.team,
                    book=x.book, price=x.price, fair=round(x.p_rating, 3) if (x.arm in ('A2', 'A3', 'TS') and x.p_rating == x.p_rating and x.p_rating is not None) else (round(x.p_pin, 3) if x.p_pin else None),
                    why=ARM.get(x.arm, x.arm), hours_before=round(x.hrs), close=round(r.p_close, 3) if (r is not None and str(r.src).startswith('pinnacle') and r.p_close == r.p_close and r.p_close is not None) else None,   # 15 Nov: public = Pinnacle closes only ('no close', never a Betfair close); the printed internal score keeps both
                    clv=round(float(r.clv), 4) if (r is not None and str(r.src).startswith('pinnacle') and r.clv == r.clv) else None,
                    result=None if (r is None or r.won is None or r.won != r.won) else ('won' if r.won == 1 else 'lost')))
# one public row per fixture / side (the earliest posting; the arms that agreed are listed), so the summary counts each bet once
G = {}
for o, x in zip(out, P.sort_values('ts', ascending=False).itertuples()):
    k = (x.fixture_id, x.side)
    if k not in G or o['posted'] < G[k]['posted']: G[k] = dict(o, why=G[k]['why'] if k in G else o['why'])
arms = {}
for x in P.itertuples(): arms.setdefault((x.fixture_id, x.side), set()).add(ARM.get(x.arm, x.arm))
out = sorted([dict(v, why=' + '.join(sorted(arms[k]))) for k, v in G.items()], key=lambda o: o['posted'], reverse=True)
done = [o for o in out if o['clv'] is not None]
summ = dict(asof=now.strftime('%Y-%m-%dT%H:%MZ'), picks=len(out), scored=len(done), clv_mean=round(float(np.mean([o['clv'] for o in done])), 4) if done else None,
            clv_se=round(float(np.std([o['clv'] for o in done], ddof=1) / np.sqrt(len(done))), 4) if len(done) > 1 else None,
            beat_close=round(float(np.mean([o['clv'] > 0 for o in done])), 3) if done else None,
            settled=sum(o['result'] is not None for o in out), profit_units=round(sum((o['price'] - 1) if o['result'] == 'won' else -1 for o in out if o['result']), 2),
            note='Paper picks, posted 12-48 h before the start. Closing-line value = our price x the fair price at the start (Pinnacle without margin, else Betfair) - 1. Verdict after 200 picks.')
# 15 Nov (coordinator 12:45): COMMIT-REVEAL, off until the paid launch (flag file output/markets/live/commit_reveal.flag or EDGES_COMMIT_REVEAL=1).
# On: a pick still to start is published only as {posted, competition, start, fingerprint}; fingerprint = sha256 of the pick's canonical
# JSON (posted, match, pick, book, price, start) + a random salt kept privately (pick_salts.json, never published). At the start the full pick
# and its salt are published, so anyone can recompute the hash and see the pick was fixed before the start. Off: every pick public as now.
import hashlib, secrets as _sec
def canon(o): return json.dumps({k: o.get(k) for k in ('posted', 'match', 'pick', 'book', 'price', 'start')}, sort_keys=True, separators=(',', ':'))
SALTF = LV + 'pick_salts.json'; SALTS = json.load(open(SALTF)) if os.path.exists(SALTF) else {}
for o in out:
    k_ = canon(o)
    if k_ not in SALTS: SALTS[k_] = _sec.token_hex(16)
    o['fingerprint'] = hashlib.sha256((k_ + SALTS[k_]).encode()).hexdigest()
json.dump(SALTS, open(SALTF, 'w'))
CR = os.path.exists(LV + 'commit_reveal.flag') or os.environ.get('EDGES_COMMIT_REVEAL') == '1'
def public(o):
    if not CR: return {k: v for k, v in o.items()}
    if pd.Timestamp(o['start']) > now: return dict(posted=o['posted'], competition=o['competition'], start=o['start'], fingerprint=o['fingerprint'], status='hidden until the start')
    return dict(o, salt=SALTS[canon(o)], check='sha256(canonical(posted, match, pick, book, price, start) + salt) == fingerprint')
J = dict(summary=dict(summ, commit_reveal=CR), picks=[public(o) for o in out]); open(LV + 'picks.json', 'w').write(json.dumps(J, separators=(',', ':')))
open(LV + 'picks_member.json', 'w').write(json.dumps(dict(summary=summ, picks=out), separators=(',', ':')))   # full, for the members' feed (never published)
if '--publish' in sys.argv:
    asof_ = summ['asof']; Rp = os.path.expanduser(os.environ.get('FM_LIVE_DIR', '~/fm-live')); open(os.path.join(Rp, 'picks.json'), 'w').write(json.dumps(J, separators=(',', ':')))
    HFN = 'edges_health_cloud.json' if ACTIONS else 'edges_health.json'   # 15 Nov: for Ansh HQ via hub.py (cloud and Mac each publish their own)
    if os.path.exists(LV + HFN) and os.path.abspath(LV + HFN) != os.path.abspath(os.path.join(Rp, HFN)): open(os.path.join(Rp, HFN), 'w').write(open(LV + HFN).read())
    r_ = subprocess.run(f'cd {Rp} && git add picks.json $(test -f {HFN} && echo {HFN}) && (git diff --cached --quiet && echo unchanged || (git commit -q -m "picks {asof_}" && (git push -q 2>/dev/null || (git pull -q --rebase origin main && git push -q)) && echo pushed))', shell=True, capture_output=True, text=True)
    print('picks feed:', (r_.stdout or r_.stderr).strip()[-120:])
