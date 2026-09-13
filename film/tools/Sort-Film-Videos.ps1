# ==========================================================
#  יום במשטרה עם מישל בנט - סידור כל החומר הגולמי
#  גרסה 2 - מטפלת ב-82 הקבצים: ליפסינק, שוטים שקטים,
#  מקורות ותמונות ייחוס.
#
#  שימוש:
#     .\Sort-Film-Videos.ps1 -Root "D:\archive (2)" -WhatIfOnly
#     .\Sort-Film-Videos.ps1 -Root "D:\archive (2)"
# ==========================================================
param(
  [string]$Root = "D:\archive (2)",
  [switch]$Copy,
  [switch]$WhatIfOnly
)

# ----------------------------------------------------------
# מפתח: תחילית ה-GUID  ->  "תיקייה|שם חדש"
#
# EDIT\  = הקבצים לעריכה. רק מהם מרכיבים את הסרט.
# _source-silent\ = אותם שוטים לפני הליפסינק, בלי קול. גיבוי בלבד.
# _reference\     = תמונות הייחוס של הדמויות.
# ----------------------------------------------------------
$map = @{

# ============ EDIT - סצנה 0 : פתיחה ============
  "fba8cab9" = "EDIT\00-opening|S00_01_ESTABLISH_police-station"
  "53e183ef" = "EDIT\00-opening|S00_02_Michel_opening"
  "6e902a5e" = "EDIT\00-opening|S00_03_Michel_what-well-see"
  "07eeca5b" = "EDIT\00-opening|S00_04_Michel_kinder"

# ============ EDIT - רצף 1 : מסוק ============
  "049a1b29" = "EDIT\01-helicopter|S01_01a_FR_helicoptere_QUESTION__hold-pause-after"
  "e594ee3f" = "EDIT\01-helicopter|S01_01b_FR_helicoptere_ANSWER"
  "e5e4c6d9" = "EDIT\01-helicopter|S01_02_Michel_helicopter-intro"
  "dd64230c" = "EDIT\01-helicopter|S01_03_Michel_hero-walk"
  "a540997f" = "EDIT\01-helicopter|S01_04a_helicopter-takeoff"
  "6cd947b8" = "EDIT\01-helicopter|S01_04b_REVEAL_hanging-on-helicopter"
  "cf5c16ab" = "EDIT\01-helicopter|S01_05_Michel_MEGAPHONE_see-everything"
  "09cd5363" = "EDIT\01-helicopter|S01_06_aerial-city"
  "b63bf8a0" = "EDIT\01-helicopter|S01_07_Michel_MEGAPHONE_let-me-down"
  "cffe8acd" = "EDIT\01-helicopter|S01_08_Michel_under-control"

# ============ EDIT - רצף 2 : הגניבה ============
  "4ba7408c" = "EDIT\02-theft|S02_01_Michel_what-was-stolen"
  "60df4709" = "EDIT\02-theft|S02_02_Michel_dramatic-eyes"
  "b45245a7" = "EDIT\02-theft|S02_03_CCTV_thief-sneaking"
  "bf080e30" = "EDIT\02-theft|S02_04_CCTV_thief-takes-kinder"
  "c54fbf7d" = "EDIT\02-theft|S02_05_Michel_the-camera-too"
  "db6fcdba" = "EDIT\02-theft|S02_06_CCTV_thief-hides"
  "9688bbd2" = "EDIT\02-theft|S02_07_Michel_where-could-it-be"
  "d1f96117" = "EDIT\02-theft|S02_08_thief-eating"
  "30673e23" = "EDIT\02-theft|S02_09_Michel_sir-what-are-you-doing"
  "31288380" = "EDIT\02-theft|S02_12_Thief_lo-du-chocolat"

# ============ EDIT - רצף 3 : הניידת ============
  "966a79e8" = "EDIT\03-police-car|S03_01_FR_patrouille_QUESTION__hold-pause-after"
  "2f6e7227" = "EDIT\03-police-car|S03_02_Michel_not-just-a-car"
  "051a9497" = "EDIT\03-police-car|S03_03_Michel_tool-on-wheels"
  "4e7493f3" = "EDIT\03-police-car|S03_04_Michel_lots-of-buttons"
  "affc4e6c" = "EDIT\03-police-car|S03_05_Michel_lights"
  "2ead80ad" = "EDIT\03-police-car|S03_06_Michel_sirena"
  "1f1de504" = "EDIT\03-police-car|S03_07_Michel_we-dont-press-that"
  "5f8b0d00" = "EDIT\03-police-car|S03_08_INSERT_finger-red-button"
  "580f6616" = "EDIT\03-police-car|S03_09_chaos-in-car"
  "ee37e7f2" = "EDIT\03-police-car|S03_10_Michel_who-built-this_PA"
  "a31bae54" = "EDIT\03-police-car|S03_12_FR_menottes_QUESTION__hold-pause-after"
  "d3b8ee7a" = "EDIT\03-police-car|S03_13_FR_radio_QUESTION__hold-pause-after"
  "44496cf5" = "EDIT\03-police-car|S03_14_FR_radio_ANSWER"

# ============ EDIT - רצף 5 : סיום ============
  "2160e55d" = "EDIT\05-ending|S05_01_Michel_what-did-we-learn"
  "94df9791" = "EDIT\05-ending|S05_02_FR_policier_QUESTION__hold-pause-after"
  "235c4f73" = "EDIT\05-ending|S05_03_Michel_most-important-tool"
  "a88e05af" = "EDIT\05-ending|S05_04_Michel_mission-for-you"
  "4290c5b5" = "EDIT\05-ending|S05_05_Michel_wheres-my-kinder"
  "2ebd3b7d" = "EDIT\05-ending|S05_06_final-gag_thief"

# ============ טייקים חלופיים ============
  "cbe38118" = "EDIT\_alt|S00_04_Michel_kinder_OLD-wrong-chocolate"
  "d9a7e6cb" = "EDIT\_alt|S03_09_chaos-in-car_ALT-mini-model"

# ============ מקורות שקטים (לפני ליפסינק) ============
  "a77a2452" = "_source-silent|S00_02_opening_SILENT"
  "ed2b5559" = "_source-silent|S00_03_what-well-see_SILENT"
  "60773138" = "_source-silent|S00_04_kinder_SILENT"
  "b3fae832" = "_source-silent|S00_04_kinder_OLD_SILENT"
  "a089eaf7" = "_source-silent|S01_01a_helicoptere_Q_SILENT"
  "26ecd1c1" = "_source-silent|S01_01b_helicoptere_A_SILENT"
  "d0ab43ad" = "_source-silent|S01_02_helicopter-intro_SILENT"
  "6612d598" = "_source-silent|S01_05_megaphone_SILENT"
  "058fa275" = "_source-silent|S01_07_let-me-down_SILENT"
  "5f016cf5" = "_source-silent|S01_08_under-control_SILENT"
  "c21d2fa8" = "_source-silent|S02_01_what-was-stolen_SILENT"
  "c7637631" = "_source-silent|S02_02_dramatic-eyes_SILENT"
  "64f0dabb" = "_source-silent|S02_05_camera-too_SILENT"
  "bcd821dd" = "_source-silent|S02_07_where-could-it-be_SILENT"
  "29eaa988" = "_source-silent|S02_09_sir-what-are-you-doing_SILENT"
  "cc50eb19" = "_source-silent|S02_12_du-chocolat_SILENT"
  "f51d2d88" = "_source-silent|S03_01_patrouille_Q_SILENT"
  "b29d2e38" = "_source-silent|S03_02_not-just-a-car_SILENT"
  "772b13ad" = "_source-silent|S03_03_tool-on-wheels_SILENT"
  "229f7b4a" = "_source-silent|S03_04_lots-of-buttons_SILENT"
  "6f782ac9" = "_source-silent|S03_05_lights_SILENT"
  "f21c5be7" = "_source-silent|S03_06_sirena_SILENT"
  "d32c1613" = "_source-silent|S03_07_we-dont-press-that_SILENT"
  "792eedb3" = "_source-silent|S03_08_red-button_SILENT"
  "775a9a30" = "_source-silent|S03_10_who-built-this_SILENT"
  "a6891329" = "_source-silent|S03_12_menottes_Q_SILENT"
  "a49f7c7f" = "_source-silent|S03_13_radio_Q_SILENT"
  "5531c186" = "_source-silent|S03_14_radio_A_SILENT"
  "2b7305ce" = "_source-silent|S05_01_what-did-we-learn_SILENT"
  "af9bab2c" = "_source-silent|S05_02_policier_Q_SILENT"
  "4c78e2d5" = "_source-silent|S05_03_most-important-tool_SILENT"
  "f29059c7" = "_source-silent|S05_04_mission-for-you_SILENT"
  "af49c89c" = "_source-silent|S05_05_wheres-my-kinder_SILENT"

# ============ תמונות ייחוס ============
  "935f84ee" = "_reference|REF_Michel_police_USED-as-element"
  "342856e6" = "_reference|REF_Michel_police_alt"
  "0d1a7085" = "_reference|REF_Thief_v1"
  "8de115ee" = "_reference|REF_Thief_v2"
}

