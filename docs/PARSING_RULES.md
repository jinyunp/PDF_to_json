# Parsing Rules

## 헤딩 분리

-   Markdown #, ##, \### 기준 분리

## 번호형 소제목

-   1.2.3 형태 인식하여 하위 제목 기준 분리

## Figure 인식

-   Fig, FIG, Figure, FIGURE 허용
-   img_no 필드 추가

## Table 인식

-   Table N
-   바로 아래 첫 문장: 표 제목
-   이후 HTML 본문 포함 필수
    ```{=html}
    <table>
    ```
    ...
    ```{=html}
    </table>
    ```
    블록 전체 포함

## 본문 참조 탐지

-   Fig N, Figure N, Table N 발견 시 multi_data_list / multi_data_path에 추가
