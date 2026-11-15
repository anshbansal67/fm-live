"""Fixture mapping for the new seasons (15 Nov, coordinator 15:40 item 19). Every team-name variant seen in Cricsheet, ESPN, OddsPapi
and the-odds-api for ILT20, SA20, BBL and BPL (collected 15 Nov), plus generated variants (case, 'Men', brackets, apostrophes), must
match exactly ONE current team, and placeholders must match none. A season can't start with an unmapped or ambiguous team."""
import itertools, pytest
from fm_edges.mapping import same
TEAMS = {
 'ilt20': ['Abu Dhabi Knight Riders', 'Desert Vipers', 'Dubai Capitals', 'Gulf Giants', 'MI Emirates', 'Sharjah Warriorz'],
 'sa20': ["Durban's Super Giants", 'Joburg Super Kings', 'MI Cape Town', 'Paarl Royals', 'Pretoria Capitals', 'Sunrisers Eastern Cape'],
 'bbl': ['Adelaide Strikers', 'Brisbane Heat', 'Hobart Hurricanes', 'Melbourne Renegades', 'Melbourne Stars', 'Perth Scorchers', 'Sydney Sixers', 'Sydney Thunder'],
 'bpl': ['Chattogram Royals', 'Dhaka Capitals', 'Fortune Barishal', 'Khulna Tigers', 'Noakhali Express', 'Rajshahi Warriors', 'Rangpur Riders', 'Sylhet Titans'],
}
SEEN = {   # as written by each source (15 Nov)
 'ilt20': ['Mi Emirates', 'Sharjah Warriors', 'Sharjah Warriorz', 'Abu Dhabi Knight Riders', 'Gulf Giants', 'Dubai Capitals', 'Desert Vipers'],
 'sa20': ['Durban Super Giants', "Durban's Super Giants", 'Mi Cape Town', 'Joburg Super Kings', 'Sunrisers Eastern Cape', 'Paarl Royals', 'Pretoria Capitals'],
 'bbl': ['Adelaide Strikers', 'Brisbane Heat', 'Melbourne Renegades', 'Perth Scorchers', 'Sydney Sixers', 'Sydney Thunder', 'Hobart Hurricanes', 'Melbourne Stars'],
 'bpl': ['Dhaka Capital', 'Chattogram Royals', 'Fortune Barishal', 'Khulna Tigers', 'Noakhali Express', 'Rajshahi Warriors', 'Rangpur Riders', 'Sylhet Titans'],
}
PLACEHOLDERS = ['TBA', '1st Place', '2nd Place', '3rd Place', '4th Place', 'Winner Qualifier 1', 'Loser Eliminator']
def variants(n):
    yield n; yield n.upper(); yield n.lower(); yield n + ' Men'; yield n + ' (Men)'; yield n.replace("'", ''); yield n.replace("'s", '')
def matches(v, lg): return [t for t in TEAMS[lg] if same(v, t)]
CASES = [(lg, v) for lg in TEAMS for n in set(SEEN[lg] + TEAMS[lg]) for v in variants(n)]
@pytest.mark.parametrize('lg,v', CASES)
def test_every_variant_maps_to_one_team(lg, v):
    m = matches(v, lg); assert len(m) == 1, f'{v!r} -> {m}'
@pytest.mark.parametrize('lg,p', [(lg, p) for lg in TEAMS for p in PLACEHOLDERS])
def test_placeholders_map_to_nothing(lg, p):
    assert matches(p, lg) == [], p
@pytest.mark.parametrize('lg', list(TEAMS))
def test_teams_never_confused(lg):
    for a, b in itertools.combinations(TEAMS[lg], 2): assert not same(a, b), (a, b)
