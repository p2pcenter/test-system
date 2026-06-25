@echo off
:: ═══════════════════════════════════════════════════════════════
:: SNKRDUNK Card Price Scraper + Auto Git Push
:: Task Scheduler เรียกไฟล์นี้ทุก 1 ชั่วโมง
:: ═══════════════════════════════════════════════════════════════

:: ── แก้ 3 บรรทัดนี้ให้ตรงกับเครื่องคุณ ──────────────────────
set SCRIPT=F:\2.Cards\card-check-file\scraper_cloud.py
set DATA_FOLDER=F:\2.Cards\card-check-file
set PYTHON=python
:: ──────────────────────────────────────────────────────────────

echo.
echo ╔══════════════════════════════════════════╗
echo ║   SNKRDUNK Price Scraper + Git Push     ║
echo ╚══════════════════════════════════════════╝
echo  เวลา: %date% %time%
echo.

:: ════════════════════════════════
:: 1. รัน Scraper ดึงราคา
:: ════════════════════════════════
echo [1/3] กำลังดึงราคาจาก SNKRDUNK...
%PYTHON% "%SCRIPT%"

if errorlevel 1 (
    echo.
    echo [WARNING] Scraper มีบางการ์ดที่ดึงไม่สำเร็จ
    echo          จะยังคง push ข้อมูลที่ได้ต่อไป
)

echo.
echo [1/3] เสร็จแล้ว ✓

:: ════════════════════════════════
:: 2. เข้า folder และ add ไฟล์ JSON
:: ════════════════════════════════
echo.
echo [2/3] กำลัง commit ไฟล์ JSON...

cd /d "%DATA_FOLDER%"

:: ตรวจว่าเป็น git repo ไหม
git status >nul 2>&1
if errorlevel 1 (
    echo [ERROR] โฟลเดอร์นี้ยังไม่ได้ init git
    echo         กรุณาดู "วิธีตั้งค่า Git" ในไฟล์ HOW_TO_SETUP_GIT.txt
    pause
    exit /b 1
)

git add data_*.json
git diff --staged --quiet
if errorlevel 1 (
    git commit -m "update prices %date% %time%"
    echo [2/3] Commit สำเร็จ ✓
) else (
    echo [2/3] ราคาไม่มีการเปลี่ยนแปลง ข้าม commit
)

:: ════════════════════════════════
:: 3. Push ขึ้น GitHub
:: ════════════════════════════════
echo.
echo [3/3] กำลัง push ขึ้น GitHub...

git pull origin master --rebase >nul 2>&1
git push origin master
if errorlevel 1 (
    echo [ERROR] Push ไม่สำเร็จ — ตรวจสอบ internet หรือ credentials
) else (
    echo [3/3] Push สำเร็จ ✓
)

echo.
echo ══════════════════════════════════════════
echo  ✅ เสร็จสมบูรณ์ — %time%
echo  Dashboard จะอัปเดตภายใน 1-2 นาที
echo ══════════════════════════════════════════
echo.
