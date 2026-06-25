@echo off
:: ═══════════════════════════════════════════════════════════════
:: ตั้งค่า Windows Task Scheduler (รันครั้งเดียวในฐานะ Admin)
:: Scraper จะรันทุก 1 ชั่วโมงอัตโนมัติ พร้อม push ขึ้น GitHub
:: ═══════════════════════════════════════════════════════════════

:: ── แก้ path นี้ให้ตรงกับที่วาง run_scraper.bat ──────────────
set BAT_FILE=F:\2.Cards\card-check-file\run_scraper.bat
set TASK_NAME=SNKRDUNK_PriceScraper
:: ──────────────────────────────────────────────────────────────

echo.
echo [กำลังสร้าง Scheduled Task...]
echo Task Name : %TASK_NAME%
echo Run every : 1 ชั่วโมง
echo Script    : %BAT_FILE%
echo.

:: ลบ task เก่าถ้ามี
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

:: สร้าง task ใหม่ — เรียก run_scraper.bat ทุก 1 ชั่วโมง
schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "cmd /c \"%BAT_FILE%\"" ^
  /sc hourly ^
  /mo 1 ^
  /st 00:00 ^
  /du 9999:59 ^
  /rl HIGHEST ^
  /f

if errorlevel 1 (
    echo.
    echo [ERROR] สร้าง Task ไม่สำเร็จ!
    echo.
    echo วิธีแก้: Right-click ไฟล์นี้ แล้วเลือก "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo.
echo ══════════════════════════════════════════════
echo  ✅ Task สร้างสำเร็จ!
echo.
echo  Scraper จะรันทุก 1 ชั่วโมงอัตโนมัติ
echo  ดูสถานะ: Task Scheduler → SNKRDUNK_PriceScraper
echo.
echo  กำลังรันทันทีเพื่อทดสอบ...
echo ══════════════════════════════════════════════

:: รันทันทีครั้งแรก
schtasks /run /tn "%TASK_NAME%"

echo.
echo [เสร็จแล้ว] ดู window ที่เปิดขึ้นมาเพื่อดูผล
echo.
pause
