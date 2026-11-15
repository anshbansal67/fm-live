"""14 Nov: forward bookmaker snapshots from the-odds-api.com (free key: 500 credits a month; one odds call = 1 credit per region; the
events list is free). Regions uk + eu = Pinnacle, Betfair Exchange and ~15 UK books, every event of a sport in one call (2 credits).
Snapshot points per event: 24 h, 6 h, 1 h, 10 min before the start and at the start (the close). Run every few minutes by the recorder:
an odds call is made for a sport only when one of its events reaches a snapshot point not yet taken; never below 20 credits left.
-> output/markets/odds/oa/snaps.jsonl (one line per event per call). For BOOK-B-FWD (MODEL.md)."""
import os, json, time, urllib.request, urllib.parse, pandas as pd
T = os.path.expanduser(os.environ.get('FM_T', '~/cricket-project/t20')); OA = T + '/output/markets/odds/oa/'; os.makedirs(OA, exist_ok=True)
K = (os.environ.get('ODDSAPI_KEY') or open(T + '/secrets/oddsapi.txt').read()).strip()   # 15 Nov: env first (GitHub Actions secret), file on the Mac
SPORTS = ['cricket_odi', 'cricket_big_bash', 'cricket_international_t20', 'cricket_t20_blast', 'cricket_ipl', 'cricket_psl', 'cricket_caribbean_premier_league', 'cricket_the_hundred']
POINTS = [(24*60, 90), (6*60, 45), (60, 20), (10, 6), (0, 4)]   # (minutes before start, tolerance in minutes)
ST = OA + 'state.json'
DROP = {'cricket_test_match'}   # 15 Nov: BOOK-B-FWD amendment (coordinator 10:10): Tests have no Pinnacle there (0 of 24), unscoreable; rule unchanged
def call(path, q):
    q = dict(q); q['apiKey'] = K; r = urllib.request.urlopen('https://api.the-odds-api.com/v4/' + path + '?' + urllib.parse.urlencode(q), timeout=30)
    return json.loads(r.read()), int(r.headers.get('x-requests-remaining', 0) or 0)
def run():
    s = json.load(open(ST)) if os.path.exists(ST) else {'events_at': {}, 'taken': {}, 'remaining': 500, 'active': [], 'active_at': 0}
    now = pd.Timestamp.now(tz='UTC'); out = []
    if time.time() - s.get('active_at', 0) > 6*3600:   # the sports list is free
        d, _ = call('sports', {}); s['active'] = [x['key'] for x in d if (x['key'] in SPORTS or x['key'].startswith('cricket_')) and x['key'] not in DROP and x.get('active')]; s['active_at'] = time.time()   # 15 Nov: any cricket competition it adds (an ILT20 key, say)
    for sp in [x for x in s['active'] if x not in DROP]:
        ev_f = OA + f'events_{sp}.json'
        if time.time() - s['events_at'].get(sp, 0) > 3600:
            try: ev, _ = call(f'sports/{sp}/events', {}); json.dump(ev, open(ev_f, 'w')); s['events_at'][sp] = time.time()
            except Exception: ev = json.load(open(ev_f)) if os.path.exists(ev_f) else []
        else: ev = json.load(open(ev_f)) if os.path.exists(ev_f) else []
        due = []
        for e in ev:
            mins = (pd.Timestamp(e['commence_time']) - now).total_seconds() / 60
            for p, tol in POINTS:
                key = f"{e['id']}|{p}"
                if key not in s['taken'] and abs(mins - p) <= tol: due.append(key)
        if not due or s.get('remaining', 0) < 22: continue
        try: d, rem = call(f'sports/{sp}/odds', {'regions': 'uk,eu', 'markets': 'h2h', 'oddsFormat': 'decimal'})
        except Exception as x: print('oa_collect error', sp, type(x).__name__); continue
        s['remaining'] = rem
        for k in due: s['taken'][k] = now.isoformat()
        with open(OA + 'snaps.jsonl', 'a') as fo:
            for e in d:
                books = {b['key']: {o['name']: o['price'] for m in b['markets'] if m['key'] == 'h2h' for o in m['outcomes']} for b in e['bookmakers']}
                fo.write(json.dumps(dict(ts=now.isoformat(), sport=sp, id=e['id'], start=e['commence_time'], home=e['home_team'], away=e['away_team'],
                                         mins=round((pd.Timestamp(e['commence_time']) - now).total_seconds() / 60, 1), books=books)) + '\n')
        out.append(f'{sp}: {len(d)} events, {len(due)} points due, {rem} credits left')
    json.dump(s, open(ST, 'w'))
    print('oa_collect:', '; '.join(out) if out else 'nothing due', flush=True)
if __name__ == '__main__': run()
