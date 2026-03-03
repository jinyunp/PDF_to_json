# DATA CONTRACT — PDF_to_json

## texts_final.json

`List[dict]`

필수 필드:
- `id` — `<page_dir>::<doc_id>#c<n>` 형식
- `filename` — PDF 폴더명
- `section_path` — 헤딩 경로 (없으면 null)
- `page` — 페이지 번호
- `text` — `[doc: …] [path: …] [page: …]\n<본문>` 형식
- `multi_data_list` — 참조된 fig/table ID 목록 (없으면 `[]`)
- `multi_data_path` — 대응 경로 목록 (없으면 `[]`)

`stage4_keywords` 실행 후 추가되는 필드:
- `keywords` — chunk 내 TF-IDF 상위 키워드 목록 `[{"keyword": str, "score": float}]`
  - 단어·구문 통합, score 내림차순 정렬
  - 구문(2-gram·3-gram)은 단어 대비 1.5× 가중치 적용

## tables_str_final.json

`List[dict]`

필수 필드:
- `id` — `<doc_id>#table<n>::p<page>`
- `component_type` — `"table"` 고정
- `original` — `Table N: <title>\n\n<HTML table>` 형식
- `text` — prefix + original
- `table_no` — 표 번호 (문자열)
- `section_path`, `filename`, `page`, `image_link`, `placeholder`

## images_sum_final.json

`List[dict]`

필수 필드:
- `id` — `<doc_id>#fig<n>::p<page>`
- `component_type` — `"image"` 고정
- `original` — Figure 캡션
- `text` — prefix + original
- `img_no` — 그림 번호 (문자열)
- `section_path`, `filename`, `page`, `image_link`, `placeholder`, `keyword`

## keywords.json

`List[dict]`

필드:
- `keyword` — 소문자 단어 또는 구문 (공백으로 단어 구분)
- `count` — 전체 chunk 합산 등장 횟수
- `score` — TF-IDF 기반 중요도 점수 (`count × IDF`, 구문은 1.5× 부스트 적용)
- `type` — `"word"` (단일 단어) 또는 `"phrase"` (2-gram · 3-gram 구문)

정렬: `score` 내림차순 (단어·구문 통합)

예시:
```json
[
  {"keyword": "blast furnace", "count": 312, "score": 892.14, "type": "phrase"},
  {"keyword": "iron", "count": 289, "score": 521.08, "type": "word"},
  {"keyword": "hot blast", "count": 201, "score": 487.32, "type": "phrase"},
  {"keyword": "temperature", "count": 178, "score": 312.45, "type": "word"}
]
```

## logs/completed_pages.txt

`check` 명령 실행 시 `data/ocr/<pdf_name>/logs/completed_pages.txt`에 생성.

형식: 비어 있지 않은 `result.mmd`가 존재하는 페이지 폴더명을 한 줄씩 기록.

```
page_0001
page_0002
page_0005
...
```
