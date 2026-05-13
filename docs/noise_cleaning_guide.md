# Per-folder Noise Cleaning Guide

## Important change

The cleaning script now cleans each monthly/run folder separately by default.
It does **not** merge your four folders unless you explicitly add `--also-merge`.

This is the correct workflow when you have four folders such as:

```text
monthly_outputs/
  2026_01/
  2026_02/
  2026_03/
  2026_04/
```

Run:

```powershell
python scripts\clean_existing_youtube_outputs.py --input-root "C:\path\to\monthly_outputs" --config configs\config.example.json --output-dir output\cleaned_monthly
```

Output:

```text
output/cleaned_monthly/
  2026_01/
    cleaned_youtube_kol_report.xlsx
    cleaned_videos.csv
    cleaned_kol_videos.csv
    cleaned_official_videos.csv
    noise_videos.csv
    cleaning_summary.json

  2026_02/
    cleaned_youtube_kol_report.xlsx
    ...

  2026_03/
    ...

  2026_04/
    ...

  cleaning_index.json
```

## What gets cleaned

The script keeps a video row if:

1. it is from a configured official channel, in which case brand ownership is forced by official channel config;
2. or the non-official video title/description/link text contains exact brand aliases;
3. or the non-official video description/link text contains the brand's official domain.

Otherwise it goes to `noise_videos.csv`.

## What to analyze after cleaning

For each month, use that month's:

- `cleaned_youtube_kol_report.xlsx`
- `cleaned_brand_summary`
- `cleaned_creator_summary`
- `cleaned_official_summary`
- `noise_videos`

Do not use merged output unless your analysis question is explicitly annual/combined.

## Optional merge

Only if you want a combined result, run:

```powershell
python scripts\clean_existing_youtube_outputs.py --input-root "C:\path\to\monthly_outputs" --config configs\config.example.json --output-dir output\cleaned_monthly --also-merge
```

This creates:

```text
output/cleaned_monthly/_merged_optional/
```

The default does not create this merged folder.
