# Update Notes - Per-folder Cleaning Fix

This fixes the previous cleaning-script behavior.

## Previous behavior

The old script read all monthly folders under `--input-root` and cleaned them into one combined result.

## New behavior

The new script cleans each input folder separately by default.

For example, if your input is:

```text
monthly_outputs/
  2026_01/
  2026_02/
  2026_03/
  2026_04/
```

The output will be:

```text
output/cleaned_monthly/
  2026_01/
  2026_02/
  2026_03/
  2026_04/
  cleaning_index.json
```

No cross-folder merge is created unless `--also-merge` is passed.

## Replacement file

Replace:

```text
scripts/clean_existing_youtube_outputs.py
```

with the version in this package.

## Recommended command

```powershell
python scripts\clean_existing_youtube_outputs.py --input-root "C:\Users\Og\Desktop\youtube_monthly_outputs" --config configs\config.example.json --output-dir output\cleaned_monthly
```

## Optional combined output

Only use this if you intentionally want a total 1-4 month merged file:

```powershell
python scripts\clean_existing_youtube_outputs.py --input-root "C:\Users\Og\Desktop\youtube_monthly_outputs" --config configs\config.example.json --output-dir output\cleaned_monthly --also-merge
```
