"""14 Nov (v2, after the BOOK-EARLY verdict and the quota incident) BOOK-EARLY / BOOK-TOSS LIVE, arm B only (paper; pre-registered MODEL.md):
a UK bookmaker's match-winner price >= 3% above Pinnacle's no-vig price at the same moment. Models A2 / A3 / TS stopped (failed historically).
QUOTA: OddsPapi free = 250 metered requests a month. Prices come ONLY from /v4/historical-odds (does not count, but is refused once the month's 250 are spent; <= 3 bookmakers a call, 5 s cooldown);
fixture lists are metered, so they are cached per tournament and refreshed at most every 3 days, and never when /v4/account (unmetered) shows
request_count >= request_limit - 25.
  python3 early_picks.py            hourly sweep: fixtures 1-48 h out -> snapshot (early_odds.jsonl); B picks 12-48 h out (arm 'B')
  python3 early_picks.py --toss     toss window: fixtures starting within 35 min, polled every 60 s (EP_TOSS_POLL_S) until the start (arm 'BT')
  python3 early_picks.py --dry      no writes"""
import os, re, sys, json, time, urllib.request, urllib.parse, numpy as np, pandas as pd
T = os.path.expanduser(os.environ.get('FM_T', '~/cricket-project/t20')); LV = T + '/output/markets/live/'; OD = T + '/output/markets/odds/'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))); from fm_edges.rule import THRESHOLD, WINDOWS, SUSPECT; from fm_edges.prices import novig as _novig   # 15 Nov: the rule lives in fm_edges
K = (os.environ.get('ODDSPAPI_KEY') or open(T + '/secrets/oddspapi.txt').read()).strip(); SHARP = 'pinnacle'   # 15 Nov: env first (GitHub Actions secret), file on the Mac
UK = {'bet365', 'williamhill', 'paddypower', 'betfred', 'unibet', 'ladbrokes', 'coral', 'betway', '888sport', 'skybet', 'betvictor', 'boylesports'}
GROUPS = ['pinnacle,bet365,williamhill', 'paddypower,betfred,unibet', 'ladbrokes,coral,betway', 'skybet,betvictor,888sport']
TOURN = {38749: 'ILT20', 2478: 'Big Bash League', 21578: 'Super Smash', 38741: 'SA20', 20952: 'Bangladesh Premier League'}   # 15 Nov: SMAT and NPL dropped (Pinnacle never prices them; saves metered calls)
EXCH = {'betfair-ex', 'matchbook'}
_last = {}; ERR = {}; PROPS = []   # 15 Nov (lane 2, for lane 1): player-prop quotes seen in the same responses (no extra calls)
def get(path, p, cool):
    """15 Nov (lane 2): one OddsPapi key is shared by every process (hourly sweep, toss poller, other lanes' probes), so calls are serialised
    through a lock file and the cooldown is kept per endpoint across processes (odds/.oddspapi_last.json); a 429 waits 12 s and retries once."""
    import fcntl
    with open(OD + '.oddspapi.lock', 'a+') as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        lf = OD + '.oddspapi_last.json'
        try: L = json.load(open(lf))
        except Exception: L = {}
        for k in range(2):
            w = cool - (time.time() - max(L.get(path, 0), _last.get(path, 0)))
            if w > 0: time.sleep(w)
            q = dict(p); q['apiKey'] = K; out = None
            try:
                r = urllib.request.urlopen(urllib.request.Request('https://api.oddspapi.io/v4/' + path + '?' + urllib.parse.urlencode(q), headers={'User-Agent': 'fm/1'}), timeout=40)
                out = json.loads(r.read())
            except urllib.error.HTTPError as e: out = {'_err': e.code}
            except Exception: out = None
            _last[path] = L[path] = time.time()
            try: json.dump(L, open(lf, 'w'))
            except Exception: pass
            if isinstance(out, dict) and out.get('_err') == 429 and k == 0: ERR[429] = ERR.get(429, 0) + 1; time.sleep(12); continue
            break
        if isinstance(out, dict) and '_err' in out: ERR[out['_err']] = ERR.get(out['_err'], 0) + 1
        elif out is None: ERR['net'] = ERR.get('net', 0) + 1
        return out
def quota_ok():
    a = get('account', {}, 0.5) or {}
    for s in a.get('subscriptions', []):
        if s.get('is_active'): return s.get('request_count', 0) < s.get('request_limit', 0) - 25, s.get('request_count'), s.get('request_limit')
    return False, None, None
