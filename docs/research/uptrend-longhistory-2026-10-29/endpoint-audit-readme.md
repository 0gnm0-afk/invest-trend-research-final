# Fixed-hash endpoint sensitivity audit

This limited audit refits the exact original L1 filter (log close, lambda1, tolerance1e-8, unchanged segments and slope boundary) using only saved data through2015-09-30,2020-09-30 and2025-09-30. Each prefix is compared with the immutable final fit through2026-09-30. It does **not** create real-time L1 signals or alter any signal candidate.

Before calculations,40stocks were fixed by ascending SHA256 of the declared salt and market:symbol:20KR and20US, including2new research-only additions in each market. To permit all three prefix comparisons, the sampling pool required source history beginning on/before2014-12-31 and ending on/after2025-09-30. The sample and hashes are in `endpoint-audit-protocol.json`; it is not representative of every short-history listing.

Mature comparisons require65preceding and126subsequent contiguous observations **inside the prefix**, a finite slope under both fits and a date on/after2010-10-01. Common-known results require both fits to classify the day; unknown/censored labels remain visible in separate counts. The tail comparison contains the last126saved observations at each cutoff and deliberately lacks the126-future safeguard.

| Market / cutoff | Mature common-known days | Mature class agreement, including unknown | Tail class agreement, including unknown | Tail early-day Jaccard among common-known days |
|---|---:|---:|---:|---:|
| KR / 2015-09-30 | 18,718 | 100.0000% | 81.86% | 90.60% |
| KR / 2020-09-30 | 37,963 | 99.9869% | 84.44% | 97.44% |
| KR / 2025-09-30 | 60,491 | 100.0000% | 86.23% | 94.07% |
| US / 2015-09-30 | 17,402 | 100.0000% | 93.53% | 70.59% |
| US / 2020-09-30 | 41,184 | 99.9782% | 84.21% | 91.91% |
| US / 2025-09-30 | 65,098 | 100.0000% | 72.38% | 88.59% |

Common-known mature days had100%agreement in both the four-class label and early0..5membership at every market/cutoff. This does **not** mean every mature observation was unchanged: the2020prefix had5KR and9US days that were still an uncompleted UP run but became known under the final fit; each market gained one completed>=10-day start. Mature dates with both fits unknown also remain outside common-known agreement. The inclusive agreement columns expose these changes.

Tail days are materially less stable. A high common-known agreement can conceal the many prefix-censored UP days. At the2025cutoff,304KR and621US tail days were prefix-unknown but final-known. Early-day Jaccard measures overlap among the union of early days rather than agreement dominated by ordinary days: it ranges90.6–97.4% in KR and70.6–91.9% inUS across the three cutoffs. All exact and within5-observation start matches and all confusion cells are recorded in the CSV.

The evidence supports keeping a maturity buffer and explicitly excluding unfinished trends. It does not prove126bars guarantee unchanged labels for every stock or period, and does not replace the earlier endpoint checks. The40-stock historical-coverage sample cannot quantify revision risk for newly listed, unusually discontinuous or otherwise omitted histories. L1 remains an ex-post evaluation label, never a tradable signal.

All120prefix class arrays were independently reconciled against the original study's `labels()` implementation. All240confusion matrices reconcile, every solver gap is below1e-8, the frozen script hash matches, and sample membership is20permarket with2supplemental permarket. `endpoint-audit-validation.json` records the checks. Prefix fits and classes are preserved under `runtime/uptrend-longhistory-20261029/endpoint-audit/`.
