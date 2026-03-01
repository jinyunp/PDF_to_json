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
- `keyword` — 소문자 단어
- `count` — 문서 내 등장 횟수

정렬: `count` 내림차순
