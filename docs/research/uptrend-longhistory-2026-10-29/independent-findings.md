# Independent findings review

Reviewed against `evaluate-metrics.csv`, `base-rates.csv`, `classification-intervals.csv`, `paired-benchmarks.csv` and `classification-eras.csv`. Primary dates: 2010-10-01–2025-09-30. This note checks interpretation of the frozen candidates; it does not select or retune them.

Classification inference completed with 1,999 crossed stock × common stationary-month draws, 3/6-month blocks, 72 conditions per market and 180 months. The source receipt represents 2,610 KR and 4,683 US usable stock histories; eligibility and signal-bearing stock counts vary by period and condition. Families are 432 precision-minus-base contrasts, 144 early-versus-ordinary daily-rate contrasts, and 220 new-candidate-versus-benchmark contrasts. Intervals below use the wider/union bounds across both block choices.

## Supported classification conclusions

| Condition | KR early precision, pointwise 95% interval | US early precision, pointwise 95% interval | KR / US episode capture | KR / US mean delay |
|---|---:|---:|---:|---:|
| MACD signal cross + RSI40 crossing on t/t−1/t−2 | 35.23% [32.79, 37.69] | 36.81% [34.75, 39.00] | 36.48% / 34.49% | 3.73 / 3.74 bars |
| MACD signal cross while MACD<0 | 29.84% [27.73, 31.97] | 30.50% [28.85, 32.30] | 62.31% / 61.08% | 3.68 / 3.70 bars |
| CCI−100 recovery with falling MA20 | 23.19% [21.59, 24.88] | 23.83% [22.53, 25.28] | 78.26% / 78.48% | 1.97 / 1.92 bars |
| RSI30 recovery | 27.58% [24.88, 30.46] | 25.55% [23.87, 27.29] | 30.43% / 24.86% | 1.71 / 1.80 bars |
| Close crosses MA5 | 10.66% [10.02, 11.34] | 10.21% [9.59, 10.84] | 95.99% / 96.48% | 1.94 / 1.89 bars |

The MACD/RSI event is selective but misses roughly two thirds of qualifying episodes; its mean first-capture next-open rise from onset close is already 7.74% KR / 8.14% US. The negative-MACD anchor offers a useful intermediate precision/capture tradeoff, with mean prior rise 6.56% / 6.80%. CCI recovery is broader and faster, with mean prior rise 4.08% / 4.29%. These are conditional means among captured episodes, not typical returns or prospective entry-price promises.

The MACD/RSI early-day base rates are about 7.33% KR / 7.02% US, giving point lifts 4.81× / 5.24×. All four named recovery events have positive early-minus-base differences after the 432-member adjustment. The adjusted p-value floor is 0.0005, reflecting finite Monte Carlo resolution. This does not mean that all alerts are successful: about 64.8% / 63.2% of MACD/RSI alerts fail this particular early-≥10-day target.

Day 0 supplies only 0.15% KR / 0.14% US of all MACD/RSI alerts; ages 1–5 supply 35.08% / 36.68%. The result mainly describes confirmation several bars after the retrospective beginning. The preserved `before5` diagnostic is specifically the **other/down-or-flat subset** within five bars before a qualifying onset. It is 13.43% / 15.35% of RSI30 alerts and 9.62% / 10.47% of CCI-recovery alerts. It is not an exhaustive count of all leading alerts; preceding-up/short-up observations retain their own classifications.

## Early confirmation is distinct from whole-uptrend classification

Supertrend’s whole-≥10-up precision is 88.24% KR / 86.68% US, but its early precision is only 6.85% / 6.30%, with capture 6.74% / 7.20%. Its early-minus-base simultaneous intervals include zero: [−2.03, +1.06] and [−1.99, +0.53] percentage points. Thus early enrichment is not established; do not claim statistically proven underperformance merely from the lower point estimate. Late confirmations alone account for 81.39% / 80.38% of its alerts.

TRIX zero crossing has whole-up precision 77.65% / 80.15%, yet early precision only 0.15% / 0.13%; its early precision is clearly below the early base rate. Conversely, CCI recovery’s whole-up precision is only 31.26% / 34.46%, below whole-up base rates 46.03% / 52.11%, despite its strong early concentration. These conditions answer different temporal questions.

Maintaining `MACD>signal AND RSI>40` is also materially different from the crossing event: its early precision is only 3.68% / 3.50%, while its whole-up precision is 67.29% / 71.67%. Frequent qualifying state days must not be described as independent new alerts.

