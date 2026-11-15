"""14 Nov: the VALUE BOARD feed (the subscription product's core; not live until arm B is confirmed, see MODEL.md).
Every upcoming match with a sharp price: the fair price (Pinnacle, margin removed, draw included where priced), every UK bookmaker's price,
the best UK price per outcome and its gap to fair; gaps >= 3% are flagged as value (>10% flagged 'check': often a stale or mistaken quote).
Sources: the-odds-api snapshots (oa/snaps.jsonl, oa_collect.py) and OddsPapi snapshots (live/early_odds.jsonl, early_picks.py); the newest
snapshot per match wins. -> output/markets/live/value_board.json  (python3 value_board.py [--upload] -> the site's members-only feed 'value_board')"""
import os, re, sys, json, subprocess, pandas as pd
T = os.path.expanduser(os.environ.get('FM_T', '~/cricket-project/t20')); LV = T + '/output/markets/live/'; OA = T + '/output/markets/odds/oa/'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))); from fm_edges.switch import stop_if_killed; stop_if_killed('value_board')   # 15 Nov: the kill switch, checked first
UKN = {'bet365': 'bet365', 'williamhill': 'William Hill', 'paddypower': 'Paddy Power', 'betfred': 'Betfred', 'unibet': 'Unibet', 'unibet_uk': 'Unibet', 'ladbrokes': 'Ladbrokes',
       'ladbrokes_uk': 'Ladbrokes', 'coral': 'Coral', 'betway': 'Betway', '888sport': '888sport', 'sport888': '888sport', 'skybet': 'Sky Bet', 'betvictor': 'BetVictor',
       'boylesports': 'BoyleSports', 'livescorebet': 'LiveScore Bet', 'virginbet': 'Virgin Bet', 'grosvenor': 'Grosvenor', 'betano_uk': 'Betano', 'casumo': 'Casumo',
       'leovegas': 'LeoVegas', 'mrgreen': 'Mr Green'}
COMP = {'cricket_odi': 'One-day internationals', 'cricket_test_match': 'Test matches', 'cricket_big_bash': 'Big Bash League', 'cricket_international_t20': 'T20 internationals',
        'cricket_t20_blast': 'T20 Blast', 'cricket_ipl': 'IPL', 'cricket_psl': 'PSL', 'cricket_caribbean_premier_league': 'CPL', 'cricket_the_hundred': 'The Hundred'}
nm = lambda s: ' '.join(re.sub(r'[^a-z ]', ' ', str(s).lower()).split())
def snaps():
    out = []
    if os.path.exists(OA + 'snaps.jsonl'):
        for l in open(OA + 'snaps.jsonl'):
            s = json.loads(l); names = [s['home'], s['away']]; b = s['books']
            outs = names + (['Draw'] if any('Draw' in v for v in b.values()) else [])
            pr = lambda v: [v.get(o) for o in outs]
            out.append(dict(ts=s['ts'], start=s['start'], comp=COMP.get(s['sport'], s['sport']), outcomes=outs, pin=pr(b['pinnacle']) if 'pinnacle' in b else None,
                            books={k: pr(v) for k, v in b.items() if k in UKN}, src='the-odds-api'))
    if os.path.exists(LV + 'early_odds.jsonl'):
        for l in open(LV + 'early_odds.jsonl'):
            s = json.loads(l)
            if not s.get('books'): continue
            out.append(dict(ts=s['ts'], start=s['start'], comp=s.get('tournament'), outcomes=s['teams'], pin=s.get('pinnacle'),
                            books={k: v for k, v in s['books'].items() if k in UKN}, src='oddspapi'))
    return out
def build(now=None):
    now = now or pd.Timestamp.now(tz='UTC'); latest = {}; allk = {}
    for s in snaps():
        st = pd.Timestamp(s['start'])
        if not (now < st <= now + pd.Timedelta(hours=72)): continue
        k = (st.floor('h'), frozenset(nm(o) for o in s['outcomes'][:2])); allk.setdefault(k, []).append(s)
        if not s['pin'] or None in s['pin']: continue
        if k not in latest or s['ts'] > latest[k]['ts']: latest[k] = s
    # 15 Nov (lane 2): two sources (OddsPapi, the-odds-api). Fair = the newest Pinnacle snapshot; UK books it lacks are filled from the other
    # source's newest snapshot of the same match taken within 2 h of it (matched by team name, not position).
    for k, b in latest.items():
        b = latest[k] = dict(b, books=dict(b['books'])); tb = pd.Timestamp(b['ts']); srcs = {b['src']}
        for o in sorted(allk[k], key=lambda s: s['ts'], reverse=True):
            if o is b or o['src'] == b['src'] or abs(pd.Timestamp(o['ts']) - tb) > pd.Timedelta(hours=2): continue
            ix = {nm(n): i for i, n in enumerate(o['outcomes'])}
            for bk, v in o['books'].items():
                if bk in b['books'] or UKN.get(bk) in {UKN.get(x) for x in b['books']} or not v: continue
                b['books'][bk] = [v[ix[nm(n)]] if nm(n) in ix and ix[nm(n)] < len(v) else None for n in b['outcomes']]; srcs.add(o['src'])
        b['src'] = ' + '.join(sorted(srcs))
    ev = []
    for s in sorted(latest.values(), key=lambda s: s['start']):
        q = [1/p for p in s['pin']]; fair = [x/sum(q) for x in q]; rows = []
        for i, o in enumerate(s['outcomes']):
            px = {UKN[k]: v[i] for k, v in s['books'].items() if v and i < len(v) and v[i]}
            best = max(px.items(), key=lambda kv: kv[1]) if px else (None, None)
            gap = (best[1] * fair[i] - 1) if best[1] else None
            rows.append(dict(outcome=o, fair_prob=round(fair[i], 4), fair_odds=round(1/fair[i], 2), best_book=best[0], best_odds=best[1],
                             gap=round(gap, 4) if gap is not None else None, value=bool(gap is not None and gap >= 0.03), check=bool(gap is not None and gap > 0.10),
                             books=dict(sorted(px.items(), key=lambda kv: -kv[1]))))
        ev.append(dict(match=' v '.join(s['outcomes'][:2]), comp=s['comp'], start=s['start'], priced_at=s['ts'][:16] + 'Z', source=s['src'], outcomes=rows,
                       value=sum(r['value'] for r in rows)))
    rec = json.load(open(LV + 'picks.json'))['summary'] if os.path.exists(LV + 'picks.json') else {}
    return dict(asof=now.strftime('%Y-%m-%dT%H:%MZ'), events=ev, n_value=sum(e['value'] for e in ev), record=rec,
                note='Fair price = the sharpest bookmaker (Pinnacle) with its margin removed. Value = a UK bookmaker at least 3% above fair. Prices move: check before betting. 18+ only; please gamble responsibly.')
if __name__ == '__main__':
    J = build(); json.dump(J, open(LV + 'value_board.json', 'w'), separators=(',', ':'))
    print(f"value board: {len(J['events'])} matches in the next 72 h, {J['n_value']} value flags")
    if '--upload' in sys.argv:
        r = subprocess.run(['node', os.path.expanduser('~/ask-cricket/scripts/fantasy/upload_feed.mjs'), 'value_board', LV + 'value_board.json'], capture_output=True, text=True)
        print((r.stdout or r.stderr).strip()[-200:])
