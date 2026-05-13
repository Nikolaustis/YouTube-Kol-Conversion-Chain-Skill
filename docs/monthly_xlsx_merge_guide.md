# XLSX Sheet Guide and Monthly Merge Rules

The Excel output `youtube_kol_conversion_report.xlsx` contains these sheets.

## Sheets and meanings

| Sheet | Meaning | Best use |
|---|---|---|
| `brand_summary` | Brand-level aggregate metrics for the current run. | Quick one-run overview. |
| `creator_brand_summary` | KOL/creator aggregation at `channel × brand` level. Official channels are removed. | Find which creators served which brands, multi-brand creators, creator-level conversion signal. |
| `official_channel_summary` | Official-channel aggregation at `channel × brand` level. | Compare official accounts' content and CTA/link strategy. |
| `video_samples_all` | All collected video rows. One video can appear once per matched brand. | Main raw table for cross-month merging. |
| `kol_videos` | Non-official creator/KOL videos only. | Main KOL video-level raw data. |
| `official_videos` | Official account videos only. | Official video raw data. |
| `conversion_paths` | Link, CTA, invite/discount/referral/social/private redirect fields. | Main raw table for conversion-chain analysis. |
| `channel_baselines` | Channel baseline comparison for brand-video performance index. | Analyze whether brand videos outperform or underperform each channel's normal videos. |
| `run_summary` | Run metadata: date range, counts, quota estimate, status. | Audit and trace each monthly run. |

## If you run once per month, which sheets should be merged directly?

These are raw or near-raw sheets. You can concatenate 12 monthly files and then deduplicate:

1. `video_samples_all`
2. `kol_videos`
3. `official_videos`
4. `conversion_paths`
5. `channel_baselines`
6. `run_summary`

Recommended dedupe keys:

| Sheet | Dedupe key |
|---|---|
| `video_samples_all` | `brand + video_id` |
| `kol_videos` | `brand + video_id` |
| `official_videos` | `brand + video_id` |
| `conversion_paths` | `brand + video_id` |
| `channel_baselines` | `brand + video_id` |
| `run_summary` | keep all monthly rows; do not dedupe unless rerunning the same month |

## Which sheets must be recalculated after combining 12 months?

These are aggregate sheets. Do not simply add monthly rows together as the final annual result:

1. `brand_summary`
2. `creator_brand_summary`
3. `official_channel_summary`

Reason:

- counts may duplicate the same video if it appears in multiple month runs;
- `channel_count`, `kol_channel_count`, and `official_channel_count` must be recalculated from unique channel IDs;
- rates such as `referral_code_rate`, `buy_page_direct_rate`, `social_redirect_rate`, and `distribution_trace_rate` must be recalculated from deduplicated video rows;
- averages such as `avg_conversion_path_score` and `avg_performance_index` should be recomputed from underlying video rows, not averaged from monthly summaries;
- `is_multi_brand_creator_in_scope` must be recalculated across the full 12-month window.

## Recommended annual workflow

1. Run 12 monthly jobs.
2. Put all monthly xlsx/csv outputs into one folder.
3. Concatenate and dedupe raw sheets:
   - `video_samples_all`
   - `conversion_paths`
   - `channel_baselines`
4. Split official/KOL again by `is_official_channel` if needed.
5. Recalculate:
   - annual `brand_summary`
   - annual `creator_brand_summary`
   - annual `official_channel_summary`
6. Use annual summaries for final reporting.

## Most important annual metrics to recompute

Brand level:

- unique video count
- KOL video count
- official video count
- unique channel count
- total views
- average / median views
- average conversion path score
- invite/referral/code rate
- discount code rate
- buy-page direct rate
- app-store redirect rate
- social/private redirect rate
- distribution trace rate
- average brand-video performance index

Creator/channel level:

- `channel × brand` video count
- total views by `channel × brand`
- latest/earliest brand video date
- average conversion path score
- referral/discount/social/distribution trace rates
- average performance index
- all brands covered by the same channel
- whether the creator is multi-brand in the annual scope

## Important caution

Monthly API runs are practical for quota control, but YouTube search discovery is not guaranteed to return every public video in the entire platform. Treat the dataset as a structured public-signal sample, not as absolute full-platform truth.
