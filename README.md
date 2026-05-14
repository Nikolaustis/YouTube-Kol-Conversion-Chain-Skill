# YouTube KOL Conversion Chain Analyzer

This Skill collects and cleans public YouTube Data API v3 data for RF, LDCloud, UgPhone, and VSPhone KOL/creator-channel analysis.

It is designed for the research question:

> How do cloud-phone competitors use YouTube creator videos to drive downloads, purchase pages, invite codes, discount codes, referral traces, social/private redirects, and other conversion paths?

## Main workflow

### 1. Install requirements

```bash
pip install -r requirements.txt
```

### 2. Set YouTube API key

PowerShell:

```powershell
$env:YOUTUBE_API_KEY="YOUR_KEY"
```

Bash:

```bash
export YOUTUBE_API_KEY="YOUR_KEY"
```

### 3. Run monthly collection

Edit `configs/config.monthly.example.json` and set one month:

```json
"published_after": "2025-09-01T00:00:00Z",
"published_before": "2025-10-01T00:00:00Z"
```

Then run:

```bash
python scripts/youtube_kol_chain_analyzer.py --config configs/config.monthly.example.json --dry-run
python scripts/youtube_kol_chain_analyzer.py --config configs/config.monthly.example.json
```

### 4. Clean outputs

Clean one run folder, a parent folder of monthly runs, or a zip archive:

```bash
python scripts/clean_existing_youtube_outputs.py --input output --output output_cleaned --config configs/config.cleaning.example.json
```

The cleaner does not call YouTube API.

## Clean classification policy

Clean outputs use only three buckets:

| Bucket | Meaning | Main files |
|---|---|---|
| Official accounts | Official and regional official accounts for RF, LD, UgPhone, VSPhone | `official_videos_clean.csv`, `official_channel_summary_clean.csv` |
| Ordinary KOL/creators | Non-official third-party creators after false-positive cleaning | `kol_videos_clean.csv`, `creator_brand_summary_clean.csv` |
| Excluded/noise | Small competitors and false-positive matches | `excluded_channels.csv`, `dropped_false_positives.csv`, `review_videos.csv` |

There is no dealer/agent/managed-channel reporting bucket. Do not use old `managed_*` outputs if they exist in previous folders.

## Important output files

After collection:

| File | Meaning |
|---|---|
| `videos.csv` | Raw collected video rows. |
| `kol_videos.csv` | Raw non-official videos from the collector. Must be cleaned before reporting. |
| `official_videos.csv` | Official uploads recognized by config. |
| `conversion_paths.csv` | Raw link/code/CTA extraction. |
| `channel_baselines.csv` | Raw channel baseline and performance index. |
| `youtube_kol_conversion_report.xlsx` | Raw Excel report. |

After cleaning:

| File | Meaning |
|---|---|
| `videos_clean.csv` | Clean accepted rows. |
| `kol_videos_clean.csv` | Clean ordinary KOL rows only. |
| `official_videos_clean.csv` | Official and regional official rows. |
| `dropped_false_positives.csv` | Rows removed by strong false-positive cleaning. |
| `excluded_channels.csv` | Excluded small competitors such as `@botcloudphone` and `@maxcloudphone`. |
| `review_videos.csv` | Ambiguous rows for manual review. |
| `brand_summary_clean.csv` | Clean brand-level summary. |
| `creator_brand_summary_clean.csv` | Clean KOL `channel × brand` summary. |
| `official_channel_summary_clean.csv` | Clean official account summary. |
| `youtube_kol_conversion_report_clean.xlsx` | Clean Excel report for analysis. |

## Strong cleaning logic

The cleaner addresses common false positives:

- `VS Phone` is rejected when it clearly means ordinary comparison content, such as `PC vs phone`, `laptop vs phone`, `stapler vs phone`, etc.
- `Red Finger` is rejected when it means songs, ASMR, challenges, rings, horror games, kids content, etc.
- `LD Cloud` without cloud-phone context is marked as review.
- Regional brand accounts such as `@ugphone-indonesia`, `@ugphonejp`, `@ugphonevn`, and `@redfinger888` are counted as official accounts.
- `@botcloudphone` and `@maxcloudphone` are excluded as small competitors, not treated as downstream channels.

You can edit `configs/config.cleaning.example.json` to add more official or excluded accounts.
