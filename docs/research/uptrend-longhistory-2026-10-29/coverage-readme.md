# Coverage audit for the 15-year uptrend extension

The primary window is **2010-10-01 through 2025-09-30**, with all earlier and later eligible saved history shown separately. The audit attempts every stock in the two active saved-history archives plus the36 previously identified supplementary histories. It uses no current-market or account calls.

| Coverage measure | Korea | United States |
|---|---:|---:|
| Inventory records | 2,637 | 4,846 |
| Usable price/L1 caches | 2,610 | 4,683 |
| Raw date span at least15 years | 1,380 | 1,957 |
| Raw date span shorter than15 years, including empty | 1,257 | 2,889 |
| At least one continuous price segment spanning15 years | 272 | 1,572 |
| At least one continuous generic evaluable run spanning15 years | 220 | 1,528 |
| Any evaluable history, full available dates | 2,573 | 4,535 |
| Primary-window evaluable stocks | 2,515 | 4,380 |
| Primary-window evaluable stock-days | 5,919,809 | 9,797,694 |
| Primary-window available price bars | 6,668,482 | 10,588,622 |
| Unavailable65-bar preceding history | 338,301 | 637,283 |
| Unavailable126-bar future/fit | 401,106 | 140,737 |
| Censored UP-run days after other guards | 9,266 | 12,908 |

"Generic evaluable" precedes indicator-specific feature availability. The65 preceding and126 subsequent observations must be in the same inherited segment; current slope and future fit must exist. UP runs need both completed boundaries. Individual signals, especially volume-based formulas, can have fewer available observations. A stock is not dropped merely because it has less than15 years of data.

The stored raw range is1975-01-04..2026-09-30 in Korea and1990-01-02..2026-09-30 in theUS. Generic eligible dates reach1975-03-25..2026-03-26 and1990-04-04..2026-03-31, respectively. These outer dates do not imply every stock covers that range. `coverage-stocks.csv` records every stock's actual dates, segments and per-window counts. `coverage-years.csv` describes **full available history by calendar year**, not clipped primary-window annual results.

All57 prior operational exclusions were attempted in this research only (KR26, US31).56 yielded new valid caches; NUTR had38 valid bars and remains too short. The combined inventory includes all2,604KR and4,843US stocks in the active saved source universes, plus33KR historical-only records and3US selected-chart ADR histories (BP, NVO, TSM). The13-row chart-history cache contains8 successful payloads covering5unique symbols, all already represented. No additional active-source or chart-cache symbol is unaccounted for. The historical exclusion list is retained in `coverage-excluded.csv` as provenance, not applied as an exclusion in this run.

This is **all available stored stock histories**, not a survivorship-free historical listing census. The current saved universes omit many securities that ceased trading before collection;33 supplementary Korean historical records do not cure that bias. There is no basis for claiming all securities listed at each historical date were observed.

The inherited segmentation breaks at dropped invalid/zero-volume observations, audited missing sessions, or gaps exceeding10calendar days. The last rule can split a legitimate long holiday. For example Samsung has a split between2017-09-29 and2017-10-10; its subsequent2018trading suspension causes another split. Thus "continuity break" is broader than a verified provider failure. Preserving these rules costs warmup and maturity coverage but keeps the user's required price/L1 methodology unchanged. Early Korean records also retain the original calendar warning policy rather than reclassifying historical calendar disagreements.

The supplemental preparation reuses the original fixed feature formulas and original L1 solver at lambda1 on log close, dual gap<1e-8. Four deliberately varied existing caches (Samsung,000020.KS,AAPL,TSLA) had exactly identical dates, OHLCV and segment arrays after preprocessing; refitting each longest segment yielded maximum fit difference0.0. All57 source hashes and SavedHistory packet identities were checked. The prior7,237NPZs were read unchanged; the preceding extension had already verified their source/cache hashes. SciPy1.18.1 was installed only under the new supplemental research folder.

Coverage accounting reconciles for every market/window: usable bars = eligible days + unavailable past + unavailable future + censored UP days. See `coverage-validation.json`, `coverage-supplemental-receipt.json` and reproducible scripts `coverage_audit.py` / `supplemental_cache.py`.
