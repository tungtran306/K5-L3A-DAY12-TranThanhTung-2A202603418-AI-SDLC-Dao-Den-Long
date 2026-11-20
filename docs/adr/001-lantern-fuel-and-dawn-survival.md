# ADR-001: Chuyển mô hình trạng thái Đèn sang Nhiên liệu (Fuel) & Luật thắng Sống sót tới Bình minh

- **Ngày:** 2026-11-20 (Phase 3 — Ticket-03 "Đèn cạn dầu")
- **Trạng thái:** Accepted

## Bối cảnh
Ở Phase 1–2, Đèn Lồng Lớn chỉ có trạng thái nhị phân (`lit: false -> true`) và màn chơi kết thúc ngay khi toàn bộ đèn sáng (`all_lit`). Playtest cho thấy người chơi giỏi hoàn thành quá sớm và mất cảm giác căng thẳng cuối Đêm. Ticket-03 yêu cầu thay đổi cốt lõi sang cơ chế **đèn cạn dầu** và **giữ đảo sáng tới bình minh**.

## Quyết định thiết kế
1. **Biểu diễn nhiên liệu bằng số nguyên đơn vị 1/60 (`fuel_60 ∈ [0..6000]`):**
   - Tránh hoàn toàn sai số dấu phẩy động khi trừ `1/60` (tự hao) và `5/60` (Bóng Mực hút) mỗi tick trong hàng chục nghìn tick.
   - Chỉ chia cho `60` và làm tròn 1 chữ số thập phân (`round(fuel_60 / 60, 1)`) khi xuất snapshot/event.
2. **Mô hình trạng thái Đèn & Vùng an toàn:**
   - Thêm thuộc tính `ever_lit` (nhớ đèn đã từng sáng để giảm chi phí thắp lại từ `10` xuống `5`) và `relit_count`.
   - Vùng an toàn (`safe_radius = 6m`) chỉ có hiệu lực khi `lit == True` **và** `fuel_60 >= 1800` (`fuel >= 30`). Khi châm dầu vượt lại ngưỡng `>= 30`, kích hoạt lại đẩy Bóng Mực ra mép trong tối đa 30 tick.
   - Khi đèn chạm `fuel_60 <= 0` (kiểm tra ngay sau bước 2 của tick), chuyển `lit = False`, `deposited = 0`, `ever_lit = True` và phát `lantern_out`.
3. **Trạng thái `drain` của Bóng Mực:**
   - Chỉ Bóng Mực ở trạng thái `wander` mới chọn đèn yếu (`fuel < 30`) gần nhất; khi cách `<= 2m` chuyển `drain`, hút `5` fuel/s (cộng dồn) và phát `fuel_drain` mỗi 60 tick.
   - Rời `drain` khi Mây vào `<= 6m` (`chase`), trúng Pulse (`stunned`, `+15` điểm), hoặc đèn tắt / được châm lên `>= 30` (`wander`).
4. **Luật thắng mới (`dawn_survived`):**
   - Bỏ thắng sớm (`all_lit`). Màn chơi chỉ kết thúc khi `flames <= 0` (`no_flames`, ưu tiên cao nhất) hoặc khi `time_left_s <= 0`: thắng `dawn_survived` nếu số đèn sáng `>= ceil(0.6 * tổng đèn)` (Đêm 1: 3/5, Đêm 2: 4/6, Đêm 3: 5/7), ngược lại thua `dawn`.

## Hệ quả & Cập nhật Test
- Các test cũ ở Phase 1–2 kiểm tra thắng sớm `all_lit` và công thức điểm cũ (`+10/mote`, `+2/sec`) bị vô hiệu bởi luật mới → đã được cập nhật minh bạch kèm lý do trong `tests/test_engine.py`, không bỏ qua âm thầm.
