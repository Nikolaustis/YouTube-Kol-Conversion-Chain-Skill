Use the updated YouTube KOL Conversion Chain Analyzer Skill.

Task:
Clean my already collected 2026 Jan-Apr monthly YouTube outputs and generate cleaned summaries.

Requirements:
- Do not call YouTube API.
- Use existing monthly output folders only.
- Apply official-channel brand override.
- Apply strict alias/domain filtering.
- Keep raw folders unchanged.
- Output cleaned Excel and CSV files.

Command template:

```bash
python scripts/clean_existing_youtube_outputs.py \
  --input-root <folder_containing_2026_01_2026_02_2026_03_2026_04> \
  --config configs/config.example.json \
  --output-dir output/cleaned_2026_01_04
```

After cleaning, summarize:
- `cleaning_summary.json`
- `cleaned_brand_summary.csv`
- `cleaned_creator_brand_summary.csv`
- `noise_videos.csv`

Focus on:
- how many rows were removed as noise;
- which original brands had the most noise;
- how official videos were corrected;
- final cleaned brand comparison.
