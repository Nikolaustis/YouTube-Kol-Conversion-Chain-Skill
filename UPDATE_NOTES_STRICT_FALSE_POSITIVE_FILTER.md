# YouTube KOL Conversion Chain Analyzer

This Skill collects and cleans public YouTube Data API v3 data for RF, LDCloud, UgPhone, and VSPhone KOL/creator-channel analysis.

It is designed for the research question:

> How do cloud-phone competitors use YouTube creator videos to drive downloads, purchase pages, invite codes, discount codes, referral traces, social/private redirects, and other conversion paths?

## Main workflow

### 1. Install requirements

```bash
pip install -r requirements.txt
```

### 2. Set YouTube API key

PowerShell:

```powershell
$env:YOUTUBE_API_KEY="YOUR_KEY"
```

Bash:

```bash
export YOUTUBE_API_KEY="YOUR_KEY"
```

### 3. Run monthly collection

Edit `configs/config.monthly.example.json` and set one month:

```json
"published_after": "2025-09-01T00:00:00Z",
"published_before": "2025-10-01T00:00:00Z"
```

Then run:

```bash
python scripts/youtube_kol_chain_analyzer.py --config configs/config.monthly.example.json --dry-run
python scripts/youtube_kol_chain_analyzer.py --config configs/config.monthly.example.json
```

### 4. Clean outputs

Clean one run folder, a parent folder of monthly runs, or a zip archive:

```bash
python scripts/clean_existing_youtube_outputs.py --input output --output output_cleaned --config configs/config.cleaning.example.json
```

The cleaner does not call YouTube API.

## Clean classification policy

Clean outputs use only three buckets:

| Bucket | Meaning | Main files |
|---|---|---|
| Official accounts | Official and regional official accounts for RF, LD, UgPhone, VSPhone | `official_videos_clean.csv`, `official_channel_summary_clean.csv` |
| Ordinary KOL/creators | Non-official third-party creators after false-positive cleaning | `kol_videos_clean.csv`, `creator_brand_summary_clean.csv` |
| Excluded/noise | Small competitors and false-positive matches | `excluded_channels.csv`, `dropped_false_positives.csv`, `review_videos.csv` |

There is no dealer/agent/managed-channel reporting bucket. Do not use old `managed_*` outputs if they exist in previous folders.

## Important output files

After collection:

| File | Meaning |
|---|---|
| `videos.csv` | Raw collected video rows. |
| `kol_videos.csv` | Raw non-official videos from the collector. Must be cleaned before reporting. |
| `official_videos.csv` | Official uploads recognized by config. |
| `conversion_paths.csv` | Raw link/code/CTA extraction. |
| `channel_baselines.csv` | Raw channel baseline and performance index. |
| `youtube_kol_conversion_report.xlsx` | Raw Excel report. |

After cleaning:

| File | Meaning |
|---|---|
| `videos_clean.csv` | Clean accepted rows. |
| `kol_videos_clean.csv` | Clean ordinary KOL rows only. |
| `official_videos_clean.csv` | Official and regional official rows. |
| `dropped_false_positives.csv` | Rows removed by strong false-positive cleaning. |
| `excluded_channels.csv` | Excluded small competitors such as `@botcloudphone` and `@maxcloudphone`. |
| `review_videos.csv` | Ambiguous rows for manual review. |
| `brand_summary_clean.csv` | Clean brand-level summary. |
| `creator_brand_summary_clean.csv` | Clean KOL `channel × brand` summary. |
| `official_channel_summary_clean.csv` | Clean official account summary. |
| `youtube_kol_conversion_report_clean.xlsx` | Clean Excel report for analysis. |

## Strong cleaning logic

The cleaner addresses common false positives:

- `VSPhone` rows now require exact `VSPhone` / `vsphone.com` evidence in visible title, description, channel, or URL fields. Separated `VS Phone` is treated as ambiguous and rejected by default, because it frequently means ordinary `PC vs phone` / `iPad vs phone` comparison content.
- `Redfinger` rows require official domain evidence or exact `redfinger` plus cloud-phone / AFK / code context. Spaced `Red Finger` is treated as ambiguous and rejected by default, because it frequently refers to games or unrelated entertainment content.
- `LD Cloud` without cloud-phone context is marked as review.
- Regional brand accounts such as `@ugphone-indonesia`, `@ugphonejp`, `@ugphonevn`, and `@redfinger888` are counted as official accounts.
- `@botcloudphone` and `@maxcloudphone` are excluded as small competitors, not treated as downstream channels.

