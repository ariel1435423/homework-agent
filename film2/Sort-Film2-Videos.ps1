# ==========================================================
#  "Michel Inside the Body" - film 2
#  Sorts the Higgsfield export into edit-ready folders.
#  ASCII only - PowerShell 5.1 mangles non-ASCII .ps1 files.
#
#  Usage:
#     .\Sort-Film2-Videos.ps1 -Root "D:\archive (3)" -WhatIfOnly
#     .\Sort-Film2-Videos.ps1 -Root "D:\archive (3)"
#     add -Copy to copy instead of move
#
#  EDIT\           = the only files that go into the cut (20)
#  _source-silent\ = same shots before lipsync, no voice. Backup only.
#  _stills\        = the approved start images the shots were built from
#  _rejected\      = wrong-face takes from the first attempt. Do not use.
#  _tests\         = the lipsync model tests
# ==========================================================
param(
  [string]$Root = "D:\archive (3)",
  [switch]$Copy,
  [switch]$WhatIfOnly
)

$map = @{

# ===== EDIT - scene 0, the mouth =====
  "91e308cb" = "EDIT\00-mouth|S00_A_Michel_good-morning-lavi"
  "1c337d53" = "EDIT\00-mouth|S00_B_Michel_LA-BOUCHE"
  "ef13785f" = "EDIT\00-mouth|S00_C_BROLL_mouth-cave"
  "9092e630" = "EDIT\00-mouth|S00_D_FR_les-dents_QUESTION__hold-pause-after"
  "88cc7217" = "EDIT\00-mouth|S00_E_BROLL_teeth__put-LES-DENTS-answer-here"
  "341a7d23" = "EDIT\00-mouth|S00_F_Michel_LA-LANGUE_dont-swallow"

# ===== EDIT - scene 1, the stomach =====
  "203cc972" = "EDIT\01-stomach|S01_A_FR_le-ventre_QUESTION__hold-pause-after"
  "e32aacf6" = "EDIT\01-stomach|S01_B_BROLL_bubbles__put-LE-VENTRE-answer-here"

# ===== EDIT - scene 2, blood and heart =====
  "4b6486d8" = "EDIT\02-blood-heart|S02_A_Michel_LE-SANG"
  "96ff57b5" = "EDIT\02-blood-heart|S02_B_BROLL_blood-tunnel"
  "3daf4dc8" = "EDIT\02-blood-heart|S02_C_FR_le-coeur_QUESTION__hold-pause-after"
  "79e49fd5" = "EDIT\02-blood-heart|S02_D_BROLL_heart-hall__put-LE-COEUR-answer-here"

# ===== EDIT - scene 3, the lungs =====
  "b25a5997" = "EDIT\03-lungs|S03_A_Michel_LES-POUMONS"
  "dc69becd" = "EDIT\03-lungs|S03_B_BROLL_lung-domes"

# ===== EDIT - scene 4, the control room =====
  "e4c80103" = "EDIT\04-control-room|S04_A_FR_la-tete_QUESTION__hold-pause-after"
  "8d28419a" = "EDIT\04-control-room|S04_B_BROLL_control-room__put-LA-TETE-LES-YEUX-LES-OREILLES-answer-here"

# ===== EDIT - scene 5, the sneeze and landing =====
  "8a9bb247" = "EDIT\05-sneeze-landing|S05_A_BROLL_sneeze-burst"
  "e2c6b7d7" = "EDIT\05-sneeze-landing|S05_B_Michel_flying-through-air"
  "fdd12e32" = "EDIT\05-sneeze-landing|S05_C_FR_la-main_QUESTION__hold-pause-after"
  "14d8e7ee" = "EDIT\05-sneeze-landing|S05_D_Michel_LA-MAIN_LES-CHEVEUX_ending-mission"

# ===== silent sources, before lipsync =====
  "9bf95607" = "_source-silent|S00_A_good-morning_SILENT"
  "231298f9" = "_source-silent|S00_B_la-bouche_SILENT"
  "b0b1971a" = "_source-silent|S00_D_les-dents-Q_SILENT"
  "0635d7e6" = "_source-silent|S00_F_la-langue_SILENT"
  "a93a1a9b" = "_source-silent|S01_A_le-ventre-Q_SILENT"
  "2ebacd0e" = "_source-silent|S02_A_le-sang_SILENT"
  "63fda10a" = "_source-silent|S02_C_le-coeur-Q_SILENT"
  "6f9315db" = "_source-silent|S03_A_les-poumons_SILENT"
  "680470c5" = "_source-silent|S04_A_la-tete-Q_SILENT"
  "692d8c9c" = "_source-silent|S05_C_la-main-Q_SILENT"
  "ece7cd27" = "_source-silent|S05_D_ending_SILENT"

# ===== approved start images =====
  "056c9e8e" = "_stills|STILL_S00_A_waking-in-mouth"
  "872eb354" = "_stills|STILL_S00_looking-up-at-tooth"
  "3e5eef2a" = "_stills|STILL_S00_D_closeup-talking"
  "ce81be28" = "_stills|STILL_S00_F_tongue-slide"
  "5c83e688" = "_stills|STILL_S01_A_stomach"
  "a8e72831" = "_stills|STILL_S02_A_blood-tunnel"
  "4317f905" = "_stills|STILL_S02_C_heart-hall"
  "523cc4bd" = "_stills|STILL_S03_A_lungs"
  "8cecba3f" = "_stills|STILL_S04_A_control-room"
  "8260e946" = "_stills|STILL_S05_B_flying"
  "bccdf3e4" = "_stills|STILL_S05_C_landing-on-hand"
  "2ab33b0f" = "_stills|STILL_S05_D_hair-forest"

# ===== rejected - wrong face, first attempt =====
  "350b3944" = "_rejected|REJ_still_mouth-wide"
  "0615fefa" = "_rejected|REJ_still_mouth-waking"
  "e6ca0152" = "_rejected|REJ_still_tooth"
  "f291a7bb" = "_rejected|REJ_still_tongue"
  "6bf855bc" = "_rejected|REJ_still_stomach"
  "5014762f" = "_rejected|REJ_still_blood"
  "dd0f3b24" = "_rejected|REJ_still_blood-alt"
  "f8c1955f" = "_rejected|REJ_still_heart"
  "bb6dfc66" = "_rejected|REJ_still_lungs"
  "776b252b" = "_rejected|REJ_still_control-room"
  "804ba3b7" = "_rejected|REJ_still_hand"
  "efd4f3bd" = "_rejected|REJ_still_hair"
  "d4cff697" = "_rejected|REJ_video_waking"
  "087f428e" = "_rejected|REJ_video_standing-up"
  "7a1c7ec4" = "_rejected|REJ_video_tooth-talking"
  "804319fd" = "_rejected|REJ_video_tongue-slide"
  "c183ea70" = "_rejected|REJ_video_tooth-talking-lipsynced"

# ===== model tests =====
  "296d4ac7" = "_tests|TEST_mini_audio-reference_no-real-lipsync"
  "4434c1f2" = "_tests|TEST_wan27_audio-reference_no-real-lipsync"
}

