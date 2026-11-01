"""Korean explanatory report, exact result CSVs and static research figures."""
from study import *
from catalog import definitions
import shutil,textwrap,zipfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.ticker import FuncFormatter
DEST=ROOT/'docs/downtrend-confirmation-2026-10-21'
MAIN=['macd_rsi60','macd_positive','cci100_up20','rsi60','stoch80','price5','low20_volume']
SHORT={'macd_rsi60':'MACD 데드＋최근3일 RSI60 이탈','macd_positive':'MACD 양수권 데드','cci100_up20':'CCI100 이탈＋MA20 상승','rsi60':'RSI60 이탈','stoch80':'스토캐스틱80 이탈','price5':'종가5일선 이탈(비교군)','low20_volume':'20일 저가 이탈＋거래량1.5배'}
def name(x):
    if '__' in x:
        b,v=x.split('__');return SHORT.get(b,b)+' / '+{'and20':'당일 MA20 아래','then20':'5일 내 MA20 이탈','persist3':'MA20 아래3일'}[v]
    return SHORT.get(x,x)
def pct(x):return '—' if pd.isna(x) else f'{x*100:.1f}%'
def pp(x):return '—' if pd.isna(x) else f'{x*100:+.1f}pp'
def num(x):return '—' if pd.isna(x) else f'{x:,.0f}'
def dec(x):return '—' if pd.isna(x) else f'{x:.2f}'
def table(df,cols):
    return '| '+' | '.join(t for k,t,fn in cols)+' |\n| '+' | '.join('---' for _ in cols)+' |\n'+'\n'.join('| '+' | '.join(fn(r[k]) for k,t,fn in cols)+' |' for _,r in df.iterrows())