def fixtures(now):
    ok, used, lim = quota_ok(); out = []
    for tid in TOURN:
        f = OD + f'live_fix_{tid}.json'
        stale = (not os.path.exists(f)) or (time.time() - os.path.getmtime(f) > 3*86400)
        if stale and ok:
            d = get('fixtures', {'tournamentId': tid}, 2.2)
            if isinstance(d, list): json.dump(d, open(f, 'w'))
        if not os.path.exists(f) and os.path.exists(OD + f'fix_{tid}.json'): f = OD + f'fix_{tid}.json'   # 15 Nov: quota spent -> the 14 Nov full lists (no metered call)
        if os.path.exists(f): out += [dict(x, _t=TOURN[tid]) for x in json.load(open(f)) if x.get('statusId') == 0 and pd.Timestamp(x['startTime']) > now]
    return out, used, lim
def prices(fid):
    books = {}
    for i, g in enumerate(GROUPS):
        d = get('historical-odds', {'fixtureId': fid, 'bookmakers': g}, 5.3)
        if i == 0 and (not isinstance(d, dict) or '_err' in d or not d.get('bookmakers')): break   # 15 Nov (lane 2): nothing priced yet (Pinnacle's group empty) -> skip the other 3 calls
        if not isinstance(d, dict) or '_err' in d: continue
        for bk, bv in (d.get('bookmakers') or {}).items():
            for mid, mm in (bv.get('markets') or {}).items():   # every market quoted per player (player id != '0'): the newest quote per player outcome
                for oid, oo in ((mm or {}).get('outcomes') or {}).items():
                    for pid, sn in ((oo or {}).get('players') or {}).items():
                        if pid == '0' or not sn: continue
                        z = max(sn, key=lambda x: x.get('createdAt') or '')
                        PROPS.append(dict(fixture_id=fid, book=bk, market=mid, outcome=oid, player_id=pid, price=z.get('price'), limit=z.get('limit'), active=z.get('active'), created=z.get('createdAt'), n_quotes=len(sn)))
            m = (bv.get('markets') or {}).get('271')
            if not m: continue
            pr = []
            for oid in ('271', '272'):
                sn = [x for pl in ((m['outcomes'].get(oid) or {}).get('players') or {}).values() for x in pl if x.get('price')]
                last = max(sn, key=lambda x: x['createdAt']) if sn else None
                pr.append(last['price'] if (last and last.get('active', True)) else None)
            if all(pr): books[bk] = pr
    return books
def sweep(fx, now, lo, hi, arm, dry, seen):
    n = 0
    for x in fx:
        st = pd.Timestamp(x['startTime']); hrs = (st - now).total_seconds() / 3600
        if not (lo <= hrs <= hi): continue
        PROPS.clear(); books = prices(x['fixtureId']); n += 1
        if PROPS and not dry:
            tsn = pd.Timestamp.now(tz='UTC').isoformat()
            with open(LV + 'player_props.jsonl', 'a') as fp_:
                for r_ in PROPS: fp_.write(json.dumps(dict(ts=tsn, tournament=x['_t'], start=x['startTime'], hrs=round(hrs, 2), **r_)) + '\n')
        pin = books.get(SHARP); pnv = None
        if pin: pnv = list(_novig(pin[0], pin[1]))
        teams = [x['participant1Name'], x['participant2Name']]
        if not dry: open(LV + 'early_odds.jsonl', 'a').write(json.dumps(dict(ts=pd.Timestamp.now(tz='UTC').isoformat(), fixture_id=x['fixtureId'], tournament=x['_t'], start=x['startTime'], hrs=round(hrs, 2), teams=teams, pinnacle=pin, p_pin=pnv, books=books, src='historical-odds')) + '\n')
        soft = {k: v for k, v in books.items() if k in UK}
        if not pnv or not soft: continue
        lo_pick, hi_pick = WINDOWS[arm]
        if not (lo_pick <= hrs <= hi_pick): continue
        for side in (0, 1):
            bk = max(soft, key=lambda k: soft[k][side]); best = soft[bk][side]
            if best * pnv[side] >= THRESHOLD and (x['fixtureId'], side, arm) not in seen and (nm_(teams[side]), pd.Timestamp(x['startTime']).floor('h'), arm) not in seen:
                pk = dict(ts=pd.Timestamp.now(tz='UTC').isoformat(), fixture_id=x['fixtureId'], tournament=x['_t'], start=x['startTime'], hrs=round(hrs, 2), arm=arm, side=side,
                          team=teams[side], opp=teams[1-side], book=bk, price=best, p_rating=None, p_pin=pnv[side], nbooks=len(soft), gap=round(best*pnv[side]-1, 4), suspect=bool(best*pnv[side] - 1 > SUSPECT))
                seen.add((x['fixtureId'], side, arm)); seen.add((nm_(teams[side]), pd.Timestamp(x['startTime']).floor('h'), arm)); print(*(('PICK', arm, '(details kept out of the public Actions log)') if os.environ.get('FM_ACTIONS') == '1' else ('PICK', arm, x['_t'], teams[side], '@', best, bk, f'{hrs:.2f}h')), flush=True)
                if not dry: open(LV + 'early_picks.jsonl', 'a').write(json.dumps(pk) + '\n')
    return n
