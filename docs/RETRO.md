# Retrospective — Day 12 AI SDLC: Đảo Đèn Lồng (4 Phases → v1.0.0)

## 1. Tổng hợp Evaluation qua 4 Phase
| Phase | Hợp đồng | Phạm vi chính | Kết quả kiểm chứng | Ghi chú hồi quy |
|---|---|---|---|---|
| **Phase 1 (PRD-0)** | `v1.0` | Đêm 1 Đảo Bến, Headless 60-Hz, 3D Web Three.js, Harness + CI | 9/9 test PASS, determinism SHA-256 khớp | Nền tảng sạch, 0 dependency ngoài |
| **Phase 2 (Ticket-02)** | `v1.1` | Chuẩn hóa số liệu, 3 Đêm, Lướt, Gió Lạc, Bùa Gió, Tạm dừng, Audio, Full HUD + 2 bùa sáng tạo 3D | 12/12 test PASS, Đêm 3 (21,600 tick) trong `0.93s` | Cập nhật số liệu chuẩn cho test Phase 1 có ghi lý do |
| **Phase 3 (Ticket-03)** | `v1.2` | Change Request: Đèn cạn dầu (`fuel_60`), Bóng Mực `drain`, thắng `dawn_survived`, sức chứa động, chế độ mù màu, ADR-001 | 10/10 test PASS, Đêm 3 (18,000 tick) trong `0.16s` | Thay luật thắng `all_lit` bằng `dawn_survived`, ghi rõ trong ADR & CHANGELOG |
| **Phase 4 (Ticket-04)** | `v1.3` | Benchmark 3D `1280×720` (200 Bóng Mực, 100 đom đóm), Soak 10 Đêm, Bảng xếp hạng cục bộ, Trợ năng đầy đủ, Đóng gói `v1.0.0` | 13/13 test PASS, Soak 10 Đêm `0` crash, RAM ổn định, Benchmark đạt chuẩn | Giữ nguyên toàn bộ test Phase 1–3 còn hiệu lực |

## 2. Điều hiệu quả & chưa hiệu quả khi làm việc với AI
- **Hiệu quả nhất:**
  - **Tách hoàn toàn logic headless (Python 3 stdlib) khỏi đồ họa (Three.js Web)** và dùng `game.contract.json` làm nguồn chân lý duy nhất. Nhờ 0 dependency cài đặt, cả Windows (máy phát triển) lẫn macOS/Linux (máy chấm & GitHub Actions CI) đều chạy mượt ngay lập tức.
  - **Viết kế hoạch kiểm chứng & chạy `scripts/verify.py` một lệnh** ở mọi phase giúp phát hiện lỗi ngay tức thì trước khi commit/tag.
  - **Dùng số nguyên `fuel_60` (đơn vị 1/60) ở Phase 3** loại bỏ hoàn toàn sai số dấu phẩy động khi tính hao dầu/hút dầu qua hàng chục nghìn tick.
- **Chưa hiệu quả / Điểm cần lưu ý:**
  - Duy trì song song `src/engine.py` (Python headless) và `web/game.js` (JS 3D) đòi hỏi cẩn thận đồng bộ mỗi khi luật chơi thay đổi (như lúc Ticket-03 đổi luật thắng & nhiên liệu).
  - Trong Phase 3, một thao tác `edit_file` theo chuỗi chung (`for (const m of this.motes) {`) từng khớp nhầm 2 vị trí trong `web/game.js`; rất may đọc lại diff và kiểm tra số lần thay thế đã phát hiện và sửa ngay trước khi commit.

## 3. Những lần AI sai & cách phát hiện / điều chỉnh Harness
1. **Đề xuất Node.js/TypeScript trước khi kiểm tra máy:** Phát hiện ngay ở bước kiểm tra môi trường (`node` chưa cài, chỉ có Python 3.13) → đổi sang Python 3 stdlib + Three.js ESM, tiết kiệm ~15 phút cài đặt.
2. **Dùng toán tử `&&` của bash trên PowerShell 5.1:** Lệnh commit đầu tiên báo lỗi cú pháp → điều chỉnh dùng xuống dòng / kiểm tra `$LASTEXITCODE`.
3. **Thay thế trùng chuỗi ở `web/game.js` (Phase 3):** Phát hiện nhờ đọc output công cụ (`Made 2 replacements`) → đọc lại vùng code bị ảnh hưởng và sửa sạch trước khi đóng Phase 3.
4. **Hiệu quả của Harness:**
   - `scripts/verify.py` (kèm `.github/workflows/ci.yml`) là thành phần hữu ích nhất: ép mọi thay đổi phải qua biên dịch + toàn bộ unit/scenario test + kiểm tra SHA-256 tất định + soak test trước khi gắn tag.
   - `AGENTS.md` ngắn gọn (~25 dòng) cập nhật qua cả 4 phase giúp giữ ngữ cảnh cố định về invariants của từng phiên bản Contract (`v1.0` → `v1.3`) mà không tốn token thừa.

## 4. Quản lý Token & Chi phí AI ước tính
| Phase | Ước tính Token (Input + Output) | Cách tiết kiệm token đã áp dụng |
|---|---:|---|
| Phase 1 (CP0 + PRD-0) | ~30,000 | Đọc 6 file tài liệu song song; chọn stack 0-dependency không tốn vòng debug cài môi trường |
| Phase 2 (Ticket-02 + Sáng tạo) | ~42,000 | Tách `src/maps.py` riêng; viết file song song theo batch; kiểm chứng 1 lệnh |
| Phase 3 (Ticket-03 CR) | ~28,000 | Thiết kế `fuel_60` chuẩn ngay lần đầu → pass 10/10 test ngay lượt chạy đầu |
| Phase 4 (Ticket-04 + Release) | ~35,000 | Tận dụng lại server cục bộ sẵn có cho cả Leaderboard API và Benchmark runner |
| **Tổng cộng** | **~135,000 tokens** | Rất gọn cho toàn bộ dự án game 3D 4 phase + full test/bench/soak/docs |

## 5. Nếu làm lại từ đầu thì sẽ đổi gì?
1. **Một engine duy nhất cho cả 3D & Headless:** Nếu có sẵn Node.js trên máy, viết 1 lõi simulation thuần TypeScript chạy chung trên cả Node CLI (headless/soak) và trình duyệt (Three.js) sẽ đảm bảo đồng bộ 100% không cần bảo trì 2 bản.
2. **Viết thêm bài test smoke tự động cho giao diện web** (kiểm tra cú pháp JS & các ID DOM) ngay trong `scripts/verify.py` để bắt lỗi frontend sớm như backend.
3. **Chuẩn bị sẵn kịch bản quay video demo ngắn từ Phase 3** để tiết kiệm thời gian ở 15 phút cuối của Phase 4.
