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
CACHE_MINUTES  = 2
GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"
GROQ_STT_URL   = "https://api.groq.com/openai/v1/audio/transcriptions"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

_kho_cache = ""
_cache_time = None

SYSTEM_PROMPT = """Ban la tro ly kho hang cua hang giay SYNDER. Nhân viên nói giọng miền Nam, hay nói sai hoặc phát âm không chuẩn. Hãy tự suy luận ý nghĩa gần nhất để tra kho đúng.

=== BẢNG PHIÊN ÂM GIỌNG MIỀN NAM ===

DÒNG SẢN PHẨM:
- SD1 (sandal 1): ét đê một, át đê một, át dê một, ép đê một, ớt đê một, ét dê một, ép dê một, ếch đê một, ếch dê một, ét đi một, ét đê mộc, ét dê mộc, ích đê một, éc đê một, ác đê một, ét đê mụt, ếch đi một
- SD2 (sandal 2): ét đê hai, át đê hai, át dê hai, ép đê hai, ớt đê hai, ét dê hai, ếch đê hai, ếch dê hai, ét đi hai, ét đê hay, ét dê hay, ích đê hai, ích dê hai, ép đi hai, éc đê hai, ác đê hai, ếch đi hai, ích đi hai
- SD3 (sandal 3): ét đê ba, át đê ba, át dê ba, ép đê ba, ớt đê ba, ét dê ba, ếch đê ba, ếch dê ba, ét đi ba, ép đi ba, ích đê ba, ích dê ba, ét dơ ba, éc đê ba, ác đê ba
- SD2-T (sandal 2 thật): ét đê hai thật, ét đê hai tê, ét đê hai tí, ếch đê hai tê, ét đi hai tê, ét đê hay tê, săn đan hai thậc, ét đê hai tơ, ích đê hai tê, ép đê hai tê, săn đang hai thật
- B1 (boot 1): bê một, bi một, boot một, bút một, bê mộc, bi mộc, bút mộc, bê mụt, búp một, búp mộc, bít một, mi một, me một, pút một, bơ một
- B2 (boot 2): bê hai, bi hai, boot hai, bút hai, bê hay, bi hay, bút hay, búp hai, bít hai, mi hai, me hai, pút hai, bơ hai
- DK (dép): đê ka, dê ka, đê ca, dê ca, đê cờ, dep ka, đi ca, đi ka, đê ga, dê ga, đéc ca, đét ca, đáp ca, lê ca, ri ca, đê kê
- E1 (giày E1): ê một, i một, e một, ê mộc, e mộc, i mộc, y một, ây một, ê mụt, i mụt, e mụt, ép một

MÀU SẮC / KIỂU:
- DENFULL (đen full): đen full, đen phô, đen phun, đen tun, đen tui, đeng phun, đen phôn, đem phun, đen phu, len phun, đen bôn, đan phun
- DENTRANG (đen trắng): đen trắng, đen tráng, len chắng, en chắng, đen chắng, đeng chắng, đen chắn, đem trắng, đen trắn, đan trắng, cắn đen, ben chắng
- BEDO (be đỏ): be đỏ, bê đỏ, be dỏ, be rỏ, be gỏ, be đo, bê đo, me đỏ, mê đỏ, ve đỏ, bê rỏ, be gõ, me dỏ, ve dỏ
- BEFULL (be full): be full, be phô, be phun, be pun, be pull, be phum, bê phun, bê phô, be phuôn, be phôn, me phun, ve phun, bê phu, be phu, mê phun, ve phô
- BEHONG (be hồng): be hồng, bê hồng, me hồng, me hùng, be hùn, be hùm, mê hồng, be hờn, bê hờn, bê hùn, ve hồng, be gồng, be phòng, be hồn, mê hờn, ve hùn
- BENAU (be nâu): be nâu, bê nâu, be gâu, be lâu, be lau, bê lâu, bê ngâu, be ngâu, me nâu, ve nâu, be nầu, bê nầu, be lầu, mê nâu, ve lâu
- BEREU (be rêu): be reu, bê reu, be rêu, bê rêu, be rui, be riu, be gêu, bê gêu, be dêu, bê dêu, me rêu, ve rêu, be riêu, bê riêu, be rưu, bê rưu
- BECAM (be cam): be cam, bê cam, be can, bê can, me cam, ve cam, be căm, bê căm
- TRANGDEN (trắng đen): trắng đen, tráng đen, trắng đêm, chắng đen, chắn đen, chắng đeng, trắng đeng, cháng đen, tắng đen, trắng đem, trắn đen, cắn đen
- TRANGFULL (trắng full): trắng full, trắng phun, tráng phun, chắng phun, tắng phun, trắng phô, chắng phô, trắng phuôn, chắng phuôn
- TRANGQXANHDEN (trắng quai xanh đen): trắng quai xanh đen, tráng quai xanh đen, trắng dây xanh đen, chắng quai xanh đen, chắn quay xanh đen, trắng quay xanh đen, chắng oai xanh đeng
- XANHDENFULL (xanh đen full): xanh đen full, xanh đen phun, xanh đen phô, xanh đen phuôn, xanh đeng phun, xanh đem phun, xan đen phun, xăng đen phun
- XANHDENQTRANG (xanh đen quai trắng): xanh đen quai trắng, xanh đen dây trắng, xanh đeng quai trắng, xan đen quay chắng, xanh đen quai chắng, xanh đen oai chắng
- XANHNAVY (xanh navy): xanh navy, xanh nê vi, xanh nê, xanh nây, xan na vi, xăn na vi, xanh na vi, san nê vi, xanh la vi, xanh ne vi
- XANHGALAXY (xanh galaxy): xanh galaxy, xanh ga lắc xi, xanh ga, xan ga la xi, xanh ga la si, san ga lắc xi, xanh ra lắc xi, xanh ga lát
- BEXANHDAIDUONG (be xanh đại dương): be xanh đại dương, be xanh dương, bê xanh đại dương, be sanh đại dươn, be xanh đài dương, me xanh đại dương
- BEXANHTHIENTHANH (be xanh thiên thanh): be xanh thiên thanh, be xanh thiên, be xanh thanh, bê xanh thiên thanh, be sanh thiên thanh, be xanh thiêng thanh
- XAMFULL (xám full): xám full, xám phun, xam phô, xăm phun, xám phuôn, sám phun, sám phô, xám phôn, xám bôn
- XAMDEN (xám đen): xám đen, xăm đen, xam đen, xám đeng, sám đen, xám đem, sám đem
- HONGFULL (hồng full): hồng full, hồng phun, hồng phô, hồn phun, hùn phun, hờn phun, gồng phun, phòng phun
- HONGBE (hồng be): hồng be, hồng bê, hờn be, hùn be, hồn be, gồng be, hồng me, hồng ve, hồng bơ
- DENBE (đen be): đen be, đên be, đen bê, đeng be, đem be, đen me, đen ve, len be, be đen, bê đen, be đêng, mê đen, ve đen, b đen, be đen mê. QUY TẮC BẮT BUỘC: hễ câu hỏi có CẢ 2 từ "be" (hoặc bê/mê/ve) VÀ "đen" (bất kể thứ tự trước sau) thì CHẮC CHẮN LÀ DENBE — TUYỆT ĐỐI không được chọn DENFULL trong trường hợp này dù câu có chữ "đen".
- BELOGOHONG (be logo hồng): be logo hồng, bê logo hồng, be lô gô hồng, bê lô gô hồng, me logo hồng, be lu gu hồng, ve logo hồng, bê rô gô hồng
- BELOGONAU (be logo nâu): be logo nâu, bê logo nâu, be lô gô nâu, bê lô gô nâu, me logo nâu, ve logo nâu, be rô gô nâu
- DENWAX (đen wax): đen wax, đen oắc, đen uách, đeng oắc, đen quát, đen oát, đen quắc, đeng quắc, đen goắc, đen goát, đen quất
- DOQTRANG (đỏ quai trắng): đỏ quai trắng, đỏ dây trắng, đỏ quai tráng, đỏ quay trắng, đỏ oai trắng, đỏ quai chắng, rỏ quai trắng, đỏ vai trắng
- XANHMINT (xanh mint): xanh mint, xanh min, xanh mín, xanh mịn, xanh minh, xan min, xăng min, xanh mít, xanh men
- XAM (xám đơn): xám, sám, xan, xăm, xán, sán, xáp, sáp
- HONG (hồng đơn): hồng, hờn, hùn, hồn, gồng, phòng, hờng, hùng
- DO (đỏ đơn): đỏ, rỏ, dỏ, đõ, đo, đó, gỏ, ro, do, rõ
- E1-TRANGQUAIDEN (E1 trắng quai đen): e một trắng quai đen, ê một trắng quai đen, i một trắng quai đen, e mộc trắng quai đen, ê mộc chắng quay đen, e một chắng oai đeng, e một trắn quai đen, e mụt chắng quay đem, ê một chắng dây đeng, y một tắng quai đen, ép một trắng quay đeng, e một chắng oai đen, ê mộc tráng quai đeng, i mộc cắn quay đen, e một chắng quai đang, e một tắng oai đen, ê một chắng quai ben, e một trắng dây đen, e một chắng quay đen, e mộc chắng dây đeng

DÒNG ĐẶC BIỆT: mã dạng TIENTOMAU-HOATIET (ví dụ BE-CHU3D, DEN-MEO, HONG-VUTRU, TRANG-CHUCONG) — LUÔN GHÉP tiền tố màu VỚI họa tiết, không dùng riêng họa tiết một mình.
Tiền tố màu: BE (be/bê/me/ve), DEN (đen/đeng/đem/đan/đên), HONG (hồng/hờn/hùn/gồng/phòng), TRANG (trắng/chắng/tắng/trắn/chử)
Họa tiết:
- CHU3D (chữ 3D): chữ ba đê, chử ba đê, chữ ba đi, chử ba dê, chứ ba đê, trữ ba đê, chữ pa đê, chữ ba lê
- CHUCONG (chữ cong): chữ cong, chử cong, chữ con, chử con, chứ cong, chữ goong, chữ giong, chữ căng, trữ cong
- MEO (mèo): mèo, meo, mèu, mều, mẹo, mẻo, ngoèo, nghèo, méo
- VUTRU (vũ trụ): vũ trụ, dũ trụ, dũ chụ, vũ chụ, dủ chụ, vủ chụ, vủ trụ, giũ chụ, dụ chụ, vụ chụ
Ví dụ: "be chữ 3D" → MA:BE-CHU3D; "đen mèo" → MA:DEN-MEO; "hồng vũ trụ" → MA:HONG-VUTRU

Mã độc lập khác (KHÔNG cần ghép tiền tố):
- KEMREU (kem rêu): kem rêu, kem reu, kem gêu, kem dêu, keng rêu, kem riu, ken rêu, keng dêu
- MEOXAMDEN (mèo xám đen): mèo xám đen, mèo xám đeng, mèo xám đem, meo xám đen, mèu xám đen, mèo sám đen
- NAUTRASUA (nâu trà sữa): nâu trà sữa, nâu chà sữa, nâu chà sủa, nâu trà sủa, nâu chà sứa, nâu tà sữa, nâu cha sữa

NHIỆM VỤ: Xác định mã sản phẩm (dạng CODE-MAU, ví dụ SD2-DENFULL, B1-TRANGDEN) mà người dùng đang hỏi, dựa vào bảng phiên âm trên. Người dùng hay nói sai, phát âm không chuẩn giọng miền Nam — hãy tự suy luận ý nghĩa gần nhất.

QUAN TRỌNG: nếu câu hỏi đã viết RÕ RÀNG mã dòng sản phẩm bằng chữ cái/số chuẩn (SD1, SD2, SD3, SD2-T, B1, B2, DK, E1 — không phải phiên âm), LUÔN LUÔN dùng đúng mã đó làm CODE, TUYỆT ĐỐI không suy luận/đổi sang dòng khác dù trong câu có từ ngữ nghe giống dòng khác.

BẮT BUỘC chỉ xuất ra ĐÚNG 1 trong 4 dạng dưới đây, không được xuất bất cứ từ nào khác (kể cả chữ "size"):
- MA:CODE-MAU — dùng khi câu hỏi CÓ NHẮC ĐẾN MÀU/KIỂU cụ thể (dù phát âm sai), ví dụ "sd2 be đỏ", "b1 trắng đen" → MA:SD2-BEDO, MA:B1-TRANGDEN. Đây là trường hợp phổ biến nhất, ưu tiên dùng dạng này bất cứ khi nào nhận ra được màu.
- MAGOC:CODE — CHỈ dùng khi câu hỏi KHÔNG nhắc màu nào cả, hỏi liệt kê chung, ví dụ "sd2 có những màu nào", "sd2 còn màu gì". TUYỆT ĐỐI không dùng dạng này nếu câu hỏi đã có nhắc tên màu.
- MOHO:<câu hỏi làm rõ bằng tiếng Việt> — chỉ khi không thể đoán được cả dòng sản phẩm lẫn màu.
- NGOAILE (không liên quan kho giày)"""

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
        if len(parts) == 2 and (parts[1].isdigit() or parts[1].upper() in ("S", "M", "L", "XL", "XXL")):
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


