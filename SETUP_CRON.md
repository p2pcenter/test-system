# คู่มือ: ตั้ง External Cron ให้ดึงราคาการ์ดตรงเวลา (ทุก 30 นาที)

## ปัญหาที่แก้
GitHub Actions `schedule:` (cron ในไฟล์ workflow) **ไม่การันตีเวลา** — ช่วงระบบ GitHub
โหลดหนัก มันจะเลื่อน/ข้ามรอบ ผลจริงที่เจอคือรันแค่ ~4 ครั้ง/วัน (ทุก ~6-9 ชม.)
ทั้งที่ตั้งไว้ทุก 30 นาที

**ทางแก้:** ให้บริการ cron ภายนอก (ฟรี, ออนไลน์ 24 ชม.) ยิง GitHub API เรียก
`workflow_dispatch` ตามเวลาที่เราตั้งเป๊ะๆ — วิธีนี้ตรงเวลากว่ามาก เพราะเป็นการ
trigger ตรงผ่าน API ไม่ผ่านคิว schedule ที่โดน throttle

ผลลัพธ์: การ์ดทุกใบสดใหม่ทุก ~30 นาที (จากเดิม ~9.6 ชม.) โดยไม่ต้องเปิดคอม /
ไม่มีเซิร์ฟเวอร์ / ไม่มีค่าใช้จ่าย

---

## ขั้นตอนที่ 1 — สร้าง GitHub Token (Fine-grained PAT)

Token นี้ให้สิทธิ์ cron ภายนอกกดปุ่ม "Run workflow" แทนเราผ่าน API

1. เข้า https://github.com/settings/personal-access-tokens/new
   (หรือ: GitHub → รูปโปรไฟล์มุมขวาบน → **Settings** → เมนูซ้ายล่าง
   **Developer settings** → **Personal access tokens** → **Fine-grained tokens**
   → **Generate new token**)
2. ตั้งค่า:
   - **Token name:** `cron-scrape-trigger` (ตั้งชื่ออะไรก็ได้ให้จำได้)
   - **Expiration:** เลือกอายุยาวๆ เช่น 1 ปี (พอหมดอายุต้องสร้างใหม่)
   - **Repository access:** เลือก **Only select repositories** →
     เลือก `p2pcenter/test-system`
   - **Permissions** → กด **Repository permissions** → หา **Actions** →
     ตั้งเป็น **Read and write**
     (อันอื่นปล่อยเป็น No access ได้หมด — ให้สิทธิ์น้อยที่สุดเพื่อความปลอดภัย)
3. กด **Generate token** ด้านล่าง
4. **คัดลอก token เก็บไว้ทันที** (ขึ้นตัวเต็มครั้งเดียว ปิดหน้าแล้วดูซ้ำไม่ได้)
   เริ่มด้วย `github_pat_...`

> ⚠️ **ห้ามเอา token ใส่ในโค้ด/commit ขึ้น repo เด็ดขาด** — ใครเห็นก็สั่งรัน
> workflow เราได้ ถ้าเผลอหลุด ให้เข้าไป **Revoke** ทิ้งแล้วสร้างใหม่

---

## ขั้นตอนที่ 2 — สมัคร cron-job.org (ฟรี)

1. เข้า https://cron-job.org → **Sign up** (ใช้อีเมลสมัคร ฟรี ไม่ต้องใส่บัตร)
2. ยืนยันอีเมล แล้ว login เข้า dashboard

---

## ขั้นตอนที่ 3 — สร้าง Cronjob

1. ใน dashboard กด **CREATE CRONJOB** (ปุ่มขวาบน)
2. ตั้งค่าตามนี้:

### Common
| ช่อง | ค่าที่ใส่ |
|---|---|
| **Title** | `Scrape Cards (GitHub)` |
| **URL** | `https://api.github.com/repos/p2pcenter/test-system/actions/workflows/scrape.yml/dispatches` |

### Schedule (เลือก "Every 30 minutes" หรือ Custom)
- เลือกแบบ Custom: ให้ทำงานที่นาทีที่ **0** และ **30** ของทุกชั่วโมง
- (ในหน้า cron-job.org: Minutes = เลือก `0` และ `30`, Hours/Days/Months/
  Weekdays = เลือก **Every** ทั้งหมด)

### ⚙️ ต้องกดแท็บ "ADVANCED" เพื่อตั้ง method / headers / body
3. เลื่อนหา **Advanced settings** (หรือแท็บ **ADVANCED**) แล้วตั้ง:

- **Request method:** `POST`

