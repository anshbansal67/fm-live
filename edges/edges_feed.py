"""15 Nov (lane 2): the two feeds behind the /edges page, so members' numbers never reach a free visitor's browser.
In: output/markets/live/value_board.json (value_board.py), edges_players.json (lane 1), edges_teams.json (lane 3); missing files = empty.
Out: edges_member.json = {board, players, teams} as they are; edges_free.json = the same with only what the free view shows:
fair prices and chances, the number of UK prices above fair per match (not which book or by how much), each side's model win chance and
median first-innings total, the top 3 batters (runs, 30+, 50+) and top 3 bowlers (wickets, 2+) per match.   python3 edges_feed.py"""
import os, json
T = os.path.expanduser(os.environ.get('FM_T', '~/cricket-project/t20')); LV = T + '/output/markets/live/'
ld = lambda f: json.load(open(LV + f)) if os.path.exists(LV + f) else None
def free_board(b):
    if not b: return b
    return dict(asof=b.get('asof'), n_value=b.get('n_value'), note=b.get('note'),
                events=[dict(match=e['match'], comp=e['comp'], start=e['start'], priced_at=e.get('priced_at'), value=e.get('value'),
                             outcomes=[dict(outcome=o['outcome'], fair_prob=o['fair_prob'], fair_odds=o['fair_odds']) for o in e['outcomes']]) for e in b.get('events', [])])
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
    b, p, t = ld('value_board.json'), upcoming(p_raw, now), upcoming(t_raw, now)
    WS = ld('win_shown.json') or {}   # 15 Nov (coordinator 12:45): the model's win chance only where it beat a coin flip in the backtest (lane 1's win_shown.json)
    if t:
        import re as _re
        for m in t.get('matches', []):
            e_ = (WS.get('leagues') or {}).get(str(m.get('pool') or ''), {}); shown = bool(e_.get('win_shown', WS.get('default_shown', False)))
            k_ = e_.get('k')
            for sd in m.get('sides') or []:
                if sd.get('win') is None: continue
                sd['win'] = (round(0.5 + k_ * (sd['win'] - 0.5), 4) if k_ is not None else sd['win']) if shown else None
            if not shown:
                m['win_note'] = WS.get('too_close_text', 'too close to call on our numbers')
                if m.get('preview'): m['preview'] = ' '.join(x for x in _re.split(r'(?<=[.!?])\s+', m['preview']) if '%' not in x)   # drop the win-chance sentence
    # 15 Nov (coordinator 10:30, launch shape): members get every pick before the start; the free view gets each pick once its match has
    # started (with close and CLV as they arrive), plus only the NUMBER of picks still to start.
    pk = ld('picks_member.json') or ld('picks.json') or {}; P = pk.get('picks', [])   # 15 Nov: full picks (commit-reveal keeps picks.json's upcoming ones hidden)
    started = lambda x: dt.datetime.fromisoformat(str(x.get('start')).replace('Z', '+00:00')) <= now
    pk_free = dict(summary=pk.get('summary'), picks=[x for x in P if started(x)], pending=sum(not started(x) for x in P))
    json.dump(dict(board=b, players=p, teams=t, picks=dict(summary=pk.get('summary'), picks=P, pending=0)), open(LV + 'edges_member.json', 'w'), separators=(',', ':'))
    json.dump(dict(board=free_board(b), players=free_players(p), teams=free_teams(t), picks=pk_free), open(LV + 'edges_free.json', 'w'), separators=(',', ':'))
    print(f"edges feeds: {len((b or {}).get('events', []))} board matches, {len((p or {}).get('matches', []))} player cards, {len((t or {}).get('matches', []))} team cards")