WHISPER_PROMPT = (
    "Kiểm tra tồn kho giày SYNDER: SD1, SD2, SD2-T, SD3, B1, B2, DK, E1, "
    "be đỏ, be full, be cam, be nâu, be rêu, be hồng, be đen, đen full, đen trắng, "
    "trắng đen, xám full, xám đen, hồng full, xanh navy, xanh galaxy, size 36 37 38 39 40 41 42 43 44."
)


def chuyen_giong_thanh_chu(file_bytes, file_name="audio.ogg"):
    """Dung Groq Whisper de chuyen voice message thanh text.
    Tham so 'prompt' goi y truoc tu vung nganh hang de Whisper nhan dang
    dung chinh ta cac ma san pham/mau sac thay vi doan theo am thanh chung chung."""
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    files = {"file": (file_name, file_bytes, "audio/ogg")}
    data = {
        "model": "whisper-large-v3",
        "language": "vi",
        "response_format": "text",
        "prompt": WHISPER_PROMPT,
    }
    r = requests.post(GROQ_STT_URL, headers=headers, files=files, data=data, timeout=30)
    r.raise_for_status()
    return r.text.strip()


def _goi_groq(messages, retry=3):
    import time
    payload = {"model": "llama-3.1-8b-instant", "messages": messages, "temperature": 0}
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    for attempt in range(retry):
        r = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
        if r.status_code in (429, 413) and attempt < retry - 1:
            time.sleep(3)
            continue
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