if (-not (Test-Path -LiteralPath $Root)) { throw "Folder not found: $Root" }

$files = Get-ChildItem -LiteralPath $Root -File
$done = 0
$skipped = @()

foreach ($f in $files) {
  if ($f.Extension -eq ".ps1") { continue }

  $hit = $null
  foreach ($k in $map.Keys) {
    if ($f.Name -like "*$k*") { $hit = $map[$k]; break }
  }

  if (-not $hit) {
    $skipped += $f.Name
    $hit = "_unsorted|" + $f.BaseName
  }

  $parts  = $hit.Split("|")
  $folder = Join-Path $Root $parts[0]
  $target = Join-Path $folder ($parts[1] + $f.Extension)

  if (-not (Test-Path -LiteralPath $folder)) {
    New-Item -ItemType Directory -Path $folder -Force | Out-Null
  }

  if ($WhatIfOnly) {
    Write-Host ($f.Name + "   ->   " + $parts[0] + "\" + $parts[1] + $f.Extension)
    continue
  }

  if ($Copy) {
    Copy-Item -LiteralPath $f.FullName -Destination $target -Force
  } else {
    Move-Item -LiteralPath $f.FullName -Destination $target -Force
  }
  Write-Host ("OK  " + $parts[0] + "\" + $parts[1] + $f.Extension)
  $done++
}

Write-Host ""
if ($WhatIfOnly) {
  Write-Host "Preview only - nothing was moved. Run again without -WhatIfOnly."
} else {
  Write-Host ("Sorted: " + $done + " files")
}

if ($skipped.Count -gt 0) {
  Write-Host ""
  Write-Host ("NOT RECOGNIZED - sent to _unsorted (" + $skipped.Count + "):") -ForegroundColor Yellow
  foreach ($s in $skipped) { Write-Host ("   " + $s) }
}

Write-Host ""
Write-Host "For the edit, use only what is inside EDIT\ ." -ForegroundColor Green
Write-Host "Files named ...__hold-pause-after need 2-3 seconds of silence after them." -ForegroundColor Green