nm_ = lambda s: ' '.join(re.sub(r'[^a-z ]', ' ', str(s).lower()).split())
def seen_picks():   # 15 Nov: also (team, start hour, arm), so a match already picked from the-odds-api (oa_picks.py) is not picked twice
    s = set()
    if os.path.exists(LV + 'early_picks.jsonl'):
        for l in open(LV + 'early_picks.jsonl'): d = json.loads(l); s.add((d['fixture_id'], d['side'], d['arm'])); s.add((nm_(d['team']), pd.Timestamp(d['start']).floor('h'), d['arm']))
    return s
if __name__ == '__main__':
    dry = '--dry' in sys.argv; now = pd.Timestamp.now(tz='UTC'); fx, used, lim = fixtures(now); seen = seen_picks()
    if os.environ.get('EP_MIN_GAP_MIN') and '--toss' not in sys.argv and os.path.exists(LV + 'early_odds.jsonl'):   # 15 Nov: the cloud job runs every 30 min; the sweep stays hourly
        try:
            with open(LV + 'early_odds.jsonl', 'rb') as f_: f_.seek(max(0, os.path.getsize(LV + 'early_odds.jsonl') - 4000)); last_ = f_.read().decode(errors='replace').strip().splitlines()[-1]
            age_ = (now - pd.Timestamp(json.loads(last_)['ts'])).total_seconds() / 60
            if age_ < float(os.environ['EP_MIN_GAP_MIN']): print(f'early_picks: last sweep {age_:.0f} min ago; next one later', flush=True); sys.exit(0)
        except (ValueError, KeyError, IndexError): pass
    if used is not None and lim and used >= lim:   # 15 Nov (lane 2): over the monthly limit OddsPapi answers EVERY endpoint, historical-odds included, with 429 REQUEST_LIMIT_EXCEEDED
        print(f'early_picks: blocked, OddsPapi quota {used}/{lim} (all endpoints 429 until it resets); {len(fx)} fixtures cached, 0 priced', flush=True); sys.exit(0)
    if '--toss' in sys.argv:   # poll every 3 min while any fixture is in its last 35 min
        n = 0
        POLL = int(os.environ.get('EP_TOSS_POLL_S', '60'))   # 15 Nov (coordinator 15:40 item 15): 60 s sweeps (was 180) so detection lag is under a minute
        for k in range(int(36 * 60 / POLL) + 1):
            now = pd.Timestamp.now(tz='UTC'); live = [x for x in fx if 0 < (pd.Timestamp(x['startTime']) - now).total_seconds() / 60 <= 35]
            if not live: break
            sz_ = os.path.getsize(LV + 'early_picks.jsonl') if os.path.exists(LV + 'early_picks.jsonl') else 0
            n += sweep(live, now, 0, 0.6, 'BT', dry, seen)
            # 15 Nov (lane 2, latency): a toss-window pick is only useful if the alert goes out before the start. Send it now, from inside the
            # poll, instead of waiting for the hourly block (Mac) or the next 30-min run (cloud), both usually after the start. Each alert
            # script keeps its own on/off switch; shadow mode sends nothing.
            if not dry and os.environ.get('SHADOW', '0') != '1' and os.path.exists(LV + 'early_picks.jsonl') and os.path.getsize(LV + 'early_picks.jsonl') > sz_:
                # members' page too: picks_member.json (early_eval) and the feeds are otherwise refreshed hourly; the Mac also republishes
                # picks.json (free period: picks are public before the start); the cloud's toss job can't push, so it doesn't
                for c_ in ([os.path.join(os.path.dirname(os.path.abspath(__file__)), 'early_eval.py')] + ([] if os.environ.get('FM_ACTIONS') == '1' else ['--publish']),
                           [os.path.join(os.path.dirname(os.path.abspath(__file__)), 'edges_feed.py')]):
                    try: __import__('subprocess').run([sys.executable] + c_, capture_output=True, text=True, timeout=240)
                    except Exception as x: print('toss refresh error', type(x).__name__, flush=True)
                for a_ in ('tg_alerts.py', 'pro_alerts.py'):
                    try:
                        r_ = __import__('subprocess').run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), a_)], capture_output=True, text=True, timeout=60)
                        print(f'toss alert ({a_}):', (r_.stdout or r_.stderr).strip()[-120:], flush=True)
                    except Exception as x: print('toss alert error', a_, type(x).__name__, flush=True)
            time.sleep(max(0, POLL - (pd.Timestamp.now(tz='UTC') - now).total_seconds()))
        print(f'early_picks --toss: {n} price sweeps; errors {ERR or 0}', flush=True)
    else:
        n = sweep(fx, now, 1, 48, 'B', dry, seen)
        print(f'early_picks: {len(fx)} upcoming fixtures cached, {n} priced (historical-odds, unmetered); quota {used}/{lim}; errors {ERR or 0}', flush=True)
