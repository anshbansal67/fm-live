"""15 Nov (lane 2): a small health file for the Edges chain, for Ansh HQ (hub.json) to show a stall. Reads only local files, no network.
-> output/markets/live/edges_health.json: overall OK / WARN / FAIL, last recorder loop, last fm-live push of picks and of the record,
OddsPapi state (blocked or not, used / limit), the-odds-api credits left, TheRundown key present, lane hook failures in the last hour.
  python3 edges_health.py      (the recorder runs it every loop)"""
import os, re, json, datetime as dt
T = os.path.expanduser(os.environ.get('FM_T', '~/cricket-project/t20')); LV = T + '/output/markets/live/'
now = dt.datetime.now(dt.timezone.utc)
def ts(line):
    m = re.match(r'\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)Z\]', line)
    return dt.datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S').replace(tzinfo=dt.timezone.utc) if m else None
ACTIONS = os.environ.get('FM_ACTIONS') == '1'   # 15 Nov: the cloud job writes actions.log in the recorder's line format ("snapshot:" = one run)
LOGF = LV + ('actions.log' if ACTIONS else 'recorder.log')
L = open(LOGF, errors='replace').read().splitlines()[-30000:] if os.path.exists(LOGF) else []
last = lambda pat: next(((ts(l), l) for l in reversed(L) if re.search(pat, l) and ts(l)), (None, ''))
mins = lambda t: None if t is None else round((now - t).total_seconds() / 60)
loop_t, _ = last(r'snapshot: (\d+ markets|cloud run)'); pk_t, _ = last(r'picks feed: picks feed: pushed'); rec_t, _ = last(r'track record: published')
ep_t, ep = last(r'early picks: '); m = re.search(r'quota (\d+)/(\d+)', ep)
oa = json.load(open(T + '/output/markets/odds/oa/state.json')) if os.path.exists(T + '/output/markets/odds/oa/state.json') else {}
rk = T + '/secrets/therundown.json'; rk_ok = os.path.exists(rk) and 'PASTE' not in open(rk).read()
hook_fail = [l[22:120] for l in L if ts(l) and now - ts(l) < dt.timedelta(hours=1) and re.search(r'(edges_players|oa_odi_picks|oa_odi_eval|edges_teams|edges_teams_record|oa_picks|research_bfair)\.py (failed|error)', l)]
C = {}
# 15 Nov (coordinator 11:50): any gap over 30 min between recorder loops in the last 24 h (a sleeping Mac / shut lid shows on Ansh HQ)
LT = sorted(t for t in (ts(l) for l in L if 'snapshot: ' in l and ('markets' in l or 'cloud run' in l)) if t and now - t < dt.timedelta(hours=24))
GAPS = [(a_, b_) for a_, b_ in zip(LT, LT[1:]) if b_ - a_ > dt.timedelta(minutes=30)]
if LT and now - LT[-1] > dt.timedelta(minutes=30): GAPS.append((LT[-1], now))
lm = mins(loop_t); C['recorder loop'] = ('FAIL' if lm is None or lm > 20 else 'WARN' if lm > 10 else 'OK', f'last loop {lm} min ago' if lm is not None else 'no loop found')
C['gaps over 30 min (24 h)'] = (('FAIL' if GAPS and GAPS[-1][1] == now else 'WARN'), f"{len(GAPS)} gap(s): " + '; '.join(f"{a_:%d %b %H:%M}-{b_:%H:%M} UTC ({round((b_ - a_).total_seconds() / 60)} min)" for a_, b_ in GAPS[-3:])) if GAPS else ('OK', 'no gap over 30 min in the last 24 h')
pm = mins(pk_t); C['picks feed push'] = ('WARN' if pm is None or pm > 150 else 'OK', f'last push to fm-live {pm} min ago' if pm is not None else 'no push found')
rm = mins(rec_t)
if not ACTIONS: C['record push'] = ('WARN' if rm is None or rm > 90 else 'OK', f'last push to fm-live {rm} min ago' if rm is not None else 'no push found')
C['OddsPapi'] = ('FAIL', f"blocked: quota {m.group(1)}/{m.group(2)} (resets monthly)") if 'blocked' in ep else (('OK', f'quota {m.group(1)}/{m.group(2)}') if m else ('WARN', 'no early-picks run found'))
rem = oa.get('remaining'); C['the-odds-api'] = ('FAIL' if rem is not None and rem < 50 else 'WARN' if rem is not None and rem < 100 else 'OK', f'{rem} credits left' if rem is not None else 'no state')   # 15:00 item 7: under 50 -> red
# 15 Nov (coordinator 15:00 item 7): the cloud run missing for 2 h -> red. Read from the public heartbeat in the fm-live checkout (Mac side);
# only once a heartbeat has ever been published, so a cloud that hasn't started yet doesn't show red.
if not ACTIONS:
    hb = os.path.expanduser(os.environ.get('FM_LIVE_DIR', '~/fm-live')) + '/edges_cloud_heartbeat.json'
    if os.path.exists(hb):
        try:
            h = json.load(open(hb)); age = mins(dt.datetime.fromisoformat(str(h.get('ts')).replace('Z', '+00:00')))
            C['cloud run'] = ('FAIL' if age is None or age > 120 else 'OK', f"last cloud run {age} min ago ({h.get('mode')}, {h.get('status')})")
        except Exception: C['cloud run'] = ('WARN', 'heartbeat unreadable')
    else: C['cloud run'] = ('OK', 'no cloud heartbeat yet (not started)')
