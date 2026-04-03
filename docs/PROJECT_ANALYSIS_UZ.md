# Loyiha tahlili va takomillashtirish rejasi

## Joriy holat (audit)

Dastlabki tekshiruvda repozitoriyada faqat juda qisqa `README.md` bor edi, amaliy kod, test, konfiguratsiya va ishga tushirish bo'yicha aniq yo'riqnoma mavjud emas edi.

## Aniqlangan bo'shliqlar

- **Kod bazasi yo'q**: package va modul strukturasi shakllanmagan.
- **Ishga tushirish yo'riqnomasi cheklangan**: onboarding qiyin.
- **Test infratuzilmasi yo'q**: regressiya xavfi yuqori.
- **Loyiha yo'nalishi noaniq**: texnik roadmap dokumentatsiyasi yo'q.

## Kiritilgan yaxshilanishlar

1. Minimal ishlaydigan Python package arxitekturasi yaratildi.
2. Video fayllarni katalogdan analiz qiluvchi CLI qo'shildi.
3. Avtomatlashtirilgan testlar qo'shildi.
4. Yangilangan README orqali quickstart va roadmap berildi.

## Arxitektura (MVP)

- `src/video_aii/analyzer.py`: katalogni skanerlash va statistika yig'ish
- `src/video_aii/cli.py`: buyruq qatori interfeysi
- `tests/test_analyzer.py`: asosiy funksional testlar

## Tavsiya etiladigan navbatdagi qadamlar

- `ffprobe` integratsiyasi (codec, duration, fps)
- ML pipeline modullari (feature extraction + inference)
- CI (lint/test) va versiyalash siyosati
- Docker image va reproducible deployment
