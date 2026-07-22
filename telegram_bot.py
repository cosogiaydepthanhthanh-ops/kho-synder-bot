"""
Kho SYNDER Telegram Bot - Groq (Llama 3.3 70B + Whisper)
Ho tro ca tin nhan text va voice message
"""

import logging
import requests
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

TELEGRAM_TOKEN    = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY      = os.environ["GROQ_API_KEY"]
ABIT_ACCESS_TOKEN = os.environ["ABIT_ACCESS_TOKEN"]

ABIT_BASE_URL  = "https://new.abitstore.vn"
PARTNER_NAME   = "synder1"
STORE_ID       = 27952
CACHE_MINUTES  = 5
GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"
GROQ_STT_URL   = "https://api.groq.com/openai/v1/audio/transcriptions"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

_kho_cache = ""
_cache_time = None


def _post_abit(endpoint, body):
    body.setdefault("access_token", ABIT_ACCESS_TOKEN)
    body.setdefault("partner_name", PARTNER_NAME)
    r = requests.post(f"{ABIT_BASE_URL}{endpoint}", json=body, timeout=15)
    r.raise_for_status()
    return r.json()


def lay_du_lieu_kho():
    global _kho_cache, _cache_time
    if _cache_time and (datetime.now() - _cache_time).seconds < CACHE_MINUTES * 60 and _kho_cache:
        return _kho_cache

    logging.info("Dang tai du lieu kho tu Abit...")
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

    nhom = {}
    for p in all_items:
        code = p.get("productcode", "")
        sl = max(0, int(float(p.get("slton") or 0)))
        parts = code.rsplit("-", 1)
        if len(parts) == 2 and parts[1].isdigit():
            ma_cha, size = parts[0], parts[1]
        else:
            ma_cha, size = code, ""
        if ma_cha not in nhom:
            nhom[ma_cha] = []
        nhom[ma_cha].append({"size": size, "sl": sl})

    lines = [f"DU LIEU TON KHO SYNDER (cap nhat: {datetime.now().strftime('%H:%M %d/%m/%Y')})\n"]
    for ma_cha in sorted(nhom.keys()):
        sizes = nhom[ma_cha]
        con = [(s["size"], s["sl"]) for s in sizes if s["sl"] > 0]
        het = [s["size"] for s in sizes if s["sl"] == 0]
        tong = sum(s["sl"] for s in sizes)
        if tong == 0:
            lines.append(f"{ma_cha}: HET HANG")
        else:
            chi_tiet = ", ".join(f"size{sz}={sl}" for sz, sl in sorted(con, key=lambda x: x[0]))
            dong = f"{ma_cha}: tong {tong} doi | {chi_tiet}"
            if het:
                dong += f" | het: {','.join(sorted(het))}"
            lines.append(dong)

    _kho_cache = "\n".join(lines)
    _cache_time = datetime.now()
    logging.info(f"Da tai {len(nhom)} mau san pham")
    return _kho_cache


def chuyen_giong_thanh_chu(file_bytes, file_name="audio.ogg"):
    """Dung Groq Whisper de chuyen voice message thanh text."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    files = {"file": (file_name, file_bytes, "audio/ogg")}
    data = {"model": "whisper-large-v3", "language": "vi", "response_format": "text"}
    r = requests.post(GROQ_STT_URL, headers=headers, files=files, data=data, timeout=30)
    r.raise_for_status()
    return r.text.strip()


def hoi_groq(cau_hoi, du_lieu_kho):
    prompt = f"""Ban la tro ly kho hang cua cua hang giay SYNDER. Duoi day la toan bo du lieu ton kho hien tai.

Cach doc ma san pham:
- SD1/SD2/SD3 = sandal dong 1/2/3, B1/B2 = boot, DK = dep, E1 = giay E1
- Mau: DEN=den, TRANG=trang, FULL=mot mau full, HONG=hong, DO=do, NAU=nau, XAM=xam, BE=be/kem, CAM=cam, XANH=xanh
- Vi du: SD2-DENFULL = sandal 2 mau den full, SD2-BEDO = sandal 2 mau be do
- SD2-T = phien ban that no cua SD2

{du_lieu_kho}

---
Cau hoi cua nhan vien: {cau_hoi}

Quy tac tra loi:
1. Neu cau hoi RO RANG tra loi ngay, ngan gon, dung emoji.
2. Format tra loi THEO CHIEU DOC, moi size tren mot dong rieng. Vi du:
   SD2 đen full còn hàng! 👟
   Size 36: 19 đôi
   Size 37: 7 đôi
   Size 38: 6 đôi
   Hết size 42 ❌
3. Neu cau hoi CON MO HO hoi nguoc lai de lam ro. Vi du: "Ban hoi mau den full hay den trang vay?"
4. Neu khong lien quan den kho hang tra loi: "Toi chi ho tro tra cuu ton kho giay nhe!"
5. Khong bia dat so lieu chi dung du lieu kho ben tren.
"""
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}]
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    r = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


async def start(update, context):
    await update.message.reply_text(
        "Kho SYNDER Bot 🎙️\n\n"
        "Hoi bang TIN NHAN hoac GIONG NOI:\n"
        "- sd2 den full con khong?\n"
        "- b1 trang den size 38 con bao nhieu?\n"
        "- sd2 con nhung mau nao?\n\n"
        "Cu hoi tu nhien, toi tu hieu!"
    )


async def check_stock(update, context):
    cau_hoi = update.message.text.strip()
    if not cau_hoi or len(cau_hoi) > 200:
        return
    msg = await update.message.reply_text("Dang kiem tra kho...")
    try:
        du_lieu_kho = lay_du_lieu_kho()
        tra_loi = hoi_groq(cau_hoi, du_lieu_kho)
        await msg.edit_text(tra_loi)
    except Exception as e:
        logging.error(f"Loi: {e}")
        await msg.edit_text("Loi ket noi, thu lai sau it phut.")


async def check_stock_voice(update, context):
    msg = await update.message.reply_text("Dang nghe...")
    try:
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        file_bytes = bytes(await file.download_as_bytearray())

        await msg.edit_text("Da nghe, dang kiem tra kho...")

        cau_hoi = chuyen_giong_thanh_chu(file_bytes)
        logging.info(f"Voice -> text: {cau_hoi}")

        du_lieu_kho = lay_du_lieu_kho()
        tra_loi = hoi_groq(cau_hoi, du_lieu_kho)
        await msg.edit_text(f"🎙️ \"{cau_hoi}\"\n\n{tra_loi}")
    except Exception as e:
        logging.error(f"Loi voice: {e}")
        await msg.edit_text("Loi xu ly giong noi, thu lai sau.")


def main():
    print("Dang tai du lieu kho lan dau...")
    lay_du_lieu_kho()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_stock))
    app.add_handler(MessageHandler(filters.VOICE, check_stock_voice))
    print("Kho SYNDER Bot dang chay! Ho tro ca text va voice.")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
