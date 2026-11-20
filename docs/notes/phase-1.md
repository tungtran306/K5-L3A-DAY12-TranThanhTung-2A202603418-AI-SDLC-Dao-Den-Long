# Phase 1 Notes — PRD-0 & Test Contract v1.0

## 1. Giả định cho các điểm mơ hồ trong PRD-0
| Hạng mục | Giả định & giá trị chọn | Lý do |
|---|---|---|
| Kích thước đảo & rơi khỏi đảo | Đảo tròn bán kính `45m`, `fall_enabled: false` (kẹp vị trí trong đảo) | Đảm bảo gameplay ổn định, không rơi vô ý ở Phase 1 |
| Vị trí 5 Đèn Lồng Lớn | `L1`..`L5` xếp đều trên vòng tròn bán kính `26m`, `L1` tại `(0, 0, 26)` | Dễ định hướng, đối xứng, cách xuất phát `(0,0,0)` hợp lý |
| Tốc độ & sức chứa | `player_speed: 7.0 m/s`, `carry_capacity: 6`, `lantern_cost: 4` | Cần tối thiểu 1 chuyến gom đom đóm cho mỗi đèn, nhịp chơi vừa phải |
| Bóng Mực & an toàn | `shade_speed: 4.2 m/s`, `safe_radius: 7.0 m`, `shade_hit_radius: 1.2 m` | Chậm hơn Mây để có thể né/dụ, vùng đèn sáng là nơi trú ẩn rõ ràng |
| Mất máu & rơi đom đóm | `flames: 3`, `invuln_s: 1.5 s`, `hit_drop_ratio: 0.5` (`floor`) | Bị chạm mất 1 lửa và rơi một nửa số đom đóm đang mang |
| Tỏa sáng (Pulse) | `pulse_cost: 2`, `pulse_radius: 8.0 m`, `pulse_stun_s: 3.0 s`, `pulse_push_m: 6.0 m`, `pulse_cooldown_s: 2.5 s` | Có chi phí đánh đổi với tiến độ thắp đèn nhưng đủ mạnh để thoát vây |
| Thời lượng Đêm 1 | `night1_duration_s: 240` (4 phút) | Đủ thời gian thắp 5 đèn nhưng vẫn tạo áp lực bình minh (`dawn`) |
| Công thức điểm | `per_mote: 10`, `per_lantern: 150`, `per_stun: 30`, thưởng thắng: `floor(time_left_s) * 2 + flames * 100` | Khuyến khích thắp đèn nhanh, giữ máu và dùng pulse hiệu quả |

## 2. Bảng truy vết Yêu cầu → Bằng chứng (Phase 1)
| Yêu cầu (PRD-0 / Contract v1.0) | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| `game.contract.json` đầy đủ schema & tuning | `test_contract_schema_fields` | `docs/proof/phase-1/unittest_output.txt` | Đạt |
| Nhặt đom đóm, nạp đèn, thắp đèn, thắng `all_lit`, scenario không phát event/điểm | `test_move_pickup_deposit_lit_and_win` | `docs/proof/phase-1/unittest_output.txt` | Đạt |
| Tỏa sáng (`pulse`) trừ đom đóm, làm choáng & đẩy lùi Bóng Mực | `test_pulse_stuns_and_pushes_shade` | `docs/proof/phase-1/unittest_output.txt` | Đạt |
| Bóng Mực chạm gây mất máu, rơi đom đóm, thua `no_flames` | `test_shade_hit_drops_motes_and_loses_no_flames` | `docs/proof/phase-1/unittest_output.txt` | Đạt |
| Bóng Mực sợ đèn đã thắp (`safe_radius`) | `test_shade_respects_lit_lantern_safe_radius` | `docs/proof/phase-1/unittest_output.txt` | Đạt |
| Hết giờ Đêm 1 thua `dawn` đúng tick | `test_dawn_timeout_loss` | `docs/proof/phase-1/unittest_output.txt` | Đạt |
| Xoay hướng di chuyển theo `cam_yaw_deg` + chuẩn hóa vector | `test_camera_yaw_and_diagonal_normalization` | `docs/proof/phase-1/unittest_output.txt` | Đạt |
| Tính tất định 100% giữa 2 lần chạy cùng seed | `test_determinism_identical_runs` + `scripts/verify.py` (SHA-256) | `docs/proof/phase-1/verify_summary.json` | Đạt |
| File `inputs`/`scenario` sai định dạng trả exit code `2` + `stderr` | `test_invalid_inputs_exit_code_2` | `docs/proof/phase-1/unittest_output.txt` | Đạt |
| Game 3D chơi được trên trình duyệt (Windows/macOS/Linux) | `python3 -m src.server` + kiểm tra trực tiếp trên trình duyệt | `web/index.html`, `web/game.js`, `src/server.py` | Đạt |

## 3. Nhật ký dùng AI & Quản lý Token (Phase 1)
- **Công cụ:** Antigravity (model medium) hỗ trợ thiết kế, code engine headless Python, frontend 3D Three.js, test suite và CI.
- **Cách tiết kiệm token:**
  - Chọn stack 0-dependency (**Python 3 stdlib + Three.js ESM**) giúp bỏ qua hoàn toàn bước debug cài đặt package/bundler.
  - Gộp đọc toàn bộ tài liệu và tạo file theo batch song song thay vì hỏi đáp từng file nhỏ.
  - Thiết kế `game.contract.json` làm nguồn chân lý duy nhất và chạy `scripts/verify.py` một lệnh duy nhất.
- **Ước tính token Phase 1:** ~25k–35k tokens (input + output gộp, gồm đọc 6 file hướng dẫn + 12 ảnh PRD-0 + viết toàn bộ source & test).
- **Lỗi AI / Điều chỉnh harness:**
  - Ban đầu dự định dùng Node.js/TypeScript, nhưng kiểm tra môi trường phát hiện máy chỉ có sẵn Python 3.13 → chuyển kịp thời sang Python 3 stdlib + Three.js giúp tiết kiệm ~15 phút cài đặt và chạy được ngay trên cả Windows/macOS/Linux.
  - Tạo sẵn `AGENTS.md` (ngắn gọn, tập trung vào invariants của Contract v1.0) và skill `.agents/skills/verify-phase/SKILL.md` để chuẩn bị cho Phase 2–4.

## 4. Đánh giá nhanh Phase 1
- **Đạt:** Toàn bộ yêu cầu lõi PRD-0 và Test Contract v1.0, 9/9 test tự động xanh, determinism SHA-256 khớp tuyệt đối, CI đã cấu hình.
- **Cần cải thiện ở phase sau:** Đồng bộ thêm tính năng mới khi Ticket-02 phát hành và kiểm tra trực tiếp trên trình duyệt để tinh chỉnh cảm giác điều khiển/camera.