def charts(df):
    font=FontProperties(fname='C:/Windows/Fonts/malgun.ttf');plt.rcParams.update({'font.family':font.get_name(),'axes.unicode_minus':False,'font.size':10})
    for m in ['KR','US']:
        d=df[(df.market==m)&df.id.isin(MAIN)].set_index('id').loc[MAIN].reset_index();yy=np.arange(len(d))
        fig,ax=plt.subplots(figsize=(12,6),layout='constrained')
        ax.barh(yy+.17,d.ordinary_rate*100,.32,label='상승·횡보 하루 발생률',color='#bbc4ce');ax.barh(yy-.17,d.early_rate*100,.32,label='하락 초입 하루 발생률',color='#246693')
        ax.set_yticks(yy,[name(x) for x in d.id]);ax.invert_yaxis();ax.set_xlabel('같은 단위: 신호 발생 종목일 / 평가 가능한 종목일 (%)');ax.set_title(m+' | 초입에 얼마나 집중되는가');ax.legend();fig.savefig(DEST/f'{m}-frequency.png',dpi=160);plt.close(fig)
        extra=df[(df.market==m)&df.id.str.contains('__')].sort_values('precision',ascending=False).head(2)
        d=pd.concat([d,extra]);yy=np.arange(len(d));fig,ax=plt.subplots(figsize=(12,6.3),layout='constrained')
        ax.errorbar(d.precision*100,yy,xerr=np.vstack([(d.precision-d.precision_low)*100,(d.precision_high-d.precision)*100]),fmt='o',color='#215e7a',capsize=3)
        ax.set_yticks(yy,[name(x) for x in d.id]);ax.invert_yaxis();ax.set_xlim(0,max(55,d.precision_high.max()*110));ax.axvline(50,ls=':',color='#999');ax.set_xlabel('모든 신호 중 실제0~5일 초입인 비율 (%) / 점별95% 군집 구간');ax.set_title(m+' | 경보를 받았을 때 얼마나 믿을 수 있는가');fig.savefig(DEST/f'{m}-precision.png',dpi=160);plt.close(fig)
        d=df[(df.market==m)&(df.id.isin(MAIN)|df.id.str.contains('__'))];fig,(ax,keyax)=plt.subplots(1,2,figsize=(13,7),gridspec_kw={'width_ratios':[2,1]},layout='constrained');keyax.axis('off')
        for k,r in enumerate(d.itertuples()):
            color='#ba5939' if '__' in r.id else '#246693'
            ax.scatter(r.mean_delay,r.precision*100,s=60+800*r.capture,color=color,alpha=.7,edgecolor='white')
            # Number labels avoid overlapping long Korean indicator names.
            ax.annotate(str(k+1),(r.mean_delay,r.precision*100),xytext=(5,4),textcoords='offset points',fontsize=9)
        legend='\n'.join(textwrap.fill(f'{i+1}. {name(x)}',width=28,subsequent_indent='   ') for i,x in enumerate(d.id));keyax.text(0,1,legend,transform=keyax.transAxes,va='top',fontsize=9)
        ax.set_xlim(-.1,5.3);ax.set_xlabel('포착한 하락에서 최초 확인까지 평균 거래일');ax.set_ylabel('전체 신호의 초입 적중률 (%)');ax.set_title(m+' | 속도·정확도·포착률의 교환관계\n원의 면적이 클수록 더 많은 하락 초입 포착; 주황=추가 확인');fig.savefig(DEST/f'{m}-tradeoff.png',dpi=160,bbox_inches='tight');plt.close(fig)
    cards=json.loads((OUT/'examples.json').read_bytes());exrows=[]
    for card in cards:
        rec=next(r for r in records() if r['market']==card['market'] and r['symbol']==card['symbol']);z=load(rec);t=card['index'];a=max(0,t-40);b=min(len(z['date']),t+64);x=np.arange(a,b);lab=labels(z['full'],z['segment']);fig,ax=plt.subplots(figsize=(12,5.5),layout='constrained')
        ax.plot(x,z['close'][x],label='저장 종가',color='#223a50');ax.plot(x,np.exp(z['full'][x]),label='사후 L1 추세',color='#d99435',lw=2)
        starts=lab['starts'][(lab['ends']-lab['starts']>=10)&(lab['starts']>=a)&(lab['starts']<b)]
        for i,start in enumerate(starts):ax.axvline(start,color='#26956c',ls='--',label='L1 하락 시작(사후)' if i==0 else None);ax.axvspan(start,min(start+5,b-1),color='#78c6a7',alpha=.18)
        ax.axvline(t,color='#b43144',label='신호 확인 종가일');ax.scatter([t+1],[z['open'][t+1]],marker='D',color='#6a4c93',label='다음 유효 거래일 시가',zorder=5)
        ax.axvspan(t+1,min(t+21,b-1),color='#b8b3d4',alpha=.12,label='이후21거래일 경로')
        ticks=x[::max(1,len(x)//7)];ax.set_xticks(ticks,z['date'][ticks],rotation=25);ax.yaxis.set_major_formatter(FuncFormatter(lambda v,pos:f'{v:,.0f}' if card['market']=='KR' else f'{v:,.2f}'))
        row=card['row'];ax.set_title(f"{card['market']} {card['symbol']} | {'초입 적중' if card['kind']=='success' else '목표 불일치'} | {row['signal_date']}\n{name(card['id'])} / 이후21일 종가수익률 {pct(row['return21'])}")
        ax.set_ylabel('KRW' if card['market']=='KR' else 'USD');ax.legend(loc='best',fontsize=9);fn=f"{card['market']}-{card['kind']}.png";fig.savefig(DEST/fn,dpi=160);plt.close(fig);exrows.append(dict(**row,kind=card['kind'],figure=fn))
    pd.DataFrame(exrows).to_csv(DEST/'illustrated-cases.csv',index=False,encoding='utf-8-sig')
    return cards

def main():
    DEST.mkdir(exist_ok=True);df=pd.read_csv(OUT/'test-results.csv');allr=pd.read_csv(OUT/'evaluate-metrics.csv');cov=pd.read_csv(OUT/'evaluate-coverage.csv');dur=pd.read_csv(OUT/'evaluate-duration.csv');dsig=pd.read_csv(OUT/'duration-signal-results.csv');yr=pd.read_csv(OUT/'evaluate-yearly.csv');sens=pd.read_csv(OUT/'evaluate-sensitivity.csv');end=pd.read_csv(OUT/'endpoint-summary.csv');exc=pd.read_csv(OUT/'excluded-signals.csv')
    df['ci']=df.apply(lambda r:f'{pct(r.precision_low)}~{pct(r.precision_high)}',axis=1);df['miss']=1-df.capture;df['missmatch']=1-df.precision
    # Medians/quantiles are from exact selected-event ledger, not averaged
    # stock medians; excursion is a descriptive fixed-horizon path statistic.
    ledger=pd.read_csv(OUT/'signal-ledger.csv.gz',usecols=['market','id','class','already_drop']+[f'{k}{h}' for h in [5,21,63] for k in ['return','low','high']]);pr=[]
    for (m,k),g in ledger.groupby(['market','id']):
        for pop,v in [('all',g),('hit',g[g['class']=='early'])]:
            rr=dict(market=m,id=k,population=pop,n=len(v))
            for col in ['already_drop']+[f'{a}{h}' for h in [5,21,63] for a in ['return','low','high']]:
                values=v[col].dropna();rr[col+'_n']=len(values);rr[col+'_mean']=values.mean();rr[col+'_median']=values.median();rr[col+'_p10']=values.quantile(.1);rr[col+'_p90']=values.quantile(.9)
            pr.append(rr)
    paths=pd.DataFrame(pr);paths.to_csv(DEST/'selected-price-paths.csv',index=False,encoding='utf-8-sig');del ledger
    cards=charts(df)
    for source,target in [('test-results.csv','all-signals-test.csv'),('evaluate-metrics.csv','all-periods.csv'),('evaluate-yearly.csv','yearly.csv'),('equal-stock-yearly.csv','equal-stock-yearly.csv'),('evaluate-duration.csv','duration-episodes.csv'),('duration-signal-results.csv','duration-signals.csv'),('evaluate-sensitivity.csv','early-window-sensitivity.csv'),('evaluate-coverage.csv','evaluation-coverage.csv'),('excluded-signals.csv','excluded-signals.csv'),('endpoint-summary.csv','endpoint-summary.csv'),('endpoint-details.csv','endpoint-details.csv'),('endpoint-fits.json','endpoint-fits.json'),('frozen.json','frozen-candidates.json'),('selection-receipt.json','selection-receipt.json'),('verification-synthetic.json','verification-synthetic.json'),('verification-detail.json','verification-detail.json')]:shutil.copyfile(OUT/source,DEST/target)
    shutil.copyfile(Path(__file__).with_name('protocol.json'),DEST/'protocol.json');pd.DataFrame(definitions()).to_csv(DEST/'signal-definitions.csv',index=False,encoding='utf-8-sig')
    basis=json.loads((OLD/'coverage.json').read_bytes());nfit=len(json.loads((OUT/'endpoint-fits.json').read_bytes())['fits'])
    main=df[df.id.isin(MAIN)].copy();main['sort']=main.id.map({x:i for i,x in enumerate(MAIN)});main=main.sort_values(['market','sort'])
    combo=df[df.id.str.contains('__')|df.id.isin(['macd_rsi60','macd_positive'])].copy();combo['base']=combo.id.str.split('__').str[0]
    base=combo[~combo.id.str.contains('__')].set_index(['market','id'])
    for i,r in combo.iterrows():
        b=base.loc[(r.market,r.base)];combo.loc[i,'precision_change']=r.precision-b.precision;combo.loc[i,'capture_change']=r.capture-b.capture;combo.loc[i,'delay_change']=r.mean_delay-b.mean_delay
    combo.to_csv(DEST/'confirmation-tradeoffs.csv',index=False,encoding='utf-8-sig')
    durshow=dur[(dur.period=='test')&dur.id.isin(['macd_rsi60','macd_positive'])&(dur.duration!='all')].merge(dsig,on=['market','id','duration']);durshow.to_csv(DEST/'duration-key-results.csv',index=False,encoding='utf-8-sig')
    parts=[]
    parts.append('''# 이미 시작된 하락의 초입을 얼마나 믿을 만하게 확인했는가

2026-10-21 · 한국·미국 전체 저장 자료 · 신호 발생일부터 추적한 추가 연구

이번 질문의 정답표는 **10거래일 이상 완료된 L1 하락의 시작 당일~+5일, 총6거래일**이다. 하락 전에 나온 신호도 전체 신호 수에 남기지만 적중으로 인정하지 않았다. 이전 보고서의 ‘시작 전후±5일’ 적중률과 숫자가 달라지는 것이 정상이다.

''')
    for m,label in [('KR','한국'),('US','미국')]:
        a=df[(df.market==m)&(df.id=='macd_rsi60')].iloc[0];b=df[(df.market==m)&(df.id=='macd_positive')].iloc[0];best=df[df.market==m].sort_values('precision',ascending=False).iloc[0]
        parts.append(f"**{label}:** 선정 기간에서 고정한 `MACD 데드＋최근3일 RSI60 이탈`은 전체 신호의 **{pct(a.precision)}**가 실제 초입이었다(95% 구간 {a.ci}). 실제 하락 초입의 **{pct(a.capture)}**를 발견했고 첫 확인은 평균 **{a.mean_delay:.2f}일** 뒤였다. `MACD 양수권 데드`는 적중률 **{pct(b.precision)}**, 포착률 **{pct(b.capture)}**로 더 많은 하락을 잡는 대신 정확도가 낮았다. 추가조건을 포함한 이번 비교의 최고 점추정도 **{pct(best.precision)}**였다.\n\n")
    parts.append('''**따라서 ‘평소 움직임보다 초입에 집중되는 후보’는 있지만, 경보 한 번만으로 하락 초입이라고 높은 확률로 확정할 신호를 찾았다고 결론 내리기는 어렵다.** 적중하지 않은 신호가 더 많다는 점과, 정확도를 높일수록 놓치는 하락이 늘어나는 점을 함께 봐야 한다. 이 결과는 매도 수익이나 회피 손실을 검증한 것이 아니다.

## 1. 무엇을 같은 기준으로 비교했나

L1 계산은 기존과 동일하게 `0.5 × Σ(log(C)-x)² + 1 × Σ|Δ²x|`를 최소화한다. λ=1, 수치해의 primal-dual gap<10⁻⁸을 유지했다. 날짜t의 방향은 **x[t+1]−x[t]**로 판정한다. `<−0.000001`이면 하락, `>+0.000001`이면 상승, 양 끝을 포함한 그 사이는 횡보다. 따라서 시작일t의 방향 자체가 다음 봉을 포함하는 **사후 판정**이다. 이 L1 상태는 어느 기술적 신호 조건에도 넣지 않았다. 원 L1 방법은 절대값 벌점으로 구간별 직선 추세를 얻는다. [원 논문 및 저자 설명](https://stanford.edu/~boyd/papers/l1_trend_filter.html).

20일 환산은 `100×(exp(20×기울기)−1)`이다. 경계는 하락 **−0.00199998%**, 상승 **+0.00200002%**로, 기억한 ±0.002%와 사실상 같다. **±0.2%나±2%가 아니다.** 아주 작은 부호 경계이므로, 이 기준의 ≥10일 하락이 모두 경제적으로 큰 하락이라는 뜻도 아니다. 하락끼리 임의로 연결하지 않았다.

연속 하락 기울기가10개면10거래일 하락으로 센다. 첫 하락 edge 날짜가0일이며, 초입은0·1·2·3·4·5일이다. 주 결과는 지속기간을 합친 ≥10일 하락이다. 10~20/21~62/63+일은 결과를 나눈 사후 보조 분류다.

원래63개 사건을 모두 재평가했다. 가격·이평·RSI·MACD·DMI/ADX·스토캐스틱·CCI·밴드·ATR·거래량·캔들·일목·다이버전스를 포함한다. 교차는 전일 조건의 반대쪽/경계에 있다가 오늘 아래로 넘어간 날이다. 계속 아래에 머무르는 날마다 다시 세지 않으며, 회복 후 재이탈하면 새 신호다. 갭·캔들 등 ‘그날의 모양’ 조건은 연속일에도 각각 센다. 추가한 지속 조건도 완성된 첫날 한 번만 센다. [정확한63개 산식과 후속조건 CSV](downtrend-confirmation-2026-10-21/signal-definitions.csv).

선정은 TRAIN(2016~2021)만 사용했다. 500신호·100종목 이상, 포착률10% 이상, 연환산20회 이하에서 적중률1위와 그 적중률의80% 이상인 후보 중 포착률1위를 골랐다. 5·10일선 단순 이탈 계열은 비교군이다. 이 연구 선택 기준은 자연법칙이 아니며 별도 튜닝하지 않았다. 두 시장 모두 `macd_rsi60`, `macd_positive`가 고정됐다. 이후6조건을 추가했으며, 잘 나온 것만 남기지 않고 모두 공개한다.

**아래 주 표는 2023-04-01~2025-09-30 기간이다.** 이미 앞선 연구에서 살펴본 TEST를 새 질문으로 재평가했으므로 **탐색적 시간 분리 평가**다. 처음 보는 미래 자료에서의 확인으로 부르지 않는다. 전체 과거와 TRAIN 결과도 CSV에 함께 있다.

## 2. 신호를 받았을 때의 정확도·속도·놓치는 비율

적중률 분모는 상승·횡보·하락 전·늦은 하락·짧은 하락을 포함한 **모든 평가 가능한 해당 신호**다. 포착률 분모는 해당 지표를6일 모두 계산할 수 있는 실제 하락 에피소드다. 한 하락에서 신호가 여러 번 나오면 적중률에서는 각각 실제 경보이고, 포착률에서는 한 하락으로 센다. 지연은 포착한 에피소드의 첫 신호 기준이다. 놓친 하락에는 지연값을0으로 넣지 않았다.

''')
    for m,label in [('KR','한국'),('US','미국')]:
        d=main[main.market==m]
        parts.append(f'### {label}\n\n'+table(d,[('id','신호',name),('signals','전체 신호',num),('precision','초입 적중률',pct),('ci','95% 구간',str),('capture','포착률',pct),('miss','놓침',pct),('mean_delay','평균 지연',dec),('median_delay','중앙 지연',num),('annual','연환산 횟수',dec)])+'\n\n')
        parts.append(f'![{label} 적중률과 불확실성](downtrend-confirmation-2026-10-21/{m}-precision.png)\n\n')
    parts.append('''그림의 점은 적중률이고 가로선은 종목·시기 연관성을 반영한95% 구간이다. 오른쪽일수록 알림을 받았을 때 더 믿을 수 있다. 구간이 좁아도 적중률 자체가 낮으면 ‘정확하게 낮은 성능을 측정한 것’일 수 있다. 추가조건 중 그림에 보인2개는 결과상 높은 점추정 예시이며, 그 순위의 독립 검증은 아니다. 표의 연간 횟수는 `252×신호 수/계산 가능한 종목일`이다. 실제 달력연도마다 고정된 횟수라는 뜻은 아니다.

주요 발생 조건은 다음과 같다.

- **MACD 데드＋최근3일 RSI60 이탈:** EMA12−EMA26이 그 EMA9 시그널을 오늘 하향 교차하고, 오늘·전일·전전일 중 Wilder RSI14가60을 하향 교차했다. 두 사건이 모두 확인된 오늘이 신호일이다.
- **MACD 양수권 데드:** 같은 MACD 하향 교차가 MACD>0에서 발생했다. ‘양수’는 MACD선의 값이며 당일 수익률이 아니다.
- **CCI＋MA20 상승:** 전형가격(H+L+C)/3의 CCI20이+100을 하향 교차하고, 오늘 SMA20이5거래일 전보다 높다.
- **RSI60·스토캐스틱80:** 각각 Wilder RSI14의60 하향교차, 14일 가격범위에서 구한 K를3일 평활한 값의80 하향교차다. D선과의 교차와 다르다.

## 3. 평소에도 흔한가, 초입에 특별히 집중되는가

다음 비교의 단위는 양쪽 모두 **하루의 종목 관측**이다. 평소는 사후 L1 상승·횡보일, 초입은0~5일이다. 따라서6일 창 포착률을 하루 발생률과 비교한 표가 아니다. 상승·횡보를 각각 나눈 결과와 하락 중후반·짧은 하락의 발생률도 전체 CSV에 있다.

''')
    parts.append(table(main,[('market','시장',str),('id','신호',name),('ordinary_rate','평소 하루 발생률',pct),('early_rate','초입 하루 발생률',pct),('rate_difference','차이',pp),('rate_ratio','배수',lambda x:f'{x:.2f}배'),('context_difference','비슷한 상태 대비 초입확률',pp),('context_support','비교 가능 신호',pct)])+'\n\n')
    for m in ['KR','US']:parts.append(f'![{m} 같은 하루 단위의 발생률](downtrend-confirmation-2026-10-21/{m}-frequency.png)\n\n')
    parts.append('''파란 막대가 회색보다 길면 초입에 신호가 집중된다. 그러나 이것만으로 ‘그 신호의 대부분이 초입’이라는 뜻은 아니다. 화재가 드문 동네에서 좋은 경보도 비화재 상황에 더 자주 울릴 수 있는 것과 같다. 적중률은 앞 표에서 별도로 확인해야 한다.

‘비슷한 상태’는 **같은 종목·같은 달력 분기·MA20의5일 기울기 양/음·종가의MA20 위/아래·RSI60 위/아래**가 같은 경우다. 신호일 분포에 맞춰 비신호일의 초입 비율을 가중했다. 비신호일이 없는 층은 제외하고 비교 가능 비율을 표시했다. 이는 이미 관찰 가능한 기술적 상태에 비해 추가 연관성이 있는지를 보는 검사다. 사후 하락 상태로 비교 대상을 골라내지 않았다. 모든 상태를 통제한 인과효과나 수익 보장은 아니다.

''')
    parts.append(table(main,[('market','시장',str),('id','신호',name),('rate_difference_adjusted_low','집중도 차이 보정 하한',pp),('context_difference_adjusted_low','유사상태 개선 보정 하한',pp),('equal_stock_precision','종목 동일가중 적중률',pct)])+'\n\n')
    parts.append('''보정 하한이0보다 크면 이번 비교 집합에서 우연히 양수로 보이는 문제를 보수적으로 반영해도 차이가 남았다. **차이가 남는 것과 높은 적중률은 별개다.** 특히5일선 이탈은 자주 발생하면서 실제 초입이 아닌 경보가 많다. 거래량을 동반한20일 저가 이탈도 이름만으로 초입 신호라고 판단할 수 없다. 가격이 이미 많이 하락한 뒤의 사건일 수 있기 때문이다.

## 4. 실패는 어떤 실패였나

''')
    fail=main.copy()
    for k in ['day0','day1_5','late','short','other','before5']:fail[k+'_pct']=fail[k]/fail.signals
    parts.append(table(fail,[('market','시장',str),('id','신호',name),('day0_pct','시작 당일 적중',pct),('day1_5_pct','+1~5일 적중',pct),('late_pct','6일 이후 늦은 하락',pct),('short_pct','10일 미만 하락',pct),('other_pct','상승·횡보 등',pct),('before5_pct','그중 시작 전5일',pct)])+'\n\n')
    parts.append('''당일·+1~5일·늦은 하락·짧은 하락·그 밖의 다섯 칸은100%가 된다. 마지막 ‘시작 전5일’은 상승·횡보 칸의 부분집합이므로 다시 더하면 안 된다. 성공하지 못한 신호가 반드시 이후 가격 상승을 뜻하지는 않는다. 이미6일 이상 하락한 신호는 가격 위험을 알렸을 수 있어도, 이번 ‘초입 확인’ 질문에는 실패다.

## 5. 추가 확인을 기다릴 가치가 있었나

후보2개마다 세 조건을 고정했다. (1) 기본 신호와 종가<MA20이 같은 날, (2) 기본 신호일부터+5일 안에 첫 MA20 하향 이탈, (3) 기본 신호 이후 시작한 MA20 아래 종가가3일 연속 유지되고+5일 안에 완성. (2)는 같은 날 교차도 허용한다. (3)은 최소2일을 기다린다. 새 기본 신호가 나오면 기준일을 갱신하며, 공백은 초기화한다. 모든 신호일은 **최종 조건이 실제 확인된 날**이다.

''')
    parts.append(table(combo,[('market','시장',str),('id','조건',name),('signals','신호 수',num),('precision','적중률',pct),('precision_change','기본 대비',pp),('capture','포착률',pct),('capture_change','포착률 변화',pp),('mean_delay','평균 지연',dec),('delay_change','지연 변화',lambda x:f'{x:+.2f}일')])+'\n\n')
    parts.append('''**이번에 시험한 추가 확인은 대체로 도움이 되지 않았다.** 한국 MACD＋RSI에 당일MA20 아래 조건을 붙이면 적중률37.2%→35.9%, 포착률31.2%→12.7%로 둘 다 낮아졌다. 미국의 같은 조건은32.5%→32.8%로 겨우0.3pp 높아졌지만 포착률31.1%→13.9%로 절반 이하가 됐다. 이 정도 점추정 개선으로 기다릴 가치가 입증됐다고 보기 어렵다. MA20 하향 이탈을 뒤따라 기다리면 두 시장의 적중률이약24%대로 떨어졌고,3일 지속은약5%까지 낮아졌다. 이미 시작된 하락을 더 강하게 확인할수록 ‘시작 후5일 이내’라는 시간 제한을 넘기는 경우가 늘었다. 이는 모든 추가조건이 쓸모없다는 뜻이 아니라, **이번에 고정해서 시험한 이6개 조건은 초입 확인의 대가가 컸다**는 결과다.\n\n''')
    parts.append('''차이 표는 성능 변화의 점추정이다. 각 조건의 적중률 구간은 전체 CSV에 있지만, 기본조건 대비 개선폭 자체의 별도 유의성 검정으로 읽지 않는다. 포착된 에피소드의 구성이 달라지므로 평균 지연이 짧아져도 같은 하락을 더 빨리 확인했다는 뜻은 아니다. 순차·지속 조건이 낮은 적중률을 크게 해결하는지, 단지 많은 신호를 제거했는지 구별해야 한다.

''')
    for m in ['KR','US']:parts.append(f'![{m} 속도 정확도 포착률](downtrend-confirmation-2026-10-21/{m}-tradeoff.png)\n\n')
    parts.append('''왼쪽 위의 큰 원이 이상적이지만 세 속성을 동시에 개선하기는 어렵다. 작은 원이 위로 이동하면 ‘더 정확하지만 많이 놓치는 조건’이다. 원의 위치는 성공한 경우의 지연 평균이므로, 놓친 하락이 없는 것처럼 해석하지 않는다. 추가조건을 붙였다는 이유만으로 더 좋은 신호로 채택하지 않는다.

## 6. 확인할 때 이미 얼마나 내렸고, 그 다음에는 어떻게 움직였나

이미 내린 폭은 **1−신호 다음 연속 유효 거래일 시가/하락 시작일 종가**다. 시작일 장중 고가나 미래 고점을 기준으로 삼지 않았다. 음수이면 시작 종가보다 다음 시가가 높다는 뜻이다. 아래 값은 실제 초입 적중에 한정한다.

''')
    hitpaths=paths[(paths.population=='hit')&paths.id.isin(['macd_rsi60','macd_positive'])].merge(df[['market','id','first_drop','all_hit_drop']],on=['market','id'])
    parts.append(table(hitpaths,[('market','시장',str),('id','신호',name),('first_drop','첫 확인까지 평균 하락',pct),('already_drop_median','전체 적중 신호 중앙값',pct),('already_drop_p10','10백분위',pct),('already_drop_p90','90백분위',pct)])+'\n\n')
    parts.append('''이후 경로의 기준은 그 다음 시가다. 기간5·21·63은 각각 신호일t의 **t+1 시가부터 t+h 종가까지 h개 봉**이다. ‘최저 경로’는 그h개 봉의 최저가/기준시가−1, ‘최고 경로’는 최고가/기준시가−1이다. 최고 경로는 기준시가 위로 움직인 정도이며, 저점 이후에 실제로 실현한 반등 수익은 아니다. 일봉만으로 고가·저가의 장중 선후를 알 수 없다. 미래 저점을 정확히 매매한 수익이나 피한 손실로 표현하지 않았다.

''')
    pshow=paths[paths.id.isin(['macd_rsi60','macd_positive'])]
    parts.append(table(pshow,[('market','시장',str),('id','신호',name),('population','집합',lambda x:'전체 신호' if x=='all' else '초입 적중만'),('n','신호 수',num),('return21_median','21일 종가 중앙',pct),('return21_mean','21일 종가 평균',pct),('low21_median','21일 최저 경로 중앙',pct),('high21_median','21일 최고 경로 중앙',pct)])+'\n\n')
    parts.append(table(pshow,[('market','시장',str),('id','신호',name),('population','집합',lambda x:'전체' if x=='all' else '적중'),('return5_median','5일 종가 중앙',pct),('return63_median','63일 종가 중앙',pct),('low63_median','63일 최저 경로 중앙',pct),('high63_median','63일 최고 경로 중앙',pct)])+'\n\n')
    parts.append('''적중한 신호만 보면 이후 하락이 뚜렷해 보이는 것은 자연스럽다. 그 집합 자체가 미래 가격으로 정한 L1 정답을 통과했기 때문이다. 실제 사용자가 알림을 받는 시점의 판단에는 **전체 신호 행**이 더 가깝다. 63일 경로는 중간에 반등하거나 추세가 바뀌는 경우도 포함한다. 평균은 큰 급등락에 끌릴 수 있어 중앙값과10·90백분위를 함께 CSV에 제공했다.

## 7. 실제 성공과 실패를 차트로 읽기

동일한 MACD＋RSI 조건을 사용한 네 사례다. 전체 표본의 빈도를 그림 몇 장으로 대신하지 않기 위해, 각 시장·성공/실패 집합에서21일 수익률이 각각−5%/+5%에 가장 가까운 연속 이력 사례를 골랐다. 이 선택은 설명용이며 무작위 대표 표본이나 별도 검증이 아니다.

''')
    for card in cards:
        row=card['row'];m=card['market'];kind=card['kind']
        parts.append(f"### {m} {card['symbol']} — {'초입 적중' if kind=='success' else '목표 불일치'}\n\n![실제 사례](downtrend-confirmation-2026-10-21/{m}-{kind}.png)\n\n빨간 선 **{row['signal_date']}**에 신호가 확인됐다. ")
        if kind=='success':parts.append(f"사후 시작일은 **{row['onset_date']}**, 지연은 **{row['age']}일**이다. 다음 시가까지 시작 종가 대비 **{pct(row['already_drop'])}** 내렸고, 그 시가에서21일 후 종가 변화는 **{pct(row['return21'])}**였다. ")
        else:parts.append(f"이 날은 정답표상 상승·횡보였으므로 초입 적중이 아니다. 다음 시가에서21일 후 종가 변화는 **{pct(row['return21'])}**였다. ")
        parts.append('초록 점선은 그림 범위 안의 ≥10일 하락 시작, 초록 음영은0~5일, 보라 점은 다음 시가다. 주황 L1 선은 나중에 얻은 정답표이므로 당시 화면에서 같은 모양으로 확정되어 있었다고 읽으면 안 된다. 한 사례는 조건의 작동 방식을 보여주지만 전체 신뢰도를 입증하지 않는다.\n\n')
    parts.append('''## 8. 지속기간별 보조 결과

''')
    parts.append(table(durshow,[('market','시장',str),('id','신호',name),('duration','사후 지속일',str),('episodes','하락 수',num),('capture','포착률',pct),('mean_delay','첫 확인 평균일',dec),('first_drop','첫 확인까지 평균 하락',pct),('duration_precision','모든 신호 중 이 기간 초입',pct)])+'\n\n')
    parts.append('''여기서 긴 하락을 많이 놓친다면 ‘하락 초입 확인’의 실용성이 제한된다. 하지만 긴 하락에서 잘 맞았다는 결과를 신호 당시 미래63일 이상 지속을 구별했다는 뜻으로 바꿀 수 없다. 마지막 열의 분모는 해당 기간 하락만이 아니라 모든 신호이며, 세 기간 적중률을 더하면 주 결과 적중률이 된다.

## 9. 어디까지 믿을 수 있는가

''')
    robustness=allr[allr.id.isin(['macd_rsi60','macd_positive'])]
    parts.append(table(robustness,[('market','시장',str),('period','기간',str),('id','신호',name),('precision','적중률',pct),('capture','포착률',pct),('equal_stock_precision','종목 동일가중',pct)])+'\n\n')
    yy=yr[(yr.period=='test')&yr.id.isin(['macd_rsi60','macd_positive'])]
    parts.append(table(yy,[('market','시장',str),('year','연도',num),('id','신호',name),('signals','신호 수',num),('precision','적중률',pct),('rate_difference','집중도 차이',pp),('context_difference','유사상태 개선',pp)])+'\n\n')
    parts.append('''2023년은4월부터, 2025년은9월까지다. 큰 표본의 전체 평균이 매년 같은 성능을 보장하지 않는다. 종목 동일가중은 신호가 있는 종목의 적중률을 한 표씩 평균한 것이며, 신호 없는 종목을 실패율0으로 넣지 않았다. 종목×연도 동일가중도 별도 CSV에 있다. 전체 과거는 TRAIN·TEST와 겹치므로 세 기간의 사례 수를 합쳐 독립 표본으로 세지 않는다.

''')
    sw=sens[(sens.period=='test')&sens.id.isin(['macd_rsi60','macd_positive','cci100_up20'])]
    parts.append(table(sw,[('market','시장',str),('id','신호',name),('window','초입 범위',str),('precision','적중률',pct),('capture','포착률',pct)])+'\n\n')
    parts.append('''**‘초입’을 얼마나 좁게 정의하느냐에는 결론이 민감했다.** MACD＋RSI를0~3일 안에만 인정하면 한국 적중률11.9%·포착률10.0%, 미국 적중률11.4%·포착률10.9%까지 내려간다. 이 후보는 주로4~5일째 확인하는 신호이므로 ‘시작 직후를 빠르게 알아챈다’고 확대해석하면 안 된다.0~10일로 넓히면 적중률이 한국52.7%·미국46.7%로 올라가지만, 이는 주 질문보다 늦은 확인까지 성공으로 허용한 결과다. 기준 창을 바꿔도 성능이 그대로인 강건한 신호라고 할 수 없다.\n\n''')
    parts.append('''더 빠른 확인을 우선하면 순위도 달라진다.0~3일 기준 CCI＋MA20 상승은 한국 적중률23.6%·포착률72.3%, 미국 적중률20.7%·포착률69.3%로 MACD＋RSI보다 빠르고 넓게 포착했다. 그러나 그 경우에도 신호의약4분의3~5분의4는 목표 초입 밖이다. 한국 RSI70 이탈의0~3일 적중률24.1%도 포착률25.7%에 그친다. 이 보조 순위는 새로 검증된 후보 선정이 아니라 창 민감도를 설명하는 탐색 결과다.\n\n''')
    parts.append('''0~3일은4일,0~5일은6일,0~10일은최대11일이다. 10일짜리 하락의 경우0~10일 창 중 실제 하락인0~9일까지만 성공 대상으로 삼았다. 창을 넓혀 얻은 적중률 상승은 같은 신호가 더 빨라진 것이 아니라 ‘초입’ 허용 범위가 넓어진 결과다.

**L1 미래 자료 분리.** TRAIN용 L1은2022-12-31까지만 적합했고 선정 신호는2021년까지다. TEST 시작2023-04-01 이후의 가격이 선정용 정답표에 들어가지 않았다. TEST 정답표는2026-09-30까지의 사후 가격을 사용했다. 평가 가능한 날에는 최소126개 후속 연속 봉을 요구했다. 이는 실시간 정답표가 되었다는 뜻이 아니라 끝점 불안정을 줄이는 연구 처리다.

''')
    ee=end[end.kind=='prefix_vs_full'].copy();ee['disagree_rate']=ee.early_disagree/ee.both_known;ee['signal_disagree_rate']=ee.signal_label_disagree/ee.signals;ee['exact_rate']=ee['exact']/ee.prefix_onsets;ee['range']=ee.apply(lambda r:f'{int(r.distance_lo)}~{int(r.distance_hi)}' if r.distance_hi<100000 else '253+',axis=1)
    parts.append(f'끝점을 바꾸는 별도 실험은 시장별40종목, 총80종목에서 **{nfit}회** L1을 다시 적합했다. 2024년 말까지600봉 이상이고2025-09-30까지 이어지는 구간을 가진 종목을 심벌 SHA-256 순서로 골랐으며 성능으로 고르지 않았다. 2020·2021·2023·2024년 말에 자료를 끊은 정답표를 더 긴 자료의 정답표와 대조했다.\n\n')
    parts.append(table(ee,[('market','시장',str),('range','자료 끝에서 거리(일)',str),('both_known','양쪽 평가 가능일',num),('disagree_rate','초입 분류 수정률',pct),('signal_disagree_rate','63신호 분류 수정률',pct),('prefix_onsets','짧은 자료의 완료 시작점',num),('long_onsets','긴 자료의 완료 시작점',num),('exact_rate','짧은 자료 시작점 정확히 유지',pct)])+'\n\n')
    parts.append('''완료 여부가 한쪽에서 미정이면 위 수정률 분모에서 제외하고 `prefix_unknown/long_unknown`으로 별도 저장했다. 따라서 끝부분의 낮은 수정률만 보고 안전하다고 해석하면 안 된다. 시작점이 없었다가 완료 하락으로 확정되는 현상은 두 시작점 수의 차이에서도 확인해야 한다. ±5일 이내 이동·미대응 수와 종목별 결과는 endpoint CSV에 있다. TRAIN용2022년 말 정답표와 전체 정답표도 같은 표본에서 비교했다. 이 실험은 표본 검사이며 모든 종목·모든 시점에서 수정이 없음을 보장하지 않는다.

**불확실성과 다중 비교.** 신호들이 같은 종목에서 반복되고 같은 분기에 함께 발생하므로 독립 동전 던지기로 취급하지 않았다. 종목과 달력 분기에 각각 Poisson 가중치를 뽑아 곱하는 교차 군집 부트스트랩1,000회를 썼다. 적중률의95% 구간은 점별 구간이다. 집중도 차이와 유사상태 개선은69조건×2시장×2검정=276개 집합에 Bonferroni 보정을 한 정규 근사 하한과 p값을 함께 제공했다. 신호 간 독립을 요구하지 않는 보수적인 보정이지만, 시간 군집이10분기뿐이라는 한계와 연구자가 이전 결과를 이미 본 문제까지 지워주지는 않는다. 구간은 자료 수집의 생존편향이나 모든 기업행사 오류를 포함하지 않는다.

''')
    tr=end[end.kind=='train_vs_full'];recent=ee[ee.distance_lo==0]
    parts.append(f"표본의 TRAIN 구간에서 양쪽 모두 평가 가능한 **{num(tr.both_known.sum())}종목일** 중 초입 분류 수정은 **{num(tr.early_disagree.sum())}건**이었다. 끝점 실험의64일 이상 떨어진 양쪽 평가 가능일에서도 이번 표본의 수정은0건이었다. 반면 마지막0~20일에는 한국 **{pct(recent[recent.market=='KR'].iloc[0].disagree_rate)}**, 미국 **{pct(recent[recent.market=='US'].iloc[0].disagree_rate)}**가 바뀌었다. 이것은 종료 부근 경고가 실시간 확정 정답이 될 수 없다는 직접적인 예다.\n\n")
    parts.append('## 10. 표본·평가 불가 처리와 재현\n\n')
    coverage=[]
    for m,v in basis['markets'].items():coverage.append(dict(market=m,inventory=v['inventory'],usable=v['usable_history'],bars=v['used_bars'],first=v['earliest'],last=v['latest']))
    parts.append(table(pd.DataFrame(coverage),[('market','시장',str),('inventory','점검 이력',num),('usable','계산 가능 이력',num),('bars','저장 유효 봉',num),('first','가장 오래된 자료',str),('last','자료 상한',str)])+'\n\n')
    parts.append('''현재 보유한7,426개 종목 이력을 점검했고, 그중7,237개에서 지표·L1을 계산할 수 있었다. 현재 상장 중심 수집과 제한적인 과거 한국33종목·ADR3종목 보강이며, 과거에 존재했던 모든 상장폐지 종목을 포함한 완전한 역사적 시장은 아니다. 현재 승인된 정확한 식별자 제외정책을 유지했다. 가격은 기존 공급자 저장 수정가격을 그대로 사용했고 재조정하거나 새로 수집하지 않았다. 수량·거래량의 기업행사 처리 불확실성은 남는다.

잘못된 OHLC·거래량0·명시적 거래일 누락·10일 초과 달력 공백은 시계열 구간을 끊는다. 전방 채우기를 하지 않는다. 지표마다 준비기간/결측은 실패신호0과 구별한다. 기본65봉 과거 조건에 더해200일선 등은 자기 준비기간을 충족해야 한다. 시작이나 끝이 불명인 하락 전체는 평가 불가로 두며, 짧은 하락으로 강제 분류하지 않는다. 모든 가격 경로에 같은126봉 후속 조건을 적용했기 때문에5·21·63일 간 표본 변경으로 생기는 차이를 줄였다.

''')
    parts.append(table(cov[cov.period=='test'],[('market','시장',str),('dated','기간 내 종목일',num),('history_short','과거 부족',num),('future_short','후속126봉/적합 부족',num),('censored_down','끝/시작 미확정 하락일',num),('valid','공통 평가 가능일',num),('indicator_missing_pairs','그중 지표 결측 종목일×조건',num)])+'\n\n')
    exshow=exc[exc.id.isin(['macd_rsi60','macd_positive','price5'])]
    parts.append(table(exshow,[('market','시장',str),('id','신호',name),('dated_signals','기간 내 계산된 신호',num),('history_short_signals','과거 부족 제외',num),('future_short_signals','후속자료 부족 제외',num),('censored_down_signals','미확정 하락 제외',num)])+'\n\n')
    parts.append('''결측 쌍 수는 여러 지표가 같은 날 비어 있으면 각각 세므로 종목일 수와 더하지 않는다. 고정 후속자료 조건은 종료·거래정지·최근 상장 등 일부 사례를 배제하며 그 결과를 무작위 결측으로 볼 수 없다. 결측이나 미완료 추세를 적중 또는 실패로 억지 계산하지 않은 대신, 이 표본 제한을 성능의 한계로 남긴다.

계산 검증에서는6일 창·시작 전 신호의 실패 처리·미완료 하락·순서/지속 조건의 실제 확인일·접두 구간 인과성·다음 시가와 관측기간을 직접 확인했다. 별도 원장 계산의480개 표본 날짜/경로를 스칼라 계산과 대조했고, 선정·비교 조건의1,288,049개 신호 원장을 합계 표와 비교한다. 전체414행의 분류 합·분모·기간별 성공 수와 입력 캐시 해시는 [최종 검증 영수증](downtrend-confirmation-2026-10-21/verification-final.json)에 기록한다.

주요 파일은 다음과 같다.

- [69조건 전체 TEST 결과·신뢰구간·빈도·경로 평균](downtrend-confirmation-2026-10-21/all-signals-test.csv)
- [결과 CSV 묶음 ZIP](downtrend-confirmation-2026-10-21/results-csv.zip)
- [TRAIN·TEST·전체 과거 결과](downtrend-confirmation-2026-10-21/all-periods.csv) · [연도별](downtrend-confirmation-2026-10-21/yearly.csv) · [종목 동일가중 연도별](downtrend-confirmation-2026-10-21/equal-stock-yearly.csv)
- [추가 확인의 교환관계](downtrend-confirmation-2026-10-21/confirmation-tradeoffs.csv) · [정확한 조건](downtrend-confirmation-2026-10-21/signal-definitions.csv)
- [선정 신호 가격 경로의 평균·중앙·10/90백분위](downtrend-confirmation-2026-10-21/selected-price-paths.csv) · [그림의 실제 사례](downtrend-confirmation-2026-10-21/illustrated-cases.csv)
- [기간별 포착·지연](downtrend-confirmation-2026-10-21/duration-episodes.csv) · [기간별 신호 적중·경로](downtrend-confirmation-2026-10-21/duration-signals.csv) · [초입 창 민감도](downtrend-confirmation-2026-10-21/early-window-sensitivity.csv)
- [L1 끝점 민감도](downtrend-confirmation-2026-10-21/endpoint-summary.csv) · [종목별 상세](downtrend-confirmation-2026-10-21/endpoint-details.csv) · [제외된 신호 수](downtrend-confirmation-2026-10-21/excluded-signals.csv)
- [분석 규약](downtrend-confirmation-2026-10-21/protocol.json) · [선정 동결 영수증](downtrend-confirmation-2026-10-21/selection-receipt.json) · [계산 검증](downtrend-confirmation-2026-10-21/verification-synthetic.json)

선정 후보·후속조건·비교군의 실제 신호별 날짜/분류/가격 원장은 `runtime/downtrend-confirmation-20261021/signal-ledger.csv.gz`, 종목×연도 원장은 같은 폴더의 `stock-year-results.csv.gz`에 보존했다. 대용량 로컬 원장을 운영DB에 넣지 않았다. 재현 코드는 `scripts/downtrend_confirmation/README.md`를 따른다. 결과 CSV의 비율은0~1 소수, 차이는 같은 비율 단위이며 화면 표만%/pp로 바꿨다. 코드·정의·입력 해시는 영수증과 manifest에 남겼다.

## 11. 통계 항목을 질문과 연결해서 읽는 법

**평소 발생 빈도 —** 별일 없을 때도 얼마나 자주 나타나는지다. 화재경보기가 요리할 때도 자주 울리는지 확인하는 것과 같다. 여기서는 상승·횡보 하루 중 신호가 뜬 비율을, 초입 하루의 같은 비율과 비교했다.5일선 이탈의 높은 빈도를 보면서 ‘많이 잡는다’만으로 유용하다고 하지 않는 이유다.

**포착률 —** 실제 문제가 있는 사례를 얼마나 발견했는지다. 실제 화재100건 중 경보가 몇 건에서 울렸는지를 묻는다. 여기서는 실제 ≥10일 하락 에피소드 중0~5일 안에 적어도 한 번 확인한 비율이다. 정확한 신호라도 포착률이 낮으면 많은 하락을 놓친다. 이 설명의100건은 개념용 가상 숫자이며 실제 건수는 표의 하락 수다.

**적중률 —** 경보가 울렸을 때 실제 문제인 비율이다. 울린 경보를 모두 모아 실제 화재였는지 확인한다. 여기서는 발생한 모든 신호가 출발점이다. 시작 전 신호나 이미 늦은 신호를 빼고 계산하면 실제 사용자가 느낄 신뢰도보다 좋아 보이므로 그대로 분모에 남겼다. 이번 연구에서 가장 먼저 볼 숫자다.

**확인 지연 —** 맞는 경보라도 얼마나 늦었는지다. 불씨일 때와 방 전체로 번졌을 때의 알림은 가치가 다르다. 여기서는 사후 시작일에서 첫 신호일까지의 거래일과 다음 시가까지 이미 내린 폭을 함께 봤다. 지속 조건의 확인일을 첫날로 소급하면 실제 기다린 시간을 숨기므로 금지했다.

**비슷한 상태와의 비교 —** 원래 환경이 위험했던 사실 외에 신호가 정보를 더 주는지다. 같은 주방·같은 시간대에서 경보가 울린 날과 울리지 않은 날을 비교하는 것에 가깝다. 같은 종목·분기·MA20/RSI 상태의 비신호일을 사용했다. 양수 개선폭은 추가 연관성을 지지하지만 비교하지 못한 요인이 남아 있어 원인이라고 부르지 않는다.

**신뢰구간 —** 관측된 비율 주변의 통계적 흔들림 범위다. 경보기 몇 번의 경험으로 얻은 성적과 여러 환경에서 반복한 경험은 확실성이 다르다. 같은 종목·같은 분기의 경보는 서로 닮으므로 하나씩 독립이라고 가정하지 않고 묶어서 다시 가중했다.95% 구간은 이번 고정된 참값이95% 확률로 그 안에 있다는 단순 보증이나, 다음 신호의 가격 범위가 아니다.

**다중검정 —** 많은 후보를 보면 운 좋게 좋아 보이는 후보가 생기는 문제다. 많은 사람에게 동전 던지기를 시키면 우연히 연속 성공하는 사람이 나오는 것과 같다. 여기서는63조건과12개 시장별 후속조건을 비교한 효과 검정 집합 전체를 보정했다. 그래도 이미 본 자료를 바탕으로 질문을 다듬은 영향은 남아 있으므로 순위만으로 실전 규칙을 확정하지 않는다.

**새 기간에서의 검증 —** 조건을 고르는 자료와 성적을 매기는 자료를 나누는 것이다. 풀어본 문제와 처음 보는 시험의 차이다. TRAIN으로 후보를 고정하고 나중 기간에 대조했지만, 그 TEST 자체를 이전 연구에서 봤기 때문에 완전히 처음 보는 시험은 아니다. 다음에 조건을 그대로 고정해 아직 관찰하지 않은 기간을 쌓아야 더 강한 검증이 된다.

**사후 L1 정답표와 당시 신호 —** 경기 뒤 영상을 돌려보는 판정과 경기 중 판단의 차이다. 영상 판정으로 ‘여기가 시작’이라고 알게 된 사실을 경기 중에도 알았던 것처럼 쓰면 안 된다. L1은 미래 가격을 포함한 평가용 정답표, MACD·RSI 등은 그날까지의 가격으로 계산한 경보다. 끝점을 잘랐을 때 판정이 바뀌는 실험은 이 차이를 수치로 확인한 것이다.

실제 활용 관점에서는 한국·미국 모두 MACD＋RSI를 정확도 우선 검토 후보로, MACD 양수권 데드를 포착률 보완 후보로 볼 수 있다. CCI 등은 더 넓게 잡는 대신 신호의 상당수가 목표 초입 밖이다. 추가 확인의 장점은 표의 정확도 개선과 함께 잃는 포착률을 감수할 때만 의미가 있다. **이번 자료에서 확인된 것은 차등적인 연관성과 그 대가이며, 높은 신뢰도의 단독 하락 확정 신호가 입증된 것은 아니다.**
''')
    (ROOT/'docs/downtrend-confirmation-2026-10-21.md').write_text(''.join(parts),encoding='utf-8',newline='\n')
    (DEST/'.gitattributes').write_text('* -text whitespace=cr-at-eol\n',encoding='utf-8')
    with zipfile.ZipFile(DEST/'results-csv.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(DEST.glob('*.csv')):archive.write(p,p.name)
        archive.write(Path(__file__).with_name('README.md'),'README.md')
    manifest={p.name:sha(p) for p in sorted(DEST.iterdir()) if p.is_file() and p.name!='artifact-manifest.json'}
    write(DEST/'artifact-manifest.json',dict(files=manifest,report_sha256=sha(ROOT/'docs/downtrend-confirmation-2026-10-21.md'),ledger_sha256=sha(OUT/'signal-ledger.csv.gz')))
    print('REPORT',len(''.join(parts)),'characters',len(manifest),'artifacts',flush=True)

if __name__=='__main__':main()
