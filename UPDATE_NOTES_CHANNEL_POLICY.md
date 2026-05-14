# Channel policy update

This update changes channel classification rules for YouTube KOL conversion-chain analysis.

## New policy

1. Treat these accounts as official accounts, not KOL and not dealer/agent:
   - @ugphone-indonesia
   - @redfinger888
   - @ugphonejp
   - @ugphonevn
   - @ugphonevietnam
   - @ugphone_kr

2. Remove these accounts from target-brand analysis:
   - @botcloudphone
   - @maxcloudphone

They are treated as small cloud-phone competitors rather than downstream channels of UgPhone/RF/LD/VS. Their rows are excluded from clean outputs and written to `excluded_channels.csv`.

3. Keep `dealer_or_agent` only for accounts that are explicitly treated as channel/dealer accounts. Current default only keeps @vsphone233 in this bucket.

## Output changes

- `official_videos_clean.csv` now includes regional official / official-like accounts listed above.
- `kol_videos_clean.csv` excludes all official accounts and excluded small-competitor accounts.
- `managed_videos_clean.csv` contains dealer/agent rows only, not official-like rows.
- `excluded_channels.csv` contains rows removed by handle/name exclusion rules.

## Recommended historical cleaning

Run `scripts/clean_existing_youtube_outputs.py` once per month folder, not on the 8-month parent folder, if you need monthly outputs kept separate.
