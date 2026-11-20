# Changelog

## [Phase 3 / Contract v1.2] - 2026-11-20 (Ticket-03: "Đèn cạn dầu")

### Breaking Changes (Thay đổi phá vỡ tương thích so với Phase 2 / v1.1)
- **Luật thắng `[THAY THẾ]`:** Bỏ thắng sớm `all_lit`. Thắng khi sống sót tới bình minh (`time_left_s <= 0`) với ít nhất `ceil(0.6 * tổng đèn)` đèn đang sáng (`game_over.reason = "dawn_survived"`). Thời lượng 3 Đêm đổi thành `240 / 270 / 300 s`.
- **Nhiên liệu đèn `[THAY THẾ]`:** Đèn đã sáng vẫn nhận tương tác châm dầu (`refuel`, `+10` fuel/đom đóm, tối đa `100`), tự hao `1.0` fuel/s, tắt khi `<= 0` (`lantern_out`), thắp lại chỉ tốn `5` đom đóm (`lantern_lit.relight = true`).
- **Vùng an toàn & Bóng Mực hút dầu `[THAY THẾ]`:** Đèn có `fuel < 30` mất vùng an toàn; Bóng Mực ở trạng thái `wander` đi tới hút `5` fuel/s (trạng thái mới `drain`, phát `fuel_drain` mỗi 60 tick).
- **Công thức điểm `[THAY THẾ]`:** `+5` mỗi đom đóm nạp/châm dầu, `+100` thắp lần đầu, `+40` thắp lại, `+5` Pulse thường / `+15` Pulse trúng Bóng Mực đang `drain`; thưởng bình minh (khi thắng) `+50 + floor(fuel)` mỗi đèn sáng + `+50` mỗi Ngọn Lửa còn lại; bỏ thưởng thời gian.
- **Test Contract v1.2:** Snapshot đèn thêm `fuel`, `ever_lit`, `relit_count`; `player` thêm `capacity`; `lantern_lit` thêm `relight`; thêm sự kiện `refuel`, `lantern_out`, `fuel_drain`.

### Added
- Sức chứa đom đóm tăng dần theo số lần thắp thành công: `10 + 2 * successful_lights` (tối đa `20`).
- Chế độ mù màu (**"Bảng màu dễ phân biệt"**, lưu `localStorage`): viền Bóng Mực `#00B3FF`, cảnh báo `#FFFFFF` kèm `⚠`, đèn tắt xẹp 20% + vết rách, đèn yếu `< 30` nhấp nháy 1 Hz.
- ADR-001 ([`docs/adr/001-lantern-fuel-and-dawn-survival.md`](docs/adr/001-lantern-fuel-and-dawn-survival.md)).

## [Phase 2 / Contract v1.1] - 2026-11-20 (Ticket-02: "Ba hòn đảo")
- Chuẩn hóa số liệu, mở rộng 3 Đêm (Đảo Bến, Đảo Cau, Đảo Chuông), Lướt, Gió Lạc, Bùa Gió, Tạm dừng, Cài đặt, Âm thanh, HUD đầy đủ, bảng màu chuẩn, sáng tạo 2 bùa buff 3D.

## [Phase 1 / Contract v1.0] - 2026-11-20 (PRD-0)
- Bản chơi đầu tiên Đêm 1 – Đảo Bến + Headless Test Contract v1.0 + Harness AI + CI.
