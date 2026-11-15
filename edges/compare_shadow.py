"""15 Nov (lane 2, coordinator 13:50 item 2): shadow comparison, cloud v Mac, one for one, without making anything new public.
Runs INSIDE the shadow workflow: the cloud's would-be picks (work/output/markets/live/early_picks.jsonl, private cache) against the Mac's
published picks (fm-live picks.json, public already). Writes fm-live/shadow_compare.json with COUNTS for everything, and pick-level detail
only for picks whose match has started (those are public on the Mac side by then anyway). Nothing about a cloud-only future pick is shown.
  key = (picked team, opponent, start hour UTC); arms compared: those the Mac publishes (picks.json rows).
  python3 compare_shadow.py [--cloud path] [--mac path] [--out path]"""
import os, sys, json, re, datetime as dt
T = os.path.expanduser(os.environ.get('FM_T', '~/cricket-project/t20')); a = sys.argv[1:]
arg = lambda k, d: a[a.index(k) + 1] if k in a else d
CL = arg('--cloud', T + '/output/markets/live/early_picks.jsonl'); MC = arg('--mac', os.path.join(os.environ.get('FM_LIVE_DIR', '.'), 'picks.json'))
OUT = arg('--out', os.path.join(os.environ.get('FM_LIVE_DIR', '.'), 'shadow_compare.json'))
now = dt.datetime.now(dt.timezone.utc)
nm = lambda s: re.sub(r'[^a-z]', '', str(s).lower())
def ts(s): return dt.datetime.fromisoformat(str(s).replace('Z', '+00:00'))
def hr(s): return ts(s).strftime('%Y-%m-%dT%H')
since = ts(os.environ.get('SHADOW_SINCE', '2026-11-23T00:00:00Z'))   # compare only from the shadow start
cloud = [json.loads(l) for l in open(CL)] if os.path.exists(CL) else []
mac = (json.load(open(MC)).get('picks') or []) if os.path.exists(MC) else []
mac = [p for p in mac if 'pick' in p and ts(p['posted'] if p['posted'].endswith('Z') else p['posted'] + 'Z') >= since]
C = {}
for r in cloud:
    if ts(r['ts']) < since or not r.get('p_pin'): continue        # published arms are priced off Pinnacle (p_pin); early model tests are not
    C.setdefault((nm(r['team']), nm(r['opp']), hr(r['start'])), r)
M = {}
for p in mac:
    opp = ' v '.join(x for x in p['match'].split(' v ') if x != p['pick'])
    M.setdefault((nm(p['pick']), nm(opp), hr(p['start'])), p)
both, mac_only, cloud_only = [k for k in M if k in C], [k for k in M if k not in C], [k for k in C if k not in M]
started = lambda s: ts(s) <= now
diff = [abs(C[k]['price'] - M[k]['price']) for k in both]
lag = [(ts(C[k]['ts']) - ts(M[k]['posted'] + ('' if M[k]['posted'].endswith('Z') else 'Z'))).total_seconds() / 60 for k in both]
med = lambda x: sorted(x)[len(x) // 2] if x else None
J = dict(asof=now.strftime('%Y-%m-%dT%H:%MZ'), since=since.strftime('%Y-%m-%d'), mac_picks=len(M), cloud_picks=len(C), matched=len(both),
         mac_only=len(mac_only), cloud_only=len(cloud_only), same_book=sum(C[k]['book'] == M[k]['book'] for k in both),
         median_abs_price_diff=None if not diff else round(med(diff), 3), median_minutes_cloud_minus_mac=None if not lag else round(med(lag)),
         detail_started=[dict(match=M[k]['match'] if k in M else f"{C[k]['team']} v {C[k]['opp']}", start=(M.get(k) or C[k])['start'],
                              mac=(dict(book=M[k]['book'], price=M[k]['price']) if k in M else None),
                              cloud=(dict(book=C[k]['book'], price=C[k]['price']) if k in C else None))
                         for k in both + mac_only + cloud_only if started((M.get(k) or C[k])['start'])][-40:],
         note='Counts cover every pick since the shadow start. Detail lists only picks whose match has started. A cloud-only pick still to start is counted, never shown.')
json.dump(J, open(OUT, 'w'), indent=1)
print(f"shadow compare: mac {len(M)}, cloud {len(C)}, matched {len(both)}, mac only {len(mac_only)}, cloud only {len(cloud_only)}")
