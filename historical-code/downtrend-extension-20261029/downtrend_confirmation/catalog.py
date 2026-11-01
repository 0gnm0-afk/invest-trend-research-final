"""Human-readable exact causal signal specification; formulas live in features.py."""
from study import *

def definitions():
    d={}
    for k in [5,10,20,50,60,200]:d[f'price{k}']=f'C가 SMA{k}를 신규 하향 교차'
    for a,b in [(5,10),(5,20),(10,20),(20,60),(50,200)]:d[f'ma{a}_{b}']=f'SMA{a}가 SMA{b}를 신규 하향 교차'
    d.update(price5_up20='price5 AND SMA20[t]>SMA20[t-5]',ma510_up20='ma5_10 AND SMA20[t]>SMA20[t-5]',ma510_early='ma5_10 AND SMA10>SMA20',requested='ma510_early AND C<SMA20',price20_early='price20 AND SMA10>SMA20',ma20_turn='SMA20[t]<SMA20[t-5] 상태의 신규 진입')
    for q in [70,60,50,40]:d[f'rsi{q}']=f'Wilder RSI14가 {q}를 신규 하향 교차'
    d.update(macd_signal='MACD=EMA12(C)-EMA26(C)가 EMA9(MACD)를 신규 하향 교차',macd_positive='macd_signal AND MACD>0',macd_zero='MACD가0을 신규 하향 교차',dmi_cross='Wilder14 평활 +DM이 평활 -DM을 신규 하향 교차(동일 ATR 분모이므로 DI 교차와 동일)',dmi_adx25='dmi_cross AND Wilder ADX14>=25',adx_bear_rising='ADX14가20을 신규 상향 교차 AND -DM평활>+DM평활',stoch80='rawK=100*(C-최저L14)/(최고H14-최저L14), K=SMA3(rawK), K가80을 신규 하향 교차',stoch_high_cross='K가 D=SMA3(K)를 신규 하향 교차 AND K[t-1]>=80')
    for q in [100,0,-100]:d[f'cci{q}']=f'TP=(H+L+C)/3; CCI20=(TP-SMA20(TP))/(0.015*20일 평균절대편차)가{q}를 신규 하향 교차'
    d.update(bb_upper_reentry='C가 SMA20(C)+2*20일 모집단표준편차를 신규 하향 교차',bb_lower='C가 SMA20(C)-2*20일 모집단표준편차를 신규 하향 교차',bb_squeeze_down='bb_lower AND 전일 밴드폭/중심선 <= 전일까지120일 최소폭의1.1배',keltner_lower='C가 EMA20(C)-2*Wilder ATR14를 신규 하향 교차')
    for k in [20,60]:d[f'low{k}']=f'C<직전{k}일 최저 L 상태의 신규 진입(오늘 저가 제외)'
    d.update(failed_breakout20='H>직전20일 최고H AND C<직전20일 최고H AND C<O 상태의 신규 진입',bear_gap='O<전일L AND C<O; 충족하는 매일',bear_engulf='전일C>전일O AND C<O AND O>=전일C AND C<=전일O; 충족하는 매일',upper_wick='(H-max(O,C))/(H-L)>=0.6 AND (C-L)/(H-L)<=0.3, H>L; 충족하는 매일',down_volume15='C<전일C AND V/직전20일 평균V>=1.5 상태 신규 진입',atr_drop_volume='C<전일C-1.5*전일ATR14 AND V/직전20일 평균V>=1.5; 충족하는 매일',obv_outflow='최근20일 sum(V*sign(C/전일C-1))/sum(V)가 -0.2를 신규 하향 교차',cmf_zero='CMF20=sum(((2C-H-L)/(H-L))*V)/sum(V)가0을 신규 하향 교차; H=L의 계수0',cmf_minus10='CMF20이 -0.1을 신규 하향 교차',mfi80='TP*V의 TP 상승일/하락일14합으로 계산한 MFI14가80을 신규 하향 교차',mfi50='동일 MFI14가50을 신규 하향 교차',roc10_zero='C/C[t-10]-1이0을 신규 하향 교차',aroon_cross='최근25일 최고H/최저L 발생위치(동률은 최근)를0..100으로 환산; AroonUp이 AroonDown을 신규 하향 교차',vortex_cross='최근14일 sum(abs(H-전일L))가 sum(abs(L-전일H))를 신규 하향 교차',ichimoku_tk='(최고H9+최저L9)/2가(최고H26+최저L26)/2를 신규 하향 교차',ichimoku_base='C가 일목26일 기준선을 신규 하향 교차',ichimoku_cloud='C가26봉 전 계산한 min((전환선+기준선)/2,(최고H52+최저L52)/2)를 신규 하향 교차',vol_expansion='로그 일수익률5일 표준편차/20일 표준편차가1.25를 신규 상향 교차',macd_rsi60='macd_signal AND 당일 포함 최근3거래일 중 rsi60 발생(오늘,t-1,t-2)',stoch_macd='stoch80 AND MACD<시그널',cci100_up20='cci100 AND SMA20[t]>SMA20[t-5]',bb_rsi60='bb_upper_reentry AND RSI14<60',macd_volume='macd_signal AND V/직전20일 평균V>=1.5',low20_volume='low20 AND V/직전20일 평균V>=1.5',rsi_divergence='C가 직전20일 종가 최고값보다 높고 RSI14가 그 고점일 RSI보다5 낮음; 고점 동률은 numpy argmax의 첫날, 충족하는 매일')
    assert set(d)=={b['id'] for b in BASE}
    rows=[]
    for b in BASE:rows.append(dict(**b,condition=d[b['id']],signal_day='모든 조건이 그날 종가까지 확인된 날',repeat='교차/신규진입은 재교차·재진입 때 다시 집계; 일별 패턴은 연속일 각각' ))
    for m in ['KR','US']:
        for ident in json.loads((OUT/'frozen.json').read_bytes())[m]:
            for tag,cond in [('and20','기본 신호 당일 C<SMA20'),('then20','기본 신호일~+5일 사이 최초 C/SMA20 하향교차일. 같은 날 허용'),('persist3','기본 신호일 이후 시작한 C<SMA20 연속3일이 기본 신호일~+5일 안에 완성된 최초날')]:
                rows.append(dict(market=m,id=ident+'__'+tag,label=ident+' '+tag,family='Follow-up',condition=cond+'; 기준 신호='+d[ident],signal_day='실제 확인일; 첫 신호일로 소급하지 않음',repeat='새 기본 신호가 재무장; 각 기본 신호당 해당 후속조건 최대1회; 공백 초기화'))
    return rows

if __name__=='__main__':pd.DataFrame(definitions()).to_csv(OUT/'definitions.csv',index=False,encoding='utf-8-sig')