if (-not (Test-Path -LiteralPath $Root)) { throw "לא נמצאה התיקייה: $Root" }

$files = Get-ChildItem -LiteralPath $Root -File
$done = 0; $skipped = @()

foreach ($f in $files) {
  if ($f.Name -eq 'Sort-Film-Videos.ps1') { continue }

  $hit = $null
  foreach ($k in $map.Keys) { if ($f.Name -like "*$k*") { $hit = $map[$k]; break } }

  if (-not $hit) { $skipped += $f.Name; $hit = "_unsorted|$($f.BaseName)" }

  $parts  = $hit.Split('|')
  $target = Join-Path (Join-Path $Root $parts[0]) ($parts[1] + $f.Extension)
  $dir    = Split-Path $target -Parent
  if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

  if ($WhatIfOnly) { Write-Host "$($f.Name)`n   -> $($parts[0])\$($parts[1])$($f.Extension)"; continue }
  if ($Copy) { Copy-Item -LiteralPath $f.FullName -Destination $target -Force }
  else       { Move-Item -LiteralPath $f.FullName -Destination $target -Force }
  Write-Host "OK  $($parts[0])\$($parts[1])$($f.Extension)"
  $done++
}

Write-Host ""
Write-Host "סודרו: $done קבצים"
if ($skipped.Count) {
  Write-Host "לא זוהו - הועברו ל-_unsorted ($($skipped.Count)):" -ForegroundColor Yellow
  $skipped | ForEach-Object { Write-Host "   $_" }
}
Write-Host ""
Write-Host "לעריכה: קח רק את מה שבתוך EDIT\ ." -ForegroundColor Green
