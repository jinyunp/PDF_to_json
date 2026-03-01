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
- `count` — 문서 내 등장 횟수
- `type` — `"word"` (단일 단어) 또는 `"phrase"` (2-gram · 3-gram 구문)

정렬: `count` 내림차순 (단어·구문 통합)

예시:
```json
[
  {"keyword": "blast furnace", "count": 312, "type": "phrase"},
  {"keyword": "iron", "count": 289, "type": "word"},
  {"keyword": "hot blast", "count": 201, "type": "phrase"},
  {"keyword": "temperature", "count": 178, "type": "word"}
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
