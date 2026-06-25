"""
SNKRDUNK Card Price Scraper — Cloud / GitHub Actions Version
รันครั้งเดียวจบ (ไม่มี while loop), headless=True, บันทึก JSON ใน repo
"""

from playwright.sync_api import sync_playwright
import time, random, re, json, os, sys
from datetime import datetime, timezone

# ══════════════════════════════════════════════════════
# รายการการ์ดที่ต้องการติดตาม  (ชื่อ + URL SNKRDUNK)
# ══════════════════════════════════════════════════════
TARGET_CARDS = [
    {
        "name": "Zoro Juro:R-SPC [OP05-067]",
        "url": "https://snkrdunk.com/search?keywords=%E3%82%BE%E3%83%AD%E5%8D%81%E9%83%8E+R-SPC&sort=price_low&itemConditions=psa_10&isSaleOnly=true&page=1"
    },
    {
        "name": "Tashigi C-SPC [ST06-006]",
        "url": "https://snkrdunk.com/search?keywords=%E3%81%9F%E3%81%97%E3%81%8E+C-SPC&sort=price_low&itemConditions=psa_10&isSaleOnly=true&page=1"
    },
    {
        "name": "Sabo:Wanted SEC-SPC [OP13-120]",
        "url": "https://snkrdunk.com/search?keywords=SEC-SPC+%5BOP13-120%5D&sort=price_low&itemConditions=psa_10&isSaleOnly=true&page=1"
    },
    {
        "name": "Gol D. Roger:Wanted SEC-SPC [OP09-118]",
        "url": "https://snkrdunk.com/search?keywords=SEC-SPC+%5BOP09-118%5D&sort=price_low&itemConditions=psa_10&isSaleOnly=true&page=1"
    },
    {
        "name": "Buggy:Wanted R-SPC [OP09-051]",
        "url": "https://snkrdunk.com/search?keywords=R-SPC+%5BOP09-051%5D&sort=price_low&itemConditions=psa_10&isSaleOnly=true&page=1"
    },
    {
        "name": "Marshall D Teach:SR-SPC [OP09-093]",
        "url": "https://snkrdunk.com/search?keywords=SR-SPC+%5BOP09-093%5D&sort=price_low&itemConditions=psa_10&isSaleOnly=true&page=1"
    },
    {
        "name": "Sengoku:R-SPC [OP07-046]",
        "url": "https://snkrdunk.com/search?keywords=Sengoku+R-SPC++%5BOP07-046%5D&sort=price_low&itemConditions=psa_10&isSaleOnly=true&page=1"
    },
    {
        "name": "Queen:C-SPC [ST04-005]",
        "url": "https://snkrdunk.com/search?keywords=C-SPC+%5BST04-005&sort=price_low&itemConditions=psa_10&isSaleOnly=true&page=1"
    },
    {
        "name": "Rob Lucci:SR-SPC [OP05-093]",
        "url": "https://snkrdunk.com/search?keywords=SR-SPC+%5BOP05-093&sort=price_low&itemConditions=psa_10&isSaleOnly=true&page=1"
    },
    {
        "name": "Kaido:SR-SPC [ST04-003]",
        "url": "https://snkrdunk.com/search?keywords=SR-SPC+%5BST04-003%5D&sort=price_low&itemConditions=psa_10&isSaleOnly=true&page=1"
    },
    {
        "name": "Donquixote Rocinante:SEC-SPC [OP04-119]",
        "url": "https://snkrdunk.com/search?keywords=SEC-SPC+%5BOP04-119%5D&sort=price_low&itemConditions=psa_10&isSaleOnly=true&page=1"
    },
    {
        "name": "Perona:SR-SPC [OP06-093]",
        "url": "https://snkrdunk.com/search?keywords=SR-SPC++%5BOP06-093%5D&sort=price_low&itemConditions=psa_10&isSaleOnly=true&page=1"
    },
    {
        "name": "Shirahoshi:SR-SPC [EB01-057]",
        "url": "https://snkrdunk.com/search?keywords=SR-SPC+%5BEB01-057%5D&sort=price_low&itemConditions=psa_10&isSaleOnly=true&page=1"
    }
]