- **Headers** (กด "Add header" ทีละอัน — ใส่ครบ 3 อัน):

  | Key | Value |
  |---|---|
  | `Accept` | `application/vnd.github+json` |
  | `Authorization` | `Bearer github_pat_xxxxxxxx` *(วาง token จากขั้นตอน 1 ต่อท้าย `Bearer ` — เว้นวรรค 1 เคาะ)* |
  | `X-GitHub-Api-Version` | `2022-11-28` |

- **Request body** (ช่อง Body / POST data):
  ```json
  {"ref":"master"}
  ```

4. กด **CREATE** / **SAVE**

---

## ขั้นตอนที่ 4 — ทดสอบว่าใช้ได้

1. ในหน้า cronjob ที่เพิ่งสร้าง กด **TEST RUN** (หรือ **Run now**)
2. ผลที่ถูกต้อง: cron-job.org แสดง response **HTTP 204 No Content** = สำเร็จ
   (GitHub API ตอบ 204 เมื่อรับคำสั่ง dispatch แล้ว — ไม่มี body ถือว่าปกติ)
3. เปิด https://github.com/p2pcenter/test-system/actions →
   ต้องเห็น workflow run ใหม่ชื่อ **Scrape Card Prices** เพิ่งเริ่ม
   (สังเกตว่า trigger เป็น `workflow_dispatch` ไม่ใช่ `schedule`)

### ถ้าไม่ขึ้น run ใหม่ — ไล่เช็ก
- **HTTP 401** = token ผิด/หมดอายุ → สร้าง token ใหม่
- **HTTP 403** = token ไม่มีสิทธิ์ Actions: Read and write → แก้ permission
- **HTTP 404** = URL ผิด หรือ token ไม่มีสิทธิ์เข้า repo นี้ →
  เช็กชื่อ repo และ Repository access ของ token
- **HTTP 422** = body ผิด → ต้องเป็น `{"ref":"master"}` เป๊ะ (ชื่อ branch ให้ตรง)

---

## ขั้นตอนที่ 5 — เฝ้าดูช่วงแรก (สำคัญ)

หลังปรับให้ทำครบ 112 ใบในรอบเดียว (3 workers) ให้ดู run แรกๆ 2-3 รอบ:

1. เปิด Actions → คลิก run ล่าสุด → ดู log ของ step **Run scraper**
2. เช็ก 2 อย่าง:
   - **รันจบภายใน ~13 นาทีไหม** (ต้องไม่ชน deadline 19 นาที / timeout 22 นาที)
     ถ้าเห็นข้อความ `⏰ หมดงบเวลา` แปลว่าทำไม่ทัน — มีการ์ดตกค้าง
   - **มีใบโดน "ไม่พบราคา ¥" เยอะผิดปกติไหม** (เช่น เกิน 10-15 ใบ/รอบ)
     = สัญญาณว่า snkrdunk เริ่มบล็อก IP ของ runner

### ถ้าเจอปัญหา — ปรับกลับได้ง่ายๆ (แก้ที่ `.github/workflows/scrape.yml`)
- ทำไม่ทัน / โดนบล็อกเยอะ → ลด `MAX_WORKERS` กลับเป็น `"2"`
- ยังโดนบล็อก → ยืด interval บน cron-job.org เป็นทุก 45 หรือ 60 นาที
- โดนหนักมาก → กลับไปใช้ `BATCH_SIZE: "70"` (ทำทีละครึ่ง หมุน offset เหมือนเดิม)

---

## สรุปค่าที่ตั้งไว้ตอนนี้ (ในไฟล์ workflow)
| ค่า | เดิม | ใหม่ | เหตุผล |
|---|---|---|---|
| ตัวยิง | GitHub schedule (ไม่ตรงเวลา) | external cron → workflow_dispatch | ตรงเวลาจริง |
| `MAX_WORKERS` | 2 | 3 | ทำครบ 112 ใบใน ~11-13 นาที |
| `BATCH_SIZE` | 70 (2 รอบ/ครบ) | 0 (ครบใน 1 รอบ) | ทุกใบสดพร้อมกันทุกรอบ |
| concurrency | — | guard กันรอบซ้อน | ไม่ยิงซ้อน/commit ไม่ชน |
| ดีเลย์ต่อใบ | 5-10 วิ | **คงเดิม** | คือตัวที่ทำให้ระบบเสถียร/ไม่โดนบล็อก |

> หมายเหตุ: `schedule:` cron ในไฟล์ยังเปิดไว้เป็น **ตัวสำรอง** — ถ้า cron ภายนอก
> ล่ม GitHub ก็ยังดึงให้บ้าง (แต่ไม่ตรงเวลา) ไม่ต้องปิดทิ้ง
