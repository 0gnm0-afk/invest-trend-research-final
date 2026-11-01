"""Static research figures from validated CSVs, with exact plotted-data sidecars."""
from study import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

DOC=ROOT/'docs/research/uptrend-extension-2026-10-29'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'axes.axisbelow':True,'grid.alpha':.18,'figure.facecolor':'white','savefig.facecolor':'white'})
LABELS={'supertrend':'Supertrend flip','psar':'Parabolic SAR','trix_zero':'TRIX zero cross','trix_signal':'TRIX signal cross','stochrsi20':'StochRSI K20','stochrsi_cross':'StochRSI low K/D','rmi30':'RMI30','rmi50':'RMI50','chaikin':'Chaikin zero cross','avwap_quarter':'Quarter AVWAP proxy','volume_osc':'Volume osc. + up day','rsi30':'RSI30 [prior]','cci-100':'CCI -100 [prior]','cci_recovery':'CCI + falling MA20 [prior]','macd_rsi40':'MACD + RSI40 [prior]','price5':'Close / SMA5 [prior]'}

def save(fig,name):
    fig.savefig(DOC/name,dpi=170,bbox_inches='tight');plt.close(fig)

def tradeoff(m):
    d=pd.read_csv(DOC/'primary-summary.csv');d=d[d.market==m].copy();d['order']=d.id.map({b['id']:j for j,b in enumerate(BASE)});d=d.sort_values('order');y=np.arange(len(d))
    fig,axes=plt.subplots(1,2,figsize=(14,8),sharey=True,gridspec_kw={'width_ratios':[1.15,1]});colors=['#137f82' if x else '#7c8590' for x in d.new]
    a=axes[0];a.barh(y,100*d.precision,color=colors,height=.64,alpha=.85);a.errorbar(100*d.precision,y,xerr=np.vstack([100*(d.precision-d.precision_low),100*(d.precision_high-d.precision)]),fmt='none',ecolor='#172b3a',capsize=2,lw=1)
    a.scatter(100*d.early_base,y,marker='|',s=100,color='#b74e23',zorder=5,label='Each signal\'s eligible-day baseline')
    for yy,(_,r) in zip(y,d.iterrows()):
        x=100*r.precision_high+.7
        if x<=100*r.early_base<=x+3.2:x=100*r.early_base+.8
        a.text(x,yy,f'{100*r.precision:.1f}%',va='center',fontsize=9,zorder=6)
    a.set_yticks(y,[LABELS[k] for k in d.id]);a.invert_yaxis();a.set_xlim(0,max(45,100*d.precision_high.max()+8));a.set_xlabel('Early precision: age 0–5 / ALL signals (%)');a.set_title('Accuracy, with marginal 95% intervals');a.legend(loc='lower right',fontsize=8,frameon=False)
    b=axes[1];b.barh(y,100*d.capture,color=colors,height=.64,alpha=.85);b.errorbar(100*d.capture,y,xerr=np.vstack([100*(d.capture-d.capture_low),100*(d.capture_high-d.capture)]),fmt='none',ecolor='#172b3a',capsize=2,lw=1)
    for yy,(_,r) in zip(y,d.iterrows()):b.text(101,yy,f'{r.mean_delay:.2f}d  |  {r.annual:.1f}/yr',va='center',fontsize=9)
    b.set_xlim(0,137);b.set_xticks([0,25,50,75,100]);b.set_xlabel('Eligible completed rises captured (%)');b.set_title('Coverage | first-hit delay and frequency')
    for a in axes:a.axhline(10.5,color='#c0c6cc',lw=1)
    fig.suptitle(f'{m}: extra indicators vs unchanged benchmarks',x=.06,ha='left',fontsize=17,fontweight='bold')
    fig.text(.06,.012,'TEST 2023-04–2025-09 (reused history). New events: teal; prior benchmarks: grey.\nIntervals span 3/6-month crossed stock/time bootstrap bounds. Delay is conditional on an early hit; frequency is per 252 eligible days.',fontsize=9,color='#45515d')
    fig.tight_layout(rect=[0,.055,1,.94]);save(fig,f'{m}-tradeoff.png');d.to_csv(DOC/f'{m}-tradeoff-data.csv',index=False)

