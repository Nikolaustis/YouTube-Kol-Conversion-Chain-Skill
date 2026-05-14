# Data cleaning guide

## Why cleaning is required

The brand search terms are intentionally broad enough to improve recall. However, broad terms also create noise:

- `VS Phone` can match ordinary comparison videos such as `PC vs Phone`.
- `Red Finger` can match kids songs, ASMR, horror games, rings, challenges, etc.
- Some regional official, store, or dealer accounts can be incorrectly counted as KOL.

Therefore, every monthly or annual output should be cleaned before being used in a final report.

## Main cleaning statuses

| Field | Meaning |
|---|---|
| `clean_status=keep` | Safe enough to use in clean summaries. |
| `clean_status=drop_false_positive` | High-risk false positive; excluded from clean outputs. |
| `clean_status=review` | Ambiguous; excluded from strict clean summaries unless `--include-review` is passed. |

## Channel roles

| Role | Meaning | Included in KOL summary? |
|---|---|---|
| `kol_creator` | Ordinary creator/KOL account | Yes |
| `official` | Official brand account | No |
| `official_like` | Regional official-like brand account | No |
| `dealer_or_agent` | Store, agent, channel, or seller-like account | No |

## Performance index cleaning

The original `performance_index` can be distorted by weak baselines. The cleaner adds:

```text
clean_performance_index
performance_quality_status
```

A performance index is usable only when:

```text
baseline_video_count >= 5
baseline_avg_views_per_day >= 5
video_age_days >= 7
```

Use `median_clean_performance_index` before `avg_clean_performance_index` in reporting.

## Clean historical data

For a parent folder that contains monthly folders:

```bash
python scripts/clean_existing_youtube_outputs.py --input path/to/monthly_outputs --output path/to/cleaned_outputs --config configs/config.cleaning.example.json
```

For a zip file:

```bash
python scripts/clean_existing_youtube_outputs.py --input 2025_09-12.zip --output cleaned_2025_09_12 --config configs/config.cleaning.example.json
```

Default mode is strict: `review` rows are not used in clean summaries. To include review rows:

```bash
python scripts/clean_existing_youtube_outputs.py --input path/to/monthly_outputs --output path/to/cleaned_outputs --config configs/config.cleaning.example.json --include-review
```

## Clean outputs

| File | Purpose |
|---|---|
| `videos_clean.csv` | All clean accepted rows after dedupe. |
| `kol_videos_clean.csv` | Clean ordinary KOL rows only. |
| `official_videos_clean.csv` | Official and official-like rows. |
| `managed_videos_clean.csv` | Official-like and dealer/agent rows. |
| `dropped_false_positives.csv` | Rows removed by strong cleaning. |
| `review_videos.csv` | Ambiguous rows for manual review. |
| `brand_summary_clean.csv` | Recomputed brand summary after cleaning. |
| `creator_brand_summary_clean.csv` | Recomputed KOL `channel × brand` summary after cleaning. |
| `official_channel_summary_clean.csv` | Recomputed official/official-like summary. |
| `managed_channel_summary_clean.csv` | Recomputed dealer/agent/official-like summary. |
| `youtube_kol_conversion_report_clean.xlsx` | Clean Excel report. |