C['TheRundown'] = ('OK', 'key present') if rk_ok else ('OK', 'no key yet (collector idle)')
C['lane hooks'] = ('WARN', f'{len(hook_fail)} failures in the last hour: ' + '; '.join(hook_fail[-2:])) if hook_fail else ('OK', 'no failures in the last hour')
# 15 Nov (item 17): a refused publish (the record would have shrunk) is red until a good publish clears it
if os.path.exists(LV + 'publish_blocked.json'):
    try: pb = json.load(open(LV + 'publish_blocked.json')); C['picks shrink guard'] = ('FAIL', f"publish refused at {pb.get('ts')}: picks {pb.get('public')} -> {pb.get('new')}; restore the history")
    except Exception: C['picks shrink guard'] = ('FAIL', 'publish refused (picks would shrink)')
import sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))); from fm_edges import health as _H   # 15 Nov: status logic lives in fm_edges
ov = _H.overall(C)
J = dict(ts=now.strftime('%Y-%m-%dT%H:%M:%SZ'), source='cloud' if ACTIONS else 'mac', overall=ov, checks={k: dict(state=a, why=b) for k, (a, b) in C.items()},
         gaps_24h=[dict(start=a_.strftime('%Y-%m-%dT%H:%MZ'), end=b_.strftime('%Y-%m-%dT%H:%MZ'), minutes=round((b_ - a_).total_seconds() / 60)) for a_, b_ in GAPS])
HF = LV + ('edges_health_cloud.json' if ACTIONS else 'edges_health.json')   # cloud and Mac never overwrite each other's file
# Ansh HQ reads two fields only: status (OK / WARN / FAIL) and since (when it last changed), plus a one-line reason.
try: prev = json.load(open(HF))
except Exception: prev = {}
J['status'] = ov; J['since'] = _H.since(prev, ov, J['ts'])
J['reason'] = '; '.join(f'{k}: {v[1]}' for k, v in C.items() if v[0] == ov) if ov != 'OK' else 'all checks OK'
json.dump(J, open(HF + '.tmp', 'w'), indent=1); os.replace(HF + '.tmp', HF)
print('edges health:', ov, '|', '; '.join(f'{k}: {v[0]}' for k, v in C.items()))
