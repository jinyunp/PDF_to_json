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
완료 후 `run_check_completed`를 자동 호출하여 `logs/completed_pages.txt`를 갱신한다.

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

`data/json_output/<pdf_name>/texts_final.json`을 읽어 chunk별 TF-IDF 키워드를 추출한다.

**동작 순서:**
1. `texts_final.json`의 각 chunk에서 단어·구문 빈도 집계
2. 전체 chunk 기준 IDF 계산
3. 각 chunk에 `keywords: [{keyword, score}]` 필드 추가 후 `texts_final.json` in-place 업데이트
4. 전체 chunk 통합 `keywords.json` 생성 (score = count × IDF, 구문 1.5× 부스트)

**추출 기준:**
- **단어(word)**: 3자 이상 영문 토큰, 불용어 제외
- **구문(phrase)**: 2-gram · 3-gram, 구성 단어 모두 불용어가 아닌 경우만 포함, 의미 단위 우선을 위해 1.5× 가중치 적용
- `[doc:][path:][page:]` 메타데이터 prefix 줄은 추출 전 자동 제거
- 결과는 `score` 내림차순 정렬, 각 항목에 `type: "word" | "phrase"` 및 `score` 필드 포함

인자:
```
--root_dir        (미사용, 하위 호환용) OCR 루트 경로 (기본: data/ocr)
--pdf             PDF 폴더명 (필수)
--out_root        JSON 출력 루트 (기본: data/json_output)
--top_n           chunk별 및 전역 단어 추출 수 (기본: 30)
--top_n_phrases   전역 구문 추출 수 (기본: top_n과 동일)
--min_count       전역 keywords.json 최소 등장 횟수 (기본: 2)
```

## check

OCR 결과(`result.mmd`)가 존재하는 페이지 목록을 출력하고
`logs/completed_pages.txt`에 저장한다.
`retry-empty` 실행 시 자동으로 호출되므로, 단독 실행은 별도로 현황을 확인할 때 사용한다.

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
