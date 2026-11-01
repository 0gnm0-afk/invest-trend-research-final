"""Inspectable merged tables and five static scientific figures.

No analysis or candidate selection happens here. All figures use fixed IDs,
validated result tables and exact plotted-data sidecars. Completion is recorded
only after every required source, shape and numerical reconciliation passes.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import PercentFormatter, StrMethodFormatter

ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'runtime/uptrend-longhistory-20261029'
DOC=ROOT/'docs/research/uptrend-longhistory-2026-10-29'
REQUIRED=['evaluate-metrics.csv','base-rates.csv','classification-intervals.csv',
          'classification-eras.csv','matched-paths.csv','balance.csv',
          'classification-inference.json','paths-inference.json',
          'evaluate-errors.json','paths-errors.json']
FOCUS=['rmi30','macd_rsi40','cci_recovery','rsi30','price5','supertrend','psar','stochrsi20']
DOZEN=FOCUS+['mfi20','cci-100','high20_volume','price20']
ERAS=['rmi30','macd_rsi40','cci_recovery','rsi30','price5','supertrend']
OUTCOMES=['gain05','gain10','loss05','loss10','favorable','adverse','return','positive_return']
COVS=['atr_pct','return1','return5','return20','distance_ma20','rsi14','relative_volume']
LABELS={'rmi30':'RMI30 recovery','macd_rsi40':'MACD + recent RSI40',
        'cci_recovery':'CCI recovery / falling MA20','rsi30':'RSI30 recovery',
        'price5':'Close crosses SMA5','supertrend':'Supertrend bullish flip',
        'psar':'Parabolic SAR reversal','stochrsi20':'StochRSI K20 recovery',
        'mfi20':'MFI20 recovery','cci-100':'CCI -100 recovery',
        'high20_volume':'20-bar breakout + volume','price20':'Close crosses SMA20'}
SHORT={'rmi30':'RMI30','macd_rsi40':'MACD + RSI40','cci_recovery':'CCI + falling MA20',
       'rsi30':'RSI30','price5':'SMA5 cross','supertrend':'Supertrend',
       'psar':'Parabolic SAR','stochrsi20':'StochRSI K20'}
COLORS=dict(zip(FOCUS,['#007f73','#315f9c','#a55c18','#884c91','#5c6873','#b83d51','#66832c','#357a9b']))
MARKETS={'KR':'Korea','US':'United States'}
STYLE={'font.family':'DejaVu Sans','font.size':11,'axes.titlesize':13,
       'axes.labelsize':11,'axes.spines.top':False,'axes.spines.right':False,
       'axes.grid':True,'axes.axisbelow':True,'grid.alpha':.18,
       'figure.facecolor':'white','savefig.facecolor':'white','legend.frameon':False}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_ready():
    missing=[f for f in REQUIRED if not (RUN/f).is_file()]
    missing += [f for f in ['coverage-years.csv','coverage-summary.json'] if not (DOC/f).is_file()]
    if missing:raise RuntimeError('Source outputs incomplete: '+', '.join(missing))
    for f in ['evaluate-errors.json','paths-errors.json']:
        assert not json.loads((RUN/f).read_bytes()),f
    c=json.loads((RUN/'classification-inference.json').read_bytes())
    p=json.loads((RUN/'paths-inference.json').read_bytes())
    assert c['conditions_per_market']==72 and c['family']==432 and set(c['blocks'])=={3,6}
    assert p['family']==4896 and set(p['blocks'])=={3,6}
    assert sum(len(v) for v in p['focal'].values())==51
    return c,p


def envelope(g,lo,hi):
    assert set(g.block_months)=={3,6} and len(g)==2
    return float(g[lo].min()),float(g[hi].max())


def constant(g,key):
    a=g[key].to_numpy();np.testing.assert_allclose(a,np.repeat(a[:1],len(a)),equal_nan=True,rtol=1e-10,atol=1e-12)
    return a[0]


def summaries():
    raw=pd.read_csv(RUN/'evaluate-metrics.csv')
    primary=raw[raw.period=='primary'].copy()
    assert len(primary)==144 and primary.groupby('market').size().to_dict()=={'KR':72,'US':72}
    assert not primary.duplicated(['market','id']).any()
    base=pd.read_csv(RUN/'base-rates.csv');ci=pd.read_csv(RUN/'classification-intervals.csv')
    assert len(base)==864 and len(ci)==2304
    blookup={(m,k,st):g for (m,k,st),g in base.groupby(['market','id','state'],sort=False)}
    ilookup={(m,k,metric):g for (m,k,metric),g in ci.groupby(['market','id','metric'],sort=False)}
    records=[];mismatches=[]
    for r in primary.to_dict('records'):
        m,k=r['market'],r['id']
        for state,prefix in [('early0_5','early'),('whole_up_ge10','whole'),('whole_up_any','whole_any')]:
            g=blookup[m,k,state]
            for col in ['precision','base_rate','difference','lift']:
                r[prefix+'_'+col]=float(constant(g,col))
            r[prefix+'_precision_low'],r[prefix+'_precision_high']=envelope(g,'precision_low','precision_high')
            r[prefix+'_difference_sim_low'],r[prefix+'_difference_sim_high']=envelope(g,'difference_sim_low','difference_sim_high')
            r[prefix+'_adjusted_p_conservative']=float(g.adjusted_p.max())
            assert int(constant(g,'signals'))==int(r['signals'])
            assert int(constant(g,'eligible_days'))==int(r['known'])
        np.testing.assert_allclose(r['early_precision'],r['precision'],rtol=1e-10)
        r['precision_low'],r['precision_high']=r['early_precision_low'],r['early_precision_high']
        for metric in ['capture','mean_delay','annual','first_rise','early_daily_rate','ordinary_daily_rate','rate_difference','rate_ratio']:
            g=ilookup[m,k,metric];point=float(constant(g,'estimate'))
            if metric in r and np.isfinite(r[metric]) and np.isfinite(point):
                delta=abs(r[metric]-point);assert delta<1e-5,(m,k,metric,delta)
                mismatches.append(delta)
            r[metric+'_low'],r[metric+'_high']=envelope(g,'low','high')
            if metric not in r:r[metric]=point
            if metric=='rate_difference':
                r['rate_difference_sim_low'],r['rate_difference_sim_high']=envelope(g,'sim_low','sim_high')
                r['rate_difference_adjusted_p_conservative']=float(g.adjusted_p.max())
        for category in ['day0','day1_5','late','short','other','before5']:
            r[category+'_precision']=r[category]/r['signals'] if r['signals'] else np.nan
        r['early_base']=r['early_base_rate'];r['whole_base']=r['whole_base_rate']
        r['interval_convention']='Envelope of3/6-month block bounds; pointwise precision/misc; simultaneous state-minus-base family432'
        records.append(r)
    primary=pd.DataFrame(records)
    np.testing.assert_allclose(primary.signals,primary.early+primary.late+primary['short']+primary.other)
    matched=pd.read_csv(RUN/'matched-paths.csv');balance=pd.read_csv(RUN/'balance.csv')
    mm=matched[matched.horizon==21].copy();assert len(mm)==3264
    blo={(m,k,s):g for (m,k,s),g in balance.groupby(['market','id','scheme'],sort=False)}
    combined=[]
    for (m,k,s),g in mm.groupby(['market','id','scheme'],sort=False):
        assert len(g)==16 and set(g.outcome)==set(OUTCOMES)
        r=dict(market=m,id=k,scheme=int(s),horizon=21)
        for col in ['all_signals','matched_signals','support']:
            r[col]=float(constant(g,col))
        b=blo[m,k,s];assert set(b.covariate)==set(COVS) and len(b)==7
        for col in ['control_days','control_effective_n']:
            r[col]=float(constant(b,col))
        np.testing.assert_allclose(constant(b,'matched_signals'),r['matched_signals'],rtol=1e-7,atol=1e-5)
        r['max_abs_smd']=float(b.standardized_difference.abs().max())
        r['largest_imbalance_covariate']=b.loc[b.standardized_difference.abs().idxmax(),'covariate'] if b.standardized_difference.notna().any() else None
        for _,bb in b.iterrows():r['smd_'+bb.covariate]=bb.standardized_difference
        for endpoint in OUTCOMES:
            o=g[g.outcome==endpoint]
            for col in ['signal','control','difference']:r[endpoint+'_'+col]=float(constant(o,col))
            r[endpoint+'_low'],r[endpoint+'_high']=envelope(o,'low','high')
            r[endpoint+'_sim_low'],r[endpoint+'_sim_high']=envelope(o,'sim_low','sim_high')
            r[endpoint+'_adjusted_p_conservative']=float(o.adjusted_p.max())
        r['interpretation_scope']='Supported signals only; no retrospective L1 filter in matching population'
        r['interval_convention']='Envelope of3/6-month block bounds; simultaneous family4896; fixed cells and approximate control influence'
        combined.append(r)
    matched=pd.DataFrame(combined);assert len(matched)==204 and matched.groupby('market').size().to_dict()=={'KR':104,'US':100}
    assert matched.support.between(0,1).all()
    assert primary.groupby('market').apply(lambda g:(g.kind=='event').sum(),include_groups=False).to_dict()=={'KR':68,'US':68}
    primary.to_csv(DOC/'primary-summary.csv',index=False,encoding='utf-8-sig')
    matched.to_csv(DOC/'matched-summary21.csv',index=False,encoding='utf-8-sig')
    return primary,matched,dict(primary_rows=144,matched21_rows=204,max_rounding_difference=max(mismatches,default=0))


def save(fig,name,data):
    fig.savefig(DOC/(name+'.png'),dpi=190,bbox_inches='tight')
    plt.close(fig)
    data.to_csv(DOC/(name+'-data.csv'),index=False,encoding='utf-8-sig')


def title(fig,heading,note,top=.94,bottom=.12):
    fig.suptitle(heading,x=.055,y=.985,ha='left',fontsize=17,fontweight='bold',color='#243644')
    fig.text(.055,.015,note,ha='left',va='bottom',fontsize=10,color='#44515a',linespacing=1.4)
    fig.tight_layout(rect=[.02,bottom,.99,top])


def tradeoff(d):
    shown=d[d.kind=='event'].copy();shown['highlighted']=shown.id.isin(FOCUS)
    fig,axs=plt.subplots(1,2,figsize=(15,7.3),sharex=True,sharey=True)
    ymax=max(35,math.ceil(100*shown.early_precision_high.max()/5)*5)
    for ax,m in zip(axs,['KR','US']):
        a=shown[shown.market==m]
        ax.scatter(a.capture*100,a.precision*100,s=25,c='#a6afb7',alpha=.60,edgecolors='white',linewidths=.4,zorder=2)
        selected=a.set_index('id').loc[FOCUS]
        # Label slots make names legible without moving the underlying points.
        order=selected.sort_values('precision')
        positions={};last=-100
        for key,r in order.iterrows():
            yp=max(float(r.precision*100),last+2.0);positions[key]=yp;last=yp
        overflow=max(positions.values())-(ymax-2)
        if overflow>0:positions={k:y-overflow for k,y in positions.items()}
        for key,r in selected.iterrows():
            x,y=r.capture*100,r.precision*100
            ax.plot([100*r.capture_low,100*r.capture_high],[y,y],color=COLORS[key],lw=1,alpha=.8)
            ax.plot([x,x],[100*r.precision_low,100*r.precision_high],color=COLORS[key],lw=1,alpha=.8)
            ax.scatter(x,y,s=45,color=COLORS[key],edgecolor='white',linewidth=.7,zorder=5)
            tx=x-6 if x>70 else x+6
            ax.annotate(SHORT[key],xy=(x,y),xytext=(tx,positions[key]),textcoords='data',fontsize=10,
                        color=COLORS[key],va='center',ha='right' if x>70 else 'left',arrowprops=dict(arrowstyle='-',color=COLORS[key],alpha=.65,lw=.65),
                        bbox=dict(boxstyle='square,pad=.10',facecolor='white',edgecolor='none',alpha=.87))
        ax.set_title(MARKETS[m]);ax.set_xlim(0,100);ax.set_ylim(0,ymax)
        ax.set_xlabel('Completed rises captured in ages 0–5 (%)')
        ax.xaxis.set_major_formatter(PercentFormatter(100));ax.yaxis.set_major_formatter(PercentFormatter(100))
    axs[0].set_ylabel('Early confirmation / all eligible signals (%)')
    title(fig,'Early accuracy and coverage are different objectives',
          'Primary period: Oct 2010–Sep 2025. Each grey dot is one of 68 fixed event conditions per market; four daily states are excluded.\n'
          'Eight named conditions were fixed before this figure. Error bars show envelopes of pointwise 95% stock/time-bootstrap bounds (3/6-month blocks).\n'
          'Capture counts completed ≥10-day upward episodes with at least one age 0–5 hit; these are not trade success rates.',bottom=.16)
    save(fig,'01-accuracy-capture',shown)


def precision_baseline(d):
    fig,axs=plt.subplots(1,2,figsize=(16,9.4),sharex=True,sharey=True)
    plot=[];ys=np.arange(len(DOZEN))
    for ax,m in zip(axs,['KR','US']):
        a=d[d.market==m].set_index('id').loc[DOZEN];plot.append(a.reset_index())
        for prefix,off,color,marker in [('early',-.16,'#007f73','o'),('whole',.16,'#315f9c','s')]:
            y=ys+off;x=100*a[prefix+'_precision']
            for yy,lo,hi in zip(y,100*a[prefix+'_precision_low'],100*a[prefix+'_precision_high']):ax.plot([lo,hi],[yy,yy],color=color,lw=1.4)
            ax.scatter(x,y,s=32,marker=marker,color=color,zorder=4)
            ax.scatter(100*a[prefix+'_base_rate'],y,s=95,marker='|',linewidth=1.7,color='#ac6d29' if prefix=='early' else '#818997',zorder=5)
        ax.set_yticks(ys,[LABELS[k] for k in DOZEN]);ax.set_title(MARKETS[m]);ax.set_xlim(0,100)
        ax.xaxis.set_major_formatter(PercentFormatter(100));ax.set_xlabel('Signals in the stated L1 status (%)')
        ax.grid(axis='y',alpha=.08)
    axs[0].invert_yaxis()
    handles=[Line2D([],[],marker='o',color='#007f73',ls='',label='Early ages 0–5 precision'),Line2D([],[],marker='s',color='#315f9c',ls='',label='Whole completed ≥10-day rise precision'),Line2D([],[],marker='|',ms=12,color='#ac6d29',ls='',label='Early eligible-day base rate'),Line2D([],[],marker='|',ms=12,color='#818997',ls='',label='Whole-rise eligible-day base rate')]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.52,.084),ncol=2,fontsize=10)
    title(fig,'Early concentration must be separated from whole-rise identification',
          'Oct 2010–Sep 2025; 12 fixed conditions. Precision uses all eligible signals, including pre-onset and other failures.\n'
          'Each base rate uses that condition’s eligible days. Whiskers span pointwise 95% bounds from both 3/6-month bootstrap settings.',bottom=.18)
    save(fig,'02-early-whole-baselines',pd.concat(plot,ignore_index=True))


def eras():
    allrows=pd.read_csv(RUN/'classification-eras.csv')
    d=allrows[allrows.id.isin(ERAS)].copy();assert len(d)==36
    order=sorted(d.period.unique());assert len(order)==3
    fig,axs=plt.subplots(1,2,figsize=(15,7.2),sharex=True,sharey=True)
    ymax=max(10,math.ceil(100*d.early_precision.max()/5)*5+5)
    linestyles=['-','--','-.',':',(0,(5,1,1,1)),(0,(3,1,1,1,1,1))]
    for ax,m in zip(axs,['KR','US']):
        for key,ls in zip(ERAS,linestyles):
            a=d[(d.market==m)&(d.id==key)].set_index('period').loc[order]
            ax.plot(np.arange(3),100*a.early_precision,marker='o',markersize=5,color=COLORS[key],lw=1.8,ls=ls,label=SHORT[key])
        ax.set_title(MARKETS[m]);ax.set_xticks(range(3),['Oct 2010–Sep 2015','Oct 2015–Sep 2020','Oct 2020–Sep 2025'])
        ax.set_xlabel('Prespecified five-year era');ax.set_xlim(-.15,2.15);ax.set_ylim(0,ymax)
        ax.yaxis.set_major_formatter(PercentFormatter(100))
    axs[0].set_ylabel('Early ages 0–5 / all eligible signals (%)')
    fig.legend(*axs[0].get_legend_handles_labels(),ncol=3,loc='lower center',bbox_to_anchor=(.52,.10),fontsize=10)
    title(fig,'Early precision across three fixed historical eras',
          'Six conditions fixed for display; each point is an independently pooled five-year estimate. Connecting lines are visual guides.\n'
          'Era values are descriptive and have no era-specific confidence bands. The period is previously inspected history, not a new holdout.',bottom=.22)
    save(fig,'03-fixed-eras',d)


def strict_paths(d):
    fig,axs=plt.subplots(2,2,figsize=(16,9.3),sharey=True,gridspec_kw={'width_ratios':[1.7,1]})
    ys=np.arange(len(FOCUS));plot=[]
    selected=d[(d.scheme==3)&d.id.isin(FOCUS)]
    maxbound=max(abs(selected.return_sim_low.min()),abs(selected.return_sim_high.max()))*100
    limit=max(.5,math.ceil(maxbound*2)/2)
    for row,m in enumerate(['KR','US']):
        a=selected[selected.market==m].set_index('id').loc[FOCUS];plot.append(a.reset_index())
        left,right=axs[row]
        for y,(key,r) in zip(ys,a.iterrows()):
            col=COLORS[key];marker='D' if r.max_abs_smd>.1 else 'o'
            left.plot([100*r.return_sim_low,100*r.return_sim_high],[y,y],color=col,lw=1.6)
            left.scatter(100*r['return_difference'],y,marker=marker,color=col,s=42,zorder=4)
            right.barh(y,100*r.support,height=.58,color=col,alpha=.70)
            right.text(101,y,f'{100*r.support:.1f}%   SMD {r.max_abs_smd:.2f}',va='center',fontsize=10)
        left.axvline(0,color='#555f68',lw=1);left.set_xlim(-limit,limit)
        left.set_yticks(ys,[SHORT[k] for k in FOCUS]);right.set_xlim(0,160);right.set_xticks([0,25,50,75,100]);right.xaxis.set_major_formatter(PercentFormatter(100))
        left.set_title(MARKETS[m]+' · terminal return difference');right.set_title(MARKETS[m]+' · matched support / residual balance')
        left.set_xlabel('Signal − matched non-signal, percentage points');right.set_xlabel('Share of path-eligible signals matched (%)')
    axs[0,0].invert_yaxis()
    title(fig,'Does the signal add information after strict observable-state matching?',
          'All path-eligible signals; no retrospective L1 success filter. Return = close on bar 21 / next valid open −1. Same stock and quarter; scheme 3.\n'
          'Intervals envelop simultaneous family-adjusted bounds across 4,896 endpoint contrasts and both 3/6-month blocks. Diamond: max |SMD| >0.10.\n'
          'SMD is residual state imbalance, not a significance test. Estimates apply only to matched support; fixed-cell control uncertainty is approximate.',bottom=.18)
    save(fig,'04-strict-matched-return',pd.concat(plot,ignore_index=True))


def coverage():
    d=pd.read_csv(DOC/'coverage-years.csv');summary=json.loads((DOC/'coverage-summary.json').read_bytes())
    fig,axs=plt.subplots(1,2,figsize=(15,6.3),sharey=True)
    ymax=math.ceil(d.usable_stock_years.max()/500)*500
    for ax,m in zip(axs,['KR','US']):
        a=d[d.market==m]
        ax.axvspan(2010.75,2025.75,color='#dbe6ee',alpha=.6,zorder=0)
        ax.plot(a.year,a.usable_stock_years,color='#8797a5',lw=1.8,label='Usable cached prices during year')
        ax.plot(a.year,a.evaluable_stocks,color='#007f73',lw=2,label='At least one generic eligible day')
        ax.set_title(MARKETS[m]+f" · {summary['markets'][m]['inventory']:,} stored records")
        ax.set_xlabel('Calendar year');ax.set_xlim(d.year.min(),2026.5);ax.set_ylim(0,ymax);ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
        ax.legend(loc='upper left',fontsize=10)
    axs[0].set_ylabel('Number of stocks with available observations')
    title(fig,'The available universe and usable history change over time',
          'Full available history by calendar year. Shading marks the 15-year primary window; first/last shaded years are partial in the main analysis.\n'
          'Generic eligibility applies 65-past /126-future continuity and completed-trend rules, before indicator-specific availability.\n'
          '2026 evaluation ends in March because of the future buffer. Saved stock coverage is not a survivorship-free historical listing census.',bottom=.20)
    save(fig,'05-history-coverage',d)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--check-only',action='store_true');args=ap.parse_args()
    receipts=check_ready()
    if args.check_only:print('All required sources and inference receipts are ready.');return
    plt.rcParams.update(STYLE);DOC.mkdir(parents=True,exist_ok=True)
    primary,matched,checks=summaries()
    tradeoff(primary);precision_baseline(primary);eras();strict_paths(matched);coverage()
    figures=['01-accuracy-capture','02-early-whole-baselines','03-fixed-eras','04-strict-matched-return','05-history-coverage']
    files=['primary-summary.csv','matched-summary21.csv']+[k+ext for k in figures for ext in ['.png','-data.csv']]
    result=dict(status='NUMERICAL_PASS_RENDERED_VISUAL_REVIEW_PENDING',checks=checks,figures=figures,
                primary_period='2010-10-01..2025-09-30',fixed_focus=FOCUS,fixed_dozen=DOZEN,fixed_era_conditions=ERAS,
                inputs={f:sha(RUN/f) for f in REQUIRED},outputs={f:sha(DOC/f) for f in files},code_sha256=sha(Path(__file__)),
                notes=['Pointwise bounds and simultaneous family bounds are kept separate.','Envelope lower=min across3/6; upper=max; conservative adjusted p=max.','No retrospective L1 condition enters the principal future-path sample.','Image inspection is a separate explicit step after rendering.'])
    (DOC/'artifacts-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Wrote144 primary rows,204 matched21 rows,5 figures and5 exact plotted-data sidecars; visual review pending.',flush=True)


if __name__=='__main__':main()
