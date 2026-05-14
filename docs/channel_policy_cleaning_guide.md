# Channel policy cleaning guide

## Classification rules

The clean reporting policy has three buckets only: official accounts, ordinary KOL/creators, and excluded/noise.

| Channel | Classification | Treatment |
|---|---|---|
| @ugphone-indonesia | official | Included in `official_videos_clean.csv` |
| @redfinger888 | official | Included in `official_videos_clean.csv` |
| @ugphonejp | official | Included in `official_videos_clean.csv` |
| @ugphonevn | official | Included in `official_videos_clean.csv` |
| @ugphonevietnam | official | Included in `official_videos_clean.csv` |
| @ugphone_kr | official | Included in `official_videos_clean.csv` |
| @botcloudphone | excluded small competitor | Removed from clean outputs; recorded in `excluded_channels.csv` |
| @maxcloudphone | excluded small competitor | Removed from clean outputs; recorded in `excluded_channels.csv` |

No channel is currently reported as a real dealer/agent channel. Do not use old `managed_videos_clean.csv` or `managed_channel_summary_clean.csv` files if they exist from earlier versions.

## How to clean existing monthly data separately

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

## Use these files for reports

- KOL: `kol_videos_clean.csv`, `creator_brand_summary_clean.csv`
- Official: `official_videos_clean.csv`, `official_channel_summary_clean.csv`
- Excluded small competitors: `excluded_channels.csv`
- Noise: `dropped_false_positives.csv`
- Review: `review_videos.csv`
- Brand overview: `brand_summary_clean.csv`

## Do not use these old files

- `managed_videos_clean.csv`
- `managed_channel_summary_clean.csv`