# ══════════════════════════════════════════════════════
# โฟลเดอร์บันทึก JSON (ปรับได้ — ค่าเริ่มต้น: โฟลเดอร์เดียวกัน)
# ══════════════════════════════════════════════════════
DATA_FOLDER = os.environ.get("DATA_FOLDER", ".")
os.makedirs(DATA_FOLDER, exist_ok=True)

NOW_UTC = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def scrape_all():
    success, fail = 0, 0

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
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
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
        # ซ่อน automation fingerprint
        context.add_init_script("""
            // ซ่อน navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            // เพิ่ม plugins จำลอง
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
            // เพิ่ม languages
            Object.defineProperty(navigator, 'languages', { get: () => ['ja-JP', 'ja', 'en-US'] });
            // ซ่อน chrome headless
            window.chrome = { runtime: {} };
            // Permissions API
            const orig = navigator.permissions.query;
            navigator.permissions.query = (p) =>
                p.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : orig(p);
        """)
        page = context.new_page()

        for index, card in enumerate(TARGET_CARDS):
            print(f"\n[{index+1}/{len(TARGET_CARDS)}] 🔍 {card['name']}")
            filepath = os.path.join(DATA_FOLDER, f"data_{index}.json")

            try:
                page.goto(card["url"], timeout=30000, wait_until="domcontentloaded")

                # รอราคา ¥ ปรากฏ (timeout 25 วิ)
                page.wait_for_selector("text=/¥/", timeout=25000)

                # เลื่อนหน้าเล็กน้อยเพื่อ trigger lazy-load
                page.mouse.wheel(0, random.randint(400, 700))
                time.sleep(random.uniform(2.0, 3.5))

                # ดึงสินค้าแรก
                first = page.locator("a").filter(has_text="¥").first
                text  = first.inner_text()
                img   = first.locator("img").first.get_attribute("src") or ""

                price_match = re.search(r"¥\s*[\d,]+", text)
                if not price_match:
                    raise ValueError("ไม่พบราคาในข้อความ")

                price_str = price_match.group(0).strip()

                # อ่าน prevPrice จากไฟล์เดิม (ถ้ามี)
                prev_price = price_str
                if os.path.exists(filepath):
                    try:
                        with open(filepath, encoding="utf-8") as f:
                            prev_price = json.load(f).get("price", price_str)
                    except Exception:
                        pass

                payload = {
                    "datetime":    NOW_UTC,
                    "name":        card["name"],
                    "price":       price_str,
                    "prev_price":  prev_price,
                    "image_url":   img,
                    "product_url": page.url,
                }

                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)

                print(f"   ✅ {price_str}  → {filepath}")
                success += 1

            except Exception as e:
                print(f"   ❌ ล้มเหลว: {e}")
                fail += 1
                # เขียน error payload ทับไฟล์เดิม (ไม่ให้ข้อมูลหาย)
                if os.path.exists(filepath):
                    print(f"   ↩  คงข้อมูลเดิมไว้")
                else:
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump({"datetime": NOW_UTC, "name": card["name"],
                                   "price": "", "error": str(e)}, f,
                                  ensure_ascii=False, indent=2)

            # หน่วงระหว่างการ์ดเพื่อไม่โดนบล็อก
            if index < len(TARGET_CARDS) - 1:
                delay = random.uniform(12, 22)
                print(f"   ⏳ รอ {delay:.1f} วิ...")
                time.sleep(delay)

        browser.close()

    print(f"\n{'='*50}")
    print(f"🏁 เสร็จ: {success} สำเร็จ, {fail} ล้มเหลว  [{NOW_UTC}]")
    print(f"{'='*50}")
    return fail   # exit code = จำนวน error

if __name__ == "__main__":
    sys.exit(scrape_all())
