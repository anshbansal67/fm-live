"""Closing-line value and the record's summary numbers."""
import math

def clv(price, p_close):
    """Our price against the fair close: price x fair closing chance - 1. clv(2.10, 0.5) -> 0.05."""
    return price * p_close - 1

def summary(clvs):
    """A list of CLVs (None skipped) -> dict(n, mean, se, beat). se = sample sd / sqrt(n); beat = share above zero."""
    c = [x for x in clvs if x is not None]; n = len(c)
    if not n: return dict(n=0, mean=None, se=None, beat=None)
    m = sum(c) / n; se = math.sqrt(sum((x - m) ** 2 for x in c) / (n - 1) / n) if n > 1 else None
    return dict(n=n, mean=m, se=se, beat=sum(x > 0 for x in c) / n)

def verdict(clvs, need=200, k=2.0):
    """The pass mark: at least `need` scored picks and mean CLV more than k standard errors above zero."""
    s = summary(clvs)
    return bool(s['n'] >= need and s['se'] and s['mean'] - k * s['se'] > 0)

def units(results):
    """[(price, won_bool)] -> profit at 1 unit a pick (paper)."""
    return sum((p - 1) if w else -1 for p, w in results)