## Additional confirmation does not reliably improve this target

RSI30 plus same-day close>MA20 has early precision 34.92% KR / 35.63% US, but captures only 0.79% / 0.71% of episodes and occurs about 0.07 / 0.06 times per 252 eligible days. Its mean already-realized rise is 14.38% / 23.57%. Rarity and high conditional precision do not establish practical usefulness.

Waiting for three consecutive closes above MA20 after RSI30 reduces early precision to 9.20% / 7.45%, capture to 1.17% / 0.76%, and delays successful confirmation to 4.73 / 4.80 bars. Its early-minus-base simultaneous intervals include zero. The fixed persistence rule often runs out of the six-bar target window. The US CCI→MA20 sequence raises point precision only from 21.27% to 22.84%, while reducing capture from 79.61% to 42.68%, increasing delay from 1.91 to 3.76 bars, and mean prior rise from 4.35% to 9.23%. These descriptive comparisons are not new optimized rules.

## New-candidate claims after paired adjustment

RMI30 is the most precise of the 11 added conditions in the pooled point tables, but this observation is not a new selection or proof of superiority. In the US, its apparent precision advantage over CCI recovery is +1.24 percentage points with a simultaneous interval [−1.44, +3.93], adjusted p=.966. Its capture is lower by 50.44 points [−53.73, −47.14]. Its apparent capture advantage over RSI30 is +3.18 points [−1.65, +8.00], adjusted p=.6625. Neither claimed advantage is established by this frozen paired family. In KR, RMI30’s precision is lower than RSI30 by 5.03 points [−9.86, −0.20], adjusted p=.0345.

PSAR and StochRSI20 have clearly lower precision and capture than CCI recovery in both markets under the paired family. StochRSI low K/D crossing is faster, around 1.47 bars, with mean prior rise 2.53% KR / 3.22% US, but early precision is only 10.87% / 10.45% and capture about 52–54%. Thus a speed/coverage tradeoff remains; a blanket claim that all new indicators are useless would exceed the evidence.

## Historical stability and remaining interpretation limits

Across the three fixed five-year eras, MACD/RSI precision is 36.86→35.37→34.26% KR and 38.19→38.12→35.51% US. CCI-recovery precision is 23.35→24.40→22.32% KR and 22.71→24.80→23.77% US; its capture remains approximately 75–80% KR and 78–79% US. The broad tradeoffs persist. These descriptive era patterns are not a tested causal trend or proof of future stability, especially as stock coverage changes.

For every condition in both markets, pooled full-available-history precision differs from the 15-year primary precision by less than one percentage point. This is overlapping-history robustness, not an independent replication. Earlier research inspected parts of this history, and a current/stored universe remains exposed to survival and provider-selection bias.

A descriptive quantile appendix is warranted before calling any price-path mean “typical”: rare US early successes already produce mean onset-to-entry rises such as 23.57% for RSI30+MA20 and 54.00% for TRIX zero crossing. Median/IQR/tails supplement, rather than replace or retune, the fixed mean/path hypotheses. Future-path conclusions below use the separate no-L1 all-signal population; the `evaluate-metrics` all/hit price columns remain classification-population diagnostics.

## Completed future-path review

Reviewed `matched-paths.csv`, `balance.csv`, `all-signal-paths.csv`, `path-eras.csv` and `path-distributions.csv`. The baseline is the **next valid open after the signal**. A 21-bar terminal return is close[t+21]/open[t+1]−1; favorable/adverse excursions use highs/lows over t+1…t+21, clipped at zero. Extrema are not executable returns. Primary path eligibility and matching contain no L1 state or future trend duration. The 4,896-member simultaneous family includes all fixed focal conditions, four matching schemes, three horizons and eight outcomes.

The following shows the strictest frozen matching scheme. Differences are signal-minus-matched-control terminal returns in percentage points, with 3/6-month simultaneous union intervals. **Each scheme retains a different supported population.** A larger contrast after stricter matching is not progressively stronger evidence for the same set of signals.

