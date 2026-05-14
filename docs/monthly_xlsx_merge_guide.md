# Monthly run and annual merge guide

## Recommended monthly workflow

1. Edit `configs/config.monthly.example.json`.
2. Set a single natural month:

```json
"published_after": "2025-09-01T00:00:00Z",
"published_before": "2025-10-01T00:00:00Z"
```

3. Run collection:

```bash
python scripts/youtube_kol_chain_analyzer.py --config configs/config.monthly.example.json
```

4. Clean that month or clean all months together:

```bash
python scripts/clean_existing_youtube_outputs.py --input output --output output_cleaned --config configs/config.cleaning.example.json
```

## Which sheets can be concatenated?

Raw-level sheets can be concatenated and deduplicated by `brand + video_id`:

- `video_samples_all`
- `kol_videos`
- `official_videos`
- `conversion_paths`
- `channel_baselines`

But after this update, use clean outputs for reporting:

- `videos_clean.csv`
- `kol_videos_clean.csv`
- `official_videos_clean.csv`
- `conversion_paths_clean.csv`
- `channel_baselines_clean.csv`

## Which summaries must be recomputed?

Do not add or average monthly summaries directly. Recompute these from clean deduped rows:

- `brand_summary_clean.csv`
- `creator_brand_summary_clean.csv`
- `official_channel_summary_clean.csv`
- `managed_channel_summary_clean.csv`

Reasons:

1. One video can be found in multiple runs.
2. `channel_count` must be recomputed from unique `channel_id`.
3. Rates such as `referral_code_rate` must be recomputed from clean videos.
4. `is_multi_brand_creator_in_scope` only makes sense at the full-year scope.
5. `clean_performance_index` must be filtered by baseline quality.

## Historical data already collected

Do not rerun YouTube API just to fix the known problems. Use:

```bash
python scripts/clean_existing_youtube_outputs.py --input path/to/8_month_outputs --output path/to/8_month_cleaned --config configs/config.cleaning.example.json
```

The cleaner does not use YouTube quota.
