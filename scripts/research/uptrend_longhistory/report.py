"""Produce an evidence-linked English report for later Korean interpretation.

No candidate selection occurs here. The main tables use a fixed display list;
the complete72-condition results remain in inspectable CSVs and the catalog.
Run only after inference, artifacts, cases and final validation are complete.
"""
from study import *
from paths import focal, HORIZONS, OUTCOMES
import re

DOC = ROOT / 'docs/research/uptrend-longhistory-2026-10-29'
MAIN = DOC.with_suffix('.md')
LINK = 'uptrend-longhistory-2026-10-29/'
DISPLAY = ['price5', 'price20', 'rsi30', 'cci-100', 'cci_recovery', 'macd_rsi40',
           'macd_negative', 'supertrend', 'psar', 'trix_zero', 'trix_signal',
           'stochrsi20', 'stochrsi_cross', 'rmi30', 'rmi50', 'chaikin',
           'avwap_quarter', 'volume_osc']
FOCUS = ['rmi30', 'macd_rsi40', 'macd_negative', 'cci_recovery', 'rsi30', 'psar', 'stochrsi20', 'supertrend', 'trix_zero']
LABEL = {'price5':'Close > SMA5 cross', 'price20':'Close > SMA20 cross', 'rsi30':'RSI14 > 30 cross',
         'cci-100':'CCI20 > -100 cross', 'cci_recovery':'CCI recovery / falling SMA20',
         'macd_rsi40':'MACD cross + recent RSI40', 'macd_negative':'MACD bullish cross with MACD < 0',
         'supertrend':'Supertrend bullish flip', 'psar':'Parabolic SAR bullish reversal',
         'trix_zero':'TRIX18 > 0 cross', 'trix_signal':'TRIX18 > signal cross',
         'stochrsi20':'StochRSI K > 20 cross', 'stochrsi_cross':'StochRSI low K/D cross',
         'rmi30':'RMI20/5 > 30 cross', 'rmi50':'RMI20/5 > 50 cross',
         'chaikin':'Chaikin3/10 > 0 cross', 'avwap_quarter':'Quarter daily AVWAP cross',
         'volume_osc':'Volume oscillator + up day', 'mfi20':'MFI14 > 20 cross',
         'state_price5':'State: close > SMA5', 'state_price20':'State: close > SMA20',
         'state_macd':'State: MACD > signal', 'state_macd_rsi40':'State: MACD > signal and RSI > 40'}


def label(key):
    if '__' in key:
        base, tag = key.split('__')
        return label(base) + ' + ' + {'and20':'same-day > SMA20', 'then20':'SMA20 cross by +5', 'persist3':'3 closes > SMA20 by +5'}[tag]
    return LABEL.get(key, key)


def finite(v):
    try:
        return bool(np.isfinite(float(v)))
    except (TypeError, ValueError):
        return False


def num(v, digits=2):
    return f'{float(v):,.{digits}f}' if finite(v) else '—'


def count(v):
    return f'{int(round(float(v))):,}' if finite(v) else '—'


def pct(v, digits=1):
    return f'{100 * float(v):.{digits}f}' if finite(v) else '—'


def interval(v, lo, hi, percent=True, digits=1):
    f = (lambda x: pct(x, digits)) if percent else (lambda x: num(x, digits))
    return f'{f(v)} [{f(lo)}, {f(hi)}]'


def effect(v, lo, hi):
    f = lambda x: f'{100 * float(x):+.2f}' if finite(x) else '—'
    return f'{f(v)} [{f(lo)}, {f(hi)}]'


def table(headers, rows):
    esc = lambda x: str(x).replace('|', '\\|').replace('\n', ' ')
    return '| ' + ' | '.join(map(esc, headers)) + ' |\n| ' + ' | '.join(['---'] * len(headers)) + ' |\n' + ''.join('| ' + ' | '.join(map(esc, row)) + ' |\n' for row in rows) + '\n'


def link(name, text=None):
    return f'[{text or name}]({LINK}{name})'


def read_csv(name):
    p = DOC / name
    return pd.read_csv(p if p.exists() else OUT / name, keep_default_na=False, na_values=[''])


def readable_spacing(text):
    """Keep compact numeric source strings readable without altering paths/code."""
    pieces=re.split(r'(`[^`]*`|\]\([^)]*\))',text)
    prefix=r'\b(all|the|only|of|for|at|with|through|full|by|from|across|under|original|selected|no|are|is|and|between|than|factor|scale|tolerance|artificial|a|date|needs|contains|plus|had|reaches|exceeding|spanning|not|least|falling|age|precision|period|window|cutoffs|compares|include|includes|retains|versus)(?=\d)'
    suffix=r'(?<=\d)(?=(?:years?|months?|bars?|sessions?|days?|stocks?|histories|records|conditions?|events?|states?|replicates?|replicate|historical|previous|following|preceding|future|past|maintained|additional|original|fixed|new|selected|calendar|uninterrupted|reset|and|or|are|is|for|through|KR|US|eligible|stored|valid|had|edges|inclusive|previously|covariates|state|minimum|scalar|source|protected|aggregate|causal|shared|membership|examples|continuity|fields?|controls?|quarter|focal|alerts?)\b)'
    for i in range(0,len(pieces),2):
        value=pieces[i]
        value=re.sub(r'(\d)through(\d)',r'\1 through \2',value)
        for _ in range(2):
            value=re.sub(suffix,' ',value)
            value=re.sub(prefix,r'\1 ',value,flags=re.IGNORECASE)
        value=re.sub(r'(?<=[%×])(?=[A-Za-z])',' ',value)
        pieces[i]=value
    return re.sub(r'\n{3,}','\n\n',''.join(pieces))


