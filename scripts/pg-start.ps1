# เริ่ม PostgreSQL ถ้ายังไม่ทำงาน
#
# ใช้กับ Scheduled Task ตอน logon และเรียกด้วยมือก็ได้
# เขียนให้ idempotent — เรียกซ้ำแล้วไม่พัง และไม่สตาร์ตซ้อน
#
# หมายเหตุ: ห้ามใช้ pg_ctl แบบที่ให้ shell รอ เพราะถ้า process แม่ถูกปิด
# server จะตายตามไปด้วย ต้องปล่อยให้ทำงานแยกต่างหาก

$ErrorActionPreference = 'Stop'

$pgBin  = Join-Path $env:USERPROFILE 'scoop\apps\postgresql\current\bin'
$pgData = Join-Path $env:USERPROFILE 'scoop\persist\postgresql\data'
$pgLog  = Join-Path $env:USERPROFILE 'scoop\persist\postgresql\pg.log'

if (-not (Test-Path $pgData)) {
    Write-Error "ไม่พบ data directory: $pgData"
    exit 1
}

# ตรวจว่ารับ connection ได้อยู่แล้วหรือไม่
& "$pgBin\pg_isready.exe" -q
if ($LASTEXITCODE -eq 0) {
    Write-Output 'PostgreSQL ทำงานอยู่แล้ว'
    exit 0
}

# มี process ค้างแต่ไม่รับ connection = ตกค้างจากการปิดที่ไม่สมบูรณ์
$stale = Get-Process postgres -ErrorAction SilentlyContinue
if ($stale) {
    Write-Output "พบ process ค้าง $($stale.Count) ตัว กำลังปิด"
    $stale | Stop-Process -Force
    Start-Sleep -Seconds 3
    Remove-Item (Join-Path $pgData 'postmaster.pid') -Force -ErrorAction SilentlyContinue
}

Start-Process -FilePath "$pgBin\pg_ctl.exe" `
    -ArgumentList 'start', '-D', "`"$pgData`"", '-l', "`"$pgLog`"" `
    -WindowStyle Hidden

# รอจนกว่าจะรับ connection ได้ ไม่เกิน 30 วินาที
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    & "$pgBin\pg_isready.exe" -q
    if ($LASTEXITCODE -eq 0) {
        Write-Output "PostgreSQL พร้อมใช้งานใน $($i + 1) วินาที"
        exit 0
    }
}

Write-Error "เริ่ม PostgreSQL ไม่สำเร็จ ดูรายละเอียดที่ $pgLog"
exit 1
