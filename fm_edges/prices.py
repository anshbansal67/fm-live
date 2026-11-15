"""Prices: implied chances, the fair (no-vig) price, the registered UK book list."""
UK = ('bet365', 'williamhill', 'paddypower', 'betfred', 'unibet', 'ladbrokes', 'coral', 'betway', '888sport', 'skybet', 'betvictor', 'boylesports')
SHARP = 'pinnacle'

def implied(price):
    """Decimal price -> implied chance (1 / price). 2.00 -> 0.5."""
    return 1.0 / price

def novig(price_a, price_b):
    """Two decimal prices for the two sides -> their fair chances, margin removed (they add to 1).
    novig(1.90, 1.90) -> (0.5, 0.5); novig(1.50, 2.80) -> (0.651, 0.349)."""
    qa, qb = implied(price_a), implied(price_b)
    return qa / (qa + qb), qb / (qa + qb)

def margin(price_a, price_b):
    """The book's margin: how far the implied chances add up above 100%. margin(1.90, 1.90) -> 0.0526."""
    return implied(price_a) + implied(price_b) - 1

def best_uk(books, side):
    """books: {book: (price_side0, price_side1)}. The best price for `side` among the registered UK books -> (book, price) or (None, None)."""
    uk = {k: v for k, v in books.items() if k in UK and v and v[side]}
    if not uk: return None, None
    bk = max(uk, key=lambda k: uk[k][side]); return bk, uk[bk][side]
