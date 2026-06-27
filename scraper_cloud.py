"""
SNKRDUNK Card Price Scraper v2
────────────────────────────────────────────────────────
✅ อ่านรายการการ์ดจาก cards.json (แก้ที่เดียวใช้ทุกที่)
✅ หมุน User-Agent ทุกรอบ
✅ เข้าหน้าแรก snkrdunk.com ก่อนเริ่ม
✅ จำลองการขยับเมาส์แบบ human
✅ เก็บประวัติราคา 7 จุด
✅ Cache รูปการ์ด (ไม่ดึงซ้ำถ้ามีอยู่แล้ว)
✅ สุ่มลำดับการ์ดทุกรอบ
✅ สุ่มหน่วงเวลา 5-10 วิ (บางครั้ง 15-25 วิ)
✅ รัน 2 workers parallel (เร็วขึ้น ~50%)
────────────────────────────────────────────────────────
"""

from playwright.sync_api import sync_playwright
import time, random, re, json, os, sys
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

# ══════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════
CARDS_FILE  = os.path.join(os.path.dirname(__file__), "cards.json")
DATA_FOLDER = os.environ.get("DATA_FOLDER", os.path.dirname(__file__) or ".")
MAX_HISTORY        = 7      # (เดิม) ไม่ใช้แล้ว
MAX_HISTORY_POINTS = 160    # เก็บจุดที่ราคาเปลี่ยนไม่เกินกี่จุด
HISTORY_MAX_DAYS   = 20     # ตัดจุดที่เก่ากว่ากี่วัน (คงไว้อย่างน้อยพอเทียบ 72 ชม.)
MAX_WORKERS = 2   # จำนวน browser parallel (แนะนำ 2)
MAX_RETRIES = 3   # ลองดึงซ้ำกี่รอบถ้า fail
MIN_PRICE   = 500       # ราคาต่ำสุดที่ยอมรับ (¥) — กันราคาเพี้ยน
MAX_PRICE   = 5_000_000 # ราคาสูงสุดที่ยอมรับ (¥)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

