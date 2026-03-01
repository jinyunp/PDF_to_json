# CLI Specification — PDF_to_json

## stage1_ocr / ocr

PDF를 페이지별 OCR 수행 후 `data/ocr/<pdf_name>/page_xxxx/result.mmd` 생성.

기본 실행 시 터미널에는 페이지 진행 상황(`[file.pdf] 3/20 페이지 처리 중...`)만 표시되며,
transformers/torch 등 라이브러리 로그는 자동 억제된다.

인자:
```
--pdf_input   PDF 파일 또는 폴더 경로 (필수)
--out_root    OCR 출력 루트 (기본: data/ocr)
--start_page  1-based 시작 페이지
--end_page    1-based 종료 페이지
--dpi         렌더링 DPI (기본: 200)
--device      cuda/cpu 강제 지정
--verbose     상세 로그 출력 (기본: False)
```

## stage2_quality / retry-empty

빈 mmd 파일 탐지 및 해당 페이지 재OCR 수행.
처리 대상 페이지는 `logs/empty_pages_quality.txt`에 기록되고,
재시도 후에도 실패한 페이지는 `logs/empty_pages_retry_failed.txt`에 기록된다.

인자:
```
--root_dir    OCR 루트 경로 (기본: data/ocr)
--pdf         PDF 폴더명 (필수)
--max_retry   재시도 횟수 (기본: 1)
--device      cuda/cpu 강제 지정
```

## stage3_structure / structure

mmd를 파싱하여 구조화 JSON 생성.

인자:
```
--root_dir    OCR 루트 경로 (기본: data/ocr)
--pdf         PDF 폴더명 (필수)
--out_root    JSON 출력 루트 (기본: data/json_output)
```

## stage4_keywords / keywords

mmd 파일 전체에서 자주 등장하는 단어(word)와 구문(phrase)을 추출하여
`keywords.json`에 저장한다.

- **단어**: 3자 이상 영문 토큰, 불용어 제외
- **구문**: 2-gram · 3-gram, 구성 단어가 모두 불용어가 아닌 경우만 포함
- 결과는 등장 횟수 내림차순으로 정렬되며 각 항목에 `type: "word" | "phrase"` 필드 포함

인자:
```
--root_dir        OCR 루트 경로 (기본: data/ocr)
--pdf             PDF 폴더명 (필수)
--out_root        JSON 출력 루트 (기본: data/json_output)
--top_n           추출할 단어 수 (기본: 50)
--top_n_phrases   추출할 구문 수 (기본: top_n과 동일)
--min_count       최소 등장 횟수 (기본: 2)
```

## check

OCR 결과(`result.mmd`)가 존재하는 페이지 목록을 출력하고
`logs/completed_pages.txt`에 저장한다.

인자:
```
--root_dir    OCR 루트 경로 (기본: data/ocr)
--pdf         PDF 폴더명 (필수)
```

출력 예시:
```
[my_document] 완료: 22/266 페이지
저장됨: data/ocr/my_document/logs/completed_pages.txt
미완료 페이지 (244개): page_0023, page_0024, ...
```

## Exit Code

`0`: Success
`2`: Input error
`3`: OCR failure
