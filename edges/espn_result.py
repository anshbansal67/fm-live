"""15 Nov (lane 2): match results from ESPN's public scoreboard (no login, standard library), for scoring picks where the Mac's Betfair
settlement isn't available (the GitHub Actions job; LAPTOP_PROOF.md). result(team, opp, start, tournament) -> 1.0 won, 0.0 lost, None
(not finished, no result, abandoned, or not found). Cached per league/day in output/markets/live/espn_sb/.
  python3 espn_result.py "<team>" "<opp>" <start ISO> "<tournament>"      (a quick check)"""
import os, re, sys, json, time, difflib, urllib.request, datetime as dt
T = os.path.expanduser(os.environ.get('FM_T', '~/cricket-project/t20')); C = T + '/output/markets/live/espn_sb/'
LEAGUE = {'ilt20': '20921', 'big bash league': '8044', 'bbl': '8044', 'sa20': '21275', 'bangladesh premier league': '8653', 'bpl': '8653',
          'super smash': '8654', 'nepal premier league': '23081', 'syed mushtaq ali trophy': '8661'}
SB = 'https://site.api.espn.com/apis/site/v2/sports/cricket/{lg}/scoreboard?dates={d}'
nm = lambda s: ' '.join(re.sub(r'[^a-z ]', ' ', re.sub(r'\(.*?\)', ' ', str(s).lower())).split())
same = lambda a, b: nm(a) == nm(b) or nm(a) in nm(b) or nm(b) in nm(a) or difflib.SequenceMatcher(None, nm(a), nm(b)).ratio() >= 0.8
def league_of(tournament):
    t = nm(tournament)
    for k, v in LEAGUE.items():
        if k in t: return v
    return None
def board(lg, day):
    os.makedirs(C, exist_ok=True); f = C + f'{lg}_{day}.json'
    if os.path.exists(f) and time.time() - os.path.getmtime(f) < 1800: return json.load(open(f))
    try:
        j = json.loads(urllib.request.urlopen(urllib.request.Request(SB.format(lg=lg, d=day), headers={'User-Agent': 'Mozilla/5.0'}), timeout=30).read())
    except Exception: return json.load(open(f)) if os.path.exists(f) else {}
    json.dump(j, open(f, 'w')); return j
def result(team, opp, start, tournament):
    lg = league_of(tournament)
    if not lg: return None
    st = dt.datetime.fromisoformat(str(start).replace('Z', '+00:00'))
    for d in sorted({(st + dt.timedelta(days=k)).strftime('%Y%m%d') for k in (-1, 0, 1)}):
        for e in board(lg, d).get('events', []):
            c = (e.get('competitions') or [{}])[0]; cs = c.get('competitors') or []
            if len(cs) != 2: continue
            nms = [(x.get('team') or {}).get('displayName', '') for x in cs]
            try: es = dt.datetime.fromisoformat(str(e.get('date')).replace('Z', '+00:00'))
            except Exception: continue
            if abs((es - st).total_seconds()) > 6 * 3600: continue
            i = 0 if same(nms[0], team) and same(nms[1], opp) else 1 if same(nms[1], team) and same(nms[0], opp) else None
            if i is None: continue
            stt = ((c.get('status') or e.get('status') or {}).get('type') or {})
            if not (stt.get('completed') is True or stt.get('state') == 'post'): return None
            w = [str(x.get('winner')).lower() == 'true' for x in cs]   # ESPN sends 'true' / 'false' as strings
            return None if not any(w) else (1.0 if w[i] else 0.0)
    return None
if __name__ == '__main__': print(result(*sys.argv[1:5]))
