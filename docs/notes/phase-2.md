# Phase 2 Notes — Ticket-02 "Ba Hòn Đảo" & Test Contract v1.1

## 1. Thay đổi so với Phase 1 (Chuẩn hóa & Cập nhật test)
- Chuyển từ thông số tự chọn ở Phase 1 sang **số liệu chuẩn bắt buộc của Ticket-02** (`contract_version: "1.1"`): `player_speed: 6.0`, `carry_capacity: 10`, `lantern_cost: 10`, `pickup_radius: 1.0`, `interact_radius: 2.0`, `pulse_cost: 3`, `pulse_radius: 5.0`, `safe_radius: 6.0`, `fall_enabled: true`, thời lượng 3 Đêm `300 / 330 / 360 s`.
- **Cập nhật test Phase 1 kèm lý do:** Các test regression trong `tests/test_engine.py` đã được cập nhật con số kỳ vọng (tốc độ `6.0`, `lantern_cost: 10`, điểm `+10` mỗi đom đóm nạp, `+100` mỗi đèn, `+5` mỗi Bóng Mực trúng Pulse, `+50` mỗi Ngọn Lửa còn lại) theo đúng chuẩn Ticket-02, không tắt test cũ nào.

## 2. Spec & Acceptance Criteria cho Phần 3 (Tính năng mới)
| Mục Phần 3 | Acceptance Criteria (Kiểm chứng được) | Cách kiểm chứng | Kết quả |
|---|---|---|---|
| 1. **Gió Lạc (Drifters)** | Đêm 2 & 3 tối đa 2 con, sinh tại tick 1200/2400; `idle -> chase` khi mang `>=5` đom đóm & cách `<=15m`; chạm (`<=1.2m`) cướp `min(3, carried)` phát `drifter_steal` rồi `flee` 240 tick; Pulse trúng khi `flee` thả đom đóm rơi phát `drifter_drop`. | `test_night2_jump_pad_and_drifter_steal_and_pulse_drop` | Đạt |
| 2. **Bùa Gió (Wind Charm)** | Nhặt phát `charm_picked`, hiệu lực 600 tick: tốc độ `7.2 m/s`, Lướt hồi chiêu `0s` (nhưng vẫn phải bấm cạnh lên & bỏ qua khi đang lướt); hồi lại sau 2700 tick. | `test_dash_and_wind_charm_zero_cooldown` | Đạt |
| 3. **Chuỗi 3 Đêm** | Menu chính → Giới thiệu Đêm (tên đảo + lời Ông Đăng) → Chơi → Kết quả → Đêm kế tiếp → Màn hình Bình Minh tổng điểm sau Đêm 3; thua được chơi lại Đêm đó. | `web/index.html`, `web/game.js` (chạy trực tiếp qua `src.server`) | Đạt |
| 4. **Tạm dừng (Esc/P)** | Logic dừng hoàn toàn (`sim_tick`, thời gian, hồi chiêu, spawn, TTL đứng yên; `tick` vẫn tăng, `state: "paused"`); phát `paused` / `resumed`; menu có Tiếp tục / Chơi lại / Cài đặt / Về Menu. | `test_pause_freezes_sim_tick_and_timers` + UI `screen-pause` | Đạt |
| 5. **Cài đặt** | Điều chỉnh âm lượng & độ nhạy chuột, lưu bền vững qua `localStorage` giữa các lần mở game. | `web/game.js` (`dao_den_long_settings`) | Đạt |
| 6. **Âm thanh** | Nhạc nền đêm + hiệu ứng Web Audio cho nhặt, thắp đèn, tỏa sáng, bị đánh, nhảy, lướt, thắng, thua, Bóng Mực xuất hiện, đếm ngược 10s cuối. | `SoundFX` trong `web/game.js` (procedural Web Audio) | Đạt |
| 7. **HUD đầy đủ** | Ngọn Lửa (trên trái), đồng hồ `mm:ss` đỏ nhấp nháy `<=30s` (trên giữa), đèn `k/n` + điểm (trên phải), thanh 10 ô đom đóm (dưới giữa), hồi chiêu Lướt & Tỏa Sáng (dưới phải), nhắc `"E — Nạp ánh sáng (x/10)"`, mũi tên chỉ đèn chưa sáng gần nhất ngoài màn hình. | `web/index.html`, `web/style.css`, `web/game.js` | Đạt |
| 8. **Bảng màu chuẩn & Ánh sáng** | Dùng đúng mã hex chuẩn Ticket-02 (`#0E1430`, `#1B2350`, `#2F5050`, `#FFB347`, `#120A1A`, `#7A3CFF`, `#E8E2D0`, `#C8102E`, `#F2C14E`, `#8FA3B8`, `#FF5A5F`, `#F5F1E6`); ánh sáng môi trường `0.15 + 0.55 * (lit/total)`. | `PALETTE` & `updateAtmosphere()` trong `web/game.js` | Đạt |
| 9. **Bản đồ 3 Đêm & Rơi khỏi đảo** | Đêm 1 (r=40m, 5 đèn), Đêm 2 (2 đảo r=28m + cầu tre + 2 bục nhảy + 6 đèn), Đêm 3 (3 tầng + 2 dốc + bục nhảy lên tầng 2 + tháp chuông + gió mạnh + 7 đèn); rơi `Y < -10` bỏ qua bất tử, mất hết đom đóm, hồi sinh sau 60 tick. | `test_fall_off_island_ignores_invuln_and_respawns`, `test_night2_...`, `test_night3_...` | Đạt |
| 10. **Hiệu năng Headless** | Chạy trọn Đêm 3 (21,600 tick) trong `<= 30s`. | `scripts/verify.py` -> `docs/proof/phase-2/verify_summary.json` | Đạt |

## 3. Nhật ký dùng AI & Quản lý Token (Phase 2)
- **Tách module sạch:** Tạo `src/maps.py` riêng cho hình học 3 Đêm (tầng, dốc, bục nhảy, tháp chuông, điểm sinh) để `src/engine.py` gọn và bám sát thứ tự 12 bước của Ticket-02.
- **Cách tiết kiệm token:** Viết song song các file theo nhóm (backend contract -> frontend 3D & test -> harness & docs), dùng 1 lệnh `python scripts/verify.py` xác minh toàn bộ.
- **Ước tính token Phase 2:** ~35k–45k tokens (gồm đọc 12 ảnh Ticket-02 + nâng cấp toàn bộ 3 Đêm, HUD, Web Audio, Contract v1.1 và 12 kịch bản kiểm thử).
- **Cập nhật Harness:** Đã cập nhật `AGENTS.md`, `.agents/skills/verify-phase/SKILL.md` và `scripts/verify.py` cho Contract v1.1 (thêm kiểm tra 12 bước tick, tất định 3 Đêm và benchmark 21,600 tick).
