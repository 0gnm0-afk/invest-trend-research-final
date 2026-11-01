# Independent method review: long-history uptrend confirmation

Reviewed 2026-10-29. This is a methodological review before the extended results, not a second analysis or a claim of independent out-of-sample validation. Source inspected: `scripts/research/uptrend_extension/{study,paths,infer,signals}.py` and the restored original `runtime/uptrend-extension-20261029/prior/scripts/uptrend_confirmation/signals.py`.

## Recommended frozen scope

Use a common primary signal-date window **2010-10-01 through 2025-09-30**, exactly 180 calendar months. This extends the preceding 2023-04-01–2025-09-30 evaluation window backwards while preserving its mature ending date. Include every usable stored stock, allowing recently listed or otherwise shorter histories to enter at their earliest *eligible* date. Do not require 15 years per stock and thereby discard younger stocks. Use full available pre-window history to initialize causal indicators; truncating prices at the window start would create artificial warmup losses and initial crossings.

Separately report descriptive classification over the entire available history, with per-stock raw and eligible first/last dates and market/year coverage. Label this the stored-universe history. It is not the historical universe of every Korean or American listing: delisted and absent names remain a survival/coverage limitation. Calendar years with sparse holdings cannot be compared to recent broad years without showing that change. A 15-year market window is not 15 years of observation for every security.

The original code contains 47 basic events, 4 fixed simultaneous anchors, 6 previously selected followups and 4 maintained states: 61 conditions per market. Retaining the 11 added indicators gives **72 frozen conditions per market**. Market-specific prior selections differ: KR RSI30/MFI20, US RSI30/CCI−100. Do not reselect the winners or tune thresholds using the enlarged window. Keep maintained states separate from new events; a state’s annual frequency is qualifying days, not new alerts.

This rerun is retrospective robustness and coverage expansion. Previous selection and prior studies already examined parts of 2016–2025. The older segment does not make the combined period a fresh independent validation. The phrase “backtest” should mean historical signal and future-path evaluation here; it should not imply a trading strategy with defined exits, costs or portfolio sizing.

## Preserve the target and denominator

The inherited target must remain unchanged: fit log closes with objective `0.5*sum((log(C)-x)^2) + 1*sum(abs(diff(x,2)))`; the slope attached to date t is `x[t+1]-x[t]`. Up is strictly greater than `1e-6`, down strictly below `-1e-6`, and flat includes both boundaries. Positive-edge runs need known non-up boundaries on both ends to be completed. A completed run of at least 10 positive edges is the principal uptrend; ages 0 through 5, inclusive, are its early window.

Retain the inherited contiguous-history and future-maturity guards. The 65 preceding bars do not override a particular indicator’s longer warmup. The 126 following bars for classification and 63 following bars for the main path population are different populations and must be shown as such. All evaluable signal dates belong in precision denominators, including dates before an eventual onset. Split early confirmation, late confirmation, short completed rises and other known states. Do not filter the main path comparison by L1 state, completion or eventual duration.

Show early precision and its early-day base rate separately from whole ≥10-day uptrend precision and its whole-up base rate. Episode capture counts an eligible onset once and uses its first qualifying signal. Precision can include an early day near a window boundary even when that episode cannot meet the full-window capture rule; disclose those boundary exclusions instead of forcing the denominators to agree. Report age 0 versus ages 1–5 and retain 0–3 / 0–5 / 0–10 sensitivity without selecting a preferred horizon after seeing results.

The next eligible open divided by retrospective onset close is the already-realized rise at confirmation; it is not a realizable trade return. Future maxima/minima and terminal close must all use the explicitly stated next-open baseline and the same fixed 5/21/63-bar horizons. Keep all-signal outcomes primary and successful early-confirmation outcomes diagnostic.

## Comparable non-signal days and remaining imbalance

Reuse the same-stock, same-calendar-quarter matched cells, successively adding the frozen observable trend/momentum, volatility and recent-return conditions. Controls must be non-signal dates for the exact condition under evaluation. No cell key may use L1 or a future variable. Preserve the fixed-support signal weighting and the first-order control uncertainty assigned to each control’s actual month.

For every refinement, report retained signal count/fraction, distinct controls, weighted control effective sample size, signal/control covariate means and standardized differences. Inspect ATR/price, day-1 and recent returns, MA distance, RSI and relative volume. A small standardized volume difference can hide economically large raw means when variance is large. Sparse strict matches support an inference about their retained subset only; they cannot justify an all-signal conclusion. At least coarse historical-period support and balance summaries should accompany pooled estimates because volatility and universe coverage change over 15 years.

## Scalable dependence inference

Preserve the preceding crossed stock × common stationary-month multiplier method, using 1,999 replicates and mean monthly blocks 3 and 6. A 63-trading-day outcome overlaps several months, and common months preserve cross-stock market shocks. These are dependence-aware approximations, not proof that long-memory dependence or survivorship bias has disappeared. Report the wider/union interval across the two block choices for summary conclusions.

