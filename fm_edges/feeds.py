"""What the free view may show (the members' numbers never go into it)."""
import datetime as dt

def started(start_iso, now):
    return dt.datetime.fromisoformat(str(start_iso).replace('Z', '+00:00')) <= now

def free_picks(picks, now):
    """Free view: only picks whose match has started, plus how many are still to start (count only)."""
    return dict(picks=[p for p in picks if started(p['start'], now)], pending=sum(not started(p['start'], now) for p in picks))

def win_gate(win, shown, k=None):
    """Win chance on /edges: None where the league hasn't beaten a coin flip; recalibrated 0.5 + k (p - 0.5) where k is given."""
    if not shown or win is None: return None
    return round(0.5 + k * (win - 0.5), 4) if k is not None else win
