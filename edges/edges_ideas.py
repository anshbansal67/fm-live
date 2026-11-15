"""15 Nov (lane 2, coordinator 14:30): the record page's "In testing" list -> output/markets/live/edges_ideas.json (public with the page).
Every idea in the edge pipeline with its stage (1 idea, 2 registered test, 3 live paper in public, 4 proven) and its count. Lane 2's
entries are built here; lanes 1 and 3 add theirs by writing output/markets/live/ideas_lane1.json / ideas_lane3.json as a list of
{name, lane, stage, what, n, clv, se, verdict_at, status} (missing files are skipped). Only stage 4 ever reaches members' alerts."""
import os, json, math, datetime as dt
T = os.path.expanduser(os.environ.get('FM_T', '~/cricket-project/t20')); LV = T + '/output/markets/live/'
ld = lambda f: json.load(open(LV + f)) if os.path.exists(LV + f) else None
def stats(P):
    c = [p['clv'] for p in P if p.get('clv') is not None]; n = len(c); m = sum(c) / n if n else None
    se = math.sqrt(sum((x - m) ** 2 for x in c) / (n - 1) / n) if n > 1 else None
    return n, m, se
pk = (ld('picks.json') or {}).get('picks', []); pk = [p for p in pk if 'pick' in p]
t20 = [p for p in pk if not (p.get('why') or '').startswith(('rating', 'team sheet'))]
bbl = [p for p in t20 if 'big bash' in (p.get('competition') or '').lower()]
n, m, se = stats(t20); nb, mb, seb = stats(bbl)
I = [dict(name='Arm B, T20 (the alert record)', lane=2, stage=3, what='UK price at least 3% over Pinnacle\'s fair price, 12-48 h before, or at the toss',
          n=len(t20), scored=n, clv=m, se=se, verdict_at=200, status='live paper: the record above'),
     dict(name='Arm B on BBL (the-odds-api)', lane=2, stage=3, what='the same rule on a second price source, from 12 Dec', n=len(bbl), scored=nb, clv=mb, se=seb,
          verdict_at=200, status='waiting for UK books to price BBL' if not bbl else 'live paper, inside the record above')]
new3 = [p for p in t20 if any(w in (p.get('competition') or p.get('tournament') or '') for w in ('Indian Premier League', 'Pakistan Super League', 'T20 internationals', 'T20I', 'IPL', 'PSL'))]
n3, m3, se3 = stats(new3)
I.append(dict(name='Arm B on the IPL, PSL and T20Is', lane=2, stage=3, what='the same rule on three more competitions (added 15 Nov; the backtest covered IPL and PSL); their picks count towards the 200',
              n=len(new3), scored=n3, clv=m3, se=se3, verdict_at=200, status='shadow until 30 Nov, then live paper inside the record above' if not new3 else 'live paper, inside the record above'))
o = ld('lane3_odi_record.json')
if o: I.append(dict(name='Arm B on ODIs (the-odds-api)', lane=3, stage=3, what='the same rule on one-day internationals', n=o.get('n_picks'), scored=o.get('n_scored'),
                    clv=o.get('clv_mean'), se=o.get('clv_se'), verdict_at=o.get('verdict_at'), status='live paper, its own count'))
# lane 2's finished tests (fixed text, so the Mac and the cloud publish the same list)
I.append(dict(name='Arm B with the gap capped at 10%', lane=2, stage=2, what='the same rule, but only gaps between 3% and 10% (where bets are unlikely to be voided)',
              n=None, clv=None, se=None, verdict_at=60, status='registered 15 Nov; runs once on December prices'))
I.append(dict(name='Stale UK prices after the toss', lane=2, stage=2, what='UK books that haven\'t moved when Pinnacle has, in the last 30 min',
              n=16, clv=0.0693, se=0.0206, verdict_at=60, status='failed its registered test on 15 Nov (16 bets, 60 needed): stays dead'))
I.append(dict(name='First UK quote v Pinnacle', lane=2, stage=2, what='a UK book\'s first price on a fixture against Pinnacle\'s fair price at that moment',
              n=None, clv=None, se=None, verdict_at=100, status='registered 15 Nov; runs once on December prices (new data only)'))
for f in ('ideas_lane1.json', 'ideas_lane3.json'):
    x = ld(f)
    if isinstance(x, list): I += [d for d in x if isinstance(d, dict) and d.get('name')]
J = dict(asof=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'),
         stages={'1': 'Idea', '2': 'Registered test on past prices', '3': 'Live paper, in public', '4': 'Proven: 200+ live picks beating the close by 2 SE'},
         note='Only stage 4 goes into members\' alerts. Nothing is proven yet.', ideas=I)
json.dump(J, open(LV + 'edges_ideas.json', 'w'), indent=1); print('edges ideas:', [(d['name'], d['stage'], d.get('n')) for d in I])