| Condition | KR retained signals | KR 21-bar return difference | US retained signals | US 21-bar return difference | KR / US maximum absolute SMD |
|---|---:|---:|---:|---:|---:|
| MACD+recent RSI40 | 18.79% | +0.64 pp [−0.23, +1.52] | 18.55% | +0.61 pp [−0.67, +1.89] | .158 / .087 |
| MACD cross while MACD<0 | 22.07% | +0.92 pp [+0.21, +1.64] | 22.10% | +1.13 pp [+0.09, +2.18] | .094 / .048 |
| CCI recovery | 27.28% | −0.10 pp [−0.74, +0.53] | 26.82% | +0.03 pp [−0.89, +0.96] | .138 / .114 |
| RMI30 | 17.69% | +0.27 pp [−0.46, +0.99] | 17.01% | +0.67 pp [−0.68, +2.02] | .113 / .075 |
| Supertrend | 27.42% | +3.64 pp [+2.56, +4.72] | 31.30% | +3.29 pp [+1.54, +5.03] | .323 / .147 |
| TRIX zero crossing | 40.27% | +2.07 pp [+0.93, +3.21] | 44.41% | +2.01 pp [+0.92, +3.09] | .076 / .067 |

MACD+RSI’s strong early-label precision does **not** establish a terminal-return advantage under the strictest match. Its strict mean-return intervals include zero at all 5/21/63-bar horizons in both markets. Some weaker-match outcomes, and KR strict positive-terminal-return probability, remain favorable; “no future information whatsoever” would therefore also be too strong. CCI recovery and RMI30 have no established strict mean-terminal-return advantage at any of the three horizons. Their early classification utility and future-price information are different findings.

The negative-MACD anchor retains positive 21-bar terminal-return contrasts in both markets. Its KR strict contrasts are positive at 5 and 63 bars as well; US strict 5/63-bar intervals include zero. At 21 bars it also has smaller mean adverse excursion, by 0.54 pp KR / 0.56 pp US, and higher positive-terminal-return probability, by 4.38 / 4.30 pp, with simultaneous intervals excluding zero. This supports a conditional association for the matched subset. It is not a tested pairwise superiority claim over another indicator, an all-signal effect, or a causal effect.

TRIX zero crossing and Supertrend show that a signal can carry later-path information while being poor at the requested early-onset task. TRIX’s strict 21/63-bar return contrasts are positive in both markets, with relatively smaller standardized imbalance. Supertrend’s larger strict contrasts require particular caution: KR day-return means remain 7.18% versus 5.12%, and relative volume 9.11 versus 4.45; US relative volume remains 15.75 versus 2.72. These comparisons have not fully isolated the indicator from unusually strong price/volume conditions.

Small SMDs alone do not establish balance. US strict MACD+RSI has relative-volume means 8.74 versus 1.52 despite SMD .072; RMI30 has 10.80 versus 2.24 despite .066. Even the negative-MACD US comparison, whose maximum SMD is only .048, has relative volume 2.28 versus 1.37, day returns 1.73% versus 1.37%, and five-day returns 2.41% versus 1.84%. Residual differences and unmeasured conditions remain plausible contributors. Neither fixed-bin matching nor its first-order bootstrap controls every confounder.

The strict 21-bar point contrasts for negative MACD, Supertrend and TRIX are positive in all three fixed eras. MACD+RSI and RMI30 are also point-positive in each era despite their wide pooled simultaneous intervals. CCI is approximately zero/mixed. These are descriptive stability checks; no new era-specific significance family was introduced.

## Unconditional risks and the cost of success-only interpretation

All-signal MACD+RSI 21-bar terminal returns average +1.01% KR / +1.14% US, but their medians are **−0.41% / +0.50%**, with positive-return proportions 47.63% / 51.97%. Their fifth-percentile terminal returns are −18.23% / −22.70%. An intraperiod fall of at least 10% occurs in 33.66% / 36.23% of signals. Mean favorable excursions of 12.51% / 13.08% cannot be substituted for those terminal returns.

Negative MACD’s corresponding mean/median terminal returns are +1.22%/−0.30% KR and +1.21%/+0.43% US; CCI recovery’s are +0.94%/−0.46% and +1.22%/+0.54%. Supertrend and TRIX likewise have negative KR medians (−1.66% and −1.48%) despite positive means. Exact descriptive quantiles retain the original untrimmed observations: the large US right tails are material, not a reason to silently delete or winsorize cases after seeing them.

Selecting only actual early-confirmation successes changes the picture radically. MACD+RSI’s 21-bar mean becomes +9.94% KR / +10.24% US, and CCI recovery’s +12.10% / +12.60%. These are legitimate *conditional diagnostics*, but using them as the expected result of receiving an unfiltered alert would introduce hindsight selection. The observed all-signal risk distribution and limited matched support are sufficient reasons to keep “useful confirmation evidence” separate from “a profitable buy rule.”
