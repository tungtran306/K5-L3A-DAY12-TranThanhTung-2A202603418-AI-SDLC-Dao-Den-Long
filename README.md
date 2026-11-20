# Đảo Đèn Lồng — Day 12 AI SDLC

> Game 3D góc nhìn thứ ba: **Mây** (đội nón lá treo đèn lồng nhỏ) thu thập đom đóm để thắp lại **5 Đèn Lồng Lớn** trên **Đêm 1 – Đảo Bến**, né và dùng **Tỏa Sáng (Pulse)** để xua **Bóng Mực** trong sương đen.

## Cài đặt & Chạy (tối đa 3 lệnh)

Yêu cầu: **Python 3.10+** (không cần cài thêm thư viện ngoài; chạy trên macOS, Linux và Windows — trên Windows thay `python3` bằng `python`).

```bash
# 1. Kiểm tra biên dịch
python3 -m py_compile src/engine.py src/headless.py src/server.py

# 2. Chạy toàn bộ bộ kiểm chứng & Test Contract v1.0
python3 scripts/verify.py

# 3. Mở game 3D trên trình duyệt (http://127.0.0.1:8000)
python3 -m src.server
```

## Điều khiển (3D Web)
- **`W / A / S / D`**: Di chuyển Mây theo hướng camera
- **`Space`**: Nhảy
- **`F`**: Nạp đom đóm vào Đèn Lồng Lớn gần nhất (trong `interact_radius = 2.5m`)
- **`E`**: Tỏa Sáng (`pulse`) — tốn `2` đom đóm, làm choáng `3.0s` và đẩy lùi `6.0m` Bóng Mực trong `8.0m`
- **`Q / R`**, **Mũi tên Trái/Phải**, hoặc **Kéo chuột**: Xoay camera 3D

## Cách tính điểm
Toàn bộ thông số nằm trong [`game.contract.json`](game.contract.json):
- Nhặt 1 đom đóm: `+10` điểm
- Thắp sáng 1 Đèn Lồng Lớn (cần `4` đom đóm): `+150` điểm
- Làm choáng 1 Bóng Mực bằng Tỏa Sáng: `+30` điểm
- Thưởng khi thắng (thắp đủ 5 đèn): `+2` điểm cho mỗi giây còn lại (`floor(time_left_s)`) và `+100` điểm cho mỗi ngọn lửa (`flames`) còn lại.
- `fall_enabled: false`: Mây được giữ trong ranh giới Đảo Bến (bán kính `45m`), không có cơ chế rơi khỏi đảo.

## Chế độ Headless (Test Contract v1.0)

```bash
python3 -m src.headless \
  --seed 42 --night 1 \
  [--scenario scenario.json] \
  [--inputs inputs.json] \
  --ticks 300 --out out.jsonl \
  [--snapshot-every 10]
```

- Mô phỏng cố định **60 tick/giây**, không cần GPU/cửa sổ, tất định 100% theo `--seed`.
- File `inputs` hoặc `scenario` sai định dạng trả về mã thoát `2` và in thông báo lỗi ra `stderr`.

## Bằng chứng, Ghi chép & Harness AI
- Ghi chép giả định, bảng truy vết, nhật ký AI/token & đánh giá Phase 1: [`docs/notes/phase-1.md`](docs/notes/phase-1.md)
- Bằng chứng kiểm chứng tự động Phase 1: [`docs/proof/phase-1/`](docs/proof/phase-1/)
- Harness AI: [`AGENTS.md`](AGENTS.md), [`.agents/skills/verify-phase/SKILL.md`](.agents/skills/verify-phase/SKILL.md), [`scripts/verify.py`](scripts/verify.py), [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
- Nguồn tài nguyên & giấy phép: [`CREDITS.md`](CREDITS.md), [`LICENSE`](LICENSE)

---

### Tài liệu đề bài gốc
- [GUIDE.md](GUIDE.md) · [CHECKPOINTS.md](CHECKPOINTS.md) · [SUBMISSION.md](SUBMISSION.md) · [RULES.md](RULES.md) · [RUBRIC.md](RUBRIC.md)
