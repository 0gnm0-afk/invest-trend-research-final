# 한국·미국 상승·하락 추세 지표 연구: 최종 결과

2026-10-29 장기 연구와 사용자가 최종 결과로 지정한 두 Work 세션의 해석을 함께 보존한 공개 기록이다. 원시 OHLCV·계좌·인증·개인 대화 링크·운영 DB는 포함하지 않는다.

## 먼저 읽을 파일

1. [CCI·RSI 상승추세 지표 해석](final/uptrend-interpretation-ko.md): 빠른 상승 초입 탐색이라는 목적에서 각 지표의 역할과 대가.
2. [MACD+RSI 하락추세 지표 해석](final/downtrend-interpretation-ko.md): 알림 빈도·초입 확인·진행된 하락 확인·이후 위험의 구별.
3. [연구 경위와 시행착오](HISTORY.md): 출발 질문, 초기 결과, 평가 정의의 변화와 장기 재검증.

앞선 설명까지 보려면 [상승 해설 모음](final/uptrend-explanations-ko.md)·[하락 해설 모음](final/downtrend-explanations-ko.md)을 읽는다. 마지막 판단뿐 아니라 적중률/포착률/이후 방향의 차이를 설명한 답변도 남겼다.

## 해석의 근거

- [15년 상승 연구 본편](docs/research/uptrend-longhistory-2026-10-29.md)와 같은 이름의 폴더에 CSV·차트·규약·검증 기록.
- [15년 하락 연구 본편](docs/research/downtrend-longhistory-2026-10-29.md)와 같은 이름의 폴더에 CSV·차트·규약·검증 기록.
- [21거래일 기간말 하락 추가 집계](docs/research/downtrend-terminal21-2026-10-29.md)와 전체81조건·TOP5·연도별 CSV.
- [코드·외부 입력·검증 범위](CODE_AND_DATA.md).

주 분석은2010-10-01~2025-09-30이다. 상승72조건·하락81조건을 한국/미국 별도로 비교했다. 현재 저장 목록 중심의 역사적 연구이며 새 독립 검증이나 실행 전략의 수익성 입증은 아니다.

`MANIFEST.json`은 이 공개 묶음의 파일별SHA-256이다. `provenance/source-map.json`은 원본과 공개본의 해시 및 경로 비식별화 여부를 구분한다. 원래 연구 검증 영수증은 당시 입력/파일을 설명하므로, 공개본의 현재 해시는 새MANIFEST를 따른다. 압축 묶음의 중복 사본은 포함하지 않았다.


## 이동평균선 연구의 종료 결과

[MA 연구 최종 결과 모음](ma/README.md) · [연구 목적·시행착오](ma/HISTORY.md) · [공개 제외 자료와 재현 범위](ma/OMITTED_DATA.md).

MA 후보113개 파일은 별도의 Astra high 에이전트가 공개 적합성을 전수 감사했다. 개인 기록 관련 문장/코드 경로를 수정한 뒤 최종 PASS를 받았으며, 공개 후보의 고정 MANIFEST SHA-256은 `e5dfb2576a6a26200307a2e8fb014ca39e0c382ef50fb0f1237900f661f8dc57`이다. 이는 공개 적합성 감사이며 연구 통계의 전면 재검증이나 원시자료의 재배포 권한 판단은 아니다. 원시시세·개인기록·운영/인증 자료는 공개 후보에서 제외했다.
