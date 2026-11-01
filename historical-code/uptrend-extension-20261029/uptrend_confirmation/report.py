"""Build the standalone human-readable research package from verified outputs."""
from study import *
from paths import focal
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import zipfile,shutil

DOC=ROOT/'docs/uptrend-confirmation-2026-10-23'
LABELS={'rsi30':'RSI30 recovery','rsi40':'RSI40 recovery','mfi20':'MFI20 recovery','cci-100':'CCI -100 recovery','stoch20':'Stochastic20 recovery','macd_signal':'MACD cross','macd_negative':'MACD cross below zero','macd_rsi40':'MACD + recent RSI40','cci_recovery':'CCI -100 + falling MA20','high20_volume':'20-day high + volume1.5','price5':'Close crosses SMA5','price20':'Close crosses SMA20'}
def label(k):
    if '__' in k:
        a,b=k.split('__');return label(a)+' / '+dict(and20='same-day >MA20',then20='then MA20 cross',persist3='3 closes >MA20')[b]
    return LABELS.get(k,k.replace('_',' '))
def p(x):return f'{100*x:.1f}%'
def pp(x):return f'{100*x:+.2f}pp'
def num(x):return f'{int(round(x)):,}'
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])
def collapse(df,keys):
    agg={c:('min' if c.endswith('low') else 'max' if c.endswith('high') or c=='adjusted_p' else 'first') for c in df.columns if c not in keys+['block_months']}
    return df.groupby(keys,sort=False).agg(agg).reset_index()

