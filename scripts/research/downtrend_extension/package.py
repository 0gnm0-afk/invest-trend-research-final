"""Package validated research tables and verify the delivered local artifacts."""
from pathlib import Path
import csv
import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / 'docs/research/downtrend-extension-2026-10-29'
REPORT = DOC.with_suffix('.md')
CODE = Path(__file__).parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    csv_files = sorted(DOC.glob('*.csv'))
    catalog = []
    for path in csv_files:
        with path.open(encoding='utf-8-sig', newline='') as stream:
            rows = csv.reader(stream)
            headers = next(rows)
            n = sum(1 for _ in rows)
        catalog.append(dict(file=path.name, rows=n, columns=headers, sha256=digest(path)))
    (DOC / 'csv-catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')
    readme = '''# 하락 초입 추가 연구 CSV 안내

주 결과는 primary-summary.csv, 전체 기간 계산은 evaluate-metrics.csv다.
period=test는 이미 검토한 2023-04~2025-09 자료의 추가 탐색이다.
비율은 별도 단위 표시가 없으면 0~1이며, 차이는 비율 차이다(100을 곱하면 %p).
mean_delay는 성공한 첫 신호의 거래일 지연이다. 연간 빈도는 252개 평가 가능일 기준이다.
선행 경고·늦은 확인도 전체 신호 적중률 분모에 포함된다.
matched-paths/summary21의 scheme3은 가장 엄격한 동일 종목·분기 상태 비교다.
가격경로 기준은 신호 다음 연속 유효 시가다. loss/gain 접촉은 수익 실현을 뜻하지 않는다.
KR/US-signal-definitions.csv에 고정한 발생 조건이 있고, *-data.csv는 그림의 실제 데이터다.
csv-catalog.json에 모든 CSV의 열·행수·SHA-256이 있다.
상세 정의와 해석은 함께 제공된 methods.md, literature.md 및 본 보고서를 읽어야 한다.
종목별 전체 사건 원장은 로컬 runtime/downtrend-extension-20261029/all-signal-ledger.csv.gz에 보존한다.
'''
    (DOC / 'CSV-README.md').write_text(readme, encoding='utf-8')
    archive = DOC / 'results-csv.zip'
    members = csv_files + [DOC / n for n in ('csv-catalog.json', 'CSV-README.md', 'methods.md', 'literature.md')]
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in members:
            z.write(path, path.name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(members)
        for path in members:
            assert z.read(path.name) == path.read_bytes(), path.name

    link_count = 0
    for path in [REPORT, *DOC.glob('*.md'), CODE / 'README.md']:
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if target.startswith(('http:', 'https:', '#')):
                continue
            target = target.split('#')[0].strip('<>')
            assert (path.parent / target).resolve().exists(), (path.name, target)
            link_count += 1
    images = sorted(DOC.glob('*.png'))
    assert len(images) == 9
    for path in images:
        with Image.open(path) as im:
            assert im.width >= 1000 and im.height >= 500
            im.verify()
    code_hashes = {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in sorted(CODE.iterdir()) if p.is_file()}
    previous = json.loads((DOC / 'reproduction-manifest.json').read_bytes())
    previous.update(code=code_hashes, csv={p.name: digest(p) for p in csv_files})
    (DOC / 'reproduction-manifest.json').write_text(json.dumps(previous, ensure_ascii=False, indent=2), encoding='utf-8')
    checks = dict(status='PASS', checked_at=datetime.now(timezone.utc).isoformat(), csv_files=len(csv_files),
                  archive_members=len(members), archive_bytes=archive.stat().st_size, archive_byte_comparison=True,
                  local_links=link_count, image_integrity_checks=len(images),
                  numerical_verification='verification-final.json and verification-extension.json',
                  scope='downtrend; scope-confirmation.json preserves the user correction')
    (DOC / 'delivery-verification.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')
    manifest_paths = [REPORT, *[p for p in DOC.iterdir() if p.is_file() and p.name != 'artifact-manifest.json']]
    manifest = {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in sorted(manifest_paths)}
    (DOC / 'artifact-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(checks, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
