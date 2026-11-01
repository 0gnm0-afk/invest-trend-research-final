"""Publication-style long-history figures; plotted-data CSVs accompany every image."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / 'docs/research/downtrend-longhistory-2026-10-29'
FONT = Path('C:/Windows/Fonts/malgun.ttf')
if FONT.exists():
    font_manager.fontManager.addfont(str(FONT))
plt.rcParams.update({'font.family': 'Malgun Gothic' if FONT.exists() else 'DejaVu Sans',
    'axes.unicode_minus': False,
    'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
    'axes.grid': True, 'axes.axisbelow': True, 'grid.alpha': .16,
    'figure.facecolor': 'white', 'savefig.facecolor': 'white'})

LABELS = {
    'supertrend': '슈퍼트렌드 하락 전환', 'psar': '파라볼릭 SAR',
    'trix_zero': 'TRIX 0선 이탈', 'trix_signal': 'TRIX 신호선 이탈',
    'stochrsi80': 'StochRSI K80 이탈', 'stochrsi_cross': 'StochRSI 고위 K/D',
    'rmi70': 'RMI70 이탈', 'rmi50': 'RMI50 이탈', 'chaikin': '체이킨 0선 이탈',
    'avwap_quarter': '분기 VWAP 대용치 이탈', 'volume_osc': '거래량 오실레이터·하락일',
    'fractal_break': '확정 프랙탈 저점 이탈', 'macd_rsi60': 'MACD+RSI60 (기존)',
    'macd_positive': '양수 MACD 교차 (기존)', 'cci100_up20': 'CCI100·20일선 상승 (기존)',
    'rsi60': 'RSI60 이탈 (기존)', 'stoch80': 'Stochastic K80 (기존)',
    'price5': '종가 5일선 이탈 (기존)'}
FOCAL = list(LABELS)
MARKET = {'KR': '한국', 'US': '미국'}


def save(fig, name, data):
    fig.savefig(DOC / (name + '.png'), dpi=170, bbox_inches='tight')
    plt.close(fig)
    data.to_csv(DOC / (name + '-data.csv'), index=False, encoding='utf-8-sig')


def ordered(data, market):
    return data[(data.market == market) & data.id.isin(FOCAL)].set_index('id').loc[FOCAL].reset_index()


def tradeoff(primary, market):
    d = ordered(primary, market); y = np.arange(len(d))
    fig, axes = plt.subplots(1, 2, figsize=(14, 9.2), sharey=True,
                             gridspec_kw={'width_ratios': [1.15, 1]})
    colors = ['#187b80'] * 12 + ['#8b9199'] * 6
    a = axes[0]
    a.barh(y, 100*d.precision, color=colors, height=.64)
    for k, r in d.iterrows():
        a.plot([100*r.precision_low, 100*r.precision_high], [k, k], color='#203849', lw=1.3)
        a.text(max(100*r.precision_high+.7,100*r.early_base+1.4), k, f'{100*r.precision:.1f}%', va='center', fontsize=9)
    a.scatter(100*d.early_base, y, marker='|', s=110, color='#b34c2f', zorder=5)
    a.set_yticks(y, [LABELS[k] for k in d.id]); a.invert_yaxis()
    a.set_xlim(0, max(45, 100*d.precision_high.max()+8)); a.set_xlabel('모든 신호 중 0~5일 초입인 비율 (%)')
    a.set_title('초입 적중률 · 선은 주변 95% 구간')
    b = axes[1]
    b.barh(y, 100*d.capture, color=colors, height=.64)
    for k, r in d.iterrows():
        b.plot([100*r.capture_low, 100*r.capture_high], [k, k], color='#203849', lw=1.3)
        b.text(101, k, f'{r.mean_delay:.2f}일 | {r.annual:.1f}회/년', va='center', fontsize=9)
    b.set_xlim(0, 140); b.set_xticks([0, 25, 50, 75, 100]); b.set_xlabel('실제 하락 구간의 초입 포착률 (%)')
    b.set_title('포착률 · 첫 성공 지연 · 발생 빈도')
    for a in axes: a.axhline(11.5, color='#b8c0c8', lw=1)
    fig.suptitle(f'{MARKET[market]}: 15년간 고정 신호의 정확성·포착률', x=.04, ha='left', fontsize=17, fontweight='bold')
    fig.text(.04, .01, '2010-10~2025-09. 청록=추가 12조건, 회색=기존 6기준. 작은 주황선=각 조건의 평가 가능일 초입 기저율.\n지연은 초입에 성공한 경우의 첫 신호까지다. 연간 빈도는 252개 평가 가능일 기준이며 미래의 연간 횟수 예측이 아니다.', fontsize=9)
    fig.tight_layout(rect=[0, .055, 1, .94]); save(fig, 'report-'+market+'-tradeoff', d)


def frequency(primary, market):
    d=ordered(primary, market); y=np.arange(len(d))
    fig, a=plt.subplots(figsize=(12, 9))
    for shift, col, label, color in [(-.24, 'ordinary_rate', '상승·횡보일', '#8b9aaa'),
        (0, 'early_rate', '하락 초입 0~5일', '#c65b3c'), (.24, 'late_rate', '하락 중후반 6일 이후', '#207e85')]:
        a.barh(y+shift, 100*d[col], height=.23, color=color, label=label)
    a.set_yticks(y, [LABELS[k] for k in d.id]); a.invert_yaxis()
    a.set_xlabel('해당 상태의 평가 가능 거래일 100일당 신호 발생 (%)')
    fig.suptitle(f'{MARKET[market]}: 평소와 초입의 발생 빈도를 같은 하루 단위로 비교', x=.04, y=.99, ha='left', fontsize=15, fontweight='bold')
    fig.legend(*a.get_legend_handles_labels(), loc='upper center', bbox_to_anchor=(.61,.955), ncol=3, frameon=False, fontsize=9)
    fig.text(.04,.01,'집중도와 적중률은 다른 질문이다. 초입에서 자주 울려도, 초입 밖의 신호가 많으면 실제 알림의 적중률은 낮을 수 있다.',fontsize=9)
    fig.tight_layout(rect=[0,.035,1,.92]);save(fig,'report-'+market+'-frequency',d)


def timing(primary):
    keys=['rmi70','psar','stochrsi80','macd_rsi60','macd_positive','cci100_up20']
    d=primary[primary.id.isin(keys)].copy()
    fig,axes=plt.subplots(1,2,figsize=(13.5,6),sharex=True,sharey=True)
    for a,m in zip(axes,['KR','US']):
        for _,r in d[d.market==m].iterrows():
            prior=r.id not in FOCAL[:12]
            a.scatter(r.mean_delay,100*r.precision,s=30+240*r.capture,marker='s' if prior else 'o',color='#ac583b' if prior else '#187b80',alpha=.85)
            a.annotate(LABELS[r.id].replace(' (기존)',''),(r.mean_delay,100*r.precision),xytext=(5,6),textcoords='offset points',fontsize=8)
        a.set_title(MARKET[m]);a.set_xlabel('초입에 성공한 첫 신호의 평균 지연 (거래일)')
        a.set_xlim(.5,5.3);a.set_ylim(0,max(45,100*d.precision.max()+10))
    axes[0].set_ylabel('모든 신호의 초입 적중률 (%)')
    fig.suptitle('빠른 확인·정확한 확인·넓은 포착의 관계',x=.05,ha='left',fontsize=16,fontweight='bold')
    fig.text(.05,.012,'점이 클수록 포착률이 높다. 사각형=기존 기준. 지연은 성공한 경우에만 정의되므로 놓친 하락이나 늦은 확인의 비용을 대신하지 못한다.',fontsize=9)
    fig.tight_layout(rect=[0,.06,1,.93]);save(fig,'report-timing',d)


def eras(era, market):
    d=era[(era.market==market)&era.id.isin(FOCAL)].copy()
    periods=sorted(d.period.unique()); assert len(periods)==3
    fig,axes=plt.subplots(1,2,figsize=(12.5,9),sharey=True)
    for a,key,title,vmax in zip(axes,['early_precision','capture'],['초입 적중률 (%)','하락 포착률 (%)'],[50,100]):
        values=d.pivot(index='id',columns='period',values=key).loc[FOCAL,periods].values*100
        im=a.imshow(values,aspect='auto',vmin=0,vmax=vmax,cmap='YlGnBu');a.grid(False)
        for i in range(len(FOCAL)):
            for j in range(3):
                if np.isfinite(values[i,j]):a.text(j,i,f'{values[i,j]:.1f}',ha='center',va='center',fontsize=8,color='white' if values[i,j]>.6*vmax else '#142b37')
        a.set_xticks(range(3),['2010.10~2015.09','2015.10~2020.09','2020.10~2025.09'],rotation=22,ha='right',fontsize=9)
        a.set_yticks(range(len(FOCAL)),[LABELS[k] for k in FOCAL]);a.set_title(title)
        fig.colorbar(im,ax=a,fraction=.028,pad=.02)
    fig.suptitle(f'{MARKET[market]}: 같은 조건을 세 개의 5년 구간에서 재평가',x=.04,ha='left',fontsize=16,fontweight='bold')
    fig.text(.04,.012,'기간별 수치는 기술통계다. 각 시기 종목 구성·초입 기저율이 달라지며, 이미 살펴본 역사를 새로운 독립 검증으로 바꾸지는 않는다.',fontsize=9)
    fig.tight_layout(rect=[0,.05,1,.94]);save(fig,'report-'+market+'-eras',d)


def matched(risk, market):
    d=risk[(risk.market==market)&(risk.scheme==3)&(risk.outcome=='loss05')&risk.id.isin(FOCAL)].copy()
    fig,axes=plt.subplots(1,3,figsize=(15.5,9),sharey=True)
    for a,h in zip(axes,[5,21,63]):
        rows=d[d.horizon==h].set_index('id').loc[FOCAL]
        for y,(_,r) in enumerate(rows.iterrows()):
            color='#157d80' if r.sim_low>0 or r.sim_high<0 else '#718291'
            a.plot([100*r.sim_low,100*r.sim_high],[y,y],color=color,lw=1.3)
            a.scatter(100*r.difference,y,color=color,s=24)
        a.axvline(0,color='#b34d36',lw=1);a.set_title(f'{h}거래일 안에 -5% 저가 접촉')
        a.set_yticks(range(len(FOCAL)),[LABELS[k] for k in FOCAL]);a.set_xlabel('신호일 - 비슷한 비신호일 (%p)')
    axes[0].invert_yaxis()
    for y,(_,r) in enumerate(d[d.horizon==21].set_index('id').loc[FOCAL].iterrows()):
        axes[2].text(1.03,y,f'비교 {100*r.support:.0f}% | SMD {r.max_abs_smd:.2f}',transform=axes[2].get_yaxis_transform(),va='center',fontsize=8)
    fig.suptitle(f'{MARKET[market]}: 비슷한 상태와 비교한 추가 하락 위험',x=.035,ha='left',fontsize=16,fontweight='bold')
    fig.text(.035,.012,'기준=신호 다음 연속 유효 시가. L1 상태로 표본을 고르지 않았다. 같은 종목·분기·당시 기술적 상태를 가장 엄격하게 맞춘 비교.\n선은 3,456개 비교의 동시 보정구간(3/6개월 블록의 넓은 경계). 유지율과 잔여 SMD가 적용 범위를 제한한다. 음수는 접촉이 덜 잦았다는 뜻이다.',fontsize=9)
    fig.tight_layout(rect=[0,.06,1,.94]);save(fig,'report-'+market+'-risk',d)


def coverage():
    d=pd.read_csv(DOC/'coverage-years.csv')
    fig,axes=plt.subplots(1,2,figsize=(13,4.8),sharey=True)
    for a,m in zip(axes,['KR','US']):
        q=d[d.market==m]
        a.plot(q.year,q.usable_stock_years,label='저장 유효 봉이 있는 종목',color='#8493a0',lw=1.4)
        a.plot(q.year,q.evaluable_stocks,label='공통 분류 평가 가능 종목',color='#137f82',lw=1.7)
        a.axvspan(2010.75,2025.75,color='#d79550',alpha=.13,label='주 분석 15년')
        a.set_title(MARKET[m]);a.set_xlabel('연도');a.set_xlim(q.year.min(),2026)
    axes[0].set_ylabel('종목 수');axes[1].legend(fontsize=8,frameon=False)
    fig.suptitle('전체 종목을 넣어도 과거의 평가 가능한 종목 수는 같지 않다',x=.05,ha='left',fontsize=15,fontweight='bold')
    fig.text(.05,.01,'공통 평가에는 과거 65봉·미래 126봉·완료된 추세 경계가 필요하다. 지표별 추가 준비 기간은 별도다. 2026년은 전체 연도가 아니다.',fontsize=9)
    fig.tight_layout(rect=[0,.065,1,.93]);save(fig,'report-coverage',d)


def generate(primary, era, risk):
    DOC.mkdir(parents=True,exist_ok=True)
    for m in ['KR','US']:
        tradeoff(primary,m);frequency(primary,m);eras(era,m);matched(risk,m)
    timing(primary);coverage()
    return ['report-'+m+'-'+k for m in ['KR','US'] for k in ['tradeoff','frequency','eras','risk']]+['report-timing','report-coverage']
