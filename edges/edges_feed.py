"""15 Nov (lane 2): the two feeds behind the /edges page, so members' numbers never reach a free visitor's browser.
In: output/markets/live/value_board.json (value_board.py), edges_players.json (lane 1), edges_teams.json (lane 3); missing files = empty.
Out: edges_member.json = {board, players, teams} as they are; edges_free.json = the same with only what the free view shows:
fair prices and chances, the number of UK prices above fair per match (not which book or by how much), each side's model win chance and
median first-innings total, the top 3 batters (runs, 30+, 50+) and top 3 bowlers (wickets, 2+) per match.   python3 edges_feed.py"""
import os, json, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))); from fm_edges import feeds as _F   # 15 Nov: what the free view may show lives in fm_edges
T = os.path.expanduser(os.environ.get('FM_T', '~/cricket-project/t20')); LV = T + '/output/markets/live/'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))); from fm_edges.switch import stop_if_killed; stop_if_killed('edges_feed')   # 15 Nov: the kill switch, checked first
ld = lambda f: json.load(open(LV + f)) if os.path.exists(LV + f) else None
def free_board(b):
    if not b: return b
    return dict(asof=b.get('asof'), n_value=b.get('n_value'), note=b.get('note'),
                events=[dict(match=e['match'], comp=e['comp'], start=e['start'], priced_at=e.get('priced_at'), value=e.get('value'),
                             outcomes=[dict(outcome=o['outcome'], fair_prob=o['fair_prob'], fair_odds=o['fair_odds']) for o in e['outcomes']]) for e in b.get('events', [])])

# 15 Nov (coordinator 18:58, CAP 16): this feed sits beside odds and value alerts, so it's a gambling marketing piece: no player under 25
# named in it, free or members'. Ages from data/player_meta.csv (date of birth by Cricsheet id). Fails closed: a player whose age can't be
# found is left out too. FM_MIN_AGE=0 switches it off (tests only).
MIN_AGE = int(os.environ.get('FM_MIN_AGE', '25'))
def _ages():
    import csv, datetime as _d
    f = os.path.join(T, 'data/player_meta.csv'); A = {}; today = _d.date.today()
    if not os.path.exists(f): return A
    for r in csv.DictReader(open(f)):
        try: b = _d.date.fromisoformat(r['dob']); A[r['cricsheet_id']] = today.year - b.year - ((today.month, today.day) < (b.month, b.day))
        except Exception: pass
    return A
def cap16(p):
    if not p or not MIN_AGE: return p
    A = _ages(); dropped = 0
    for m in p.get('matches', []):
        ids = {x.get('name'): x.get('id') for sd in (m.get('sides') or []) for k in ('bat', 'bowl') for x in (sd.get(k) or [])}
        ok = lambda nm, i=None: (A.get(i or ids.get(nm)) or 0) >= MIN_AGE
        n0 = len(m.get('players') or [])
        m['players'] = [x for x in (m.get('players') or []) if ok(x.get('name'), x.get('id'))]; dropped += n0 - len(m['players'])
        for sd in (m.get('sides') or []):
            for k in ('bat', 'bowl'):
                if sd.get(k): sd[k] = [x for x in sd[k] if ok(x.get('name'), x.get('id'))]
    p['cap16'] = f'players under {MIN_AGE} (or of unknown age) left out: this feed sits beside odds'; p['cap16_dropped'] = dropped
    return p
def free_players(p):
    if not p: return p
    out = []
    for m in p.get('matches', []):
        ps = m.get('players') or []
        bat = sorted([x for x in ps if x.get('exp_runs') is not None], key=lambda x: -x['exp_runs'])[:3]
        bowl = sorted([x for x in ps if x.get('exp_wkts') is not None], key=lambda x: -x['exp_wkts'])[:3]
        keep = {id(x) for x in bat + bowl}
        # 15 Nov fix: 'sides' carries every batter and bowler (members' data); the free feed keeps only each side's XI source and accuracy
        out.append(dict({k: v for k, v in m.items() if k not in ('players', 'sides')},
                        sides=[{k: sd.get(k) for k in ('team', 'xi_from', 'xi_accuracy', 'xi_note')} for sd in (m.get('sides') or [])],
                        players=[dict(name=x.get('name'), team=x.get('team'),
                                      **({'exp_runs': x.get('exp_runs'), 'p30': x.get('p30'), 'p50': x.get('p50')} if x in bat else {}),
                                      **({'exp_wkts': x.get('exp_wkts'), 'p2w': x.get('p2w')} if x in bowl else {})) for x in ps if id(x) in keep]))
    return dict(asof=p.get('asof'), matches=out)
