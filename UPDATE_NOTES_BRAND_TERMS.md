# Update Notes - Brand Search Terms + Monthly Analysis Guide

This update changes `configs/config.example.json` so each brand has exact base brand-name search terms:

- UgPhone: `UgPhone`, `Ug Phone`
- VSPhone: `VSPhone`, `VS Phone`
- RedFinger: `RedFinger`, `Red Finger`
- LD Cloud: `LD Cloud`

The exact terms are prepended before longer scenario terms such as `cloud phone`, `AFK`, `Roblox`, and `discount code`.

A monthly template is also added:

- `configs/config.monthly.example.json`

The monthly template uses:

- `lookback_days = 31`
- `search_window_days = 7`

For exact calendar-month runs, copy it to your own config and set:

```json
"published_after": "2026-04-01T00:00:00Z",
"published_before": "2026-05-01T00:00:00Z"
```

Use month-start inclusive and next-month-start exclusive style for easier merging.
