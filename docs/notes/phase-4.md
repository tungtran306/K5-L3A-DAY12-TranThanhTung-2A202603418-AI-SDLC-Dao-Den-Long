# Phase 4 Notes — Ticket-04 "Bình minh: phát hành v1.0.0" (Contract v1.3)

## Bảng truy vết Yêu cầu → Bằng chứng (Phase 4)
| Yêu cầu Ticket-04 | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| Benchmark `1280×720` (200 Bóng Mực `wander`, 100 đom đóm, L1–L3 sáng, camera bay vòng 15s, 3s warmup) | `python3 -m src.bench --seed 42 --duration 30 --out bench.json` | [`bench.json`](../../bench.json) | Đạt |
| Soak test 10 Đêm liên tiếp (`crashes = 0`, `mem_end_mb <= 1.2 * mem_start_mb`) | `python3 -m src.soak --seed 7 --nights 10 --out soak.json` | [`soak.json`](../../soak.json) & `docs/proof/phase-4/verify_summary.json` | Đạt |
| Bảng xếp hạng cục bộ Top 10 + CLI `--export-leaderboard` | `test_leaderboard_top10_sort_tiebreak_and_export_cli` + UI Menu/Result | `docs/proof/phase-4/unittest_output.txt` | Đạt |
| Trợ năng: Đổi phím (phát hiện trùng + mặc định), Phụ đề & mũi tên Bóng Mực, Giảm chuyển động, Cỡ chữ `>= 18px` + `×1.25` | `web/index.html`, `web/style.css`, `web/game.js` (`screen-settings`) | Lưu bền vững trong `localStorage` | Đạt |
| Test Contract `v1.3` (`bench_cmd`, `soak_cmd`) & Regression Phase 1–3 | `python3 scripts/verify.py` | `docs/proof/phase-4/verify_summary.json` | Đạt |
| Đóng gói `v1.0.0`, `CHANGELOG.md` 4 phase, `CREDITS.md`, `LICENSE`, `docs/RETRO.md` | `python3 scripts/package_release.py` | `dist/dao-den-long-v1.0.0.zip`, `docs/RETRO.md`, `CHANGELOG.md` | Đạt |