def chuan_hoa_cau_hoi(cau_hoi):
    """Thay 'sai'/'xai' (phat am mien Nam cua 'size') thanh 'size' truoc khi gui AI,
    tranh de AI tu suy luan gay nham lan/lan man."""
    import re
    return re.sub(r"\b(sai|xai)\b", "size", cau_hoi, flags=re.IGNORECASE)


def xac_dinh_ma(cau_hoi):
    """Chi gui bang phien am (khong gui du lieu kho) de xac dinh ma san pham."""
    cau_hoi = chuan_hoa_cau_hoi(cau_hoi)
    return _goi_groq([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": cau_hoi}
    ])


def loc_dong_theo_ma(du_lieu_kho, ma, chinh_xac):
    ket_qua = []
    for dong in du_lieu_kho.split("\n"):
        ma_dong = dong.split(":", 1)[0].strip()
        if chinh_xac and ma_dong == ma:
            ket_qua.append(dong)
        elif not chinh_xac and (ma_dong == ma or ma_dong.startswith(ma + "-")):
            ket_qua.append(dong)
    return ket_qua


def phan_tich_ket_qua(text):
    """Tim ket qua CUOI CUNG khop dinh dang, phong khi model lap lai de bai hoac
    giai thich dai dong truoc do. Voi MA/MAGOC chi lay dung phan ma (chu/so/gach
    ngang), bo qua giai thich thua ngay sau de tranh lay nham rac."""
    import re
    if "NGOAILE" in text:
        return "NGOAILE", None
    ung_vien = []
    for m in re.finditer(r"(MAGOC|MA)\s*:\s*([A-Za-z0-9\-]+)", text):
        ung_vien.append((m.start(), m.group(1), m.group(2).strip().rstrip("-")))
    for m in re.finditer(r"MOHO\s*:\s*(\S.*?)(?:\n|$)", text):
        ung_vien.append((m.start(), "MOHO", m.group(1).strip()))
    if not ung_vien:
        return None, None
    ung_vien.sort(key=lambda x: x[0])
    _, loai, noidung = ung_vien[-1]
    return loai, noidung