The old implementation hard-codes 30 months, a 2023-04 month offset and 9/12/9 month yearly slices. Replace all three with explicit dynamic bounds. Simply changing 30 to 180 can require roughly 53 GB for 72 US path conditions (`180*4653*72*221*4` bytes), before other allocations. Chunk by condition and keep compact per-condition compressed statistics. Two path conditions require about 1.48 GB for the US cell array; eight classification conditions about 0.54 GB.

Generate identical stock and month multiplier matrices once per market/block and reuse them for every chunk. Retain the small bootstrap estimates, then calculate the centered max-|t| family across **all** chunks/conditions/markets in the declared family. A maximum computed within each chunk is not family-wide adjustment. Market-specific IDs need explicit metadata, rather than assuming identical array indices mean identical rules. Do not replace crossed resampling with independent-day intervals or stock-only clustering merely to fit memory. A computational amendment to inference would need explicit documentation and a small exact-method crosscheck.

Implementation uses an equivalent, more practical alternative to all-stock condition slabs: stream at most eight (configurable up to sixteen) stocks, flatten the month × stock axis, and multiply by the corresponding exact product of stock and common month weights. It retains the same crossed draws and full-family computation. Float32 matrix multiplication and float64 accumulation preserve the inherited numeric precision; reduction-order differences are checked below. Matched inference covers the frozen 26 KR / 25 US focal conditions; all 72 conditions receive unconditional and separately labeled early-success descriptive path summaries. This is 4,896 matched comparisons, in addition to the 432 classification, 144 daily-rate and 220 new-versus-benchmark families.

Freeze the inferential families before the run. Classification precision-minus-base may cover the 72 conditions × 2 markets × 3 stated classifications; event-rate differences are a separate diagnostic family. Matched-path differences should include every condition/horizon/outcome/matching scheme for which simultaneous significance is claimed. If matching is restricted to a bounded, previously chosen focal list for runtime, expose that list and describe the remaining candidates as descriptive only.

## Necessary implementation checks

1. The old 30-month slice must reproduce previous counts and point estimates for unchanged conditions on the same source caches; explain any exact mismatch before interpreting long-history differences.
2. For each market/condition, primary-window counts must equal the sums of its monthly and yearly counts. Each outcome classification must partition its denominator without loss or overlap.
3. Compare scalar computations for representative old, recent and shorter histories against vectorized labels, crossing timestamps, next-open baselines and matched-cell weighting. Delayed fractals and sequence/persistence rules must trigger on the actual information-availability date.
4. Audit raw/eligible dates and exclusion reasons for all inventory entries, including histories missing from the existing usable cache. “All stored” is not satisfied by silently retaining only stocks admitted to an older cache under different length rules.
5. Verify candidate arrays are unchanged by merely moving the evaluation window. The new window must not influence L1 definitions, indicator parameters, candidate selection or matching bin definitions.
6. Report completed/unfinished and missing-data censoring, source cutoff and inherited price-adjustment caveats. Reuse the prior endpoint/selection-leakage audits only where their design still applies; do not present their old signal-specific counts as new long-window validation.

## Closure criterion

The expanded study can answer which frozen signals repeatedly concentrated on retrospectively defined early rises in the stored KR and US universes, the precision/capture/delay tradeoffs, and whether observable-state-matched paths retained information. It cannot establish a delisting-complete market result, prospective live onset certainty, causality or net trading profitability. Once coverage, inherited-definition reconciliation, dependence inference and matching limitations are documented, further parameter search is not required to answer this question. An inconclusive or unstable ranking is a valid final result.

## Inference implementation verification

`inference.py --self-test` passed an independently evaluated explicit crossed-product calculation with 9 months, 7 stocks, 31 draws and chunk sizes 1/3/16. It includes an empty stock, negative control-influence values and separately processed condition slices with shared draws. The maximum absolute float32 reduction difference was `1.0812655091285706e-05`, within the prespecified numeric comparison tolerance. Both new Python files compile and import with 180 months and 72 conditions per market.

A temporary end-to-end fixture exercised both CSV runners with 31 draws and one represented stock per market. It checked 864 base-rate rows, paired family 220, matched family 4,896, 432 era rows and 27,648 all-condition raw/early-success path rows across 15 CSV files. This is a software contract check, not market evidence. Fixture files were removed. The actual study retains 1,999 draws.

One inherited edge-case correction is explicit: a zero or nonfinite bootstrap standard error receives no adjusted p-value (`NaN`). The earlier expression could accidentally produce the minimum Monte Carlo p-value because comparisons to `NaN` were all false. No meaningful positive-variance estimate or candidate definition is changed by this correction.
