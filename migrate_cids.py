# -*- coding: utf-8 -*-
"""
ซ่อม id ครั้งเดียว — ให้การ์ดทุกใบมี cid ถาวร (ไม่ซ้ำ) แล้วเปลี่ยนชื่อไฟล์ข้อมูล
จาก data_{id เดิม}.json  →  data_{cid}.json  เพื่อล็อก ข้อมูล↔การ์ด ไม่ให้สลับอีก

วิธีใช้ (รันครั้งเดียวในโฟลเดอร์ repo):
    python migrate_cids.py

ปลอดภัย: ทำสำเนา cards.json.bak ไว้ก่อน และจะข้ามการ์ดที่มี cid อยู่แล้ว
"""
import json, os, secrets, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
CARDS = os.path.join(HERE, "cards.json")


def gen_cid(existing):
    while True:
        c = secrets.token_hex(4)  # 8 ตัวอักษร เช่น "a1b2c3d4"
        if c not in existing:
            return c


def main():
    if not os.path.exists(CARDS):
        print("ไม่พบ cards.json")
        return
    with open(CARDS, encoding="utf-8") as f:
        cards = json.load(f)

    shutil.copy(CARDS, CARDS + ".bak")
    print(f"สำรอง cards.json → cards.json.bak")

    used = {c["cid"] for c in cards if c.get("cid")}
    renamed, assigned = 0, 0

    for card in cards:
        if card.get("cid"):
            continue
        cid = gen_cid(used)
        used.add(cid)
        old_id = card.get("id")
        # เปลี่ยนชื่อไฟล์ข้อมูลเดิม (ถ้ามี) ให้ผูกกับ cid
        if old_id is not None:
            old_path = os.path.join(HERE, f"data_{old_id}.json")
            new_path = os.path.join(HERE, f"data_{cid}.json")
            if os.path.exists(old_path) and not os.path.exists(new_path):
                shutil.copy(old_path, new_path)
                renamed += 1
        card["cid"] = cid
        assigned += 1
        print(f"  {card.get('name','?'):<28} id={old_id} → cid={cid}")

    # คงลำดับ id เดิมไว้ (ไม่ reindex) — id เป็นแค่ลำดับแสดง, cid คือกุญแจจริง
    with open(CARDS, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)

    print(f"\nเสร็จ: ใส่ cid {assigned} ใบ, ย้ายไฟล์ข้อมูล {renamed} ไฟล์")
    print("ต่อไป: git add -A && git commit -m 'migrate to permanent cid' && git push origin master --force")


if __name__ == "__main__":
    main()
