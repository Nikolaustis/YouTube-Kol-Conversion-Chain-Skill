# Update Notes - Noise Filtering and Official Brand Override

This update implements two major fixes for future collection and adds a post-hoc cleaner for already collected monthly outputs.

## Future collection fixes

1. `strict_brand_filter` is now `true` by default.
2. Non-official videos must match either:
   - exact brand aliases in title/description, or
   - the matched brand's official domain in the video description URLs.
3. Official channel brand ownership now overrides search keyword matches.
   - If a video is published by a configured official channel, the brand is set from `official_channels`.
   - The same official video will no longer be duplicated under other brands just because it was found by another brand's search term.
4. RedFinger and VSPhone broad-term noise is reduced:
   - `VS` alone is never used as an alias.
   - `finger` alone is never used as an alias.

## Historical data cleaner

New script:

```text
scripts/clean_existing_youtube_outputs.py
```

It cleans existing monthly output folders without calling the YouTube API.

Example:

```bash
python scripts/clean_existing_youtube_outputs.py \
  --input-root output/monthly_runs \
  --config configs/config.example.json \
  --output-dir output/cleaned_2026_01_04
```

It generates:

```text
cleaned_videos.csv
cleaned_kol_videos.csv
cleaned_official_videos.csv
noise_videos.csv
cleaned_brand_summary.csv
cleaned_creator_brand_summary.csv
cleaned_official_channel_summary.csv
cleaned_channel_baselines.csv
cleaned_youtube_kol_report.xlsx
cleaning_summary.json
```

## Cleaning rules

Keep a row if any of the following is true:

1. The channel is a configured official channel. Brand is corrected by official channel config.
2. The video title/description contains an exact brand alias:
   - Ug: `UgPhone`, `Ug Phone`
   - VS: `VSPhone`, `VS Phone`
   - RF: `RedFinger`, `Redfinger`, `Red Finger`, `RF cloud phone`
   - LD: `LD Cloud`, `LDCloud`, `LD Cloud Phone`, `LDPlayer cloud phone`
3. The video description contains the matched brand's official domain:
   - `ugphone.com`
   - `vsphone.com`
   - `cloudemulator.net`, `redfinger.com`
   - `ldcloud.net`, `ldplayer.net`

Drop a row if it only matched because of broad search noise such as:

- `phone vs phone`
- `iPhone vs Samsung`
- `finger knitting`
- `finger family`
- other titles/descriptions without exact brand alias or official domain.
