Use the YouTube KOL cleaning script to clean existing monthly outputs separately.

Do not merge the folders.

Expected input structure:

```text
monthly_outputs/
  2026_01/
  2026_02/
  2026_03/
  2026_04/
```

Run:

```powershell
python scripts\clean_existing_youtube_outputs.py --input-root "C:\Users\Og\Desktop\youtube_monthly_outputs" --config configs\config.example.json --output-dir output\cleaned_monthly
```

After running, check each folder separately:

```text
output/cleaned_monthly/2026_01/cleaned_youtube_kol_report.xlsx
output/cleaned_monthly/2026_02/cleaned_youtube_kol_report.xlsx
output/cleaned_monthly/2026_03/cleaned_youtube_kol_report.xlsx
output/cleaned_monthly/2026_04/cleaned_youtube_kol_report.xlsx
```

Only use `--also-merge` if I explicitly ask for a combined annual/quarterly file.
