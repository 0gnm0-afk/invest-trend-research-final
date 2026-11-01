"""Copy inspectable summaries, package CSVs, and verify final report artifacts."""
from pathlib import Path
import json,csv,hashlib,re,shutil,zipfile
from datetime import datetime,timezone
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'runtime/downtrend-longhistory-20261029'
DOC=ROOT/'docs/research/downtrend-longhistory-2026-10-29'
REPORT=DOC.with_suffix('.md')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    for name in ['verification-longhistory.json','cases-verification.json','endpoint-recheck-validation.json']:
        assert json.loads((DOC/name).read_bytes())['status']=='PASS',name
    for name in ['classification-inference.json','paths-inference.json']:
        assert sum(json.loads((OUT/name).read_bytes())['stocks'].values())==7293,name
    if len(list((OUT/'paths').glob('*.npz')))!=7293:
        released=json.loads((DOC/'path-cache-release.json').read_bytes())
        assert released['status']=='PASS' and released['complete_available_universe']==7293
        available={p.name for stage in ['paths','ledgers'] for p in (OUT/stage).glob('*.npz')}
        assert len(available)==7293
    for p in OUT.glob('*.csv'):shutil.copyfile(p,DOC/p.name)
    for name in ['frozen-protocol.json','derivation-source-hashes.json','classification-inference.json','paths-inference.json','paths-compute-receipt.json','verification-path-matching.json','verification-path-interface.json','verification-path-reconciliation.json','tail-producer-receipt.json','interpretation-validation.json','interpretation-paths-validation.json']:
        p=OUT/name
        if p.exists():shutil.copyfile(p,DOC/name)
    import report
    results=report.load_results()
    for name,key in [('primary-summary.csv','primary'),('matched-summary.csv','risk'),('paired-summary.csv','paired')]:
        results[key].to_csv(DOC/name,index=False,encoding='utf-8-sig')
    readme='''# CSV 안내

primary-summary.csv는 81조건 × 2시장의 15년 주 결과다. 비율 필드는 0~1, 비율 차이에 100을 곱하면 %p다.
evaluate-metrics.csv의 period=all은 종목별 최초 저장 이력, reconciliation은 이전 연구의 최근 창 대조다.
classification-yearly/eras는 연도/고정5년 구간, equal-stock은 종목 동일가중이다.
matched-summary는 3/6개월 블록의 넓은 신뢰구간으로 합친 상태 비교다. scheme3이 가장 엄격하다.
path-distributions는 고정18조건의 정확한 분포, all81-path-summary는 전체81조건의 평균/접촉률이다.
coverage-stocks/input-manifest에서 자료 분모·출처를 확인할 수 있다. 그림마다 -data.csv가 있다.
KR/US-signal-definitions에는 조건과 event/daily_pattern 구분이 있다. 후속6조건은 실제 확인일에 센다.
미래 저점까지의 낙폭은 실현 수익이나 피할 수 있었던 손실이 아니다. 상세 산식과 해석은 methods.md 및 보고서를 읽어야 한다.
원자료와 코드는 보존되어 재계산 가능하다. 저장 공간 확보를 위해 검증 완료된 이번 분류 NPZ 캐시를 해제했으며 cache-release.json에 근거를 남겼다.
'''
    if (DOC/'path-cache-release.json').exists():
        readme+='\n가격경로 추론 완료 후 필요한 여유 공간을 확보할 만큼 월별 중간 배열을 해제했다. path-cache-release.json에 파일 수와 해시를 보존했다. 정리한 파일의 정확한 신호별 원장은 ledgers, 나머지는 기존 paths에 남아 전체 종목을 계속 읽을 수 있다. 재현 순서는 연구 코드 README를 따른다.\n'
    (DOC/'CSV-README.md').write_text(readme,encoding='utf-8')
    catalog=[];files=sorted(DOC.glob('*.csv'))
    for p in files:
        with p.open(encoding='utf-8-sig',newline='') as stream:
            rr=csv.reader(stream);cols=next(rr);n=sum(1 for _ in rr)
        catalog.append(dict(file=p.name,rows=n,columns=cols,sha256=sha(p)))
    (DOC/'csv-catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    members=files+[DOC/'csv-catalog.json']+sorted(DOC.glob('*.md'))
    archive=DOC/'results-csv.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in members:z.write(p,p.name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for p in members:assert z.read(p.name)==p.read_bytes(),p.name
    links=0
    for p in [REPORT,*DOC.glob('*.md')]:
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if target.startswith(('http:','https:','#')):continue
            target=target.split('#')[0].strip('<>');assert (p.parent/target).resolve().exists(),(p.name,target)
            links+=1
    images=sorted(DOC.glob('*.png'));assert len(images)>=12
    for p in images:
        with Image.open(p) as im:assert im.width>500 and im.height>400;im.verify()
    frozen=json.loads((OUT/'frozen-protocol.json').read_bytes())
    for k,h in frozen['original_reports_and_sources'].items():assert sha(ROOT/k)==h,k
    receipt=dict(status='PASS',checked_at=datetime.now(timezone.utc).isoformat(),csv_files=len(files),zip_members=len(members),zip_bytes=archive.stat().st_size,
                 zip_byte_comparison=True,local_links=links,image_integrity_checks=len(images),protected_prior_files=len(frozen['original_reports_and_sources']))
    (DOC/'delivery-verification.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    manifest={str(p.relative_to(ROOT)):sha(p) for p in [REPORT,*sorted(DOC.glob('*')),*sorted(Path(__file__).parent.glob('*'))] if p.is_file() and p.name!='artifact-manifest.json'}
    (DOC/'artifact-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
