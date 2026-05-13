# Metric Dictionary

## Video-level publisher fields

| Field | Meaning |
|---|---|
| `channel_id` | YouTube channel ID. Stable identifier for the publisher. |
| `channel_name` | Channel title from YouTube channel metadata. |
| `channel_handle` | YouTube handle, usually from `snippet.customUrl` or official config. |
| `channel_url` | Canonical channel URL using channel_id. |
| `channel_subscribers` | Public subscriber count when available. |
| `channel_video_count` | Public channel video count when available. |
| `channel_total_views` | Public channel total view count when available. |
| `is_official_channel` | `true` if the video is published by one of the configured official channels. |
| `creator_type` | `official` or `kol/creator`. |
| `official_config_name` | Official channel name from config if matched. |
| `official_config_handle` | Official handle from config if matched. |
| `query_keyword` | Search keyword(s) that matched the video. Official uploads use `official_uploads`. |

## Conversion-chain fields

| Field | Meaning |
|---|---|
| `has_any_link` | Description contains at least one URL. |
| `has_official_link` | Description contains an official domain configured for the matched brand. |
| `has_buy_page` | URL path/query contains buy, purchase, pricing, checkout, recharge, etc. |
| `has_app_store_link` | Description links to Google Play, App Store, iTunes, or AppGallery. |
| `has_referral_code` | Description contains referral/invite/affiliate/partner/sponsor-like terms. |
| `has_discount_code` | Description contains coupon/discount/code-like terms in common languages. |
| `has_shortlink` | Description contains a shortlink or link-in-bio domain. |
| `has_social_link` | Description links to Discord, Telegram, WhatsApp, Facebook, Reddit, X/Twitter, or Instagram. |
| `distribution_trace` | Any referral, discount, reseller, distributor, agent, device-code, or similar trace is detected. |
| `landing_type` | Main redirect categories detected: buy_page, app_store, official_site, social/private, shortlink, other_link, none. |
| `conversion_path_score` | 0–3 score indicating conversion-chain clarity. |
| `cta_text` | Lines in description containing CTA / referral / code / distributor terms. |

## Conversion path score

| Score | Meaning |
|---:|---|
| 0 | No link, invite code, purchase guide, or social redirect found. |
| 1 | Brand name, official site, or app-store link exists, but conversion path is weak. |
| 2 | Official site, buy page, app store, or social/private redirect exists. |
| 3 | Referral/invite/discount/code trace, buy page, or clear purchase guide exists. |

## Brand-video performance index

Formula:

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

## Creator-brand summary

`creator_brand_summary.csv` is aggregated at `channel × brand` level for non-official creators only.

This means:

- If one channel posted only UgPhone videos, it has one row for `Ug`.
- If one channel posted UgPhone and VSPhone videos in the last 365 days, it has two rows: one for `Ug`, one for `VS`.
- `is_multi_brand_creator_in_scope=true` indicates that the same channel appeared under two or more brands within the current date range.

Important fields:

| Field | Meaning |
|---|---|
| `video_count_for_brand` | Number of videos this channel posted for this brand in the date range. |
| `total_views_for_brand` | Total views from this channel's videos for this brand. |
| `avg_conversion_path_score` | Average conversion-chain clarity score for this channel-brand pair. |
| `referral_code_rate` | Share of videos containing referral/invite-related terms. |
| `discount_code_rate` | Share of videos containing discount/coupon/code terms. |
| `social_redirect_rate` | Share of videos linking to social/private channels such as Telegram, Discord, WhatsApp. |
| `distribution_trace_rate` | Share of videos containing referral, discount, reseller, distributor, device-code, or agent-like traces. |
| `avg_performance_index` | Average brand-video performance index compared with this channel's non-brand baseline videos. |
| `brands_covered_by_this_channel_in_scope` | All brands matched by this channel in the current date range. |
| `is_multi_brand_creator_in_scope` | Whether the channel served multiple brands in the current date range. |

## Official-channel summary

`official_channel_summary.csv` uses the same `channel × brand` aggregation logic, but only includes configured official channels.

Use it to compare:

- whether official videos provide more complete links than KOL videos;
- which official accounts publish the most brand videos;
- which official accounts rely on app-store links, official pages, buy pages, or social redirects;
- how official-account video performance compares against each channel's recent non-brand baseline.