def dinh_dang_dong(dong):
    """Dinh dang 1 dong du lieu kho thanh cau tra loi, HOAN TOAN bang code
    (khong qua AI) de dam bao so lieu chinh xac tuyet doi, khong bi 'ao giac'."""
    ma, phan_con_lai = dong.split(":", 1)
    ma = ma.strip()
    if "HET HANG" in phan_con_lai:
        return f"{ma}: Hết hàng toàn bộ ❌"

    phan = phan_con_lai.split("|")
    chi_tiet = phan[1].strip() if len(phan) > 1 else ""
    het = phan[2].replace("het:", "").strip() if len(phan) > 2 else ""

    dong_ra = [f"{ma} còn hàng! 👟"]
    for cap in chi_tiet.split(","):
        cap = cap.strip()
        if not cap:
            continue
        sz, sl = cap.split("=")
        dong_ra.append(f"Size {sz.replace('size', '').strip()}: {sl.strip()} đôi")
    for sz in het.split(","):
        sz = sz.strip()
        if sz:
            dong_ra.append(f"Hết size {sz} ❌")
    return "\n".join(dong_ra)


def sua_mau_khong_on_dinh(cau_hoi_goc, loai, noidung, du_lieu_kho):
    """AI (temperature=0 van khong dam bao 100% on dinh tren ha tang Groq) doi
    khi nham giua DENFULL va DENBE cho cung 1 cau hoi. Ngoai ra Abit dat ten
    KHONG NHAT QUAN giua cac dong: B2 dung 'DENBE' nhung SD2/SD2-T lai dung
    'BEDEN' (nguoc thu tu) cho CUNG 1 mau. Vi vay khong hardcode 1 ten co dinh,
    ma tu kiem tra ca 2 bien the trong du lieu kho THAT, dung dung cai ton tai."""
    import re
    if loai != "MA" or not noidung or "-" not in noidung:
        return loai, noidung
    cau = cau_hoi_goc.lower()
    co_be = bool(re.search(r"\b(be|bê|mê|ve)\b", cau))
    co_den = bool(re.search(r"\b(đen|den)\b", cau))
    if not (co_be and co_den):
        return loai, noidung

    ma_hop_le = set(dong.split(":", 1)[0].strip() for dong in du_lieu_kho.split("\n"))
    code_prefix, _, _ = noidung.rpartition("-")
    if not code_prefix:
        return loai, noidung
    for bien_the in (f"{code_prefix}-DENBE", f"{code_prefix}-BEDEN"):
        if bien_the in ma_hop_le:
            return loai, bien_the
    return loai, noidung


def hoi_groq(cau_hoi, du_lieu_kho):
    ket_qua = xac_dinh_ma(cau_hoi)
    loai, noidung = phan_tich_ket_qua(ket_qua)
    loai, noidung = sua_mau_khong_on_dinh(cau_hoi, loai, noidung, du_lieu_kho)

    if loai == "NGOAILE":
        return "Tôi chỉ hỗ trợ tra cứu tồn kho giày nhé!"

    if loai == "MOHO":
        return noidung

    if loai == "MAGOC":
        ma = noidung.split()[0].upper()
        dong_khop = loc_dong_theo_ma(du_lieu_kho, ma, chinh_xac=False)
    elif loai == "MA":
        ma = noidung.split()[0].upper()
        dong_khop = loc_dong_theo_ma(du_lieu_kho, ma, chinh_xac=True)
    else:
        return "Xin lỗi, tôi chưa hiểu rõ câu hỏi. Bạn hỏi lại giúp mình nhé?"

    if not dong_khop:
        return f"Không tìm thấy mã {ma} trong kho."

    return "\n\n".join(dinh_dang_dong(d) for d in dong_khop)


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
    except Exception:
        logging.exception("Loi check_stock")
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
    except Exception:
        logging.exception("Loi check_stock_voice")
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
