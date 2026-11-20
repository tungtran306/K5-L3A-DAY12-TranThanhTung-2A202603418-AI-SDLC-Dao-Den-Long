# Đảo Đèn Lồng — v1.0.0 (Day 12 AI SDLC)

> **Video Demo (< 5 phút):** [Xem demo trên GitHub Release v1.0.0](https://github.com/tungtran306/K5-L3A-DAY12-TranThanhTung-2A202603418-AI-SDLC-Dao-Den-Long/releases/tag/v1.0.0) *(đính kèm `demo.mp4` trong Release `v1.0.0`)*

Game **3D góc nhìn thứ ba** qua **3 Đêm** (*Đêm 1 – Đảo Bến*, *Đêm 2 – Đảo Cau*, *Đêm 3 – Đảo Chuông*): cùng **Mây** (đội nón lá treo đèn lồng nhỏ) gom đom đóm thắp và châm dầu giữ các Đèn Lồng Lớn sáng tới bình minh, dùng **Lướt**, **Tỏa Sáng**, **Bục Nhảy** và **Bùa Gió** để né **Bóng Mực** và **Gió Lạc**.

---

## Yêu cầu hệ thống & Cài đặt (Tối đa 3 lệnh)

- **Hệ điều hành:** macOS, Linux hoặc Windows (trên Windows thay `python3` bằng `python`).
- **Yêu cầu:** **Python 3.10+** (0 dependency cài thêm) + trình duyệt hiện đại có WebGL (Chrome/Edge/Firefox/Safari).

```bash
# 1. Kiểm tra biên dịch toàn bộ mã nguồn
python3 -m py_compile src/maps.py src/engine.py src/headless.py src/server.py src/leaderboard.py src/soak.py src/bench.py

# 2. Chạy toàn bộ bộ kiểm chứng (Unit/Contract v1.3 + Regression + Determinism 3 Đêm + Soak 10 Đêm)
python3 scripts/verify.py

# 3. Chơi game 3D trên trình duyệt (http://127.0.0.1:8000)
python3 -m src.server
```

## Điều khiển & Trợ năng (Accessibility)
Mọi phím đều có thể **đổi phím** (phát hiện trùng phím + nút *Khôi phục mặc định*) trong **Cài đặt & Trợ năng**:
- **`W / A / S / D`**: Di chuyển (`6.0 m/s`; `7.2 m/s` khi có Bùa Gió)
- **`Space`**: Nhảy · **`Shift`**: Lướt (`14 m/s`, hồi `1.5s`, `0s` khi có Bùa Gió)
- **`E`**: Thắp đèn / Thắp lại (`5` đom đóm) / Châm dầu (`+10` fuel/đom đóm)
- **`F`**: Tỏa Sáng (`3` đom đóm, choáng Bóng Mực `+5` điểm hoặc `+15` nếu đang `drain`, ép Gió Lạc thả đồ)
- **`Esc` / `P`**: Tạm dừng · **`Q / R` / Mũi tên / Kéo chuột**: Xoay camera 3D tự do (headless vẫn xoay theo `cam_yaw_deg`)
- **Trợ năng:** Bảng màu dễ phân biệt (mù màu), Giảm chuyển động, Cỡ chữ tối thiểu `18px` + Cỡ chữ lớn `×1.25`, phụ đề & mũi tên chỉ hướng khi Bóng Mực xuất hiện / gió mạnh / 10s cuối / đèn yếu.

## Sáng tạo của tôi
Để tăng trải nghiệm chơi mà **không làm đổi số liệu chuẩn, bản đồ chuẩn và Test Contract v1.3**, bản chơi 3D (`web/game.js`) bổ sung **2 bùa buff cổ tích** (tắt hoàn toàn trong chế độ headless, soak test và benchmark):
1. **🧲 Bùa Hút Đom Đóm (Xanh ngọc):** Hiệu lực `12s` (hồi `35s`), hút đom đóm trong bán kính `20m` bay về phía Mây.
2. **🛡️ Bùa Khiên Ánh Sáng (Vàng kim):** Hiệu lực `14s` (hồi `40s`), tạo quả cầu khiên vàng nhạt mờ quanh Mây chặn `1` lần bị Bóng Mực chạm (khiên vỡ biến mất ngay khi chặn đòn, không mất Ngọn Lửa/đom đóm).
3. **Tinh chỉnh nhịp hồi Bùa Gió bản 3D:** `20s` trong bản 3D (headless giữ nguyên `2700` tick theo Contract).
- **Bằng chứng phần lõi không bị ảnh hưởng:** [`docs/proof/phase-4/verify_summary.json`](docs/proof/phase-4/verify_summary.json) (toàn bộ test & determinism 3 Đêm `PASS`).

## Lệnh Test, Headless, Benchmark, Soak & Bảng xếp hạng (Contract v1.3)

```bash
# Headless CLI (60 tick/s, tất định 100%)
python3 -m src.headless --seed 42 --night 1 --ticks 600 --out out.jsonl --snapshot-every 10

# Benchmark 3D 1280x720 (200 Bóng Mực, 100 đom đóm, 3s warmup + 30s đo)
python3 -m src.bench --seed 42 --duration 30 --out bench.json

# Soak test 10 Đêm liên tiếp
python3 -m src.soak --seed 7 --nights 10 --out soak.json

# Xuất Bảng xếp hạng cục bộ (Top 10)
python3 -m src.server --export-leaderboard leaderboard_out.json

# Đóng gói bản phát hành v1.0.0
python3 scripts/package_release.py
```

*Lưu ý về Benchmark bản Web:* `src/bench.py` tự động mở Chrome/Edge ở cửa sổ `1280×720` kèm cờ `--disable-frame-rate-limit --disable-gpu-vsync` (`vsync_off: true`). Nếu máy không có Chrome/Edge và rơi về trình duyệt mặc định không tắt được vsync, `vsync_off` sẽ được ghi `false`. `peak_mem_mb` ghi theo `performance.memory` nếu trình duyệt hỗ trợ, ngược lại ghi `null` do giới hạn sandbox trình duyệt.

## Tài liệu, Bằng chứng, ADR, Retro & Harness AI
- **Retrospective toàn dự án:** [`docs/RETRO.md`](docs/RETRO.md)
- **ADR & Changelog:** [`docs/adr/001-lantern-fuel-and-dawn-survival.md`](docs/adr/001-lantern-fuel-and-dawn-survival.md) · [`CHANGELOG.md`](CHANGELOG.md)
- **Kết quả đo hiệu năng & ổn định:** [`bench.json`](bench.json) · [`soak.json`](soak.json)
- **Ghi chép từng phase:** [`phase-1`](docs/notes/phase-1.md) · [`phase-2`](docs/notes/phase-2.md) · [`phase-3`](docs/notes/phase-3.md) · [`phase-4`](docs/notes/phase-4.md)
- **Bằng chứng tự động:** [`docs/proof/phase-1/`](docs/proof/phase-1/) · [`phase-2/`](docs/proof/phase-2/) · [`phase-3/`](docs/proof/phase-3/) · [`phase-4/`](docs/proof/phase-4/)
- **Harness AI:** [`AGENTS.md`](AGENTS.md) · [`.agents/skills/verify-phase/SKILL.md`](.agents/skills/verify-phase/SKILL.md) · [`scripts/verify.py`](scripts/verify.py) · [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
- **Bản quyền & Nguồn:** [`CREDITS.md`](CREDITS.md) · [`LICENSE`](LICENSE)
