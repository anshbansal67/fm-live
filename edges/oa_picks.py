"""15 Nov (lane 2): arm B / BT from the-odds-api snapshots (oa_collect.py), so T20 leagues the-odds-api carries (BBL from 12 Dec) get the SAME
registered rule while OddsPapi is shut: the best price among the registered UK books x Pinnacle's no-vig price at the same snapshot >= 1.03.
B = a snapshot 12-48 h before the start (the 24 h point), BT = 0-0.6 h (the 10 min point). One pick per fixture / side / arm, and none where
early_picks.py already picked the same team, start and arm (fixture ids differ between the sources). T20 sports only: ODIs and Tests are
lane 3's (ARM-B-OTHER). -> early_picks.jsonl (fixture_id 'oa:<id>', src 'the-odds-api'), scored and published by early_eval.py with the rest.
  python3 oa_picks.py [--dry]"""
import os, re, sys, json, pandas as pd
T = os.path.expanduser(os.environ.get('FM_T', '~/cricket-project/t20')); LV = T + '/output/markets/live/'; OA = T + '/output/markets/odds/oa/'
UK = {'bet365': 'bet365', 'williamhill': 'williamhill', 'paddypower': 'paddypower', 'betfred': 'betfred', 'unibet_uk': 'unibet', 'unibet': 'unibet',
      'ladbrokes_uk': 'ladbrokes', 'coral': 'coral', 'betway': 'betway', 'sport888': '888sport', 'skybet': 'skybet', 'betvictor': 'betvictor', 'boylesports': 'boylesports'}
NAMES = {'cricket_big_bash': 'Big Bash League', 'cricket_international_t20': 'T20 internationals', 'cricket_t20_blast': 'T20 Blast', 'cricket_ipl': 'IPL',
         'cricket_psl': 'PSL', 'cricket_caribbean_premier_league': 'CPL', 'cricket_the_hundred': 'The Hundred'}
NOT_T20 = {'cricket_odi', 'cricket_test_match', 'cricket_icc_world_cup', 'cricket_icc_world_cup_womens', 'cricket_icc_trophy', 'cricket_asia_cup'}
nm = lambda s: ' '.join(re.sub(r'[^a-z ]', ' ', str(s).lower()).split())
def picked():
    s = set()
    if os.path.exists(LV + 'early_picks.jsonl'):
        for l in open(LV + 'early_picks.jsonl'):
            d = json.loads(l); s.add((d['fixture_id'], d['side'], d['arm'])); s.add((nm(d['team']), pd.Timestamp(d['start']).floor('h'), d['arm']))
    return s
def main():
    dry = '--dry' in sys.argv; st_f = OA + 'picks_state.json'
    done = json.load(open(st_f)).get('lines', 0) if os.path.exists(st_f) else 0
    L = open(OA + 'snaps.jsonl').read().splitlines() if os.path.exists(OA + 'snaps.jsonl') else []
    seen = picked(); n = 0
    for l in L[done:]:
        s = json.loads(l)
        if s['sport'] in NOT_T20 or not s['sport'].startswith('cricket_'): continue
        b = s['books']; teams = [s['home'], s['away']]
        if 'pinnacle' not in b or any(b['pinnacle'].get(t) is None for t in teams): continue
        hrs = s['mins'] / 60; arm = 'B' if 12 <= hrs <= 48 else 'BT' if 0 < hrs <= 0.6 else None
        if not arm: continue
        q = [1 / b['pinnacle'][t] for t in teams]; pnv = [x / sum(q) for x in q]
        soft = {UK[k]: [v.get(t) for t in teams] for k, v in b.items() if k in UK}
        for side in (0, 1):
            px = {k: v[side] for k, v in soft.items() if v[side]}
            if not px: continue
            bk = max(px, key=px.get); best = px[bk]; st = pd.Timestamp(s['start'])
            if best * pnv[side] < 1.03 or ('oa:' + s['id'], side, arm) in seen or (nm(teams[side]), st.floor('h'), arm) in seen: continue
            pk = dict(ts=s['ts'], fixture_id='oa:' + s['id'], tournament=NAMES.get(s['sport'], s['sport']), start=st.strftime('%Y-%m-%dT%H:%M:%S.000Z'), hrs=round(hrs, 2),
                      arm=arm, side=side, team=teams[side], opp=teams[1 - side], book=bk, price=best, p_rating=None, p_pin=pnv[side], nbooks=len(soft),
                      gap=round(best * pnv[side] - 1, 4), suspect=bool(best * pnv[side] - 1 > 0.10), src='the-odds-api')
            seen.add(('oa:' + s['id'], side, arm)); seen.add((nm(teams[side]), st.floor('h'), arm)); n += 1
            print(*(('PICK', arm, '(details kept out of the public Actions log)') if os.environ.get('FM_ACTIONS') == '1' else ('PICK', arm, pk['tournament'], pk['team'], '@', best, bk, f'{hrs:.2f}h')), flush=True)
            if not dry: open(LV + 'early_picks.jsonl', 'a').write(json.dumps(pk) + '\n')
    if not dry: json.dump(dict(lines=len(L)), open(st_f, 'w'))
    print(f'oa_picks: {len(L) - done} new snapshots, {n} picks', flush=True)
if __name__ == '__main__': main()
