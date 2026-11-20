# Changelog

## [v1.0.0 / Phase 4 / Contract v1.3] - 2026-11-20 (Ticket-04: "Bình minh: phát hành v1.0.0")

### Added
- **Chế độ Benchmark 3D (`src/bench.py` + `web/game.js?bench=1`):** Cửa sổ `1280×720`, Đêm 1 chuẩn (200 Bóng Mực `wander`, 100 đom đóm, L1–L3 sáng `fuel = 100`, tắt sáng tạo thêm, camera bay vòng `r=30m, Y=15m`, 15s/vòng, 3s warmup), xuất chuẩn `bench.json` (`avg_fps`, `p1_low_fps`, `frame_ms_p95`, `frames`, `load_ms`, `peak_mem_mb`, `vsync_off`, `renderer`, `os`).
- **Soak Test 10 Đêm (`src/soak.py`):** Chạy 10 Đêm liên tiếp xoay vòng `1→2→3` trong 1 tiến trình, đo RSS đầu/cuối đa nền tảng (Windows/Linux/macOS), xuất `soak.json` với `crashes = 0` và `mem_end_mb <= 1.2 * mem_start_mb`.
- **Bảng xếp hạng cục bộ (`src/leaderboard.py` + `src/server.py` + UI):** Lưu top 10 trên đĩa (`data/leaderboard.json`), hỗ trợ tên 3–12 ký tự (gồm tiếng Việt có dấu), xếp hạng theo điểm giảm dần và thời gian đạt sớm hơn, hỗ trợ CLI `python3 -m src.server --export-leaderboard out.json`.
- **Dễ tiếp cận (Accessibility):** Đổi phím toàn bộ 9 hành động có phát hiện trùng phím & nút khôi phục mặc định; phụ đề & mũi tên chỉ hướng khi Bóng Mực xuất hiện / gió / 10s cuối / đèn yếu; chế độ Giảm chuyển động; cỡ chữ UI tối thiểu `18px` + tùy chọn chữ lớn `×1.25`.
- **Đóng gói phát hành:** Script `scripts/package_release.py` tạo gói chạy độc lập cho GitHub Release `v1.0.0`, tài liệu Retrospective [`docs/RETRO.md`](docs/RETRO.md), commit kết quả đo thật `bench.json` và `soak.json`.

## [Phase 3 / Contract v1.2] - 2026-11-20 (Ticket-03: "Đèn cạn dầu")
- **Breaking Changes:** Thay luật thắng sớm `all_lit` bằng sống sót tới bình minh `dawn_survived` (`>= ceil(0.6 * tổng đèn)`); đèn sáng tự hao `1.0` dầu/s, châm dầu `refuel`, tắt `lantern_out`, thắp lại tốn `5` đom đóm; đèn `fuel < 30` mất vùng an toàn & bị Bóng Mực hút `5` dầu/s (`drain`, `fuel_drain`); công thức điểm mới; sức chứa tăng dần `10 + 2 * successful_lights` (tối đa `20`); chế độ mù màu; ADR-001.

## [Phase 2 / Contract v1.1] - 2026-11-20 (Ticket-02: "Ba hòn đảo")
- Chuẩn hóa toàn bộ số liệu, mở rộng 3 Đêm (Đảo Bến, Đảo Cau, Đảo Chuông), Lướt, Gió Lạc, Bùa Gió, Tạm dừng, Cài đặt lưu `localStorage`, Âm thanh Web Audio, HUD đầy đủ, bảng màu chuẩn, sáng tạo 2 bùa buff 3D (Bùa Hút Đom Đóm & Bùa Khiên Ánh Sáng).

## [Phase 1 / Contract v1.0] - 2026-11-20 (PRD-0)
- Bản chơi đầu tiên Đêm 1 – Đảo Bến + Headless Test Contract v1.0 + Harness AI (`AGENTS.md`, skills, `verify.py`) + GitHub Actions CI.
