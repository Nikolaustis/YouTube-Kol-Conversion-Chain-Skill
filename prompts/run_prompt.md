Use the installed YouTube KOL Conversion Chain Analyzer Skill.

Goal:
Analyze RF, LD, UgPhone, and VSPhone YouTube creator videos in the last 365 days.

Core requirements:
1. Use YouTube Data API v3 as the primary source.
2. Read `YOUTUBE_API_KEY` from environment only.
3. Do not hardcode or print secrets.
4. Public videos only. Do not bypass login, age, region, or member restrictions.
5. Use `configs/config.example.json` unless I provide another config.
6. Default date range must be the latest 365 days.
7. Resolve official channels by handle and collect their uploads separately.
8. Output official videos separately from KOL/creator videos.
9. Record publisher fields for every video:
   - channel_name
   - channel_handle
   - channel_id
   - channel_url
10. Build creator/KOL summaries at `channel × brand` level.
11. If one creator/channel covers multiple brands within the last 365 days, keep one row per brand.
12. Do not claim competitor GMV or revenue.

Official channels:
- UgPhone Cloud Phone / @ugphone
- Ugphone雲手機 / @Ugphone_tw
- UgPhone ประเทศไทย / @UgPhoneth
- UgScript / @UgScript
- VSPhone Official / @VSPhoneOfficial
- LDCloud / @LDCloud
- RedfingerOfficial / @redfingerofficial
- Redfinger / @Redfinger-cloud

Run commands:

```bash
python scripts/youtube_kol_chain_analyzer.py --config configs/config.example.json --dry-run
python scripts/youtube_kol_chain_analyzer.py --config configs/config.example.json
```

After the run, summarize these files:
- `brand_summary.csv`
- `creator_brand_summary.csv`
- `official_channel_summary.csv`
- `kol_videos.csv`
- `official_videos.csv`

Focus the written conclusion on:
- which brands have stronger YouTube creator exposure,
- which brands have clearer conversion links,
- which creators overlap across multiple brands,
- whether official videos and KOL videos use different link/CTA strategies,
- what UgPhone can improve in future YouTube creator cooperation.
