# Signal-first downtrend confirmation study

Offline research only. Reuses the immutable input caches of `../downtrend_research`;
does not collect prices or modify the dashboard, holdings, alerts or schedules.
The source inventory contains7426 identities and7237 usable caches. Current-listing
survivorship and historical price adjustment limitations remain.

Run from the repository root with the adjacent engine Python environment. SciPy
is imported from `runtime/downtrend-indicators-20261021/dependencies`.

```powershell
& '../invest-agent-engine/.venv/Scripts/python.exe' scripts/downtrend_confirmation/verify.py
& '../invest-agent-engine/.venv/Scripts/python.exe' scripts/downtrend_confirmation/study.py select --workers 8
& '../invest-agent-engine/.venv/Scripts/python.exe' scripts/downtrend_confirmation/study.py aggregate-select
& '../invest-agent-engine/.venv/Scripts/python.exe' scripts/downtrend_confirmation/study.py evaluate --workers 8
& '../invest-agent-engine/.venv/Scripts/python.exe' scripts/downtrend_confirmation/study.py aggregate-evaluate
& '../invest-agent-engine/.venv/Scripts/python.exe' scripts/downtrend_confirmation/uncertainty.py
& '../invest-agent-engine/.venv/Scripts/python.exe' scripts/downtrend_confirmation/endpoint.py
& '../invest-agent-engine/.venv/Scripts/python.exe' scripts/downtrend_confirmation/details.py
& '../invest-agent-engine/.venv/Scripts/python.exe' scripts/downtrend_confirmation/report.py
& '../invest-agent-engine/.venv/Scripts/python.exe' scripts/downtrend_confirmation/audit.py
```

`select` computes TRAIN only. `aggregate-select` freezes two candidates per market
before evaluation; preserve the original `selection-receipt.json` when resuming.
Do not rerun selection after looking at TEST under a claim of preselection.
`evaluate` resumes per-stock summaries. Input cache SHA256 is checked when read.
Changed definitions require a NEW output directory; existing summaries must not
be silently reused after changes. The period named TEST was previously examined
and is exploratory temporal reassessment, not untouched prospective validation.

Definitions and deliberate conventions:

- Lambda1 on stored log closes, edge slope +/-1e-6, complete runs>=10 edges.
- Target0..5 includes SIX dates. Every evaluable signal day is in the denominator.
  Leading signals are non-target, not removed. All censored down-run days are
  excluded rather than mislabeled as short/false; this differs from the prior study.
- Common65 past/126 future contiguous observations, plus feature-specific warmup.
  Classifier does not gate signals. Features and extra conditions are prefix causal.
- Daily event rates use stock-days on both sides. Capture counts episodes with all
  six signal days known. Precision counts each actual emitted event, even recrosses.
- Sequence and persistence date is actual completion; no L1, future pivots, or
  retrospective shift in the feature conditions. New base events rearm conditions.
- Forward horizon h uses open[t+1], low/high[t+1:t+h+1], close[t+h]. Price excursions
  are descriptive bounds, not executable profit. Missing is never zero return.
- Crossed Poisson stock/quarter bootstrap1000, seed21021. TEST only; per-condition
 95% precision intervals and family-adjusted276 association tests. Follow-up
 differences vs base are descriptive, not separate significance claims.
- All-history, TRAIN and TEST overlap. Do not sum them as independent samples.

Outputs are in `runtime/downtrend-confirmation-20261021` and the reviewable report
under `docs/downtrend-confirmation-2026-10-21*`. `signal-ledger.csv.gz` contains
selected bases, all extensions and fixed comparators. It is not the complete69
signal raw ledger; complete69 sufficient statistics and result CSVs are retained.

CSV ratios are fractions, not percentages. `early` is successful signal count;
`early_days` is evaluable early stock-days. `ordinary` means UP/FLAT, `late` means
age>=6 in a complete>=10-day decline, `short` means complete1..9-day decline.
`match_*` uses same symbol/quarter/three causal context bits and supports only
strata with at least one non-signal observation. `context_support` is the retained
fraction of signal events. `first_drop` averages first successful event per episode;
`all_hit_drop` averages all early signal events. Negative drop denotes a rise.
`*_sum` and `*_n` are additive numerators/denominators for independent checking.

Endpoint sensitivity uses deterministic SHA256-ordered40 eligible stocks/market,
requiring a continuous segment with>=600 pre2025 bars and continuation to2025-09-30.
Prefix fits at2020/2021/2023/2024 year ends are compared to the saved longer fit.
Unfinished prefix runs are explicitly unknown; they are not counted as zero
revision. Counts of both-known days, unknowns, prefix/long starts and matched
shifts must be read together. This80-stock audit does not prove universal stability.
