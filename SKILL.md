# YouTube KOL Conversion Chain Analyzer Skill

Use this Skill when the user needs to analyze YouTube creator/KOL videos for cloud-phone competitors such as RF/Redfinger, LDCloud, UgPhone, and VSPhone.

## What this Skill does

1. Collects public YouTube video metadata via YouTube Data API v3.
2. Searches configured brand and scene keywords by date range.
3. Resolves configured official channels by handle and collects official uploads separately.
4. Extracts conversion-chain signals from video descriptions:
   - official site links
   - purchase/buy page links
   - Google Play/App Store links
   - invite/referral/discount/code traces
   - short links
   - Discord/Telegram/WhatsApp/social redirects
   - reseller/distributor/code-selling traces as content signals only
5. Computes channel-baseline performance index.
6. Strong-cleans false positives and reclassifies regional official accounts using `clean_existing_youtube_outputs.py`.
7. Recomputes clean summaries for reporting.

## Required environment

- Python 3.10+
- `pip install -r requirements.txt`
- `YOUTUBE_API_KEY` environment variable

Never hardcode or print API keys.

## Recommended workflow

For monthly runs:

```bash
python scripts/youtube_kol_chain_analyzer.py --config configs/config.monthly.example.json --dry-run
python scripts/youtube_kol_chain_analyzer.py --config configs/config.monthly.example.json
python scripts/clean_existing_youtube_outputs.py --input output --output output_cleaned --config configs/config.cleaning.example.json
```

For already collected historical data:

```bash
python scripts/clean_existing_youtube_outputs.py --input path/to/monthly_outputs_or_zip --output path/to/cleaned_outputs --config configs/config.cleaning.example.json
```

## Current clean classification policy

Only three buckets are used in clean reporting:

1. Official accounts: official and regional official accounts.
2. Ordinary KOL/creators: non-official third-party creators after cleaning.
3. Excluded/noise: small competitors and false-positive matches.

There is intentionally no `managed` / dealer / agent reporting bucket. If old folders contain `managed_*` files, ignore them.

## Important reporting files

Always use clean recomputed outputs:

- `brand_summary_clean.csv`
- `creator_brand_summary_clean.csv`
- `official_channel_summary_clean.csv`
- `kol_videos_clean.csv`
- `official_videos_clean.csv`
- `excluded_channels.csv`
- `dropped_false_positives.csv`
- `review_videos.csv`

## Reporting guidance

Do not claim competitor GMV or revenue from YouTube data alone. Frame results as public-signal analysis:

- exposure scale
- conversion-chain clarity
- creator overlap
- official vs KOL CTA differences
- invite/referral/code traces
- content-fit via cleaned performance index