STEALTH_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver',  { get: () => undefined });
    Object.defineProperty(navigator, 'plugins',    { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages',  { get: () => ['ja-JP', 'ja', 'en-US'] });
    window.chrome = { runtime: {} };
    const origQuery = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = (p) =>
        p.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : origQuery(p);
"""

# ══════════════════════════════════════════════════════
# โหลด cards.json
# ══════════════════════════════════════════════════════
def load_cards():
    if not os.path.exists(CARDS_FILE):
        print(f"[WARNING] ไม่พบ {CARDS_FILE} — กรุณาสร้างไฟล์ก่อน")
        sys.exit(1)
    with open(CARDS_FILE, encoding="utf-8") as f:
        cards = json.load(f)
    print(f"[cards.json] โหลด {len(cards)} การ์ด")
    return cards

# ══════════════════════════════════════════════════════
# จำลองการเคลื่อนเมาส์แบบ human
# ══════════════════════════════════════════════════════
def human_mouse(page, steps=3):
    for _ in range(steps):
        page.mouse.move(
            random.randint(80, 1150),
            random.randint(80, 650),
        )
        time.sleep(random.uniform(0.08, 0.25))

# ══════════════════════════════════════════════════════
# ดึงราคาการ์ด 1 ใบ
# ══════════════════════════════════════════════════════
def scrape_one(page, card, now_utc, visited_home):
    # ใช้ cid ถาวรเป็นกุญแจไฟล์ (fallback id เดิมถ้ายังไม่ migrate)
    card_id   = card.get("cid") or card["id"]
    filepath  = os.path.join(DATA_FOLDER, f"data_{card_id}.json")

    # อ่านข้อมูลเดิม (สำหรับ history + cache รูป)
    old = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, encoding="utf-8") as f:
                old = json.load(f)
        except Exception:
            pass

    # ─── ลองดึงราคาสูงสุด 3 รอบ (retry) ───
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # ─── เข้าหน้าแรกครั้งเดียว (human-like entry point) ───
            if not visited_home[0]:
                page.goto("https://snkrdunk.com/", timeout=25000, wait_until="domcontentloaded")
                human_mouse(page, steps=random.randint(3, 6))
                page.mouse.wheel(0, random.randint(200, 500))
                time.sleep(random.uniform(2.0, 4.0))
                visited_home[0] = True

            # ─── จำลองการขยับเมาส์ก่อนไปหน้าใหม่ ───
            human_mouse(page, steps=random.randint(2, 5))
            time.sleep(random.uniform(0.3, 0.8))

            # ─── ไปหน้า search ───
            page.goto(card["url"], timeout=30000, wait_until="domcontentloaded")

            # ─── ตรวจ "ขายหมด" หรือ "ไม่มีสินค้า" ───
            body_text = page.inner_text("body")[:3000]
            sold_out = bool(re.search(r"(該当する商品はありません|商品が見つかりません|No items|0\s*件|sold\s*out)", body_text, re.I))

            if sold_out:
                # เขียนสถานะ sold_out (ไม่ถือเป็น error — การ์ดมีอยู่แต่ขายหมด)
                payload = {
                    "datetime": now_utc, "name": card["name"],
                    "code": card.get("code", ""), "rarity": card.get("rarity", ""),
                    "price": "", "price_int": 0, "prev_price": old.get("price", ""),
                    "image_url": old.get("image_url", ""), "history": old.get("history", []),
                    "product_url": card["url"], "status": "sold_out",
                }
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                print(f"   🚫 [{card_id}] {card['name']}: ขายหมด (sold out)")
                return True

            page.wait_for_selector("text=/¥/", timeout=25000)
            human_mouse(page, steps=random.randint(2, 4))
            page.mouse.wheel(0, random.randint(300, 750))
            time.sleep(random.uniform(1.5, 3.0))

            # ─── ดึงราคา: สแกนทุกราคา ¥ ในหน้า แล้วเลือกถูกสุดที่อยู่ในช่วงสมเหตุสมผล ───
            #     (หน้าเรียง price_low อยู่แล้ว → ราคาต่ำสุด = ใบที่ถูกที่สุดที่วางขาย)
            body_text = page.inner_text("body")
            all_found = re.findall(r"¥\s*[\d,]+", body_text)
            candidates = []
            for s in all_found:
                try:
                    v = int(re.sub(r"[¥,\s]", "", s))
                    if MIN_PRICE <= v <= MAX_PRICE:
                        candidates.append(v)
                except Exception:
                    pass

            if not candidates:
                # เผื่อราคาอยู่ใน element ที่ inner_text รวมไม่ครบ → ลองจาก anchor แรก
                try:
                    txt = page.locator("a").filter(has_text="¥").first.inner_text()
                    mm = re.search(r"¥\s*[\d,]+", txt)
                    if mm:
                        v = int(re.sub(r"[¥,\s]", "", mm.group(0)))
                        if MIN_PRICE <= v <= MAX_PRICE:
                            candidates.append(v)
                except Exception:
                    pass

            if not candidates:
                raise ValueError("ไม่พบราคา ¥ ที่ถูกต้องในหน้านี้ (อาจโหลดไม่ครบ/โดนบล็อก)")

            price_int = min(candidates)
            price_str = "¥" + format(price_int, ",")

            # ─── รูป: ดึงของใบถูกสุด (anchor แรก = ถูกสุดเพราะ sort price_low) ทุกครั้ง → ล็อกกับ cid ───
            img_url = old.get("image_url", "")
            try:
                new_img = page.locator("a").filter(has_text="¥").first.locator("img").first.get_attribute("src") or ""
                if new_img:
                    img_url = new_img   # เจอใบถูกสุดใหม่ → ทับรูปเก่า
            except Exception:
                pass

            # ─── อัปเดต history แบบ timestamp [{t: epoch, p: ราคา}] — เก็บเฉพาะตอนราคาเปลี่ยน ───
            now_epoch = int(datetime.now(timezone.utc).timestamp())
            raw_hist = old.get("history", [])
            history = []
            # normalize: รองรับฟอร์แมตเดิม (list ของ int) → ใส่ timestamp ประมาณ (ห่าง 1 ชม.)
            if raw_hist and isinstance(raw_hist[0], dict):
                history = [h for h in raw_hist if isinstance(h, dict) and "p" in h and "t" in h]
            else:
                n = len(raw_hist)
                for i, v in enumerate(raw_hist):
                    try:
                        history.append({"t": now_epoch - (n - 1 - i) * 3600, "p": int(v)})
                    except Exception:
                        pass
            # เพิ่มจุดใหม่เฉพาะเมื่อราคาต่างจากจุดล่าสุด
            if not history or history[-1]["p"] != price_int:
                history.append({"t": now_epoch, "p": price_int})
            else:
                # ราคาเท่าเดิม: ไม่เพิ่มจุด (คง timestamp ที่ราคาเริ่มเปลี่ยนไว้ → ย้อนดู 72 ชม.ได้)
                pass
            # ตัดจุดที่เก่ากว่า HISTORY_MAX_DAYS แต่คงจุดก่อนหน้านั้นไว้ 1 จุด (สำหรับเทียบย้อนหลัง)
            cutoff = now_epoch - HISTORY_MAX_DAYS * 86400
            if len(history) > 2:
                keep = [h for h in history if h["t"] >= cutoff]
                older = [h for h in history if h["t"] < cutoff]
                if older:
                    keep = [older[-1]] + keep   # คงจุดล่าสุดที่เก่ากว่า cutoff ไว้ 1 จุด
                history = keep
            history = history[-MAX_HISTORY_POINTS:]

            prev_price = old.get("price", price_str)

            payload = {
                "datetime":   now_utc,
                "cid":        card.get("cid", ""),
                "name":       card["name"],
                "code":       card.get("code", ""),
                "rarity":     card.get("rarity", ""),
                "price":      price_str,
                "price_int":  price_int,
                "prev_price": prev_price,
                "image_url":  img_url,
                "history":    history,
                "product_url": page.url,
                "status":     "ok",
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

            tag = f" (retry {attempt})" if attempt > 1 else ""
            print(f"   ✅ [{card_id}] {card['name']}: {price_str}  (history {len(history)} จุด){tag}")
            return True

        except Exception as e:
            last_err = e
            if attempt < MAX_RETRIES:
                backoff = random.uniform(6, 12) * attempt
                print(f"   ↻ [{card_id}] {card['name']}: ลองใหม่ {attempt}/{MAX_RETRIES} ใน {backoff:.0f}s ({e})")
                time.sleep(backoff)

    # ─── ครบ retry แล้วยัง fail ───
    print(f"   ❌ [{card_id}] {card['name']}: {last_err}")
    if old:
        print(f"        ↩  คงข้อมูลเดิมไว้")
    else:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump({
                "datetime": now_utc, "name": card["name"],
                "price": "", "error": str(last_err), "history": [], "status": "error"
            }, f, ensure_ascii=False, indent=2)
    return False

# ══════════════════════════════════════════════════════
# Worker: 1 browser รัน N การ์ด
# ══════════════════════════════════════════════════════
def worker(cards_group, ua, now_utc, worker_id):
    print(f"\n[Worker {worker_id}] เริ่ม — {len(cards_group)} การ์ด | UA: {ua[:40]}...")
    results   = []
    visited_home = [False]

    vw = random.choice([1280, 1366, 1440, 1920])
    vh = random.choice([720,  768,  800,  1080])

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
            ]
        )
        context = browser.new_context(
            user_agent=ua,
            viewport={"width": vw, "height": vh},
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
            color_scheme="light",
            extra_http_headers={
                "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            }
        )
        context.add_init_script(STEALTH_SCRIPT)
        page = context.new_page()

        for i, card in enumerate(cards_group):
            ok = scrape_one(page, card, now_utc, visited_home)
            results.append(ok)

            # หน่วงระหว่างการ์ด (ไม่หน่วงหลังใบสุดท้าย)
            if i < len(cards_group) - 1:
                delay = random.uniform(5, 10)
                if random.random() < 0.20:
                    delay = random.uniform(15, 25)
                    print(f"   ⏳ [W{worker_id}] human-like pause {delay:.1f}s...")
                else:
                    print(f"   ⏳ [W{worker_id}] {delay:.1f}s...")
                time.sleep(delay)

        browser.close()

    success = sum(results)
    print(f"[Worker {worker_id}] เสร็จ — {success}/{len(results)} สำเร็จ")
    return results

# ══════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════
def scrape_all():
    cards   = load_cards()
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    os.makedirs(DATA_FOLDER, exist_ok=True)

    # สุ่มลำดับ
    shuffled = cards[:]
    random.shuffle(shuffled)
    print(f"[สุ่มลำดับ] {[c['id'] for c in shuffled]}")

    # แบ่งเป็น N กลุ่ม
    n = min(MAX_WORKERS, len(shuffled))
    groups = [shuffled[i::n] for i in range(n)]
    uas    = random.sample(USER_AGENTS, min(n, len(USER_AGENTS)))

    print(f"\n🚀 เริ่ม {n} workers parallel — {len(cards)} การ์ด รวม")
    print(f"{'='*55}")

    all_results = []
    with ThreadPoolExecutor(max_workers=n) as executor:
        futures = []
        for i, (group, ua) in enumerate(zip(groups, uas)):
            # หน่วง worker ที่ 2 ขึ้นไปนิดหน่อย ไม่ให้ hit พร้อมกัน
            if i > 0:
                time.sleep(random.uniform(4, 10))
            futures.append(executor.submit(worker, group, ua, now_utc, i + 1))
        for f in futures:
            all_results.extend(f.result())

    success = sum(all_results)
    fail    = len(all_results) - success
    print(f"\n{'='*55}")
    print(f"🏁 เสร็จ: {success} สำเร็จ, {fail} ล้มเหลว  [{now_utc}]")
    print(f"{'='*55}")
    return fail

if __name__ == "__main__":
    sys.exit(scrape_all())
