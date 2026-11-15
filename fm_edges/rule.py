"""The registered pick rule (arm B / BT), exactly as early_picks.py applies it."""
from .prices import novig, best_uk, SHARP
THRESHOLD = 1.03              # best UK price x Pinnacle fair chance must reach this
WINDOWS = {'B': (12, 48), 'BT': (0, 0.6)}   # hours before the start
SUSPECT = 0.10                # gaps above 10% are flagged "check the price is still live"

def gap(price, p_fair):
    """price x fair chance - 1: how far a price sits above fair. gap(2.10, 0.5) -> 0.05."""
    return price * p_fair - 1

def picks(books, hours_before, arm):
    """books: {book: (p0, p1)} at one moment; hours_before: hours to the start. -> list of picks (dicts) the rule makes, [] if none.
    Needs Pinnacle and at least one UK book; only inside the arm's window."""
    lo, hi = WINDOWS[arm]
    if not (lo <= hours_before <= hi): return []
    pin = books.get(SHARP)
    if not pin or not all(pin): return []
    fair = novig(*pin); out = []
    for side in (0, 1):
        bk, best = best_uk(books, side)
        if bk is None: continue
        g = gap(best, fair[side])
        if best * fair[side] >= THRESHOLD:
            out.append(dict(side=side, book=bk, price=best, p_pin=fair[side], gap=round(g, 4), suspect=g > SUSPECT, arm=arm))
    return out