You can edit `configs/config.cleaning.example.json` to add more official or excluded accounts.


## Web report website

This package now includes a report-style website at:

```text
index.html
```

To make the website read monthly existing data, create a `Data` folder in the Skill root:

```text
Data/
  2025_05/
  2025_06/
  ...
  2026_04/
```

Then generate website data:

```bash
python scripts/build_web_data.py --data Data
```

Open `index.html`, or run:

```bash
python scripts/serve_web.py
```

and visit `http://localhost:8000`.

See `docs/web_report_guide.md` for details.

## Web data source priority

The report website now prioritizes the statistics workbook in `Data/`, for example:

```bash
python scripts/build_web_data.py --data Data
```

If `Data/youtube_kol_web_data_statistics.xlsx` or another compatible `Data/*.xlsx` exists, the builder reads that workbook directly and generates `js/generated-data.js`. If no compatible workbook is found, it falls back to monthly `Data/YYYY_MM/*.csv` files.


## 2026-05 UI text / exposure tooltip / radar scale update

本版本增加了三个网页编辑与可视化改动：

1. 网页固定文字集中到 `js/copy.js`
   - 页面标题、副标题、图表标题、说明文案、部分固定标签都可以直接在 `js/copy.js` 中改。
   - 数据值仍来自 `js/generated-data.js`，由 `scripts/build_web_data.py` 从 `Data/youtube_kol_web_data_statistics.xlsx` 生成。

2. 曝光层图表增大并支持悬停查看明细
   - 月度趋势两张图改为更大面积展示。
   - 鼠标悬停在某个月份区域，可看到四家品牌该月的 KOL 视频数或频道数。
   - 频道订阅数分布图的每个色块支持悬停，显示“该区间频道数量 / 该品牌频道总数 / 占比”。
   - 为支持此功能，`build_web_data.py` 会从 `04_Subscriber_Dist` 读取 `channel_count` 并生成 `distributionCounts`。

3. 转化层雷达图改为按指标独立缩放
   - 每个雷达轴使用该指标自己的上限，而不是统一 0–100。
   - 例如购买页直达率、App 导流率、短链率会使用更小的轴上限，避免视觉被压扁。
   - 鼠标悬停在雷达点上可以看到品牌、指标值和该轴上限。


## 2026-05 exposure median / radar axis tooltip update

本版本根据网页展示需求做了 3 个调整：

1. 曝光层「月度趋势」改为每行一张图
   - KOL 视频数、覆盖频道数、KOL 视频播放量中位数分别独占一行，避免两张图挤在一行里。
   - 图表高度和宽度已放大。

2. 曝光层新增「KOL 视频播放量中位数」
   - `build_web_data.py` 会在读取 xlsx 的同时，从 `Data/YYYY_MM/kol_videos_clean.csv` 或 `kol_videos.csv` 中计算每个品牌每月 KOL 视频播放量中位数。
   - 生成字段：`monthlyMedianViews`。
   - 如果某个月没有对应 CSV，则该月该品牌显示 0。

3. 转化层雷达图支持轴悬停
   - 鼠标悬停到任一雷达轴或轴标签上，会显示四家品牌在该指标上的值，以及该轴上限。
   - 雷达点悬停仍保留单品牌单指标明细。


## 2026-05 radar axis hover fix

转化层雷达图的轴悬停层已调整到数据多边形和点的上方。现在鼠标放到某一条指标轴或轴标题附近时，会优先显示该指标下四家产品的全部数值，而不是只触发某一个品牌点位的 tooltip。


## 2026-05 strict collection validation update

Collection now runs with `strict_brand_filter: true` by default in example configs. The collector writes `dropped_search_false_positives.csv` for rows filtered immediately after YouTube hydration. This prevents false-positive VSPhone and Redfinger rows from entering raw `videos.csv`, `kol_videos.csv`, and `conversion_paths.csv` in the first place.
