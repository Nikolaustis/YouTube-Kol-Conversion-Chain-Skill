Use the installed YouTube KOL Conversion Chain Analyzer Skill.

Goal:
Analyze RF, LDCloud, UgPhone, and VSPhone YouTube creator videos for one monthly window, then run strong cleaning before summarizing.

Requirements:
1. Use YouTube Data API v3 as the primary source for collection.
2. Read `YOUTUBE_API_KEY` from environment only.
3. Do not hardcode or print secrets.
4. Public videos only.
5. Use `configs/config.monthly.example.json` unless I provide another config.
6. After collection, run `scripts/clean_existing_youtube_outputs.py`.
7. Summarize only the clean outputs, not raw summaries.
8. Do not claim competitor GMV or revenue.

Commands:

```bash
python scripts/youtube_kol_chain_analyzer.py --config configs/config.monthly.example.json --dry-run
python scripts/youtube_kol_chain_analyzer.py --config configs/config.monthly.example.json
python scripts/clean_existing_youtube_outputs.py --input output --output output_cleaned --config configs/config.cleaning.example.json
```

Summarize these clean files:

- `brand_summary_clean.csv`
- `creator_brand_summary_clean.csv`
- `official_channel_summary_clean.csv`
- `dropped_false_positives.csv`
- `review_videos.csv`

Focus on:

- which brands have clean KOL exposure,
- which brands have clearer conversion links,
- which creators overlap across multiple brands,
- which channels should not be counted as ordinary KOL,
- how false positives changed RF/VS metrics,
- what UgPhone can improve in YouTube creator cooperation.