def matched(m):
    d=pd.read_csv(DOC/'matched-summary21.csv');d=d[(d.market==m)&(d.scheme==3)].copy();d['order']=d.id.map({b['id']:j for j,b in enumerate(BASE)});d=d.sort_values('order');y=np.arange(len(d))
    fig,axes=plt.subplots(1,3,figsize=(16,8.5),sharey=True)
    for a,out,title in zip(axes,['gain05','loss05','return'],['Probability of +5% touch','Probability of −5% touch','Day 21 close / next open return']):
        v=d[out+'_difference']*100;lo=d[out+'_sim_low']*100;hi=d[out+'_sim_high']*100
        colors=['#137f82' if (l>0 or h<0) else '#647787' for l,h in zip(lo,hi)]
        for yy,x,l,h,c in zip(y,v,lo,hi,colors):a.plot([l,h],[yy,yy],color=c,lw=1.4);a.scatter(x,yy,color=c,s=24)
        a.axvline(0,color='#aa4d34',lw=1);a.set_title(title,fontsize=11);a.set_xlabel('Signal minus matched non-signal (pp)');a.set_yticks(y,[LABELS[k] for k in d.id]);a.axhline(10.5,color='#c0c6cc',lw=1)
    axes[0].invert_yaxis()
    for yy,s,v in zip(y,d.support,d.max_abs_smd):axes[2].text(1.03,yy,f'{100*s:.0f}% kept | SMD {v:.2f}',transform=axes[2].get_yaxis_transform(),va='center',fontsize=9)
    fig.suptitle(f'{m}: additional 21-day information after strict observable-state matching',x=.04,ha='left',fontsize=15,fontweight='bold')
    fig.text(.04,.012,'ALL signals; no retrospective L1 filter. Entry reference: next valid open; bars 1–21 for touches, close 21 for terminal return.\nFamily-adjusted intervals cover 3,072 comparisons and both 3/6-month blocks. Kept=matched support; SMD=max residual standardized state difference.\nA +5% touch is an excursion, not obtainable profit. A negative loss-touch difference means lower measured downside incidence.',fontsize=9,color='#45515d')
    fig.tight_layout(rect=[0,.077,1,.94]);save(fig,f'{m}-matched.png');d.to_csv(DOC/f'{m}-matched-data.csv',index=False)

def cases(m):
    d=pd.read_csv(DOC/'illustrated-cases.csv');d=d[d.market==m];rr={(r['market'],r['symbol']):r for r in records()};data=[]
    fig,axes=plt.subplots(3,2,figsize=(14,10),sharex=True)
    keys=list(dict.fromkeys(d.id));kinds=['early_success','not_early','late']
    for col,key in enumerate(keys[:2]):
        for row,kind in enumerate(kinds):
            a=axes[row,col];r=d[(d.id==key)&(d.kind==kind)].iloc[0];z=load(rr[(m,str(r.symbol))]);t=int(r['index']);ix=np.arange(t-30,t+64);x=ix-t;ref=z['open'][t+1];lab=labels(z['full'],z['segment'])
            a.plot(x,z['close'][ix]/ref*100,color='#203e57',lw=1.2,label='Close');a.plot(x,np.exp(z['full'][ix])/ref*100,color='#d68d31',lw=1.2,label='Retrospective L1 trend')
            for s,e in zip(lab['starts'],lab['ends']):
                if e-s>=10 and s<=ix[-1] and s+5>=ix[0]:a.axvspan(max(s-t-.5,-30),min(s+5.5-t,63),color='#30a38e',alpha=.17)
            a.axvline(0,color='#ad3a36',ls='--',lw=1,label='Signal close');a.scatter(1,100,marker='o',s=18,color='#ad3a36',zorder=6);a.axhline(100,color='#84929c',ls=':',lw=.6)
            kindlabel={'early_success':'Early hit','not_early':'Outside completed uptrend','late':'Late confirmation'}[kind]
            a.set_title(f'{r.symbol} · {r.date} · {LABELS[key]}\n{kindlabel}; age {int(r.age)}; day 21 return {100*r.return21:+.1f}%',fontsize=10);a.set_xlim(-30,63)
            if col==0:a.set_ylabel('Price / next open ×100')
            if row==2:a.set_xlabel('Trading bars from signal close (0)')
            for j,xx in zip(ix,x):data.append(dict(market=m,id=key,kind=kind,symbol=r.symbol,signal_date=r.date,relative_bar=int(xx),date=z['date'][j],close_normalized=z['close'][j]/ref*100,l1_normalized=np.exp(z['full'][j])/ref*100))
    axes[0,0].legend(fontsize=8,loc='best',frameon=False);fig.suptitle(f'{m}: actual examples, selected near each group’s median 21-day return',x=.05,ha='left',fontsize=15,fontweight='bold')
    fig.text(.05,.012,'Illustrations, not a representative random sample or proof of a rule. Green shading marks retrospective ages 0–5 of completed ≥10-day rises.\nThe red dot is the next-open reference; all paths are normalized to 100 there. A confirmation failure can still be followed by a gain.',fontsize=9,color='#45515d')
    fig.tight_layout(rect=[0,.055,1,.94]);save(fig,f'{m}-cases.png');pd.DataFrame(data).to_csv(DOC/f'{m}-cases-data.csv',index=False)

if __name__=='__main__':
    for m in ['KR','US']:tradeoff(m);matched(m);cases(m)
    print('Six figures and six plotted-data CSVs saved.',flush=True)
