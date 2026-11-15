# EDGES-VERDICT-SEQ: the interim reads of the picks in testing (registered 15 Nov 2026, before the first live pick counts on 1 Dec)

Fine Margins posts paper picks: a registered UK bookmaker's price that sits at least 3% above Pinnacle's price with the margin removed.
Each pick is scored against the closing price. This file fixes, before any live pick counts, how and when those picks are judged.
It is committed publicly so that the date and the text can be checked. **It does not change after this commit.**

**What counts**
- Two arms, each judged on its own:
  - **Arm B:** posted 12-48 h before the start.
  - **Arm BT:** posted in the 36 minutes before the start (the toss window).
- Every competition on the board counts: BBL, ILT20, SA20, Super Smash, NPL, the IPL, the PSL and men's T20 internationals. IPL,
  PSL and T20Is were added on 15 Nov (ARM-B-WIDER).
- Only picks posted from **1 Dec 2026 00:00 UTC** count. Shadow picks before that do not.
- One pick per fixture and side.
- Gaps over 10% are marked, and they count.

**The measure**
- Closing-line value: CLV = our price × the fair probability at the start − 1. The fair probability is Pinnacle's, with the margin
  removed.
- A pick with no closing price is left out and listed as unscored.

**The reads (four looks)** at 50, 100, 150 and 200 scored picks in an arm.
- At each look: the average CLV and its standard error, from those picks only.
- **PASS:** the average CLV is above zero by at least **4.05 / 2.86 / 2.34 / 2.02 standard errors** at the 50 / 100 / 150 / 200 look.
  These are O'Brien-Fleming boundaries for four looks, one-sided 2.5%.
- **FAIL:** at the 100 look the average CLV is at or below zero, or the 200 look ends without a pass.
- **Otherwise:** still in testing; wait for the next look.
- No other looks. No re-tests on the same picks. No change to the rule, the arms or the boundaries after this commit.

**What each result means for members**
- **In testing** (until a look passes): every pick of that arm is labelled "in testing" wherever members see it. Nothing says it
  is proven or that a bet will win.
- **PASS:** the label for that arm becomes "passed its registered test at N picks (average CLV x%, y standard errors)". Picks stay
  paper prices, 18+, with the GamCare line.
- **FAIL:** that arm stops posting picks to members. The record keeps every pick and says "failed its registered test at N picks".
  Any new version of the rule is a new test, registered before its first pick, and counts from zero.

**Where it shows:** the public record's In testing list (fine-margins.com/t20/record) gives each arm's scored picks and the next look.

Written by lane 2 for Fine Margins (Ansh Bansal), 15 Nov 2026. The pre-registration text in POWER_AND_FORECAST.md and GATE_PROPOSAL.md
(lane 2, 15 Nov); Ansh chose this interim read at 19:45 UTC on 15 Nov.
