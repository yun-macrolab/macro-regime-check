# 제3자 고지

## folium 예제 자료 `us-states.json` — 연준 인물 페이지의 지도

`site/people-data.js`의 `map`(미국 주 경계)은 [python-visualization/folium](https://github.com/python-visualization/folium) 저장소의 예제 자료 `examples/data/us-states.json`을 받아 앨버스 등면적 투영(본토 + 알래스카·하와이 삽입)으로 미리 계산한 SVG 경로입니다. 원 자료는 아래 MIT 라이선스를 따릅니다.

```
Copyright (C) 2013-, Folium developers
See https://github.com/python-visualization/folium/graphs/contributors for a
full list of contributors.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 연준 인물 사진 `site/photos/` — 연준 인물 페이지(2026-11-16)

이 폴더의 사진은 이 저장소의 MIT 라이선스(`LICENSE`)에 들지 않는다. 사진마다 원래 기관의 조건을 따르고, 페이지의 이름 아래 출처 줄에 그 조건을 적는다. 사진은 그 기관의 것이고, 이 사이트의 글·판정은 기관과 관계없으며 기관이 보증하지 않는다.

- **연준 이사회 이사**(`warsh`·`jefferson`·`waller`·`barr`·`cook`·`powell`): 연준 이사회 누리집의 이사 소개 쪽 사진. 이사회 고지(https://www.federalreserve.gov/disclaimer.htm, 'Copyright/trademark'): "Unless otherwise indicated, information on Board's website is in the public domain and may be copied and distributed without permission. Please cite to the Board as the source of the information." — 출처 줄 '연준 이사회 공식 사진(공공 영역)'. 보먼 이사 사진은 아래 '그 밖'.
- **뉴욕 연은 총재**(`williams`): 뉴욕 연은 누리집 총재 쪽의 'Download Photo'(서버 Last-Modified 2018-07-09). 뉴욕 연은 이용 약관(https://www.newyorkfed.org/privacy/termsofuse, 2023-06-09 판)은 사진을 Content에 넣고 "a non-exclusive license … to use, copy, and distribute Content for your personal or business purposes"와 "Modify and create derivative works"를 허락한다. 조건대로 정해진 출처 줄 "© 2018 Federal Reserve Bank of New York. Content from the New York Fed subject to the Terms of Use at newyorkfed.org."을 싣고, 이 사이트가 4:5로 잘라 크기를 줄인 사본이라고 적으며(뉴욕 연은이 고친 것으로 돌리지 않는다), 같은 조건보다 좁은 조건을 붙이지 않는다 — 이 사진은 위의 MIT가 아니라 뉴욕 연은 이용 약관을 따른다.
- **그 밖**(`bowman`과 지구 연은 총재 11명 — `collins`·`paulson`·`hammack`·`barkin`·`venable`·`goolsbee`·`musalem`·`kashkari`·`schmid`·`logan`·`daly`): 연준 이사회 누리집의 이사 소개 쪽(보먼)·지구 쪽(federalreserve.gov/aboutthefed/federal-reserve-system-<지구>.htm)에 실린 공식 사진. 이용 허락을 확인하지 못했고, 운영자가 비상업적 이용에 출처를 밝혀 싣기로 했다(2026-11-16). 출처 줄에 기관과, 파일 안에 적힌 사진가(Britt Leckman · Daniel Lozada · Steve Niedorf · Gary Barber)를 밝힌다. 권리자가 원하지 않으면 내린다(README '연준 인물'의 사진 절). 보먼 이사 사진의 파일 안 표시("ALL RIGHTS RESERVED")는 이사회 고지의 'Unless otherwise indicated'에 걸려 공공 영역으로 보지 않는다.
- 모든 사본은 크기를 줄이고(130×170 안, 일부는 4:5로 잘라) 파일 안의 메타데이터(EXIF·XMP·ICC·IPTC)를 뺀 JPEG이다.
