"""
Kho SYNDER Telegram Bot
Claude AI đọc toàn bộ dữ liệu kho Abit và trả lời mọi câu hỏi tự nhiên.
"""

import logging
import json
import requests
import anthropic
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ─── CẤU HÌNH ─────────────────────────────────────────────────────────────────

import os

TELEGRAM_TOKEN    = os.environ["TELEGRAM_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
ABIT_ACCESS_TOKEN = os.environ["ABIT_ACCESS_TOKEN"]

ABIT_BASE_URL = "https://new.abitstore.vn"
ACCESS_TOKEN  = ABIT_ACCESS_TOKEN
PARTNER_NAME  = "synder1"
STORE_ID      = 27952

CACHE_MINUTES = 15   # Tự động cập nhật kho mỗi 15 phút

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
ai_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ─── CACHE TỒN KHO ────────────────────────────────────────────────────────────

_kho_cache: str = ""
_cache_time: datetime | None = None


def _post_abit(endpoint: str, body: dict):
    body.setdefault("access_token", ACCESS_TOKEN)
    body.setdefault("partner_name", PARTNER_NAME)
    r = requests.post(f"{ABIT_BASE_URL}{endpoint}", json=body, timeout=15)
    r.raise_for_status()
    return r.json()


def lay_du_lieu_kho() -> str:
    """Tải toàn bộ tồn kho từ Abit, trả về dạng text gọn cho AI đọc."""
    global _kho_cache, _cache_time

    # Dùng cache nếu còn mới
    if _cache_time and (datetime.now() - _cache_time).seconds < CACHE_MINUTES * 60 and _kho_cache:
        return _kho_cache

    logging.info("Đang tải dữ liệu kho từ Abit...")
    all_items = []
    for page in range(50):
        data = _post_abit("/products/listProductsWithStockforPartner", {
            "productstoreid": STORE_ID, "page": page, "limit": 100,
        })
        items = data if isinstance(data, list) else data.get("data", [])
        if not items:
            break
        all_items.extend(items)
        if len(items) < 100:
            break

    # Nhóm theo mã cha (bỏ phần size)
    nhom: dict[str, list] = {}
    for p in all_items:
        code = p.get("productcode", "")
        sl = int(float(p.get("slton") or 0))
        parts = code.rsplit("-", 1)
        if len(parts) == 2 and parts[1].isdigit():
            ma_cha, size = parts[0], parts[1]
        else:
            ma_cha, size = code, ""

        if ma_cha not in nhom:
            nhom[ma_cha] = []
        nhom[ma_cha].append({"size": size, "sl": sl, "code": code})

    # Tạo text tóm tắt
    lines = [f"DỮ LIỆU TỒN KHO SYNDER (cập nhật: {datetime.now().strftime('%H:%M %d/%m/%Y')})\n"]
    for ma_cha in sorted(nhom.keys()):
        sizes = nhom[ma_cha]
        con = [(s["size"], s["sl"]) for s in sizes if s["sl"] > 0]
        het = [s["size"] for s in sizes if s["sl"] == 0]
        tong = sum(s["sl"] for s in sizes)

        if tong == 0:
            lines.append(f"{ma_cha}: HẾT HÀNG")
        else:
            chi_tiet = ", ".join(f"size{sz}={sl}" for sz, sl in sorted(con, key=lambda x: x[0]))
            dong = f"{ma_cha}: tổng {tong} đôi | {chi_tiet}"
            if het:
                dong += f" | hết: {','.join(sorted(het))}"
            lines.append(dong)

    _kho_cache = "\n".join(lines)
    _cache_time = datetime.now()
    logging.info(f"Đã tải {len(nhom)} mẫu sản phẩm")
    return _kho_cache


# ─── AI TRẢ LỜI ───────────────────────────────────────────────────────────────

def hoi_ai(cau_hoi: str, du_lieu_kho: str) -> str:
    """Gửi câu hỏi + dữ liệu kho cho Claude, nhận câu trả lời."""
    prompt = f"""Bạn là trợ lý kho hàng của cửa hàng giày SYNDER. Dưới đây là toàn bộ dữ liệu tồn kho hiện tại.

Cách đọc mã sản phẩm:
- SD1/SD2/SD3 = sandal dòng 1/2/3, B1/B2 = boot, DK = dép, E1 = giày E1
- Màu: DEN=đen, TRANG=trắng, FULL=một màu full, HONG=hồng, DO=đỏ, NAU=nâu, XAM=xám, BE=be/kem, CAM=cam, XANH=xanh
- Ví dụ: SD2-DENFULL = sandal 2 màu đen full, SD2-BEDO = sandal 2 màu be đỏ
- SD2-T = phiên bản thắt nơ của SD2

{du_lieu_kho}

---
Câu hỏi của nhân viên: {cau_hoi}

Quy tắc trả lời:
1. Nếu câu hỏi RÕ RÀNG → trả lời ngay, ngắn gọn, dùng emoji, liệt kê size và số lượng cụ thể.
2. Nếu câu hỏi CÒN MƠ HỒ (không rõ mẫu nào, màu nào, hoặc có nhiều khả năng) → hỏi ngược lại để làm rõ. Ví dụ: "Bạn hỏi mẫu SD2-DENFULL hay SD2-DENTRANG vậy?" hoặc "SD2 có nhiều màu đen, bạn muốn hỏi đen full hay đen trắng?"
3. Nếu không liên quan đến kho hàng → trả lời: "Tôi chỉ hỗ trợ tra cứu tồn kho giày nhé! 😊"
4. Không bịa đặt số liệu — chỉ dùng dữ liệu kho bên trên.
"""

    response = ai_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


# ─── TELEGRAM HANDLERS ────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👟 *Kho SYNDER Bot*\n\n"
        "Hỏi tự nhiên về tồn kho:\n"
        "• _sd2 đen full còn không?_\n"
        "• _b1 trắng đen size 38 còn bao nhiêu?_\n"
        "• _sd2 còn những màu nào?_\n"
        "• _còn size 36 mẫu nào?_\n"
        "• _sd2 be đỏ hết chưa?_\n\n"
        "Cứ hỏi tự nhiên, tôi tự hiểu! 🤖",
        parse_mode="Markdown"
    )


async def check_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cau_hoi = update.message.text.strip()
    if not cau_hoi or len(cau_hoi) > 200:
        return

    msg = await update.message.reply_text("🔍 Đang kiểm tra kho...")

    try:
        du_lieu_kho = lay_du_lieu_kho()
        tra_loi = hoi_ai(cau_hoi, du_lieu_kho)
        await msg.edit_text(tra_loi, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Lỗi: {e}")
        await msg.edit_text("⚠️ Lỗi kết nối, thử lại sau ít phút.")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("⏳ Đang tải dữ liệu kho lần đầu...")
    lay_du_lieu_kho()

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_stock))

    print("✅ Kho SYNDER Bot đang chạy — sẵn sàng trả lời mọi câu hỏi về kho!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
