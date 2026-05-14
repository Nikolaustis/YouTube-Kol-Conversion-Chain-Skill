# Update notes: remove managed/dealer bucket

This update changes the clean reporting policy to three buckets only:

1. `official`: official and regional official accounts.
2. `kol_creator`: ordinary third-party creators/KOLs.
3. `exclude_channel` / false positives: excluded small competitors and noise.

## Policy changes

- `@ugphone-indonesia`, `@redfinger888`, `@ugphonejp`, `@ugphonevn`, `@ugphonevietnam`, and `@ugphone_kr` are official accounts.
- `@botcloudphone` and `@maxcloudphone` are excluded small competitors.
- The cleaner no longer creates `managed_videos_clean.csv` or `managed_channel_summary_clean.csv`.
- `managed_channels` in old config files is ignored for backward compatibility.

## Reporting files to use

- `brand_summary_clean.csv`
- `creator_brand_summary_clean.csv`
- `official_channel_summary_clean.csv`
- `kol_videos_clean.csv`
- `official_videos_clean.csv`
- `excluded_channels.csv`
- `dropped_false_positives.csv`
- `review_videos.csv`

Ignore any old `managed_*` files from previous runs.
