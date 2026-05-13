# YouTube KOL Skill Update - Noise Filtering

This package updates the YouTube KOL Conversion Chain Analyzer skill with:

1. stricter brand filtering for future YouTube API collection;
2. official-channel brand override;
3. a historical cleaner for already collected monthly outputs.

## Files included

```text
configs/config.example.json
configs/config.monthly.example.json
scripts/youtube_kol_chain_analyzer.py
scripts/clean_existing_youtube_outputs.py
docs/noise_cleaning_guide.md
UPDATE_NOTES_NOISE_FILTER.md
```

## Apply update

Extract this package into the original skill root and overwrite same-name files.

## Future monthly run

```bash
python scripts/youtube_kol_chain_analyzer.py --config configs/config.monthly.example.json --dry-run
python scripts/youtube_kol_chain_analyzer.py --config configs/config.monthly.example.json
```

## Clean already collected Jan-Apr data

Put `2026_01`, `2026_02`, `2026_03`, `2026_04` under one folder, then run:

```bash
python scripts/clean_existing_youtube_outputs.py \
  --input-root path/to/2026_01_04_outputs \
  --config configs/config.example.json \
  --output-dir output/cleaned_2026_01_04
```

Use the cleaned Excel file:

```text
cleaned_youtube_kol_report.xlsx
```
