"""15 Nov (lane 2): free Telegram channel alerts for the value board's registered rule (arms B and BT in early_picks.jsonl).
OFF until BOTH exist: secrets/telegram.json ({"token": "...", "chat": "@channel_or_id"}, pasted by Ansh) and secrets/tg_live.flag (the go-ahead).
Every alert sent is an alert in the public record (same rows as picks.json); each pick is sent once (output/markets/live/tg_sent.json).
  python3 tg_alerts.py           send any new picks (no-op while off)
  python3 tg_alerts.py --dry     print the messages that would go out, send nothing"""
import os, sys, json, urllib.request, urllib.parse, datetime as dt
T = os.path.expanduser(os.environ.get('FM_T', '~/cricket-project/t20')); LV = T + '/output/markets/live/'
BOOK = {'bet365': 'bet365', 'williamhill': 'William Hill', 'paddypower': 'Paddy Power', 'betfred': 'Betfred', 'unibet': 'Unibet', 'ladbrokes': 'Ladbrokes',
        'coral': 'Coral', 'betway': 'Betway', '888sport': '888sport', 'skybet': 'Sky Bet', 'betvictor': 'BetVictor', 'boylesports': 'BoyleSports'}
ARMS = {'B', 'BT'}
RECORD_URL = 'fine-margins.com/t20/record'   # the alert record's public address: set when the coordinator places the page
try:
    from zoneinfo import ZoneInfo; UK = ZoneInfo('Europe/London')
except Exception: UK = dt.timezone.utc
def uk(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(UK).strftime('%a %d %b, %H:%M')
def msg(p):
    fair = 1 / p['p_pin']; gap = p['price'] * p['p_pin'] - 1
    lines = [f"{p['team']} to beat {p['opp']}", f"{p['tournament']} · starts {uk(p['start'])} UK",
             f"{BOOK.get(p['book'], p['book'])} {p['price']:.2f}  ·  fair {fair:.2f}  ·  {100*gap:+.1f}%",
             "At the toss" if p['arm'] == 'BT' else f"Posted {round(p['hrs'])} h before the start"]
    if p.get('suspect'): lines.append('Unusually big gap: check the price is still live before acting on it.')
    lines.append('Fair = Pinnacle without its margin. Every alert is scored on the public record: ' + RECORD_URL + '. A record of a price, not advice. 18+, gamble responsibly.')
    return '\n'.join(lines)
def main():
    dry = '--dry' in sys.argv; sec = T + '/secrets/telegram.json'
    envc = dict(token=os.environ['TELEGRAM_TOKEN'], chat=os.environ['TELEGRAM_CHAT']) if os.environ.get('TELEGRAM_TOKEN') and os.environ.get('TELEGRAM_CHAT') else None   # 15 Nov: Actions secrets
    live = (os.path.exists(T + '/secrets/tg_live.flag') or os.environ.get('TG_LIVE') == '1') and (envc is not None or os.path.exists(sec))
    if not (live or dry): print('telegram alerts: off'); return
    P = [json.loads(l) for l in open(LV + 'early_picks.jsonl')] if os.path.exists(LV + 'early_picks.jsonl') else []
    sf = LV + 'tg_sent.json'; sent = set(json.load(open(sf))) if os.path.exists(sf) else set()
    now = dt.datetime.now(dt.timezone.utc); n = 0
    for p in P:
        k = f"{p['fixture_id']}|{p['side']}|{p['arm']}"
        if p.get('arm') not in ARMS or k in sent or not p.get('p_pin'): continue
        if dt.datetime.fromisoformat(p['start'].replace('Z', '+00:00')) <= now: sent.add(k); continue   # never alert after the start
        if dry: print('---\n' + msg(p)); n += 1; continue
        c = envc or json.load(open(sec))
        try:
            r = urllib.request.urlopen(f"https://api.telegram.org/bot{c['token']}/sendMessage", data=urllib.parse.urlencode({'chat_id': c['chat'], 'text': msg(p), 'disable_web_page_preview': 'true'}).encode(), timeout=20)
            if json.loads(r.read()).get('ok'): sent.add(k); n += 1
        except Exception as x: print('telegram error', type(x).__name__)
    if not dry: json.dump(sorted(sent), open(sf, 'w'))
    print(f"telegram alerts: {n} {'would be sent' if dry else 'sent'}")
if __name__ == '__main__': main()
