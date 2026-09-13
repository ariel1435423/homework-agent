# ==========================================================
#  יום במשטרה עם מישל בנט - סידור הסרטונים
#  מריצים ב-PowerShell. ברירת מחדל: D:\archive (1)
#  שימוש:  .\Sort-Film-Videos.ps1
#     או:  .\Sort-Film-Videos.ps1 -Root "D:\archive (1)" -Copy
# ==========================================================
param(
  [string]$Root = "D:\archive (1)",
  [switch]$Copy,          # העתקה במקום העברה
  [switch]$WhatIfOnly     # רק להראות מה יקרה
)

# מפתח: תחילית ה-GUID בשם הקובץ  ->  "תיקייה|שם חדש"
$map = @{
  # ---- סצנה 0 : פתיחה ----
  "53e183ef" = "00-opening|S00_02_Michel_opening"
  "6e902a5e" = "00-opening|S00_03_Michel_what-well-see"
  "07eeca5b" = "00-opening|S00_04_Michel_kinder"
  "cbe38118" = "00-opening|_alt\S00_04_Michel_kinder_OLD-no-kinder-element"

  # ---- רצף 1 : מסוק ----
  "049a1b29" = "01-helicopter|S01_01a_FR_helicoptere_QUESTION_hold-the-pause"
  "e594ee3f" = "01-helicopter|S01_01b_FR_helicoptere_ANSWER"
  "e5e4c6d9" = "01-helicopter|S01_02_Michel_helicopter-intro"
  "cf5c16ab" = "01-helicopter|S01_05_Michel_MEGAPHONE_see-everything"
  "b63bf8a0" = "01-helicopter|S01_07_Michel_MEGAPHONE_let-me-down"
  "cffe8acd" = "01-helicopter|S01_08_Michel_under-control"

  # ---- רצף 2 : הגניבה ----
  "4ba7408c" = "02-theft|S02_01_Michel_what-was-stolen"
  "60df4709" = "02-theft|S02_02_Michel_dramatic-eyes"
  "c54fbf7d" = "02-theft|S02_05_Michel_the-camera-too"
  "9688bbd2" = "02-theft|S02_07_Michel_where-could-it-be"
  "30673e23" = "02-theft|S02_09_Michel_sir-what-are-you-doing"
  "31288380" = "02-theft|S02_12_Thief_lo-du-chocolat"

  # ---- רצף 3 : הניידת ----
  "966a79e8" = "03-police-car|S03_01a_FR_patrouille_QUESTION_hold-the-pause"
  "2f6e7227" = "03-police-car|S03_02_Michel_not-just-a-car"
  "051a9497" = "03-police-car|S03_03_Michel_tool-on-wheels"
  "4e7493f3" = "03-police-car|S03_04_Michel_lots-of-buttons"
  "affc4e6c" = "03-police-car|S03_05_Michel_lights"
  "2ead80ad" = "03-police-car|S03_06_Michel_sirena"
  "1f1de504" = "03-police-car|S03_07_Michel_we-dont-press-that"
  "5f8b0d00" = "03-police-car|S03_08_INSERT_finger-red-button"
  "ee37e7f2" = "03-police-car|S03_10_Michel_who-built-this_PA"
  "a31bae54" = "03-police-car|S03_12_FR_menottes_QUESTION_hold-the-pause"
  "d3b8ee7a" = "03-police-car|S03_13_FR_radio_QUESTION_hold-the-pause"
  "44496cf5" = "03-police-car|S03_14_FR_radio_ANSWER"

  # ---- רצף 5 : סיום ----
  "2160e55d" = "05-ending|S05_01_Michel_what-did-we-learn"
  "94df9791" = "05-ending|S05_02_FR_policier_QUESTION_hold-the-pause"
  "a88e05af" = "05-ending|S05_04_Michel_mission-for-you"
  "4290c5b5" = "05-ending|S05_05_Michel_wheres-my-kinder"
}

if (-not (Test-Path -LiteralPath $Root)) { throw "לא נמצאה התיקייה: $Root" }

$files = Get-ChildItem -LiteralPath $Root -File -Filter *.mp4
if ($files.Count -eq 0) { $files = Get-ChildItem -LiteralPath $Root -File }

$done = 0; $skipped = @()
foreach ($f in $files) {
  $hit = $null
  foreach ($k in $map.Keys) { if ($f.Name -like "*$k*") { $hit = $map[$k]; break } }
  if (-not $hit) { $skipped += $f.Name; continue }

  $parts  = $hit.Split('|')
  $folder = Join-Path $Root $parts[0]
  $target = Join-Path $folder ($parts[1] + $f.Extension)
  $dir    = Split-Path $target -Parent
  if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

  if ($WhatIfOnly) { Write-Host "$($f.Name)  ->  $($parts[0])\$($parts[1])$($f.Extension)" ; continue }
  if ($Copy) { Copy-Item -LiteralPath $f.FullName -Destination $target -Force }
  else       { Move-Item -LiteralPath $f.FullName -Destination $target -Force }
  Write-Host "OK  $($parts[0])\$($parts[1])$($f.Extension)"
  $done++
}

Write-Host ""
Write-Host "סודרו: $done קבצים"
if ($skipped.Count) {
  Write-Host "לא זוהו ($($skipped.Count)):" -ForegroundColor Yellow
  $skipped | ForEach-Object { Write-Host "   $_" }
}
