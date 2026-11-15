import datetime as dt, pytest
from fm_edges import prices, rule, clv, mapping, feeds, health

def test_novig_even():
    assert prices.novig(1.90, 1.90) == pytest.approx((0.5, 0.5))
def test_novig_sums_to_one():
    a, b = prices.novig(1.5, 2.8); assert a + b == pytest.approx(1) and a > b
def test_margin():
    assert prices.margin(1.90, 1.90) == pytest.approx(0.05263, abs=1e-4)
def test_best_uk_ignores_non_uk():
    assert prices.best_uk({'pinnacle': (2.5, 1.6), 'bet365': (2.0, 1.8), 'williamhill': (2.1, 1.7)}, 0) == ('williamhill', 2.1)
def test_best_uk_none():
    assert prices.best_uk({'pinnacle': (2.0, 2.0)}, 0) == (None, None)

BOOKS = {'pinnacle': (1.95, 1.95), 'williamhill': (2.12, 1.75), 'bet365': (2.0, 1.8)}
def test_rule_picks_side_over_threshold():
    p = rule.picks(BOOKS, 24, 'B'); assert len(p) == 1 and p[0]['side'] == 0 and p[0]['book'] == 'williamhill'
    assert p[0]['gap'] == pytest.approx(0.06, abs=1e-3) and not p[0]['suspect']
def test_rule_threshold_edge():
    b = {'pinnacle': (2.0, 2.0), 'bet365': (2.062, 1.9)}          # 2.062 x 0.5 = 1.031 -> pick
    assert len(rule.picks(b, 24, 'B')) == 1
    b['bet365'] = (2.058, 1.9); assert rule.picks(b, 24, 'B') == []  # 1.029 -> no pick
def test_rule_window():
    assert rule.picks(BOOKS, 11.9, 'B') == [] and rule.picks(BOOKS, 48.1, 'B') == []
    assert rule.picks(BOOKS, 0.5, 'BT') and rule.picks(BOOKS, 0.7, 'BT') == []
def test_rule_needs_pinnacle():
    assert rule.picks({'bet365': (3.0, 1.4)}, 24, 'B') == []
def test_rule_suspect():
    assert rule.picks({'pinnacle': (2.0, 2.0), 'coral': (2.4, 1.6)}, 24, 'B')[0]['suspect']

def test_clv():
    assert clv.clv(2.10, 0.5) == pytest.approx(0.05)
def test_summary():
    s = clv.summary([0.1, -0.1, None, 0.3]); assert s['n'] == 3 and s['mean'] == pytest.approx(0.1) and s['beat'] == pytest.approx(2 / 3)
def test_summary_empty():
    assert clv.summary([])['n'] == 0
def test_verdict():
    assert clv.verdict([0.05, 0.04, 0.06, 0.05] * 50) and not clv.verdict([0.05, 0.04] * 50)   # 200 passes, 100 doesn't
    assert not clv.verdict([0.3, -0.3] * 100)
def test_units():
    assert clv.units([(2.0, True), (3.0, False)]) == pytest.approx(0)

def test_nm_and_same():
    assert mapping.nm('Hyderabad (India)') == 'hyderabad' and mapping.same('Melbourne Stars', 'Melbourne Stars Men')
    assert not mapping.same('Perth Scorchers', 'Sydney Sixers')
@pytest.mark.parametrize('t,lg', [('ILT20', '20921'), ('International League T20', '20921'), ('SA20', '21275'), ('Big Bash League', '8044'),
                                  ('WBBL', None), ("Women's Big Bash League", None), ('Syed Mushtaq Ali Trophy', '8661'), ('IPL', '8048'), ('Pakistan Super League', '8679'), ("Women's Premier League", None), ('T20I', None)])   # IPL / PSL joined 15 Nov 17:20
def test_league_of(t, lg):
    assert mapping.league_of(t) == lg

def test_free_picks_hides_future():
    now = dt.datetime(2026, 11, 21, 12, tzinfo=dt.timezone.utc)
    P = [dict(start='2026-11-21T10:00:00Z', pick='A'), dict(start='2026-11-21T14:30:00Z', pick='B')]
    f = feeds.free_picks(P, now); assert [p['pick'] for p in f['picks']] == ['A'] and f['pending'] == 1
def test_win_gate():
    assert feeds.win_gate(0.6, False) is None and feeds.win_gate(0.6, True) == 0.6 and feeds.win_gate(0.6, True, 0.5) == pytest.approx(0.55)

def test_health():
    assert health.overall({'a': ('OK', ''), 'b': ('WARN', '')}) == 'WARN' and health.overall({'a': ('FAIL', '')}) == 'FAIL'
    assert health.since({'status': 'WARN', 'since': 't0'}, 'WARN', 't1') == 't0' and health.since({'status': 'OK', 'since': 't0'}, 'WARN', 't1') == 't1'

def test_kill_switch(tmp_path, monkeypatch):
    from fm_edges import switch
    monkeypatch.delenv('EDGES_KILL', raising=False); (tmp_path / 'output/markets/live').mkdir(parents=True)
    assert not switch.killed(str(tmp_path))
    (tmp_path / 'output/markets/live/EDGES_KILL').write_text('')
    assert switch.killed(str(tmp_path))
    with pytest.raises(SystemExit): switch.stop_if_killed('x', str(tmp_path))
    (tmp_path / 'output/markets/live/EDGES_KILL').unlink(); monkeypatch.setenv('EDGES_KILL', '1'); assert switch.killed(str(tmp_path))

@pytest.mark.parametrize('outcome,team,res', [
    ({'winner': 'A', 'by': {'runs': 10}}, 'A', 'won'), ({'winner': 'B', 'by': {'wickets': 3}}, 'A', 'lost'),
    ({'winner': 'A', 'by': {'runs': 4}, 'method': 'D/L'}, 'A', 'won'),                    # DLS: the official winner
    ({'result': 'tie', 'eliminator': 'B'}, 'A', 'lost'), ({'result': 'tie', 'eliminator': 'A'}, 'A', 'won'),   # super over
    ({'result': 'tie'}, 'A', 'dead heat'), ({'result': 'no result'}, 'A', 'void'), ({}, 'A', 'void')])
def test_settle(outcome, team, res):
    from fm_edges import settle
    assert settle.from_cricsheet(outcome, team) == res
def test_settle_units():
    from fm_edges import settle
    assert settle.units(2.2, 'won') == pytest.approx(1.2) and settle.units(2.2, 'lost') == -1 and settle.units(2.2, 'void') == 0
    assert settle.units(2.2, 'dead heat') == pytest.approx(0.1)
