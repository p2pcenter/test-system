' ═══════════════════════════════════════════════════════════════
' รัน run_scraper.bat แบบเบื้องหลัง — ไม่มีหน้าต่าง command ขึ้นมา
' Task Scheduler เรียกไฟล์นี้ (wscript run_hidden.vbs)
' ═══════════════════════════════════════════════════════════════
Set fso = CreateObject("Scripting.FileSystemObject")
batPath = fso.GetParentFolderName(WScript.ScriptFullName) & "\run_scraper.bat"
' 0 = ซ่อนหน้าต่าง, False = ไม่รอให้จบ
CreateObject("Wscript.Shell").Run """" & batPath & """", 0, False
