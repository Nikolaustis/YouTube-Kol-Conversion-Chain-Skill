Use the installed YouTube KOL Conversion Chain Analyzer Skill.

Task:
Clean existing monthly YouTube outputs from 2025_09 to 2026_04 separately using the latest three-bucket channel classification policy.

Rules:
- Treat @ugphone-indonesia, @redfinger888, @ugphonejp, @ugphonevn, @ugphonevietnam, and @ugphone_kr as official accounts.
- Exclude @botcloudphone and @maxcloudphone as small competitors, not downstream channels.
- Do not create or use a managed/dealer/agent reporting bucket.
- Do not merge the eight months during cleaning.
- Each month should have its own output folder.

PowerShell:

```powershell
$SkillRoot = "C:\Users\Og\.codex\skills\youtube-kol-conversion-chain-skill"
$Script = "$SkillRoot\scripts\clean_existing_youtube_outputs.py"
$Config = "$SkillRoot\configs\config.cleaning.example.json"

$RawRoot = "C:\Users\Og\Desktop\youtube_8_months"
$CleanRoot = "C:\Users\Og\Desktop\youtube_8_months_cleaned_v4"

$Months = @(
  "2025_09",
  "2025_10",
  "2025_11",
  "2025_12",
  "2026_01",
  "2026_02",
  "2026_03",
  "2026_04"
)

foreach ($Month in $Months) {
  $InputDir = Join-Path $RawRoot $Month
  $OutputDir = Join-Path $CleanRoot $Month
  Write-Host "Cleaning $Month ..."
  python $Script --input $InputDir --output $OutputDir --config $Config
}

Write-Host "All monthly cleaning tasks completed."
```
