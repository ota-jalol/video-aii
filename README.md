# video-aii

`video-aii` uchun boshlang'ich, amaliy karkas yaratildi: loyiha hozircha bo'sh bo'lgani uchun uni ishlatishga tayyor minimal CLI va hujjatlar bilan takomillashtirildi.

## Nima qo'shildi?

- Loyiha holati bo'yicha qisqa tahlil va tavsiyalar (`docs/PROJECT_ANALYSIS_UZ.md`)
- `video_aii` nomli Python paketi
- Video fayllarni katalog bo'yicha topib, JSON hisobot beradigan CLI (`video-aii analyze`)
- Asosiy testlar (`tests/test_analyzer.py`)

## Tezkor ishga tushirish

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
video-aii analyze . --pretty
```

## CLI misoli

```bash
video-aii analyze ./sample_videos --extension .mp4 --pretty
```

Natijada quyidagiga o'xshash JSON chiqadi:

```json
{
  "root": "/workspace/video-aii/sample_videos",
  "video_count": 3,
  "total_size_bytes": 9876543,
  "extensions": {
    ".mp4": 2,
    ".mov": 1
  },
  "largest_files": [
    {
      "path": "trailer.mp4",
      "size_bytes": 5321987
    }
  ]
}
```

## Keyingi takomillashtirishlar

1. `ffprobe` integratsiyasi orqali duration/fps/codec kabi metadata yig'ish
2. Shot-detection va keyframe extraction pipeline
3. Model inference (captioning / moderation / tagging) moduli
4. CI/CD (lint + test + release workflow)
