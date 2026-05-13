# YouTube KOL Conversion Chain Analyzer

## Purpose

Analyze public YouTube creator videos for cloud-phone competitors and compare RF / LD / UgPhone / VSPhone on:

1. YouTube creator exposure;
2. official-account vs KOL/creator content separation;
3. conversion-chain clarity in video descriptions;
4. invite/referral/discount/code traces;
5. official buy page / app-store / social-private redirects;
6. brand-video performance relative to each channel's normal videos;
7. creator/channel-level summaries by `channel × brand`.

Use this skill for the competitor research topic:

> Cloud-phone competitor YouTube KOL conversion-chain analysis: from video descriptions, invite codes, purchase pages, social redirects, and traffic performance.

## Safety and Data Boundaries

- Use YouTube Data API v3 as the primary source.
- Public videos only.
- Do not bypass login, age, region, membership, or private-content restrictions.
- Do not scrape private analytics.
- Do not claim competitor GMV, revenue, ad spend, or exact conversion without reliable internal or third-party paid data.
- Read `YOUTUBE_API_KEY` from environment only. Do not hardcode or print secrets.

## Default Scope

The default config collects videos from the latest 365 days:

- `lookback_days = 365`
- `published_after = null`
- `published_before = null`

If `published_after` is null, the script automatically uses `run_time - 365 days`.
If `published_before` is null, the script uses current run time.

For better recall, the search stage splits the 365-day range into 30-day windows by default. YouTube Search API still cannot guarantee absolute full-platform coverage, so the result should be treated as a structured public-signal sample.

Official channels are collected separately from their uploads playlist and filtered by the same 365-day range.

## Official Channels

The default official channel list is configured in `configs/config.example.json`:

- UgPhone Cloud Phone / `@ugphone`
- Ugphone雲手機 / `@Ugphone_tw`
- UgPhone ประเทศไทย / `@UgPhoneth`
- UgScript / `@UgScript`
- VSPhone Official / `@VSPhoneOfficial`
- LDCloud / `@LDCloud`
- RedfingerOfficial / `@redfingerofficial`
- Redfinger / `@Redfinger-cloud`

Rows from these official channels are marked as:

- `is_official_channel = true`
- `creator_type = official`

All other matched videos are treated as:

- `creator_type = kol/creator`

## Key Outputs

Each run creates a timestamped folder under `output/`, for example:

```text
output/youtube_kol_run_20260512T030000Z/
```

Main files:

| File | Purpose |
|---|---|
| `videos.csv` | All collected video rows. A video can appear once per matched brand. |
| `videos.jsonl` | Same video rows in JSONL format. |
| `kol_videos.csv` | Non-official creator/KOL videos only. Official channel rows are removed. |
| `official_videos.csv` | Official account videos only. |
| `conversion_paths.csv` | Link, CTA, invite code, discount code, social redirect, distribution trace fields. |
| `channel_baselines.csv` | Channel-level baseline comparison for brand-video performance index. |
| `creator_brand_summary.csv` | KOL/creator summary at `channel × brand` level. If one creator serves multiple brands, each brand gets one row. |
| `official_channel_summary.csv` | Official account summary at `channel × brand` level. |
| `brand_summary.csv` | Brand-level aggregate metrics. |
| `youtube_kol_conversion_report.xlsx` | Excel report with all key sheets. |
| `run_summary.json` | Run status, effective date range, quota estimate, counts. |
| `api_call_log.json` | API call log without secrets. |
| `run_log.txt` | Runtime log. |

## Important Metrics

### Conversion Path Score

| Score | Meaning |
|---:|---|
| 0 | No link, invite code, purchase guide, or social redirect found. |
| 1 | Brand name, official site, or app-store link exists, but conversion path is weak. |
| 2 | Official site, buy page, app store, or social/private redirect exists. |
| 3 | Referral/invite/discount/code trace, buy page, or clear purchase guide exists. |

### Brand Video Performance Index

```text
brand_video_performance_index = brand_video_views_per_day / channel_recent_non_brand_avg_views_per_day
```

Interpretation:

| Index | Meaning |
|---:|---|
| > 1.2 | Brand video performs above channel norm. |
| 0.8–1.2 | Brand video is close to channel norm. |
| 0.5–0.8 | Brand video may underperform due to ad-like content, mismatch, or timing. |
| < 0.5 | Brand video strongly underperforms and should be manually reviewed. |

## Standard Commands

Install dependencies:

```bash
pip install -r requirements.txt
```

Set API key:

```bash
export YOUTUBE_API_KEY="YOUR_KEY"
```

Windows PowerShell:

```powershell
$env:YOUTUBE_API_KEY="YOUR_KEY"
```

Dry run:

```bash
python scripts/youtube_kol_chain_analyzer.py --config configs/config.example.json --dry-run
```

Full run:

```bash
python scripts/youtube_kol_chain_analyzer.py --config configs/config.example.json
```

## Suggested Report Angle

Do not write the report as “who has more videos.” Frame it as:

> YouTube creator-channel competition is not only about how many creators a brand uses, but whether the video traffic is connected to a clear conversion path: download, purchase, invite code, discount code, referral trace, or social/private consultation.

Focus on:

1. official videos vs KOL videos;
2. conversion-chain clarity;
3. creator overlap across brands;
4. whether brand videos perform above/below each channel's normal videos;
5. what UgPhone can standardize in future creator cooperation, such as CTA templates, landing pages, invite codes, and tracking links.