def main():
    audit=json.loads((DOC/'verification-final.json').read_bytes());assert audit['status']=='PASS'
    allstats=pd.read_csv(DOC/'evaluate-metrics.csv');stats=allstats[allstats.period=='test'].set_index(['market','id'])
    base=collapse(pd.read_csv(DOC/'base-rates.csv'),['market','id','state']).set_index(['market','id','state'])
    ci=collapse(pd.read_csv(DOC/'classification-intervals.csv'),['market','id','metric']).set_index(['market','id','metric'])
    match=collapse(pd.read_csv(DOC/'matched-paths.csv'),['market','id','scheme','horizon','outcome']).set_index(['market','id','scheme','horizon','outcome'])
    dist=pd.read_csv(DOC/'path-distributions.csv').set_index(['market','id','population','horizon','outcome'])
    balance=pd.read_csv(DOC/'balance.csv');chosen=json.loads((OUT/'frozen.json').read_bytes());cases=pd.read_csv(DOC/'illustrated-cases.csv')
    content=['# Already rising, but still early: KR and US confirmation signals',
    '\n'+(DOC/'summary.md').read_text(encoding='utf-8'),
    '\nResearch date: 2026-10-23. Offline historical study. No alerts, portfolio rules or orders changed. The final interpretive conclusions are in **Conclusion and stopping decision** below. Every probability is conditional on this stored, survivorship-affected sample and fixed retrospective L1 definition.',
    '\n## Reading guide for Chat',
    '\nThe question is **which observable signals tell us that an uptrend has already begun, while it is still within its first six trading dates?** It is not a forecast of an uptrend that has not started, and not a test of a profitable buy rule. Think of a departure board: a useful early confirmation says the train has just departed. A rare bell is not automatically accurate; a bell that rings throughout the journey can identify movement while being poor at identifying departure. A high after-entry price is scenery seen along the journey, not a profit an investor necessarily captured.',
    '\nRead three different questions separately: (1) **precision**—among ALL emitted signals, how many were at ages0..5 of a completed≥10-day rise? (2) **capture**—among actual eligible rises, how many received at least one early signal? (3) **future information**—after ALL signals, did price paths differ from observable-state-matched non-signal days? The third comparison never selects on future L1 success. “Lift” is precision/base rate, not a success probability.',
    '\n## Fixed research design and scope',
    '\nWe reused the exact input inventory and verified price/L1 caches from the downtrend research: KR2,611 investigated identities/2,584 usable histories and US4,815/4,653; 28,964,126 usable OHLCV bars in total. Archive upper date is2026-09-30, earliest stored dates1975-01-04(KR)/1990-01-02(US). This is all of that stored research universe without capitalization/liquidity screening. It is NOT every stock that existed historically, nor newly collected data through the research date. Current-listing survivorship, incomplete delisting coverage, provider-adjusted prices and corporate-action/volume uncertainty remain. Prior excluded identities and source gaps are preserved.',
    '\nL1 minimizes `0.5*sum((log(C)-x)^2)+1*sum(abs(diff(x,2)))`, using the inherited solver and primal-dual gap<1e-8. Date t has edge slope `x[t+1]-x[t]`. **Up>+1e-6; down<−1e-6; flat includes both boundaries.** Twenty-day compounded boundaries are +0.00200002% and −0.00199998%, not±0.2% or±2%. These are almost sign boundaries, not a minimum economically meaningful trend. A completed rise has finite non-up boundaries at both ends; no bridging flats or gaps. Duration counts positive edges. The first edge date is age0, so0..5 contains SIX dates. L1 uses future observations and is only the retrospective label.',
    '\nTRAIN is2016–2021, using cached fits truncated at2022-12-31; TEST is2023-04-01–2025-09-30 using longer historical fits. The one-year labeling buffer and later evaluation start prevent TEST prices from influencing selection fits. This TEST was already examined in previous work: **temporal reassessment of reused history, not untouched independent validation**. All-history results overlap TRAIN/TEST and must not be summed as separate samples.',
    '\nForty-seven fixed single events received the same selection opportunity. Moving averages, oscillators, momentum, price/volume, trend strength, bands, candles, causal confirmed pivots and drawdown recovery were included. Parameters were conventional and frozen before calculation. Among non-control events with≥500 TRAIN signals,≥100 signal stocks and≥10% capture, choose highest precision, then highest capture among remaining events with at least80% of that precision. No rarity cap, bonus or post-result threshold tuning. This selected **KR: RSI30 and MFI20; US: RSI30 and CCI−100**. The rule does not guarantee the second event has greater capture than the first; KR illustrates that limitation.',
    '\nOnly those two selected events per market received three follow-ups: same-day close>SMA20; first SMA20 upward crossing by base+5; or first three consecutive closes>SMA20 starting no earlier than base and completing by+5. New base signals rearm the clocks. The final confirmation day is the signal day. Fixed MACD+recent RSI40, below-zero MACD, CCI recovery/falling MA20 and high20/volume anchors and four maintained-state comparators were also frozen before TEST. Sixty-one conditions per market are disclosed; no TEST winner was silently promoted into the TRAIN selection.',
    '\n[Pre-calculation protocol](uptrend-confirmation-2026-10-23/protocol.json) · [protocol/hash receipt](uptrend-confirmation-2026-10-23/protocol-receipt.json) · [selection receipt](uptrend-confirmation-2026-10-23/selection-receipt.json) · [source access and implementation notes](uptrend-confirmation-2026-10-23/source-review-note.md).',
    '\n### Exact conditions of the main signals',
    table(['Signal','Causal condition at close t'],[
    ['RSI30 / RSI40','Wilder RSI14 crosses UP through30/40. RSI=100*smoothed positive close change/(smoothed gain+loss);14-day seed and recursive13/14 smoothing. Flat gain+loss=0 gives50.'],
    ['MFI20','14-day money-flow index crosses UP through20. Typical price TP=(H+L+C)/3; TP*V is assigned to positive or negative flow by TP versus previous TP. MFI=100*positive14sum/(positive+negative14sum).'],
    ['CCI−100','CCI20=(TP−SMA20(TP))/(0.015*20-day mean absolute deviation from that window mean) crosses UP through−100.'],
    ['MACD+recent RSI40','MACD=EMA12(C)−EMA26(C) crosses UP through EMA9(MACD) today; RSI14 crossed UP through40 on t,t−1 or t−2. Signal occurs today, not on the earlier RSI day.'],
    ['MACD below zero','Same MACD signal-line upward crossing, with MACD[t]<0. The sign is the MACD value, not the daily return.'],
    ['CCI recovery/falling MA20','CCI−100 event today AND SMA20[t]<SMA20[t−5].'],
    ['Stochastic20','RawK=100*(C−min L14)/(max H14−min L14), slowK=SMA3(rawK); slowK crosses UP through20. Not K/D crossing.'],
    ['High20+volume','First day C>max high of preceding20 bars, AND V>=1.5*mean V of preceding20 bars. Today is excluded from both reference windows.'],
    ['Price5 / Price20','Close crosses UP through current SMA5/SMA20; maintained C>SMA is a separate state.']]),
    '\nUpward crossing uses today difference>1e−12*max(abs(a),abs(b)) and yesterday difference<=yesterday tolerance. EMA uses recursive adjust=False/min_periods equal to span, as inherited. All indicators reset at source gaps and have at least65 prior bars; longer lookbacks retain their extra warmup. No future-confirmed pivot is visible before its two right-hand bars have actually closed.']
    focus={}
    for m in ['KR','US']:
        ids=list(dict.fromkeys(chosen[m]+['macd_rsi40','macd_negative','cci-100','cci_recovery','rsi40','stoch20','price5','price20','high20_volume']));focus[m]=ids
        content+=['\n## '+m+': accuracy, speed and coverage','\nAll signals, including signals before the uptrend, remain in the precision denominator. Capture counts each episode once; delay is the first successful signal within that episode. Misses have no fabricated zero delay. Intervals below are the union of pointwise95% intervals using3/6-month blocks.']
        rr=[]
        for key in ids:
            r=stats.loc[m,key];b=base.loc[m,key,'early0_5'];rr.append([label(key),num(r.signals),p(r.precision),f'[{100*b.precision_low:.1f}, {100*b.precision_high:.1f}]%',p(b.base_rate),f'{b.lift:.2f}x',p(r.capture),f'{r.mean_delay:.2f}',f'{r.annual:.2f}'])
        content.append(table(['Signal','N','Early precision','95%','Early base','Lift','Capture','First delay(days)','Per252 eligible days'],rr))
        rr=[]
        for key in list(dict.fromkeys(chosen[m]+['macd_rsi40','cci_recovery'])):
            intervals=[]
            for metric in ['capture','mean_delay','annual','first_rise']:
                a=ci.loc[m,key,metric];scale=100 if metric in ['capture','first_rise'] else 1
                intervals.append(f'{scale*a.estimate:.2f} [{scale*a.low:.2f}, {scale*a.high:.2f}]')
            rr.append([label(key)]+intervals)
        content+=['\nUncertainty also affects coverage, delay, frequency and the move already missed. The following are point estimates with pointwise95% intervals (union of both block lengths); delay and already-risen are conditional on a first successful confirmation.',table(['Signal','Capture (%)','First delay (days)','Events per252 days','Already risen at first next-open (%)'],rr)]
        content.append('\n![Accuracy and base rates](uptrend-confirmation-2026-10-23/'+m+'-accuracy.png)')
        rr=[]
        for key in ids:
            r=stats.loc[m,key];b=base.loc[m,key,'whole_up_ge10'];rr.append([label(key),p(r.day0/r.signals),p(r.day1_5/r.signals),p(r.late/r.signals),p(r.short/r.signals),p(r.other/r.signals),p(r.before5/r.signals),f'{p(b.precision)} / {p(b.base_rate)}',f'[{100*b.difference_sim_low:+.1f},{100*b.difference_sim_high:+.1f}]pp'])
        content+=['\nEarly accuracy must not be confused with identifying the whole uptrend. The first five outcome columns below sum to100%; “pre5” is a subset of Other, not an additional category. Whole-up includes only completed≥10-edge rises here; including shorter completed rises is in the CSV.',table(['Signal','Day0','Days1–5','Late≥6','Short<10','Other','of which pre5','Whole-up precision/base','Whole-minus-base simultaneous95%'],rr)]
        rr=[]
        for key in ids:
            r=stats.loc[m,key];iv=ci.loc[m,key,'rate_difference'];rr.append([label(key),p(r.ordinary_rate),p(r.early_rate),f'{r.rate_ratio:.2f}x',f'[{100*iv.sim_low:+.2f},{100*iv.sim_high:+.2f}]pp',p(1-r.capture)])
        content+=['\nBoth event rates below use **one eligible stock-day**. Ordinary means non-up L1 days (down/flat), while the base rate above uses all label-evaluable days. This avoids comparing a six-day capture probability to a one-day occurrence probability.',table(['Signal','Ordinary daily rate','Early daily rate','Concentration','Rate difference simultaneous95%','Missed episodes'],rr)]
        rr=[]
        for key in chosen[m]:
            r0=stats.loc[m,key]
            for k in [key]+[key+'__'+x for x in ['and20','then20','persist3']]:
                r=stats.loc[m,k];rr.append([label(k),num(r.signals),p(r.precision),pp(r.precision-r0.precision),p(r.capture),pp(r.capture-r0.capture),f'{r.mean_delay:.2f}',f'{r.mean_delay-r0.mean_delay:+.2f}'])
        content+=['\n### Additional confirmation costs',table(['Condition','N','Precision','Δprecision','Capture','Δcapture','Delay','Δdelay'],rr),'\nChanges are descriptive comparisons, not separately proven improvements. The surviving episodes change when a filter is added; a lower mean delay does not mean the same episodes were confirmed earlier. The sequential conditions never backdate their signal to the base event.','\n![Speed/precision/capture](uptrend-confirmation-2026-10-23/'+m+'-tradeoff.png)']
        rr=[]
        for key in ['state_price5','state_price20','state_macd','state_macd_rsi40']:
            r=stats.loc[m,key];b=base.loc[m,key,'whole_up_ge10'];rr.append([label(key),p(r.precision),p(r.capture),p(b.precision),p(b.base_rate),f'{r.annual:.1f}'])
        content+=['\n### Maintained conditions are not new crossing events',table(['State, true on each qualifying day','Early precision','Capture','Whole-up precision','Whole-up base','Qualifying days/252'],rr),'\nA state can cover much of an uptrend and still be poor at locating its beginning. These rows were not eligible for selection.']
        sensitivity=pd.read_csv(DOC/'evaluate-sensitivity.csv');duration=pd.read_csv(DOC/'evaluate-duration.csv');rr=[]
        for key in list(dict.fromkeys(chosen[m]+['macd_rsi40'])):
            for _,r in sensitivity[(sensitivity.market==m)&(sensitivity.period=='test')&(sensitivity.id==key)].iterrows():rr.append([label(key),r.window,p(r.precision),p(r.capture),num(r.episodes)])
        content+=['\n### Onset-window sensitivity',table(['Signal','Window (inclusive)','Precision','Capture','Eligible rises'],rr)]
        rr=[]
        for key in chosen[m]:
            for _,r in duration[(duration.market==m)&(duration.period=='test')&(duration.id==key)&(duration.duration!='all')].iterrows():rr.append([label(key),r.duration,num(r.episodes),p(r.capture),f'{r.mean_delay:.2f}',p(r.first_rise)])
        content+=[table(['Signal','Retrospective duration','Eligible rises','Capture','Delay','Already risen(first hit)'],rr),'\nDuration is unknown at the signal date; these rows do not show an ability to predict how long a rise will last.']
        # Main all-signal and successful-only paths, same selected/anchor family.
        pathids=list(dict.fromkeys(chosen[m]+['macd_rsi40','macd_negative','cci_recovery','high20_volume','price5','price20']))
        rr=[]
        for key in pathids:
            rise=dist.loc[m,key,'early_hit',0,'already_rise'];a=dist.loc[m,key,'all',21,'return'];hit=dist.loc[m,key,'early_hit',21,'return']
            rr.append([label(key),f'{p(rise["mean"])} / {p(rise["median"])}',num(a.n),p(dist.loc[m,key,'all',21,'gain05']['mean']),p(dist.loc[m,key,'all',21,'loss05']['mean']),f'{p(a["mean"])} / {p(a["median"])}',p(hit['mean'])])
        content+=['\n### Price already paid, and what happened afterwards',table(['Signal','Already risen mean/median(all early-hit alerts)','All path N','Further+5% high probability','Further−5% low probability','21-day return mean/median(all)','21-day mean return(hits only)'],rr),'\nAll path outcomes start at **the next contiguous valid trading-day open**. For h=5/21/63, maxima/minima use bars t+1..t+h and the terminal return uses close[t+h]/open[t+1]−1. Already-risen uses that next open/onset close−1, only for early successes. Favorable excursion is max(0, max-high/next-open−1); adverse excursion is max(0, 1−min-low/next-open), reported as a positive loss depth. These extrema are not attainable returns. Positive and negative excursions can both occur in the same window. Distributions, tails,5%/10% thresholds and all three horizons are in path-distributions.csv; successful-only values are hindsight diagnostics, not the signal’s expected return.',
        '\n### Matched comparison: does the signal add future information?', '\nThe primary path population requires65 prior and63 subsequent contiguous valid bars and observable covariates, **without any L1 state/duration/completion criterion**. Thus its count differs from classification. Same-stock/same-quarter controls must be non-signal days for that exact condition. Both earlier and later controls in a quarter are allowed; this is historical comparison, not an executable real-time control-selection strategy.']
        rr=[]
        for key in pathids:
            for scheme in [2,3]:
                a=match.loc[m,key,scheme,21,'gain05'];b=match.loc[m,key,scheme,21,'loss05'];r=match.loc[m,key,scheme,21,'return']
                rr.append([label(key),str(scheme),p(a.support),f'{p(a.signal)} / {p(a.control)}',f'{pp(a.difference)} [{100*a.sim_low:+.2f},{100*a.sim_high:+.2f}]',f'{pp(b.difference)} [{100*b.sim_low:+.2f},{100*b.sim_high:+.2f}]',f'{pp(r.difference)} [{100*r.sim_low:+.2f},{100*r.sim_high:+.2f}]'])
        content.append(table(['Signal','Scheme','Supported','+5% high signal/control','Δgain probability [sim95%,pp]','Δloss probability [sim95%,pp]','Δterminal return [sim95%,pp]'],rr))
        rr=[]
        for key in [chosen[m][0],'macd_rsi40']:
            for h in [5,21,63]:
                a=dist.loc[m,key,'all',h,'return'];r=match.loc[m,key,3,h,'return']
                rr.append([label(key),h,p(dist.loc[m,key,'all',h,'gain05']['mean']),p(dist.loc[m,key,'all',h,'loss05']['mean']),p(dist.loc[m,key,'all',h,'favorable']['mean']),p(dist.loc[m,key,'all',h,'adverse']['mean']),f'{p(a["mean"])} / {p(a["median"])}',f'[{p(a.q10)}, {p(a.q90)}]',f'{pp(r.difference)} [{100*r.sim_low:+.2f},{100*r.sim_high:+.2f}]'])
        content+=['\nThe horizon changes both upside opportunity and downside exposure. All columns below use every path-eligible signal, not just early successes. Excursion means are path extrema; the final column is a strict matched terminal-return contrast, not a strategy return.',table(['Signal','Bars','P(high≥+5%)','P(low≤−5%)','Mean favorable excursion','Mean adverse excursion','Terminal mean/median','Terminal10th/90th percentile','Strict Δterminal [sim95%,pp]'],rr)]
        content+=['\nScheme0 matches MA20 five-day slope sign, close>MA20 and RSI≥50. Scheme1 adds ATR/close bins(2%,4%) and five-day return bins(−5%,0,5%). Scheme2 adds daily return bins(−3%,−1%,0,1%,3%). Scheme3 adds20-day return bins(−10%,−3%,0,3%,10%) and MA20-distance bins(−5%,−2%,0,2%,5%). These bins were fixed before results. Non-supported signals remain in the unpaired analysis; they are excluded only from the matched estimate. All four schemes, all horizons/outcomes and unsuccessful comparisons are disclosed.', '\n![Matched future information](uptrend-confirmation-2026-10-23/'+m+'-matched.png)']
        rr=[]
        for key in pathids:
            for scheme in [2,3]:
                b=balance[(balance.market==m)&(balance.id==key)&(balance.scheme==scheme)];worst=b.iloc[abs(b.standardized_difference).argmax()]
                core=b[b.covariate.isin(['atr_pct','return1','return5','return20','distance_ma20'])];w=core.iloc[abs(core.standardized_difference).argmax()]
                rr.append([label(key),scheme,f'{w.covariate}: {w.standardized_difference:+.3f}',f'{worst.covariate}: {worst.standardized_difference:+.3f}',num(w.control_days),num(w.control_effective_n)])
        content+=[table(['Signal','Scheme','Largest core SMD','Largest SMD(all7)','Distinct control days','Weighted control ESS'],rr),'\nSMD is the difference in weighted means divided by pooled standard deviation.0.1 is a diagnostic convention, not an optimized pass/fail rule. All7 include RSI and relative volume. Residual imbalance means the contrast cannot isolate a pure causal signal effect. Strict matching changes which signals remain; it must not be generalized to every alert or used to rank signals with different supported populations.']
        # figures
        plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
        fig,axs=plt.subplots(1,2,figsize=(12,6),sharey=True);yy=np.arange(len(ids))
        for ax,st,title in zip(axs,['early0_5','whole_up_ge10'],['Early ages0..5','Whole completed rise>=10']):
            bs=[base.loc[m,k,st] for k in ids];x=np.array([b.precision for b in bs])*100
            ax.errorbar(x,yy,xerr=[x-np.array([b.precision_low for b in bs])*100,np.array([b.precision_high for b in bs])*100-x],fmt='o',label='Signal precision / pointwise95%')
            ax.scatter([100*b.base_rate for b in bs],yy,marker='D',color='#dd8a24',label='Eligible-day base rate');ax.set_title(m+' — '+title);ax.set_xlabel('% of observations');ax.grid(axis='x',alpha=.2)
        axs[0].set_yticks(yy,[label(k) for k in ids]);axs[0].invert_yaxis();axs[1].legend(fontsize=8);fig.tight_layout();fig.savefig(DOC/f'{m}-accuracy.png',dpi=170);plt.close(fig)
        fig,ax=plt.subplots(figsize=(12,6));single=stats.loc[m];single=single[single.family.isin([b['family'] for b in BASE])]
        ax.scatter(single.mean_delay,single.precision*100,s=single.capture*450,alpha=.18,color='gray')
        point_number=0
        for key in chosen[m]:
            for tag in ['', '__and20','__then20','__persist3']:
                point_number+=1
                r=stats.loc[m,key+tag];ax.scatter(r.mean_delay,r.precision*100,s=80+450*r.capture,label=f'{point_number}. {label(key+tag)}\n    Capture {p(r.capture)}');ax.annotate(str(point_number),(r.mean_delay,r.precision*100),xytext=(6,6),textcoords='offset points',fontsize=9)
        ax.set(xlabel='First successful confirmation delay (trading days)',ylabel='Early precision (%)',title=m+' — speed, precision and episode capture');ax.grid(alpha=.2)
        ax.legend(loc='center left',bbox_to_anchor=(1.02,.5),fontsize=9,frameon=False,labelspacing=1.1)
        fig.tight_layout();fig.savefig(DOC/f'{m}-tradeoff.png',dpi=170);plt.close(fig)
        plotids=list(dict.fromkeys(chosen[m]+['macd_rsi40','macd_negative','cci_recovery','price5']));fig,axs=plt.subplots(1,3,figsize=(14,6),sharey=True)
        for ax,outcome,title in zip(axs,['gain05','loss05','return'],['+5% high probability','-5% low probability','Terminal price return']):
            for scheme,off,color in [(2,-.12,'#356e9e'),(3,.12,'#bd632b')]:
                bs=[match.loc[m,k,scheme,21,outcome] for k in plotids];x=np.array([b.difference*100 for b in bs]);y=np.arange(len(bs))+off
                ax.errorbar(x,y,xerr=[x-np.array([b.sim_low*100 for b in bs]),np.array([b.sim_high*100 for b in bs])-x],fmt='o',color=color,label=f'Scheme{scheme}',capsize=2)
            ax.axvline(0,color='gray',lw=1);ax.set_title(title);ax.set_xlabel('Signal minus control (percentage points)');ax.grid(axis='x',alpha=.2)
        axs[0].set_yticks(range(len(plotids)),[label(k) for k in plotids]);axs[0].invert_yaxis();axs[2].legend();fig.suptitle(m+' —21-day matched paths; simultaneous95% intervals');fig.tight_layout();fig.savefig(DOC/f'{m}-matched.png',dpi=170);plt.close(fig)
        mc=cases[cases.market==m];fig,axs=plt.subplots(2,3,figsize=(15,8),squeeze=False)
        recs={(r['market'],r['symbol']):r for r in records()}
        for ax,(_,case) in zip(axs.flat,mc.iterrows()):
            z=load(recs[m,str(case.symbol)]);t=int(case['index']);ix=np.arange(t-30,t+64);xx=ix-t;entry=z['open'][t+1]
            ax.plot(xx,100*z['close'][ix]/entry,label='Stored close');ax.plot(xx,100*np.exp(z['full'][ix])/entry,label='Retrospective L1',alpha=.7)
            ax.axvline(0,color='k',ls='--',label='Signal close');ax.axvline(1,color='#cc7722',ls=':',label='Next-open basis100');ax.axhline(100,color='gray',lw=.7)
            lab=labels(z['full'],z['segment'])
            for s,e in zip(lab['starts'],lab['ends']):
                if e-s>=10 and t-30<=s<=t+63:ax.axvspan(s-t,min(s+5,e-1)-t,color='#3c9965',alpha=.15)
            ax.set_title(f'{case.symbol} {case.date}\n{label(case.id)} | {case.kind}',fontsize=9);ax.set_xlabel('Trading bars relative to signal');ax.grid(alpha=.15)
        for ax in axs[:,0]:ax.set_ylabel('Price index (next open = 100)')
        axs[0,0].legend(fontsize=7);fig.suptitle(m+' —actual cases near group median21-day terminal return; not selected extremes');fig.tight_layout();fig.savefig(DOC/f'{m}-cases.png',dpi=170);plt.close(fig)
        content+=['\n### Actual examples','\nCases are selected near each group’s median21-day terminal return, with a continuous30-bar prehistory and63-bar future. They illustrate early success, non-early mismatch and late confirmation; they are not independent corroboration or recommendations. Green shading marks retrospective0..5 windows. The dashed line is the signal; the dotted line is the next-open price basis.','\n![Actual examples](uptrend-confirmation-2026-10-23/'+m+'-cases.png)',table(['Stock/date','Signal','Outcome class','L1 age/duration','21-day terminal return'],[[f'{r.symbol} / {r.date}',label(r.id),r.kind,f'{int(r.age)} / {int(r.duration)}',p(r.return21)] for _,r in mc.iterrows()])]
    ep=pd.read_csv(DOC/'endpoint-summary.csv');er=[]
    for _,r in ep[ep.kind=='prefix_vs_full'].iterrows():er.append([r.market,f'{r.distance_lo}..{r.distance_hi}' if r.distance_hi<100000 else '253+',num(r.both_known),p(r.early_disagree/r.both_known) if r.both_known else 'NA',num(r.prefix_unknown),num(r.long_unknown),f'{int(r.prefix_onsets)}/{int(r.long_onsets)}'])
    content+=['\n## Robustness, uncertainty and exclusions',
    '\nClassification requires65 contiguous prior bars,126 subsequent bars and a finite fit at t+126, plus feature warmup and completed up boundaries. Incomplete up runs are unknown, not automatically short/failures. Paths require63 subsequent bars and no L1 condition. These completeness requirements can exclude halted, delisted or newly listed stocks non-randomly. Invalid OHLC, zero-volume, declared missing sessions and calendar gaps>10 days break series. No filling or bridging. Selection/evaluation coverage gives excluded stock-days by reason; per-signal classification and all-path denominators are shown separately.',
    '\nThe audit reconciles a small further population difference: six KR early-hit condition records across six focal conditions lack complete observable matching covariates (relative volume), so they remain in classification but cannot enter the path population. This is not six independently identified stock-days. The US reconciliation has no such exclusions. No successful case was removed based on its subsequent return.',
    '\nThe0..3/0..5/0..10 window sensitivity and10–20/21–62/63+ duration groups are in evaluate-sensitivity.csv and evaluate-duration.csv. A0..10 window is truncated at the end of a10-day rise; duration groups are hindsight diagnostics, never signal inputs. Classification-yearly and equal-stock tables assess composition dependence;2023/2025 are partial years. None is a new independent dataset.',
    '\nUncertainty uses1,999 stock Poisson multiplier draws crossed with common calendar-month stationary-bootstrap weights. Mean3-month and6-month block results are both retained and reported as their union; larger adjusted p-values are used. All61 conditions×2 markets×3 precision-minus-base contrasts share a366-comparison simultaneous family. Early-versus-ordinary daily-rate contrasts use a separate122-comparison family. All focal signals×2 markets×4 matching schemes×3 horizons×8 outcomes share the matched-path family shown in paths-inference.json. Pointwise precision/capture intervals and simultaneous contrast intervals answer different questions.',
    '\nOverlapping future windows, repeated stocks, common calendar shocks and reused controls are not treated as independent coin tosses. Controls contribute a zero-sum first-order cell-mean influence in their actual month, preserving point estimates and adding comparison-mean uncertainty. Cells/support remain fixed; this is approximate conditional inference, not full rematching in every bootstrap. Only30 evaluation months exist, stationary assumptions may fail, and no bootstrap corrects source survivorship or cumulative historical data snooping.',
    '\nEndpoint checks refit40 deterministic hash-ordered eligible stocks per market at2020/2021/2023/2024 year ends and compare to the longer saved fit. They also compare TRAIN’s2022-ending fit to the full fit. Unknown boundaries remain unknown. Endpoint-summary.csv must be read with both-known counts, unknown counts and start-count changes, not just agreement among known observations.',
    table(['Market','Bars before prefix end','Both-known days','Early-label revision','Prefix unknown','Long-fit unknown','Prefix/long onsets'],er),
    '\n## Academic evidence and what it changed',
    '\nKim et al.(2009) anchors the exact L1 objective, not its predictive validity. Lo et al.(2000) motivates mechanical events and conditional-versus-baseline distributions. Sullivan et al.(1999) motivates frozen selection, dependent resampling and whole-family inference. Bajgrowicz & Scaillet(2012) motivates separating selected historical associations, persistence and trading costs. Jegadeesh & Titman(1993) and Moskowitz et al.(2012) support examining momentum as a distinct mechanism while warning against transporting multi-month portfolio/futures evidence to six-day stock onset recognition. We did not perform their portfolio tests or White’s profit Reality Check. [Paper-by-paper source and method map](uptrend-confirmation-2026-10-23/literature.md), with [source-access limits](uptrend-confirmation-2026-10-23/source-review-note.md).',
    '\n## Conclusion and stopping decision',
    '\n'+(DOC/'conclusion.md').read_text(encoding='utf-8'),
    '\n## Reproduction and audit package',
    '\n[CSV bundle](uptrend-confirmation-2026-10-23/results-csv.zip) · [reproduction instructions](../scripts/uptrend_confirmation/README.md) · [final verification](uptrend-confirmation-2026-10-23/verification-final.json) · [package verification](uptrend-confirmation-2026-10-23/verification-report.json) · [reproduction hashes](uptrend-confirmation-2026-10-23/reproduction-manifest.json) · [exact KR definitions](uptrend-confirmation-2026-10-23/KR-signal-definitions.csv) · [US definitions](uptrend-confirmation-2026-10-23/US-signal-definitions.csv).',
    '\nThe CSV bundle includes all61 conditions/market, TRAIN/TEST/all-history summaries, class decompositions, concentration/base-rate intervals, capture/delay/frequency intervals, duration/window sensitivity, four matched schemes and balance/ESS, all-signal versus early-hit path distributions, yearly/equal-stock results, endpoints and actual case dates. Runtime contains per-stock input hashes/new causal features, sufficient statistics and the compressed all-signal path ledger. Proportions in CSV are fractions, not percentages. `evaluate-metrics` path columns are the label-evaluable subset; use `all-signal-paths`, `matched-paths`, `path-distributions` for the primary no-L1 analysis.',
    '\nVerification reconciles ledger counts with classifier successes and all-path sufficient statistics; checks synthetic label boundaries, leading-signal failures, delay completion, prefix causality, RSI/MA computations, direct price paths, matched non-signal membership and old-file hashes. Existing downtrend reports/code/results are preserved. No market collection, alerts, account reads, orders, deployment or remote publication occurred.']
    content.append(table(['Verified item','Count/result'],[['Protected prior files',f'{audit["original_files_unchanged"]} unchanged'],['All-signal ledger rows',num(audit['ledger_rows'])],['Direct horizon price checks',num(audit['scalar_horizon_checks'])],['Matched signal/control horizon checks',num(audit['matched_horizon_checks'])],['Independent date-label checks',num(audit['independent_label_checks'])],['Classification rows reconciled',num(audit['classification_rows'])],['TRAIN selection vs final evaluation totals','PASS'],['Prefix/synthetic checks','57,904 feature cells;9 synthetic groups PASS']]))
    (ROOT/'docs/uptrend-confirmation-2026-10-23.md').write_text('\n\n'.join(content)+'\n',encoding='utf-8')
    with zipfile.ZipFile(DOC/'results-csv.zip','w',compression=zipfile.ZIP_DEFLATED) as zz:
        for file in sorted(DOC.glob('*.csv')):zz.write(file,file.name)
    print('report written',len(content),'blocks',flush=True)

if __name__=='__main__':main()
