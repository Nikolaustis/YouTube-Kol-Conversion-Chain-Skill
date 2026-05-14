# Update notes: strong cleaning + official/managed channel correction

This update addresses the 2025-09 to 2025-12 data quality issues:

1. Strong false-positive cleaning for ambiguous brand terms:
   - `VS Phone` no longer inflates VSPhone results with generic `PC vs phone`, `laptop vs phone`, `stapler vs phone`, etc.
   - `Red Finger` no longer inflates Redfinger results with songs, ASMR, challenges, rings, horror/game-only content, etc.
   - `LD Cloud` rows without cloud-phone context are marked for review.

2. Official-like and dealer/channel accounts are no longer counted as ordinary KOL:
   - `@redfinger888`
   - `@ugphone-indonesia`
   - `@ugphonejp`
   - `@ugphonevn`
   - `@maxcloudphone`

3. New cleaner for historical monthly data:
   - `scripts/clean_existing_youtube_outputs.py`
   - Does not call YouTube API.
   - Reads existing monthly output folders or zip archives.
   - Recomputes clean brand, creator, official, and managed summaries.

4. Performance index is now quality-filtered in cleaned outputs:
   - `baseline_video_count >= 5`
   - `baseline_avg_views_per_day >= 5`
   - `video_age_days >= 7`
   - only then is `clean_performance_index` considered usable.

Recommended workflow:

```bash
python scripts/youtube_kol_chain_analyzer.py --config configs/config.monthly.example.json
python scripts/clean_existing_youtube_outputs.py --input output --output output_cleaned --config configs/config.cleaning.example.json
```
