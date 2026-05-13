# Update Notes

This update package is meant to be extracted over the existing `youtube-kol-conversion-chain-skill` folder.

## Updated / replacement files

```text
SKILL.md
README.md
configs/config.example.json
docs/metric_dictionary.md
prompts/run_prompt.md
scripts/youtube_kol_chain_analyzer.py
```

## What changed

1. Default collection range is now the latest 365 days.
2. Search is split into 30-day windows by default to improve recall.
3. Official channels are configured and resolved by YouTube handle.
4. Official channel uploads are collected separately from uploads playlists.
5. Every video row now records:
   - `channel_name`
   - `channel_handle`
   - `channel_id`
   - `channel_url`
6. Official videos and KOL videos are split into separate outputs:
   - `official_videos.csv`
   - `kol_videos.csv`
7. New `creator_brand_summary.csv` aggregates non-official creators by `channel × brand`.
8. If one creator covers multiple brands in the last 365 days, each brand gets one row.
9. New `official_channel_summary.csv` aggregates configured official channels by `channel × brand`.
10. Multi-brand video matching is preserved instead of assigning each video to only the first matched brand.

## How to apply

From the original skill root directory, copy or extract this package so that paths match the existing folders.

Then run:

```bash
python scripts/youtube_kol_chain_analyzer.py --config configs/config.example.json --dry-run
python scripts/youtube_kol_chain_analyzer.py --config configs/config.example.json
```