def free_teams(t):
    if not t: return t
    return dict(asof=t.get('asof'), matches=[dict({k: m.get(k) for k in ('match', 'teams', 'start', 'comp', 'label', 'xi_from', 'preview', 'win_note') if k in m},   # free: names and label only (no sixes, venue factors)
                sides=[dict(team=s.get('team'), win=s.get('win'), xi_from=s.get('xi_from'), first_innings_basis=s.get('first_innings_basis'), first_innings={'median': (s.get('first_innings') or {}).get('median')} if s.get('first_innings') else None)
                       for s in m.get('sides') or []]) for m in t.get('matches', [])])
def upcoming(f, now):   # 15 Nov: cards for matches already started (or past) are dropped; the board itself only holds the next 72 h
    if not f: return f
    import datetime as dt
    keep = []
    for m in f.get('matches', []):
        try: st = dt.datetime.fromisoformat(str(m.get('start')).replace('Z', '+00:00'))
        except Exception: continue
        if now < st <= now + dt.timedelta(days=4): keep.append(m)
    return dict(f, matches=keep)
if __name__ == '__main__':
    import datetime as dt; now = dt.datetime.fromisoformat(os.environ['EDGES_NOW'].replace('Z', '+00:00')) if os.environ.get('EDGES_NOW') else dt.datetime.now(dt.timezone.utc)   # EDGES_NOW: dry runs only
    p_raw, t_raw = ld('edges_players.json'), ld('edges_teams.json')
    if p_raw and t_raw:   # 15 Nov: a player card without a start borrows the start of the team card for the same event / teams
        ts_ = {}
        for m in t_raw.get('matches', []):
            if m.get('start'): ts_[str(m.get('espn_event') or '')] = m['start']; ts_['|'.join(sorted(m.get('teams') or []))] = m['start']
        for m in p_raw.get('matches', []):
            if not m.get('start'): m['start'] = ts_.get(str(m.get('espn_event') or '')) or ts_.get('|'.join(sorted(m.get('teams') or [])))
    b, p, t = ld('value_board.json'), cap16(upcoming(p_raw, now)), upcoming(t_raw, now)
    WS = ld('win_shown.json') or {}   # 15 Nov (coordinator 12:45): the model's win chance only where it beat a coin flip in the backtest (lane 1's win_shown.json)
    if t:
        import re as _re
        for m in t.get('matches', []):
            e_ = (WS.get('leagues') or {}).get(str(m.get('pool') or ''), {}); shown = bool(e_.get('win_shown', WS.get('default_shown', False)))
            k_ = e_.get('k')
            for sd in m.get('sides') or []:
                if sd.get('win') is None: continue
                sd['win'] = _F.win_gate(sd['win'], shown, k_)
            if not shown:
                m['win_note'] = m.get('win_note') or WS.get('too_close_text', 'too close to call on our numbers')   # lane 3's own note first
                if m.get('preview'): m['preview'] = ' '.join(x for x in _re.split(r'(?<=[.!?])\s+', m['preview']) if '%' not in x)   # drop the win-chance sentence
    # 15 Nov (coordinator 10:30, launch shape): members get every pick before the start; the free view gets each pick once its match has
    # started (with close and CLV as they arrive), plus only the NUMBER of picks still to start.
    pk = ld('picks_member.json') or ld('picks.json') or {}; P = pk.get('picks', [])   # 15 Nov: full picks (commit-reveal keeps picks.json's upcoming ones hidden)
    started = lambda x: dt.datetime.fromisoformat(str(x.get('start')).replace('Z', '+00:00')) <= now
    pk_free = dict(summary=pk.get('summary'), **_F.free_picks(P, now))
    # 15 Nov (coordinator 14:25 item 5): lane 1's season ratings, free view: rank and net runs per side (model), win only where win_shown allows
    SR = ld('season_ratings.json') or {}; WS_ = ld('win_shown.json') or {}
    def _shown(pool): e_ = (WS_.get('leagues') or {}).get(pool, {}); return bool(e_.get('win_shown', WS_.get('default_shown', False)))
    season = dict(asof=SR.get('asof'), pools={pool: dict(asof=v.get('asof'), fixtures=v.get('fixtures'), win_shown=_shown(pool),
                  teams=[dict(team=tm, rank=x.get('rank'), net_runs=x.get('net_runs'), **({'win': x.get('win')} if _shown(pool) else {}))
                         for tm, x in sorted((v.get('teams') or {}).items(), key=lambda kv: kv[1].get('rank') or 99)])
                  for pool, v in (SR.get('pools') or {}).items()})
    json.dump(dict(board=b, players=p, teams=t, picks=dict(summary=pk.get('summary'), picks=P, pending=0), season=season), open(LV + 'edges_member.json', 'w'), separators=(',', ':'))
    json.dump(dict(board=free_board(b), players=free_players(p), teams=free_teams(t), picks=pk_free, season=season), open(LV + 'edges_free.json', 'w'), separators=(',', ':'))
    print(f"edges feeds: {len((b or {}).get('events', []))} board matches, {len((p or {}).get('matches', []))} player cards, {len((t or {}).get('matches', []))} team cards")
