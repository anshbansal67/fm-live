"""Matching names across sources (team names, competitions)."""
import re, difflib
LEAGUE = {'ilt20': '20921', 'international league t20': '20921', 'big bash league': '8044', 'bbl': '8044', 'sa20': '21275',
          'bangladesh premier league': '8653', 'bpl': '8653', 'super smash': '8654', 'nepal premier league': '23081', 'syed mushtaq ali trophy': '8661',
          'indian premier league': '8048', 'ipl': '8048', 'pakistan super league': '8679', 'psl': '8679'}
# 15 Nov 17:20 (coordinator): IPL and PSL joined the board. ESPN probe (fast 4313): 8679 = PSL (an April 2026 match found); 8048 is named
# 'Indian Premier League' but returned no events for April 2025 or 2026, so IPL results may sit under a per-season id (as BBL / ILT20 do):
# check against ESPN's upcoming list before March. T20Is have no single ESPN league: they settle on the Mac (Betfair) and from Cricsheet.

def nm(s):
    """Lower-case letters and single spaces, bracketed bits removed. nm('Hyderabad (India)') -> 'hyderabad'."""
    return ' '.join(re.sub(r'[^a-z ]', ' ', re.sub(r'\(.*?\)', ' ', str(s).lower())).split())

def same(a, b):
    """Same team? Equal, one inside the other, or 0.8+ similar after nm()."""
    a, b = nm(a), nm(b)
    return a == b or a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() >= 0.8

def league_of(tournament):
    """Competition name -> ESPN league id, or None. Women's / WBBL never map to a men's board; digits are kept (ILT20, SA20)."""
    t = ' '.join(re.sub(r'[^a-z0-9 ]', ' ', str(tournament).lower()).split())
    if re.search(r'\bwbbl\b|\bwomen|\bw\b', t): return None
    for k, v in LEAGUE.items():
        if k in t: return v
    return None
