# Exact condition catalog

72 conditions per market: 47 standalone events, 4 fixed anchors, 6 prior followups, 4 maintained states, and 11 extension events. No threshold search or new combination was performed in this reassessment.

All upward crossings use the inherited relative tolerance `tol[t]=1e-12 × max(abs(a[t]),abs(b[t]))`: `a[t]−b[t]>tol[t]` and `a[t−1]−b[t−1]≤tol[t−1]`, with both dates finite. Simple above/below states use their stated strict inequalities. A true condition with an unknown prerequisite remains unknown. Shared warmup masks the first65 bars of each valid segment; longer formula warmups still apply. EMA uses span n, adjust=False, minimum n observations. Wilder averages seed at the first n finite observations. Signals are known at the completed close.

| ID | Readable name | Markets | Type | Exact condition |
| --- | --- | --- | --- | --- |
| price5 | Close > SMA5 cross | KR, US | event | C crosses above SMA5 |
| price10 | price10 | KR, US | event | C crosses above SMA10 |
| price20 | Close > SMA20 cross | KR, US | event | C crosses above SMA20 |
| price50 | price50 | KR, US | event | C crosses above SMA50 |
| price200 | price200 | KR, US | event | C crosses above SMA200 |
| ma5_10 | ma5_10 | KR, US | event | SMA5 crosses above SMA10 |
| ma5_20 | ma5_20 | KR, US | event | SMA5 crosses above SMA20 |
| ma10_20 | ma10_20 | KR, US | event | SMA10 crosses above SMA20 |
| ma20_60 | ma20_60 | KR, US | event | SMA20 crosses above SMA60 |
| ma50_200 | ma50_200 | KR, US | event | SMA50 crosses above SMA200 |
| ma20_turn | ma20_turn | KR, US | event | SMA20[t]>SMA20[t-5], first true day |
| rsi30 | RSI14 > 30 cross | KR, US | event | Wilder RSI14 crosses above 30 |
| rsi40 | rsi40 | KR, US | event | Wilder RSI14 crosses above 40 |
| rsi50 | rsi50 | KR, US | event | Wilder RSI14 crosses above 50 |
| rsi60 | rsi60 | KR, US | event | Wilder RSI14 crosses above 60 |
| macd_signal | macd_signal | KR, US | event | EMA12(C)-EMA26(C) crosses above EMA9(MACD) |
| macd_zero | macd_zero | KR, US | event | MACD crosses above 0 |
| dmi_cross | dmi_cross | KR, US | event | Wilder14 +DM crosses above -DM (common ATR denominator) |
| adx_bull | adx_bull | KR, US | event | ADX14 crosses above20 while +DM>-DM |
| stoch20 | stoch20 | KR, US | event | Slow K=SMA3(100*(C-min L14)/(max H14-min L14)) crosses above20 |
| stoch_low_cross | stoch_low_cross | KR, US | event | K crosses above SMA3(K), previous K<=20 |
| cci-100 | CCI20 > -100 cross | KR, US | event | (TP-SMA20(TP))/(.015*mean absolute deviation20) crosses above -100 |
| cci0 | cci0 | KR, US | event | (TP-SMA20(TP))/(.015*mean absolute deviation20) crosses above 0 |
| cci100 | cci100 | KR, US | event | (TP-SMA20(TP))/(.015*mean absolute deviation20) crosses above 100 |
| bb_reentry | bb_reentry | KR, US | event | C crosses above SMA20-2*population SD20 |
| bb_upper | bb_upper | KR, US | event | C crosses above SMA20+2*population SD20 |
| bb_squeeze | bb_squeeze | KR, US | event | bb_upper AND previous bandwidth<=1.1*previous120 minimum bandwidth |
| keltner_upper | keltner_upper | KR, US | event | C crosses above EMA20+2*Wilder ATR14 |
| high20 | high20 | KR, US | event | C>maximum H of prior20 bars, first true day |
| high60 | high60 | KR, US | event | C>maximum H of prior60 bars, first true day |
| failed_low20 | failed_low20 | KR, US | event | L<prior20 minimum L AND C>that level AND C>O, first true day |
| bull_gap | bull_gap | KR, US | event | O>previous H AND C>O; every qualifying day |
| bull_engulf | bull_engulf | KR, US | event | previous C<O, C>O, O<=previous C and C>=previous O; every qualifying day |
| up_volume15 | up_volume15 | KR, US | event | C>previous C AND V/prior20 mean V>=1.5, first true day |
| atr_jump_volume | atr_jump_volume | KR, US | event | C>previous C+1.5*previous ATR14 AND relative volume>=1.5; every qualifying day |
| obv_inflow | obv_inflow | KR, US | event | sum20(V*sign(return1))/sum20(V) crosses above .2 |
| cmf_zero | cmf_zero | KR, US | event | CMF20 crosses above0; H=L contribution0 |
| mfi20 | MFI14 > 20 cross | KR, US | event | MFI14 crosses above20 |
| mfi50 | mfi50 | KR, US | event | MFI14 crosses above50 |
| roc10_zero | roc10_zero | KR, US | event | C/C[t-10]-1 crosses above0 |
| aroon_cross | aroon_cross | KR, US | event | AroonUp25 crosses above AroonDown25; ties most recent |
| vortex_cross | vortex_cross | KR, US | event | sum14(abs(H-prev L)) crosses above sum14(abs(L-prev H)) |
| ichimoku_tk | ichimoku_tk | KR, US | event | 9-bar midpoint crosses above26-bar midpoint |
| ichimoku_cloud | ichimoku_cloud | KR, US | event | C crosses above max of both cloud spans calculated26 bars earlier |
| rebound2atr | rebound2atr | KR, US | event | (C-min L20)/ATR14 crosses above2 |
| pivot_break | pivot_break | KR, US | event | C crosses above latest 5-bar pivot high, known only 2 bars after pivot; left strict/right inclusive |
| reclaim_drawdown | reclaim_drawdown | KR, US | event | price20 AND previous close<=90% of preceding63 close maximum |
| macd_rsi40 | MACD cross + recent RSI40 | KR, US | event | macd_signal AND rsi40 crossed upward on t,t-1 or t-2 |
| macd_negative | MACD bullish cross with MACD < 0 | KR, US | event | macd_signal AND MACD<0 |
| high20_volume | high20_volume | KR, US | event | high20 AND relative_volume>=1.5 |
| cci_recovery | CCI recovery / falling SMA20 | KR, US | event | cci-100 AND SMA20[t]<SMA20[t-5] |
| rsi30__and20 | RSI14 > 30 cross + same-day > SMA20 | KR, US | event | base event AND C>SMA20 on same day |
| rsi30__then20 | RSI14 > 30 cross + SMA20 cross by +5 | KR, US | event | first price20 event base day..+5 inclusive |
| rsi30__persist3 | RSI14 > 30 cross + 3 closes > SMA20 by +5 | KR, US | event | first three consecutive C>SMA20, run starts>=base and completes<=base+5 |
| mfi20__and20 | MFI14 > 20 cross + same-day > SMA20 | KR | event | base event AND C>SMA20 on same day |
| mfi20__then20 | MFI14 > 20 cross + SMA20 cross by +5 | KR | event | first price20 event base day..+5 inclusive |
| mfi20__persist3 | MFI14 > 20 cross + 3 closes > SMA20 by +5 | KR | event | first three consecutive C>SMA20, run starts>=base and completes<=base+5 |
| state_price5 | State: close > SMA5 | KR, US | state | C>SMA5; every qualifying day |
| state_price20 | State: close > SMA20 | KR, US | state | C>SMA20; every qualifying day |
| state_macd | State: MACD > signal | KR, US | state | MACD>signal; every qualifying day |
| state_macd_rsi40 | State: MACD > signal and RSI > 40 | KR, US | state | MACD>signal AND RSI>40; every qualifying day |
| supertrend | Supertrend bullish flip | KR, US | event | Wilder ATR10 * 3 trailing bands; down-to-up flip at close |
| psar | Parabolic SAR bullish reversal | KR, US | event | PSAR start=.02, increment=.02, max=.20; bearish-to-bullish direction reversal |
| trix_zero | TRIX18 > 0 cross | KR, US | event | 1-bar percent change of triple EMA18 crosses above0 |
| trix_signal | TRIX18 > signal cross | KR, US | event | TRIX18 crosses above its EMA9 |
| stochrsi20 | StochRSI K > 20 cross | KR, US | event | RSI14, range14, SMA3 K: K crosses20; flat range unknown |
| stochrsi_cross | StochRSI low K/D cross | KR, US | event | K crosses SMA3(K) and previous K<=20 |
| rmi30 | RMI20/5 > 30 cross | KR, US | event | Wilder20 smoothed 5-day changes: RMI crosses above30 |
| rmi50 | RMI20/5 > 50 cross | KR, US | event | Wilder20 smoothed 5-day changes: RMI crosses above50 |
| chaikin | Chaikin3/10 > 0 cross | KR, US | event | EMA3(ADL)-EMA10(ADL) crosses0; H=L contribution0 |
| avwap_quarter | Quarter daily AVWAP cross | KR, US | event | C crosses sum(TP*V)/sum(V) since calendar quarter/segment start; at least 5 previous anchor bars |
| volume_osc | Volume oscillator + up day | KR, US | event | SMA5(V)/SMA20(V)-1 crosses0 AND C>previous C |
| cci-100__and20 | CCI20 > -100 cross + same-day > SMA20 | US | event | base event AND C>SMA20 on same day |
| cci-100__then20 | CCI20 > -100 cross + SMA20 cross by +5 | US | event | first price20 event base day..+5 inclusive |
| cci-100__persist3 | CCI20 > -100 cross + 3 closes > SMA20 by +5 | US | event | first three consecutive C>SMA20, run starts>=base and completes<=base+5 |

For RSI, use Wilder14 of one-day positive/negative close changes. For CCI, use typical price `(H+L+C)/3`, SMA20 and mean absolute deviation20 with scale 0.015. MACD is EMA12(close)−EMA26(close), signal EMA9(MACD). Sequence and persistence rules trigger only when the final required observation is available; a new base event rearms the rule and the completion deadline is base day+5. Three-close persistence requires its run to begin no earlier than the base event. There are 68 events and 4 maintained states per market. Most events are new crossings/transitions; the candle/jump rules explicitly marked “every qualifying day” can recur on consecutive dates. States count each qualifying day; they are not first-entry alerts.

Daily AVWAP is a typical-price/volume proxy from a pre-known calendar-quarter anchor (or segment start), with at least 5 previous anchor bars. It does not reconstruct intraday transaction VWAP. The 5-bar pivot is available only 2 bars after the pivot date. PSAR initialization and recursive band details are reproducible in [new_signals.py](../../../scripts/research/uptrend_longhistory/new_signals.py); the inherited formulas are in [old_signals.py](../../../scripts/research/uptrend_longhistory/old_signals.py). Platform-specific equality is not assumed.
