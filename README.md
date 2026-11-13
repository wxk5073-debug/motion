# Real Magic — 30초 모션그래픽 (스펙 광고)

코카-콜라 브랜드 슬로건 "Real Magic"을 주제로 만든 30초, 16:9 키네틱 타이포그래피 광고입니다.
컨셉은 **어둡고 분위기 있게 시작해 탄산이 터지는 순간 청량하게 전환**되는 흐름입니다.

## 파일

| 파일 | 설명 |
|---|---|
| `CocaCola_RealMagic_30s.mp4` | 완성 영상 (1920×1080, 30fps, 30초, AAC 스테레오) |
| `CocaCola_RealMagic_30s.html` | 브라우저에서 실시간 재생되는 HTML 버전 (이미지·오디오 내장, 단일 파일) |
| `make_ad.py` | 영상 생성 스크립트 (프레임 렌더링 + BGM 합성 + ffmpeg 인코딩) |
| `assets/` | 공식 홈페이지 이미지, 슬로건 음성(vo1/vo2), 최종 믹스 오디오 |

## 구성

| 시간 | 장면 |
|---|---|
| 0–3.5s | 어둠 속 기포, "치익—" → "톡." |
| 3.5–8.5s | 제로 글라스 클로즈업, "차갑게 / 터지는 / 그 순간" |
| 8.5–13.5s | 레드 화면, FIZZ · POP · AHH / REFRESH 마키 + 로고 |
| 13.5–19.5s | 친구들, "함께라서 / 더 짜릿하게" |
| 19.5–24.5s | REAL MAGIC 글자 단위 낙하·상승 |
| 24.5–30s | 엔드카드 + "매일이 짜릿한 마법이 되도록" |

## HTML 조작

`Space` 재생/일시정지 · `F` 전체화면 · `R` 처음부터 · 하단 진행바 클릭으로 이동

## 다시 렌더링

```bash
pip install pillow numpy imageio-ffmpeg
python make_ad.py
```

BGM은 코드로 직접 합성했고, 음성은 Windows TTS(Microsoft Heami)입니다.

## 고지

비상업적 포트폴리오용 스펙 광고입니다. Coca-Cola 로고·상표 및 `assets/`의 이미지는 The Coca-Cola Company의 자산이며, 공식 광고가 아닙니다.