def catalog():
    rows = []
    for market in ['KR', 'US']:
        for item in features.metadata(market):
            rows.append(dict(market=market, **item))
    frame = pd.DataFrame(rows)
    frame.to_csv(DOC / 'conditions.csv', index=False, encoding='utf-8-sig')
    text = ['# Exact condition catalog\n\n72 conditions per market: 47 standalone events, 4 fixed anchors, 6 prior followups, 4 maintained states, and 11 extension events. No threshold search or new combination was performed in this reassessment.\n']
    text.append('All upward crossings use the inherited relative tolerance `tol[t]=1e-12 × max(abs(a[t]),abs(b[t]))`: `a[t]−b[t]>tol[t]` and `a[t−1]−b[t−1]≤tol[t−1]`, with both dates finite. Simple above/below states use their stated strict inequalities. A true condition with an unknown prerequisite remains unknown. Shared warmup masks the first65bars of each valid segment; longer formula warmups still apply. EMA uses span n, adjust=False, minimum n observations. Wilder averages seed at the first n finite observations. Signals are known at the completed close.\n\n')
    grouped = frame.groupby(['id', 'kind', 'formula'], sort=False, dropna=False)
    catalog_rows = []
    for (key, kind, formula), group in grouped:
        catalog_rows.append([key, label(key), ', '.join(group.market), kind, formula])
    text.append(table(['ID', 'Readable name', 'Markets', 'Type', 'Exact condition'], catalog_rows))
    text.append('For RSI, use Wilder14 of one-day positive/negative close changes. For CCI, use typical price `(H+L+C)/3`, SMA20 and mean absolute deviation20 with scale0.015. MACD is EMA12(close)−EMA26(close), signal EMA9(MACD). Sequence and persistence rules trigger only when the final required observation is available; a new base event rearms the rule and the completion deadline is base day+5. Three-close persistence requires its run to begin no earlier than the base event. There are68events and4maintained states per market. Most events are new crossings/transitions; the candle/jump rules explicitly marked “every qualifying day” can recur on consecutive dates. States count each qualifying day; they are not first-entry alerts.\n\n')
    text.append('Daily AVWAP is a typical-price/volume proxy from a pre-known calendar-quarter anchor (or segment start), with at least5previous anchor bars. It does not reconstruct intraday transaction VWAP. The5-bar pivot is available only2bars after the pivot date. PSAR initialization and recursive band details are reproducible in [new_signals.py](../../../scripts/research/uptrend_longhistory/new_signals.py); the inherited formulas are in [old_signals.py](../../../scripts/research/uptrend_longhistory/old_signals.py). Platform-specific equality is not assumed.\n')
    (DOC / 'conditions.md').write_text(readable_spacing('\n'.join(text)), encoding='utf-8')


