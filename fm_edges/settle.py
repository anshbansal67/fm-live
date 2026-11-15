"""How a match-winner pick is settled (15 Nov, coordinator 15:40 item 18). The record follows UK bookmakers' usual match-odds rules:
- a winner on the field, including by DLS (rain-revised target), counts as that side's win;
- a tie decided by a SUPER OVER: the super-over winner counts (match odds include the super over);
- a tie with no super over (or a tied super over with no further decider): DEAD HEAT, half the stake on each side: result 'dead heat',
  profit at 1 unit = (price - 1) / 2 - 1 / 2;
- NO RESULT / abandoned (no winner): VOID, stake returned, profit 0; the pick still counts for CLV (the price was posted).
CLV never depends on the result: it is scored on the price and the close only."""

def from_cricsheet(outcome, side_team):
    """Cricsheet info.outcome -> 'won' / 'lost' / 'dead heat' / 'void' for the team picked."""
    o = outcome or {}
    if o.get('winner'): return 'won' if o['winner'] == side_team else 'lost'
    if o.get('eliminator'): return 'won' if o['eliminator'] == side_team else 'lost'    # super over (Cricsheet: result 'tie', eliminator)
    if o.get('result') == 'tie': return 'dead heat'
    return 'void'                                                                      # 'no result', abandoned, or missing

def units(price, result):
    """Profit at 1 unit a pick for a settled result."""
    return {'won': price - 1, 'lost': -1.0, 'dead heat': (price - 1) / 2 - 0.5, 'void': 0.0}[result]
