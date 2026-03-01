# CLI Specification — PDF_to_json

## stage1_ocr / ocr

PDF를 페이지별 OCR 수행 후 `data/ocr/<pdf_name>/page_xxxx/result.mmd` 생성

인자:
```
--pdf_input   PDF 파일 또는 폴더 경로 (필수)
--out_root    OCR 출력 루트 (기본: data/ocr)
--start_page  1-based 시작 페이지
--end_page    1-based 종료 페이지
--dpi         렌더링 DPI (기본: 200)
--device      cuda/cpu 강제 지정
```

## stage2_quality / retry-empty

빈 mmd 파일 탐지 및 해당 페이지 재OCR 수행

인자:
```
--root_dir    OCR 루트 경로 (기본: data/ocr)
--pdf         PDF 폴더명 (필수)
--max_retry   재시도 횟수 (기본: 1)
--device      cuda/cpu 강제 지정
```

## stage3_structure / structure

mmd를 파싱하여 구조화 JSON 생성

인자:
```
--root_dir    OCR 루트 경로 (기본: data/ocr)
--pdf         PDF 폴더명 (필수)
--out_root    JSON 출력 루트 (기본: data/json_output)
```

## stage4_keywords / keywords

mmd 파일 전체에서 자주 등장하는 키워드 추출

인자:
```
--root_dir    OCR 루트 경로 (기본: data/ocr)
--pdf         PDF 폴더명 (필수)
--out_root    JSON 출력 루트 (기본: data/json_output)
--top_n       추출할 키워드 수 (기본: 50)
--min_count   최소 등장 횟수 (기본: 2)
```

## Exit Code

`0`: Success
`2`: Input error
`3`: OCR failure
