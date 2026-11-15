"""14 Nov, rewired 15 Nov (lane 2) — NOT LIVE. Members' email alerts = the arm B / BT picks (early_picks.jsonl: the registered rule, the same rows
as the public record and the Telegram channel), posted to fine-margins.com/api/pro/alert (secret header; the site emails Pro members via Resend).
Was: every new value flag on the board. Payload shape unchanged ({'items': [{match, comp, start, outcome, book, odds, fair_odds, gap}]}), so the
site's email template needs no change. Each pick once, never after the start (output/markets/live/pro_alerted.json).
The recorder calls this only when secrets/pro_live.flag exists (Ansh's go-ahead); the secret is secrets/pro_alert.txt (= Vercel PRO_ALERT_SECRET).
  python3 pro_alerts.py [--dry]"""
import os, sys, json, urllib.request, datetime as dt
T = os.path.expanduser(os.environ.get('FM_T', '~/cricket-project/t20')); LV = T + '/output/markets/live/'
BOOK = {'bet365': 'bet365', 'williamhill': 'William Hill', 'paddypower': 'Paddy Power', 'betfred': 'Betfred', 'unibet': 'Unibet', 'ladbrokes': 'Ladbrokes',
        'coral': 'Coral', 'betway': 'Betway', '888sport': '888sport', 'skybet': 'Sky Bet', 'betvictor': 'BetVictor', 'boylesports': 'BoyleSports'}
LIVE = os.path.exists(T + '/secrets/pro_live.flag') or os.environ.get('PRO_LIVE') == '1'   # 15 Nov: its own switch, now that the toss poll calls it too
if not LIVE and '--dry' not in sys.argv: print('pro alerts: off'); sys.exit(0)
P = [json.loads(l) for l in open(LV + 'early_picks.jsonl')] if os.path.exists(LV + 'early_picks.jsonl') else []
sf = LV + 'pro_alerted.json'; seen = set(json.load(open(sf))) if os.path.exists(sf) else set()
now = dt.datetime.now(dt.timezone.utc); new = []; keys = []
for p in P:
    k = f"{p['fixture_id']}|{p['side']}|{p['arm']}"
    if p.get('arm') not in ('B', 'BT') or not p.get('p_pin') or k in seen: continue
    if dt.datetime.fromisoformat(p['start'].replace('Z', '+00:00')) <= now: seen.add(k); continue
    new.append(dict(match=f"{p['team']} v {p['opp']}", comp=p['tournament'], start=p['start'], outcome=p['team'], book=BOOK.get(p['book'], p['book']),
                    odds=p['price'], fair_odds=round(1 / p['p_pin'], 2), gap=round(p['price'] * p['p_pin'] - 1, 4), check=bool(p.get('suspect')))); keys.append(k)
if not new: print('pro alerts: nothing new'); sys.exit(0)
if '--dry' in sys.argv: print('pro alerts (dry):', json.dumps(new)); sys.exit(0)
sec = (os.environ.get('PRO_ALERT_SECRET') or open(T + '/secrets/pro_alert.txt').read()).strip()
req = urllib.request.Request('https://www.fine-margins.com/api/pro/alert', data=json.dumps({'items': new}).encode(), headers={'Content-Type': 'application/json', 'x-alert-secret': sec}, method='POST')
try: r = json.loads(urllib.request.urlopen(req, timeout=60).read()); print('pro alerts:', len(new), 'new ->', r)
except Exception as x: print('pro alerts failed:', type(x).__name__); sys.exit(1)
json.dump(sorted(seen | set(keys)), open(sf, 'w'))
