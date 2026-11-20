# Phase 3 Notes — Ticket-03 Change Request "Đèn Cạn Dầu" (Contract v1.2)

## 1. Tóm tắt thay đổi & ADR
- Chi tiết kiến trúc & lý do đổi hướng: [`docs/adr/001-lantern-fuel-and-dawn-survival.md`](../adr/001-lantern-fuel-and-dawn-survival.md).
- Danh sách breaking changes: [`CHANGELOG.md`](../../CHANGELOG.md).

## 2. Bảng truy vết Yêu cầu → Bằng chứng (Phase 3)
| Yêu cầu Ticket-03 | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| Nhiên liệu đèn (100 max, hao 1/s, tắt `lantern_out`, thắp lại tốn 5, `relight: true`) | `test_lantern_fuel_decay_out_and_relight_cost_5` | `docs/proof/phase-3/unittest_output.txt` | Đạt |
| Châm dầu đèn đang sáng (`refuel`, bỏ qua đèn đầy 100) | `test_refuel_lit_lantern_and_full_lantern_ignored` | `docs/proof/phase-3/unittest_output.txt` | Đạt |
| Bóng Mực hút dầu (`drain`, `fuel_drain` mỗi 60 tick, Pulse trúng `+15`) | `test_shade_drains_weak_lantern_and_pulse_gives_15_bonus` | `docs/proof/phase-3/unittest_output.txt` | Đạt |
| Luật thắng mới `dawn_survived` (`>= ceil(0.6*total)`) & không thắng sớm | `test_dawn_survived_win_vs_dawn_loss`, `test_lighting_all_lanterns_...` | `docs/proof/phase-3/unittest_output.txt` | Đạt |
| Sức chứa tăng dần `10 + 2 * successful_lights` (max 20) | `test_lighting_all_lanterns_does_not_end_night_early_and_scales_capacity` | `docs/proof/phase-3/unittest_output.txt` | Đạt |
| Chế độ mù màu (viền `#00B3FF`, cảnh báo `#FFFFFF` + `⚠`, đèn tắt xẹp 20%, đèn yếu nhấp nháy 1 Hz) | `web/index.html`, `web/style.css`, `web/game.js` (`opt-colorblind`) | Cài đặt lưu `localStorage` | Đạt |
| Regression Phase 1–2 (pause, fall, pulse, hit/recoil, determinism, perf `<= 30s`) | `scripts/verify.py` | `docs/proof/phase-3/verify_summary.json` | Đạt |

## 3. Nhật ký dùng AI & Token (Phase 3 — 30 phút)
- **Ước tính token Phase 3:** ~25k–30k tokens.
- **Cách tiết kiệm token:** Dùng số nguyên `fuel_60` ngay từ thiết kế đầu nên pass test ngay lần chạy đầu, không tốn vòng debug sai số float.
- **Cập nhật Harness:** Cập nhật `AGENTS.md` và `scripts/verify.py` lên Contract v1.2 (bổ sung invariant `fuel_60`, `drain`, `dawn_survived`).