def main():
    DOC.mkdir(parents=True, exist_ok=True)
    catalog()
    a = read_csv('primary-summary.csv').set_index(['market', 'id'], drop=False)
    assert len(a) == 144 and all((m, k) in a.index for m in ['KR', 'US'] for k in DISPLAY)
    met = read_csv('evaluate-metrics.csv'); mat = read_csv('matched-summary21.csv')
    matched = read_csv('matched-paths.csv'); raw = read_csv('all72-path-summary.csv')
    era = read_csv('classification-eras.csv'); path_era = read_csv('path-eras.csv')
    sens = read_csv('evaluate-sensitivity.csv'); balance = read_csv('balance.csv')
    paired = read_csv('paired-benchmarks.csv'); equal = read_csv('equal-stock.csv')
    cases = read_csv('representative-cases.csv')
    quantiles = read_csv('path-distributions.csv')
    first_dist = read_csv('first-confirmation-distributions.csv')
    coverage = json.loads((DOC / 'coverage-summary.json').read_bytes())
    required_figures = [f'cases-{key}.png' for key in ['rmi30', 'macd_rsi40', 'cci_recovery', 'supertrend']]
    required_figures += [f'{stem}.png' for stem in ['01-accuracy-capture','02-early-whole-baselines',
                        '03-fixed-eras','04-strict-matched-return','05-history-coverage']]
    assert len(cases) == 16 and all((DOC / f).exists() for f in required_figures)
    def rawval(m, key, pop, out, h=21, field='mean'):
        rr = raw[(raw.market == m) & (raw.id == key) & (raw.population == pop) &
                 (raw.period_type == 'primary') & (raw.horizon == h) & (raw.outcome == out)]
        assert len(rr) == 1
        return rr.iloc[0][field]
    def matchrow(m, key, scheme=3):
        rr = mat[(mat.market == m) & (mat.id == key) & (mat.scheme == scheme)]
        assert len(rr) == 1
        return rr.iloc[0]
    parts = ['# Early uptrend confirmation across 15 years: Korea and the United States\n\nStudy UPTREND-LONGHISTORY-20261029 · report date2026-10-29 · saved data through2026-09-30 · research only.\n']
    parts.append('## The question and the answer\n\n**Which technical signals concentrate beyond ordinary recurring fluctuations on the first six trading days of an already-started rise?** This report measures recognition after onset, coverage of actual rises, confirmation delay and subsequent price paths as separate quantities. The common main window is **2010-10-01–2025-09-30**, a full15years. Short-history stocks enter from their earliest evaluable date; older available history is also evaluated descriptively.\n\nThe following fixed reference points show the main tradeoff without declaring a universal winner. Every percentage in this report uses its stated denominator.\n')
    rows = []
    for m in ['KR', 'US']:
        for key in ['macd_rsi40', 'macd_negative', 'cci_recovery', 'rsi30', 'rmi30', 'price5']:
            r = a.loc[(m, key)]
            rows.append([m, label(key), interval(r.precision, r.precision_low, r.precision_high),
                         pct(r.capture), num(r.mean_delay), pct(1 - r.capture), pct(r.first_rise)])
    parts.append(table(['Market', 'Fixed reference', 'Early precision% [95%]', 'Episode capture%', 'Mean lag, bars', 'Missed episodes%', 'Already risen%'], rows))
    parts.append('Read precision as “out of100historical alerts, this many occurred inside the specified early window.” Read capture as “out of100eligible completed rises, this many had an alert in their first six days.” These are different denominators. A more selective condition can recognize a larger proportion of its alerts correctly while missing more actual rises. Lag and already-risen amount describe the first successful early alert, not every alert.\n\n')
    parts.append('**Practical reading of these historical results:** MACD plus recent RSI40 is a relatively selective confirmation clue, but roughly two-thirds of its alerts still miss this exact target and roughly two-thirds of eligible rises receive no such early alert. The MACD-below-zero anchor offers an intermediate accuracy/coverage tradeoff. CCI recovery against a falling20-day average covers more starts and arrives earlier, with lower precision. RSI30 is another fast but narrower recovery clue. A close crossing SMA5 covers nearly every start by firing very often; its low precision makes the frequent-alert cost visible. The11additional events did not establish a replacement that improves this whole set of tradeoffs. The paired family-adjusted comparisons below qualify apparent small improvements.\n\n')
    parts.append('An analogy for interpretation: a sensitive doorbell rings for most arrivals but also for many passers-by; a selective doorbell rings less often but misses visitors. A light showing that someone is already inside is a different instrument again. Here, precision, capture and whole-uptrend recognition measure these separate properties. None of them measures the profit from opening a position.\n\n')
    for m in ['KR', 'US']:
        st, tx = a.loc[(m, 'supertrend')], a.loc[(m, 'trix_zero')]
        parts.append(f"In **{m}**, Supertrend's whole completed-uptrend precision is{pct(st.whole_precision)}%, while its early precision is{pct(st.precision)}% and{pct(st.late_precision)}% of all alerts are late confirmations. TRIX-zero has whole-uptrend precision{pct(tx.whole_precision)}% and early precision{pct(tx.precision,2)}%. Their usefulness for identifying an ongoing rise must therefore be evaluated separately from the six-day task.\n")
    parts.append('The larger history is an **expanded retrospective reassessment**, not a new independent holdout. Some of these rules and years were examined previously. The study can identify historical accuracy/coverage/timing tradeoffs; it does not establish that buying after an alert earns a profit.\n')

    parts.append('## Universe, dates and the meaning of “all stocks”\n')
    rows = []
    for m in ['KR', 'US']:
        c = coverage['markets'][m]; w = c['windows']['fifteen']
        rows.append([m, count(c['inventory']), count(c['status_counts']['ok']), count(w['stocks']),
                     count(c['source_span_ge_15y']), count(c['source_span_lt_15y']), count(w['evaluable_days']),
                     f"{c['source_first']}–{c['source_last']}"])
    parts.append(table(['Market', 'Stored inventory', 'Valid price/L1 caches', 'Primary eligible stocks', 'Raw span≥15y', 'Raw span<15y / empty', 'Generic eligible days', 'Raw date range'], rows))
    parts.append('The combined research inventory attempts **all7,483stored histories**: the2,604KR and4,843US active saved-source names, plus33KR historical-only histories and3selected-chart ADR histories. All57previous operational exclusions were reconsidered for research;56had usable caches, while NUTR had38valid bars and remained too short. Operational exclusion settings were preserved. A valid cache is not a guarantee that a stock contributes to every indicator, period or outcome.\n\n')
    parts.append('“All stored” is a statement about the available archives, **not a point-in-time census of every stock listed in each historical year**. Earlier delistings and absent firms remain missing; survival and provider selection bias remain. There is no newly collected delisting-complete dataset. The per-stock coverage ledger identifies missing/too-short/no-long-segment histories and actual raw/eligible dates.\n\n')
    parts.append('Primary eligibility needs65preceding and126following contiguous observations plus finite L1 information and a known completed state. Individual formulas may require longer warmups. Short histories are included when eligible. Stocks first available after the primary ending date can contribute to the full-history supplement if the maturity guard is met; they do not receive fabricated observations in the15-year main window. KR generic evaluable history reaches1975-03-25–2026-03-26; US reaches1990-04-04–2026-03-31. The sparse early years do not represent the current breadth of either market.\n\n')
    parts.append('Indicators use their full available preceding history, with no artificial2010reset. The inherited segmentation breaks at invalid/nonpositive price or volume observations, audited session gaps, or gaps exceeding10calendar days. This can also split a legitimate long holiday or suspension. Only220KR and1,528US stocks have a continuous generic evaluable run spanning15years; a15-year market window is not15uninterrupted years per stock. The provider’s currently adjusted historical series is reused; historical corporate-action information is not reconstructed as it was known on every old date. Details and reconciled exclusions: '+link('coverage-readme.md')+', '+link('coverage-stocks.csv')+', '+link('coverage-years.csv')+'.\n')
    parts.append(f'![Stored coverage and evaluable history]({LINK}05-history-coverage.png)\n')

    parts.append('## Fixed target and signal definitions\n\nThe inherited L1 objective is `0.5 Σ(log(close)−x)² + 1 Σ|Δ²x|`. The slope attached to date t is `x[t+1]−x[t]`: **up > +1e−6; down < −1e−6; flat includes both boundaries**. Completed positive-edge runs need finite non-up boundaries before and after the run. Flats and gaps are not bridged. Duration counts positive trading edges. The main target is a completed rise of at least10edges; its early window is age0through5inclusive, six sessions.\n\nL1 uses later observations and is an evaluation label only. No L1 state, eventual duration or future return is supplied to a signal or matching cell. Each causal event is timestamped at the close when its final requirement becomes known. The4maintained states count qualifying days and are shown separately from new events.\n\n')
    parts.append('The frozen union contains72conditions per market:47original standalone events,4fixed anchors,6previously selected followups,4states and11additional events. KR followups use RSI30/MFI20; US uses RSI30/CCI−100. No new candidate selection or parameter grid was run. Exact formulas for all conditions are in '+link('conditions.md','the condition catalog')+' and '+link('conditions.csv')+'.\n')
    rows = []
    md = {b['id']: b for b in features.metadata('KR')}
    for key in DISPLAY:
        rows.append([label(key), md[key]['formula']])
    parts.append(table(['Displayed condition', 'Exact fixed rule'], rows))
    parts.append('Upward cross means `a−b > tol` now and prior `a−b ≤ prior tol`, with both dates finite and `tol=1e−12×max(abs(a),abs(b))`; simple maintained states use their stated strict inequalities. RSI is Wilder14; CCI uses typical price,20-bar mean absolute deviation and factor0.015; MACD uses EMA12−EMA26 and EMA9 signal. The quarter AVWAP is a daily typical-price proxy, not intraday VWAP. Formula initialization may differ from a charting platform. Some candle/jump events are explicitly every qualifying day, rather than first transitions. Source evidence and deferred indicators remain documented in '+link('literature-refresh.md')+'.\n')

    parts.append('## Accuracy, concentration, coverage and timing\n\nEvery evaluable alert is in the precision denominator, including alerts before an eventual onset. Early precision is compared with the early-day base rate among that condition’s eligible dates. Lift is precision/base. Episode capture requires the entire specified early window to be observable and counts at most one first alert per episode. A boundary alert can enter precision even when the entire episode window is unavailable for capture. Frequency is252×alerts/feature-known eligible stock-sessions; it is a normalized rate, not a calendar-year forecast for a stock with sparse or gapped history. Eligibility can differ by formula, particularly longer moving averages and volume indicators.\n\nBrackets envelope the marginal95%bootstrap intervals from3- and6-month blocks. The envelope is a conservative presentation of two specifications, not a separately calibrated joint95%interval. A precision interval is not a family-adjusted difference test. Family-adjusted early-minus-base and paired contrasts are retained in the CSVs.\n')
    for m in ['KR', 'US']:
        parts.append(f'### {m}: first-six-day confirmation\n')
        rows = []
        for key in DISPLAY:
            r = a.loc[(m, key)]
            rows.append([label(key), count(r.signals), interval(r.precision, r.precision_low, r.precision_high),
                         pct(r.early_base), num(r.early_lift) + '×',
                         interval(r.capture, r.capture_low, r.capture_high), num(r.annual)])
        parts.append(table(['Signal', 'All-alert N', 'Early% [95%]', 'Early base%', 'Lift', 'Capture% [95%]', 'Alerts /252days'], rows))
        rows = []
        for key in DISPLAY:
            r = a.loc[(m, key)]
            rows.append([label(key), interval(r.mean_delay, r.mean_delay_low, r.mean_delay_high, False, 2),
                         num(r.median_delay, 0), interval(r.first_rise, r.first_rise_low, r.first_rise_high),
                         pct(r.day0_precision), pct(r.day1_5_precision), pct(r.late_precision)])
        parts.append(table(['Signal', 'Mean first-hit lag [95%]', 'Median lag', 'Onset close→next open% [95%]', 'Day0% of alerts', 'Days1–5%', 'Late%'], rows))
    parts.append(f'![Accuracy, episode capture and pointwise uncertainty]({LINK}01-accuracy-capture.png)\n')
    parts.append('Already risen uses the next open after the **first successful early signal**, divided by the retrospectively identified onset close minus1. It is a timing cost, not a trade return. Rare early hits can have unstable conditional timing estimates. A low-frequency signal earns no preference merely for being rare. Every omitted main-table condition remains available in '+link('primary-summary.csv')+'.\n')
    rows=[]
    for m in ['KR','US']:
        for key, benchmark in [('rmi30','macd_rsi40'),('psar','cci_recovery'),('stochrsi20','cci_recovery')]:
            for metric in ['precision','capture']:
                rr=paired[(paired.market==m)&(paired.id==key)&(paired.benchmark==benchmark)&(paired.metric==metric)]
                rows.append([m,label(key)+' minus '+label(benchmark),metric,
                             effect(rr.difference.iloc[0],rr.sim_low.min(),rr.sim_high.max())])
    parts.append(table(['Market','Fixed paired comparison','Metric','Difference pp [family-adjusted envelope]'],rows))
    parts.append('These paired intervals use common draws for correlated signals. They are the appropriate comparison evidence; separate pointwise interval overlap is not a test of their difference. All11new signals against all5benchmarks remain in '+link('paired-benchmarks.csv')+'.\n')

    parts.append('### Whole-uptrend recognition is a separate question\n')
    rows = []
    for key in DISPLAY:
        kr, us = a.loc[('KR', key)], a.loc[('US', key)]
        rows.append([label(key), f'{pct(kr.whole_precision)} / {pct(kr.whole_base)}',
                     f'{pct(us.whole_precision)} / {pct(us.whole_base)}',
                     f'{num(kr.whole_lift)} / {num(us.whole_lift)}',
                     f'{num(kr.rate_ratio)} / {num(us.rate_ratio)}'])
    parts.append(table(['Signal', 'KR whole≥10 up% / base%', 'US whole≥10 up% / base%', 'Whole lift KR / US', 'Early / down-flat event rate KR / US'], rows))
    parts.append(f'![Early and whole-uptrend precision with separate baselines]({LINK}02-early-whole-baselines.png)\n')
    parts.append('Whole precision counts both early and late dates in completed≥10-day rises. Its base rate is much larger than the early-window base. The early/down-flat event-rate ratio compares signal incidence within those two states and omits late and short rises; it cannot replace all-alert precision. Whole-up-any-duration rates are also saved in '+link('base-rates.csv')+'.\n')
    rows = []
    for m in ['KR', 'US']:
        for key in FOCUS:
            r = a.loc[(m, key)]
            rows.append([m, label(key), pct(r.day0_precision), pct(r.day1_5_precision), pct(r.late_precision),
                         pct(r.short_precision), pct(r.other_precision), pct(r.before5_precision)])
    parts.append(table(['Market', 'Signal', 'Day0%', 'Days1–5%', 'Late%', 'Short<10%', 'Other%', 'Before onset5%'], rows))
    parts.append('The first five outcome columns partition100%of alerts before rounding. Before-onset5is a subset of other, remains a failure for this purpose, and stays in the denominator. An early-confirmation miss can still precede a price gain; it missed this specified label and timing window. “Most alerts miss the exact early label” does not mean “most trades lose money.”\n')

    parts.append('### How far had prices moved at the first successful confirmation?\n\nThe mean timing cost can be pulled upward by rare jumps. This descriptive supplement reports the median and tails of `first captured signal next open / retrospective onset close − 1`. Each eligible episode contributes one first alert. Raw prices can fluctuate inside a positive fitted trend, so a negative timing value is possible.\n')
    rows=[]
    for m in ['KR','US']:
        for key in ['macd_rsi40','macd_negative','cci_recovery','rsi30','rmi30','trix_zero']:
            r=first_dist[(first_dist.market==m)&(first_dist.id==key)].iloc[0]
            rows.append([m,label(key),count(r.captured_episodes),pct(r.reference_mean_float64),pct(r['median']),f'{pct(r.q25)} / {pct(r.q75)}',f'{pct(r.q05)} / {pct(r.q95)}'])
    parts.append(table(['Market','Signal','Captured episodes','Mean%','Median%','P25 / P75%','P5 / P95%'],rows))
    parts.append('For example, the US TRIX-zero mean timing rise is54.0%, but the median is18.6% across only130captured episodes. Its upper tail includes an883.6% maximum. The trace ledger identifies the original symbols/dates/prices without removing observations. The quantile appendix was added after aggregate means exposed this skew; it is an explicitly descriptive supplement, not a changed hypothesis, target or candidate selection. No trimming or winsorization changes the main results. See '+link('first-confirmation-distributions.csv')+', '+link('first-confirmation-extremes.csv')+' and '+link('distributions-readme.md')+'.\n')
    parts.append('## Standalone signals, simultaneous filters and delayed confirmation\n\nThe original six followups per market are repeated unchanged. No new combination was selected on the expanded history. Each row must be assessed with its loss of episode coverage and its confirmation delay.\n')
    rows = []
    for m, bases in [('KR', ['rsi30', 'mfi20']), ('US', ['rsi30', 'cci-100'])]:
        for base in bases:
            for key in [base] + [base + '__' + tag for tag in ['and20', 'then20', 'persist3']]:
                r = a.loc[(m, key)]
                rows.append([m, label(key), count(r.signals), pct(r.precision), pct(r.capture), num(r.mean_delay), pct(r.first_rise), num(r.annual)])
    parts.append(table(['Market', 'Condition', 'N', 'Early%', 'Capture%', 'Mean lag', 'Already risen%', 'Frequency'], rows))
    parts.append('“Same day” adds close>SMA20to the base event. “By+5” waits for the first actual upward SMA20cross from base day through base+5. “3closes” waits for three consecutive closes above SMA20, beginning at/after the base and completing by+5. They trigger on completion, not retrospectively on the original base date.\n')
    rows = []
    for m in ['KR', 'US']:
        for key in ['state_price5', 'state_price20', 'state_macd', 'state_macd_rsi40']:
            r = a.loc[(m, key)]
            rows.append([m, label(key), pct(r.precision), pct(r.whole_precision), pct(r.capture), num(r.annual)])
    parts.append(table(['Market', 'Maintained state', 'Early%', 'Whole≥10 up%', 'Capture%', 'Qualifying days /252'], rows))
    parts.append('These state rows answer how informative a condition is while it remains true. Their high frequency can repeat essentially the same episode; it must not be read as a stream of independent new crossings.\n')

    parts.append('## Stability across three fixed five-year eras\n\nEach cell reports early precision / episode capture. Periods were fixed before inspecting the expanded results. These are descriptive slices, not three independent validation experiments. Changes in market regime and the stock universe can both change a pooled percentage.\n')
    periods = sorted(era.period.unique())
    rows = []
    for m in ['KR', 'US']:
        for key in FOCUS:
            values = []
            for period in periods:
                r = era[(era.market == m) & (era.id == key) & (era.period == period)].iloc[0]
                values.append(f'{pct(r.early_precision)} / {pct(r.capture)}')
            rows.append([m, label(key), *values])
    parts.append(table(['Market', 'Signal', *[p + ' precision% / capture%' for p in periods]], rows))
    parts.append(f'![Accuracy, capture and alert frequency in three fixed eras]({LINK}03-fixed-eras.png)\n')
    parts.append('All72era estimates, annual counts and changes in base rates are in '+link('classification-eras.csv')+' and '+link('classification-yearly.csv')+'. Calendar2010and2025are partial years in the primary window. Precision is assigned by signal date; capture is assigned by the episode’s onset month, so a captured early-window signal can occur in the following period. Equal-stock estimates weight each stock with a signal equally, whereas the main precision weights every alert equally.\n')
    rows = []
    for m in ['KR', 'US']:
        for key in ['macd_rsi40', 'cci_recovery', 'rmi30', 'supertrend', 'trix_zero']:
            r = a.loc[(m, key)]; e = equal[(equal.market == m) & (equal.id == key)].iloc[0]
            allrow = met[(met.market == m) & (met.id == key) & (met.period == 'all')].iloc[0]
            rows.append([m, label(key), pct(r.precision), pct(e.early_precision), pct(allrow.precision), count(allrow.signals)])
    parts.append(table(['Market', 'Signal', 'Primary pooled%', 'Primary equal-stock%', 'Full available history%', 'Full-history alerts'], rows))
    parts.append('The full-history column includes eligible observations before2010and after the main window, where available. It overlaps the primary data and changes the represented universe; it is a sensitivity description, not another independent test.\n')

    parts.append('## Prices after every signal, including failures\n\nThe reference is the **next contiguous valid open, open[t+1]**. For horizon h=5,21or63, touches and extrema use high/low from t+1through t+h inclusive; terminal return uses close[t+h]. Favorable excursion is `max(0, maximum high/reference−1)`; adverse depth is `max(0,1−minimum low/reference)`. They describe opportunity and risk ranges, not achievable returns. A path can touch both+5%and−5%.\n\nThe primary path population uses65past and63future bars plus observable covariates. It does **not** require any retrospective L1 state, completion or future duration. Thus path counts differ from classification counts.\n')
    rows = []
    for m in ['KR', 'US']:
        for key in FOCUS:
            rows.append([m, label(key), count(rawval(m,key,'all_signals','return',field='signals')),
                         *[pct(rawval(m,key,'all_signals',o)) for o in ['gain05','loss05','favorable','adverse','return','positive_return']]])
    parts.append(table(['Market', 'Signal', 'All-signal N', '+5%touch%', '−5%touch%', 'Mean favorable%', 'Mean adverse%', 'Mean end21%', 'Positive end21%'], rows))
    parts.append('All72conditions and all three horizons are saved in '+link('all72-path-summary.csv')+'. Matching and bootstrap path inference cover the predeclared26KR/25US focal conditions; the remaining unconditional path summaries are descriptive. Means remain sensitive to exceptional observations and inherited adjustment errors; no favorable-return outlier trimming was applied.\n')
    rows = []
    for m in ['KR', 'US']:
        for key in ['macd_rsi40', 'cci_recovery', 'rmi30']:
            rows.append([m, label(key), count(rawval(m,key,'early_confirmation_success','return',field='signals')),
                         pct(rawval(m,key,'early_confirmation_success','return')),
                         pct(rawval(m,key,'early_confirmation_success','loss05')),
                         pct(rawval(m,key,'all_signals','return'))])
    parts.append(table(['Market', 'Signal', 'Hindsight early-hit N', 'Early-hit mean end21%', 'Early-hit −5%touch%', 'ALL-signal mean end21%'], rows))
    parts.append('The successful subset is explicitly conditioned on a future-known label and is only a diagnostic description. Its favorable outcomes cannot be used as the live signal’s expected result. The all-signal comparison above and below answers the prospective information question more directly.\n')

    parts.append('### Incremental information versus comparable non-signal dates\n\nControls are dates with flag 0 for the same condition, in the same stock and calendar quarter. Scheme 0 matches SMA20[t]>SMA20[t−5], close>SMA20 and RSI≥50. Scheme 1 adds ATR/close and recent 5-bar return bins. Scheme 2 adds same-day return bins. Scheme 3 adds 20-bar return and distance to SMA20. No scheme uses L1 or future information. The unchanged boundaries are ATR/close:0.02,0.04; return5:−0.05,0,0.05; return1:−0.03,−0.01,0,0.01,0.03; return20:−0.10,−0.03,0,0.03,0.10; close/SMA20−1:−0.05,−0.02,0,0.02,0.05. Interior bins include their lower boundary and exclude their upper boundary. Implementation: [paths.py](../../scripts/research/uptrend_longhistory/paths.py); the frozen protocol preserves the inherited matching rule in '+link('protocol.json')+'.\n\nThe following strict-scheme tables show the **retained subset**. Unsupported alerts remain in the all-signal results, but cannot contribute to the matched contrast. SMD is a standardized signal/control mean difference; a small SMD is not a guarantee of causal comparability. The intervals below are envelopes of the 3/6-month **family-adjusted** intervals across 4,896 matched comparisons. All differences are percentage points.\n')
    for m in ['KR', 'US']:
        rows = []
        for key in DISPLAY:
            r = matchrow(m,key)
            rows.append([label(key), pct(r.support), num(r.max_abs_smd,3),
                         effect(r.return_difference,r.return_sim_low,r.return_sim_high),
                         effect(r.gain05_difference,r.gain05_sim_low,r.gain05_sim_high),
                         effect(r.loss05_difference,r.loss05_sim_low,r.loss05_sim_high)])
        parts.append(f'#### {m}:21-bar strict matched contrasts\n\n' + table(['Signal', 'Retained%', 'Max abs SMD', 'Δ terminal pp [sim95%]', 'Δ +5%touch pp [sim95%]', 'Δ −5%touch pp [sim95%]'],rows))
        rows=[]
        for key in FOCUS:
            r=matchrow(m,key)
            rows.append([label(key),f'{pct(r.return_signal)} / {pct(r.return_control)}',
                         f'{pct(r.favorable_signal)} / {pct(r.favorable_control)}',
                         effect(r.favorable_difference,r.favorable_sim_low,r.favorable_sim_high),
                         f'{pct(r.adverse_signal)} / {pct(r.adverse_control)}',
                         effect(r.adverse_difference,r.adverse_sim_low,r.adverse_sim_high),count(r.control_effective_n)])
        parts.append(table(['Signal','Terminal signal/control%','Favorable signal/control%','Δ favorable pp [sim95%]',
                            'Adverse signal/control%','Δ adverse pp [sim95%]','Control effective N'],rows))
    parts.append(f'![Strict supported terminal-return contrasts and uncertainty]({LINK}04-strict-matched-return.png)\n')
    parts.append('**Incremental information is more limited than early-label accuracy.** Under the strict comparison, the21-bar terminal-return differences for MACD+RSI, CCI recovery and RMI30 have simultaneous intervals spanning zero in both markets. This is an absence of established advantage under this comparison, not proof that the differences are exactly zero.\n\n')
    for m in ['KR','US']:
        r=matchrow(m,'macd_negative')
        parts.append(f"In {m}, the predeclared MACD-below-zero signal-cross anchor retains {pct(r.support)}% of its path signals and has a21-bar terminal contrast of {effect(r.return_difference,r.return_sim_low,r.return_sim_high)} percentage points. This is a supported-subset association; it is not a paired proof that this indicator beats another indicator, nor an effect established for every alert.\n")
    parts.append('TRIX-zero retains a positive matched terminal contrast with broader support, while being exceptionally poor at the six-session onset task. Supertrend also has positive matched contrasts, but substantial remaining same-day/volume differences limit attribution. Stricter matching does not completely isolate a technical signal: even small standardized differences can coexist with meaningful raw differences when a covariate is highly skewed. The tables below show that limitation directly.\n')
    parts.append('A positive terminal contrast is a historical association on supported dates. It can coexist with larger adverse excursions, low early precision, residual imbalance, costs and selection. A confidence interval crossing zero does not prove equivalence. A strictly positive simultaneous interval is not itself a profitable trading rule.\n')
    rows=[]
    for m in ['KR','US']:
        for key in ['rmi30','macd_rsi40','supertrend','trix_zero']:
            for scheme in range(4):
                r=matchrow(m,key,scheme)
                rows.append([m,label(key),scheme,pct(r.support),num(r.max_abs_smd,3),r.largest_imbalance_covariate,
                             effect(r.return_difference,r.return_sim_low,r.return_sim_high)])
    parts.append(table(['Market','Signal','Scheme','Retained%','Max abs SMD','Largest imbalance','Δ end21 pp [sim95%]'],rows))
    parts.append('Stricter matching trades broader coverage for comparability. The estimates in different scheme rows need not describe the same signals. Where support becomes small, the strict result cannot be generalized to the whole signal family. All covariate raw means, SMDs, distinct control days and effective sample sizes are in '+link('balance.csv')+'. The next table exposes same-day returns and relative volume for representative conditions because large skew can make standardized differences look modest.\n')
    rows=[]
    for m in ['KR','US']:
        for key in ['macd_rsi40','macd_negative','cci_recovery','rmi30','supertrend','trix_zero']:
            sub=balance[(balance.market==m)&(balance.id==key)&(balance.scheme==3)].set_index('covariate')
            cells=[]
            for cov in ['atr_pct','return1','return5','relative_volume']:
                r=sub.loc[cov];fmt=num if cov=='relative_volume' else pct
                cells.append(f'{fmt(r.signal_mean)} / {fmt(r.control_mean)}')
            rows.append([m,label(key),*cells])
    parts.append(table(['Market','Signal','ATR/close% signal/control','Same-day return% signal/control','Recent5 return% signal/control','Relative volume× signal/control'],rows))
    rows=[]
    for m in ['KR','US']:
        for key in ['rmi30','macd_rsi40','macd_negative','cci_recovery','supertrend','trix_zero']:
            cells=[]
            for h in HORIZONS:
                rr=matched[(matched.market==m)&(matched.id==key)&(matched.scheme==3)&(matched.horizon==h)&(matched.outcome=='return')]
                cells.append(effect(rr.difference.iloc[0],rr.sim_low.min(),rr.sim_high.max()))
            rows.append([m,label(key),*cells])
    parts.append(table(['Market','Signal','5-bar Δ terminal pp [sim95%]','21-bar Δ terminal pp [sim95%]','63-bar Δ terminal pp [sim95%]'],rows))
    parts.append('Annual and five-year matched path contrasts/support are retained in '+link('path-yearly.csv')+' and '+link('path-eras.csv')+'. They use fixed full-quarter means and allocate first-order control influence to the controls’ actual months. The primary/era boundaries align to calendar quarters. These are dependence-aware descriptive adjustments, not randomized comparisons.\n')

    parts.append('### All-signal return distributions: the mean is not a typical outcome\n\nThese are all-signal path-population results, with no retrospective-success restriction. Return is next-open to21st-bar close. Percentiles are empirical descriptive values, not confidence intervals. Their purpose is to expose skew and downside, while the fixed mean/threshold hypotheses above remain unchanged.\n')
    rows=[]
    for m in ['KR','US']:
        for key in ['macd_rsi40','macd_negative','cci_recovery','rsi30','rmi30','supertrend','trix_zero']:
            r=quantiles[(quantiles.market==m)&(quantiles.id==key)&(quantiles.population=='all_signals')&(quantiles.horizon==21)&(quantiles.outcome=='return')].iloc[0]
            rows.append([m,label(key),count(r.n),pct(r.reference_mean_float64),pct(r['median']),pct(r.positive_probability),f'{pct(r.q05)} / {pct(r.q95)}'])
    parts.append(table(['Market','Signal','All path signals','Mean end21%','Median end21%','Positive end21%','P5 / P95%'],rows))
    parts.append('For MACD+RSI, the21-bar median is about−0.4%KR /+0.5%US despite positive mean returns near1%. The lower5th percentile is about−18.2% /−22.7%. A successful early-label association therefore does not imply that most alerts lead to large positive returns. All5/21/63-bar return and favorable/adverse-depth distributions, separately for all signals and early-success diagnostics, are in '+link('path-distributions.csv')+'. These are marginal signal distributions; they are not median treatment effects versus matched controls.\n')
    parts.append('## Sensitivity and representative cases\n\nThe early window was not widened to make an indicator look better. Each cell below reports precision/capture under the three fixed windows. The principal result remains0–5.\n')
    rows=[]
    for m in ['KR','US']:
        for key in FOCUS:
            cells=[]
            for w in ['0..3','0..5','0..10']:
                r=sens[(sens.market==m)&(sens.id==key)&(sens.period=='primary')&(sens.window==w)].iloc[0]
                cells.append(f'{pct(r.precision)} / {pct(r.capture)}')
            rows.append([m,label(key),*cells])
    parts.append(table(['Market','Signal','0–3 precision/capture%','0–5 precision/capture%','0–10 precision/capture%'],rows))
    parts.append('Duration strata10–20,21–62and63+are auxiliary descriptions in '+link('evaluate-duration.csv')+'. They are never inputs to a live signal.\n\nThe following16examples were chosen deterministically at the **lower median21-bar terminal return** within each fixed market/condition/known-label success-or-miss group. They illustrate typical paths under that selection rule; they are not best/worst exhibits, representative of every market regime, or additional evidence of accuracy.\n')
    rows=[]
    for _,r in cases.iterrows():
        rows.append([r.market,label(r.id),r.symbol,r.signal_date,'early hit' if r.early_hit else 'early miss',
                     int(r.label_class),pct(r.return21),pct(r.favorable21),pct(r.adverse21),count(r.population_count)])
    parts.append(table(['Market','Condition','Symbol','Signal close date','Target result','Class code','End21%','Favorable21%','Adverse21%','Selection population'],rows))
    parts.append('Class codes:0known down/flat;1early≥10-day rise;2late≥10-day rise;3short rise. Unknown labels are excluded only from illustrative case selection, not from the main all-signal price population. Green chart shading uses retrospective early windows. Zero on the price axis is the next open.\n')
    for key in ['rmi30','macd_rsi40','cci_recovery','supertrend']:
        parts.append(f'![Typical {label(key)} success and miss cases]({LINK}cases-{key}.png)\n')

    parts.append('## Academic basis, uncertainty and retrospective-label limits\n\nThe source review affected actual choices: Kim et al. keeps the two-sided L1 label separate from signals; Lo et al. motivates explicit conditional-information tests; Sullivan et al. motivates freezing/reporting the candidate family and controlling multiple comparisons; Bajgrowicz and Scaillet motivates persistence checks and the distinction between statistical discovery and economic value. Original/author/institution links and the specific decisions are in '+link('literature-refresh.md')+'. Long-horizon momentum profitability is not used as proof of short-horizon early confirmation.\n\n')
    parts.append('The1,999replicate inference crosses Poisson stock weights with common stationary-month weights, using mean blocks3and6months. Common month weights preserve shared market shocks, and blocks address recurring/overlapping observations. The simultaneous families are432classification-state-minus-base contrasts,144early-versus-ordinary event-rate contrasts,220paired new-versus-benchmark precision/capture contrasts, and4,896matched path contrasts. The computation streams bounded stock chunks while retaining the same weights and full families. Zero/nonfinite standard errors receive no adjusted p-value.\n\n')
    parts.append('This correction covers the frozen reassessment, not every candidate or decision tried across earlier research. Some followups were selected in prior2016–2021work; previously inspected2016–2025years remain reused. Final-sample L1 can depend on prices after evaluation cutoffs, even though signal computations do not. A wider historical window does not solve that labeling dependence or create a fresh out-of-sample test. Fixed matching cells and first-order control influence approximate uncertainty; controls are not fully rematched in each draw.\n\n')
    parts.append('A new fixed-hash **40-stock endpoint audit** refitted the original solver through2015-09-30,2020-09-30and2025-09-30and compared with the final saved fit. Mature common-known days agreed on class and early membership in every audited market/cutoff. That100%common-known agreement omits changes in whether a label was known: the2020prefix had5KR and9US mature days still in unfinished rises that became known under the final fit.\n\nTail labels were materially less stable. At the2025cutoff,304KR and621US tail days changed from prefix-unknown to final-known. Across cutoffs, tail early-day Jaccard was90.6–97.4%KR and70.6–91.9%US. This supports a maturity buffer and explicit censoring; it does not prove126bars guarantee stable labels in every security or period. The hash sample required long history and is not representative of all recent listings. All120prefix label arrays and240confusion matrices reconcile; every audited solver gap was below1e−8. Exact counts and scope: '+link('endpoint-audit-readme.md')+', '+link('endpoint-audit.csv')+', '+link('endpoint-audit-validation.json')+'.\n')

    parts.append('## Reproduction and verification\n\nThe old research and input caches are preserved. New code lives under `scripts/research/uptrend_longhistory/`; new computation artifacts live under `runtime/uptrend-longhistory-20261029/`. The research-only57-source preparation reused the original preprocessing and solver. Four deliberately varied existing caches exactly reproduced dates/OHLCV/segments, and the longest-segment refits had maximum fit difference0.0. The supplemental source hashes and identities are recorded.\n\n')
    parts.append('Core verification passed:379,584causal-prefix cells;23,040shared formula cells;2,310original/extension metrics in the exact overlapping30-month window;77,189,112aggregate cells with monthly/episode/denominator conservation;7,293source-cache hashes;94protected prior-file hashes. The vectorized matching reference test compares132,795scalar cells, with maximum absolute difference1.71e−12;12real-stock overlapping path checks compare1,272,960cells. Streaming bootstrap is checked against explicit crossed products, including negative control influences and condition slices. All7,293stocks reconcile in the descriptive-quantile supplement. These software checks validate calculations under the stated data and definitions; they do not remove historical-universe or adjustment limitations.\n\n')
    receipts=sorted({p.name for p in DOC.glob('*verification*.json')}|{p.name for p in DOC.glob('*validation*.json')})
    if receipts:parts.append('Saved verification receipts: '+', '.join(link(name) for name in receipts)+'.\n\n')
    parts.append(table(['Deliverable','Purpose'],[
        [link('primary-summary.csv'),'All144market/condition rows: precision/base/concentration/capture/lag/frequency and uncertainty'],
        [link('conditions.md')+' / '+link('conditions.csv'),'Exact definitions and event/state distinction'],
        [link('base-rates.csv')+' / '+link('paired-benchmarks.csv'),'Three state bases and dependent paired contrasts'],
        [link('classification-eras.csv')+' / '+link('classification-yearly.csv'),'Fixed-era and annual stability'],
        [link('matched-summary21.csv')+' / '+link('matched-paths.csv'),'Matched differences, support and family-adjusted uncertainty'],
        [link('all72-path-summary.csv'),'All signals and retrospective successes separately,5/21/63bars'],
        [link('path-distributions.csv')+' / '+link('first-confirmation-distributions.csv'),'Descriptive quantiles and timing-cost tails; no changed hypotheses'],
        [link('balance.csv')+' / '+link('path-eras.csv'),'Remaining observable differences and period support'],
        [link('coverage-stocks.csv')+' / '+link('endpoint-audit.csv'),'Per-stock scope and retrospective-label sensitivity'],
        [link('representative-cases.csv'),'Deterministic case selection and exact dates/prices'],
        ['[Reproduction code](../../scripts/research/uptrend_longhistory/)','Frozen protocol, feature/label/path producers, inference, validation and report generator']]))

    parts.append('## Confirmed findings, remaining uncertainty and permitted interpretation\n\n**Confirmed within this dataset:** the tables quantify which fixed events concentrated on retrospective early rises and the accompanying precision, episode coverage, lag and already-risen cost. Whole-uptrend recognition, early recognition and incremental future-path association are different results. The all-alert denominator includes pre-onset, late, short and other failures; successful-only paths are clearly separated.\n\n**Still uncertain:** the results are not delisting-complete, independently prospective or causal. Label revision near endpoints, provider/adjustment errors, unequal history lengths, remaining state imbalance, limited strict-match support and repeated historical research constrain generalization. Statistical significance does not erase these limitations.\n\n**Useful scope:** these results can inform how a human interprets a technical alert—whether it is a relatively selective early recovery clue, a broad but noisy coverage tool, or confirmation of an already established rise. The report supplies historical tradeoffs and price-risk context. It does not supply an execution/exit/position-sizing/cost model or establish that purchasing after a signal is profitable.\n\nThe fixed research question is sufficiently specified to be closed after the stated verification. A universal winner is not required. Further threshold searches are not needed merely to obtain a stronger-looking result. A new prospective, point-in-time universe study would be needed for a materially stronger claim about future investability; that is a different objective and is not automatically started here. No operating alert, automated trade or order is changed by this research.\n')
    MAIN.write_text(readable_spacing('\n'.join(parts)),encoding='utf-8')
    write(OUT/'report-receipt.json',dict(report=str(MAIN),sha256=sha(MAIN),
          conditions=144,main_display_per_market=len(DISPLAY),cases=len(cases),
          primary_summary_sha256=sha(DOC/'primary-summary.csv'),
          matched_summary_sha256=sha(DOC/'matched-summary21.csv')))
    print(str(MAIN),len(MAIN.read_text(encoding='utf-8').splitlines()),'lines',flush=True)


if __name__=='__main__':main()
