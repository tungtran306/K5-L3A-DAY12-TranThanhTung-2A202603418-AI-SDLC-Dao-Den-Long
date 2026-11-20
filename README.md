# Đảo Đèn Lồng — Day 12 AI SDLC (Phase 2: Ba Hòn Đảo)

> Game 3D góc nhìn thứ ba qua **3 Đêm**: **Đêm 1 – Đảo Bến**, **Đêm 2 – Đảo Cau**, **Đêm 3 – Đảo Chuông**. Cùng **Mây** thu thập đom đóm, sử dụng **Lướt (Dash)**, **Tỏa Sáng (Pulse)**, **Bục Nhảy**, và **Bùa Gió** để thắp sáng tất cả Đèn Lồng Lớn, né **Bóng Mực**, **Gió Lạc** và **Gió mạnh**.

## Cài đặt & Chạy (tối đa 3 lệnh)

Yêu cầu: **Python 3.10+** (0 dependency ngoài; chạy trên macOS, Linux và Windows — trên Windows thay `python3` bằng `python`).

```bash
# 1. Kiểm tra biên dịch
python3 -m py_compile src/maps.py src/engine.py src/headless.py src/server.py

# 2. Chạy toàn bộ bộ kiểm chứng (Regression Phase 1 + Phase 2 + Determinism 3 Đêm + Benchmark 21,600 tick)
python3 scripts/verify.py

# 3. Mở game 3D trên trình duyệt (http://127.0.0.1:8000)
python3 -m src.server
```

## Điều khiển (3D Web)
- **`W / A / S / D`**: Di chuyển (`6.0 m/s`; `7.2 m/s` khi có Bùa Gió)
- **`Space`**: Nhảy (`7.0 m/s`, trọng lực `-20 m/s²`)
- **`Shift`**: Lướt (`14.0 m/s` trong `0.2s`, hồi chiêu `1.5s`, `0s` khi có Bùa Gió)
- **`E`**: Nạp đom đóm vào Đèn Lồng Lớn gần nhất (`interact_radius = 2.0m`, cần `10` đom đóm/đèn)
- **`F`**: Tỏa Sáng (`pulse`) — tốn `3` đom đóm, bán kính `5.0m`, hồi chiêu `3.0s`, làm choáng Bóng Mực `2.0s` & đẩy lùi `4.0m`, ép Gió Lạc thả đồ
- **`Esc` / `P`**: Tạm dừng (dừng hoàn toàn logic)
- **`Q / R`**, **Mũi tên Trái/Phải**, hoặc **Kéo chuột**: Xoay camera 3D

## Cách tính điểm (Chuẩn hóa Ticket-02)
Thông số chính thức tại [`game.contract.json`](game.contract.json) (`contract_version: "1.1"`):
- Nạp 1 đom đóm vào đèn: `+10` điểm
- Thắp sáng 1 Đèn Lồng Lớn: `+100` điểm
- Mỗi Bóng Mực trúng Tỏa Sáng: `+5` điểm
- Thưởng khi thắng Đêm: `+ floor(giây còn lại) * 2 + 50 * Ngọn Lửa còn lại`. Tổng điểm hành trình = tổng các Đêm đã thắng.

## Chế độ Headless (Test Contract v1.1)

```bash
python3 -m src.headless \
  --seed 42 --night <1|2|3> \
  [--scenario scenario.json] \
  [--inputs inputs.json] \
  --ticks 600 --out out.jsonl \
  [--snapshot-every 10]
```

- Mô phỏng cố định **60 tick/giây**, tuân thủ chính xác thứ tự 12 bước của Ticket-02, tất định 100%, chạy trọn Đêm 3 (21,600 tick) trong dưới 2 giây.

## Bằng chứng, Ghi chép & Harness AI
- Ghi chép & Spec: [`docs/notes/phase-1.md`](docs/notes/phase-1.md) · [`docs/notes/phase-2.md`](docs/notes/phase-2.md)
- Bằng chứng kiểm chứng tự động: [`docs/proof/phase-1/`](docs/proof/phase-1/) · [`docs/proof/phase-2/`](docs/proof/phase-2/)
- Harness AI: [`AGENTS.md`](AGENTS.md), [`.agents/skills/verify-phase/SKILL.md`](.agents/skills/verify-phase/SKILL.md), [`scripts/verify.py`](scripts/verify.py), [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
- Bản quyền & Nguồn: [`CREDITS.md`](CREDITS.md) · [`LICENSE`](LICENSE)

---

### Tài liệu đề bài gốc
- [GUIDE.md](GUIDE.md) · [CHECKPOINTS.md](CHECKPOINTS.md) · [SUBMISSION.md](SUBMISSION.md) · [RULES.md](RULES.md) · [RUBRIC.md](RUBRIC.md)
