#!/usr/bin/env python3
"""Clean already-collected YouTube KOL outputs without using YouTube API.

Default behavior is PER-FOLDER cleaning:
- input-root can contain multiple monthly/run folders;
- each folder is cleaned separately;
- outputs are written to output-dir/<source_folder_name>/;
- no cross-month merge is performed unless --also-merge is explicitly used.

Supported input per folder:
- videos.csv / conversion_paths.csv / channel_baselines.csv, or
- youtube_kol_conversion_report.xlsx with sheets:
  video_samples_all, conversion_paths, channel_baselines.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple
from urllib.parse import urlparse

import pandas as pd


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def norm_handle(h: Any) -> str:
    h = str(h or "").strip()
    if not h:
        return ""
    if h.startswith("https://www.youtube.com/") or h.startswith("https://youtube.com/"):
        h = h.rstrip("/").split("/")[-1]
    if not h.startswith("@"):
        h = "@" + h
    return h.lower()


def alias_pattern(alias: str) -> re.Pattern:
    # Exact phrase with flexible whitespace, avoiding matches inside longer words.
    parts = [re.escape(p) for p in str(alias).strip().split() if p]
    body = r"\s+".join(parts)
    return re.compile(rf"(?<![A-Za-z0-9]){body}(?![A-Za-z0-9])", re.I)


def alias_match(text: str, aliases: Sequence[str]) -> bool:
    text = str(text or "")
    return any(alias_pattern(a).search(text) for a in aliases if a)


def extract_urls(text: str) -> List[str]:
    urls: List[str] = []
    for m in re.finditer(r"https?://[^\s)\]}>\"']+", str(text or ""), flags=re.I):
        urls.append(m.group(0).rstrip(".,;:!?)]}>\"'"))
    return urls


def host(url: str) -> str:
    try:
        h = urlparse(url).netloc.lower()
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


def domain_match(text: str, domains: Sequence[str]) -> bool:
    for u in extract_urls(text):
        h = host(u)
        for d in domains:
            d = str(d).lower().strip()
            if d and (h == d or h.endswith("." + d)):
                return True
    return False


def truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def num(v: Any) -> float:
    try:
        if pd.isna(v):
            return 0.0
        return float(v)
    except Exception:
        return 0.0


def mean(vals: Sequence[Any]):
    clean = [float(v) for v in vals if pd.notna(v)]
    return sum(clean) / len(clean) if clean else None


def med(vals: Sequence[Any]):
    clean = sorted([float(v) for v in vals if pd.notna(v)])
    return clean[len(clean) // 2] if clean else None


def bool_rate(df: pd.DataFrame, col: str):
    if df.empty or col not in df.columns:
        return None
    return round(df[col].apply(truthy).mean(), 4)


def make_config_maps(config: Dict[str, Any]):
    brands = {b["brand"]: b for b in config.get("brands", [])}
    official_by_handle: Dict[str, str] = {}
    official_by_name: Dict[str, str] = {}
    for ch in config.get("official_channels", []):
        official_by_handle[norm_handle(ch.get("handle"))] = ch.get("brand")
        official_by_name[str(ch.get("channel_name", "")).strip().lower()] = ch.get("brand")
    return brands, official_by_handle, official_by_name


def safe_rel_name(root: Path, folder: Path) -> str:
    try:
        rel = folder.relative_to(root)
        name = "__".join(rel.parts)
        return name or folder.name
    except Exception:
        return folder.name


def find_input_folders(root: Path) -> List[Path]:
    """Find folders that look like one YouTube output run/month."""
    candidates = []
    if (root / "videos.csv").exists() or (root / "youtube_kol_conversion_report.xlsx").exists():
        candidates.append(root)
    for p in root.rglob("videos.csv"):
        candidates.append(p.parent)
    for p in root.rglob("youtube_kol_conversion_report.xlsx"):
        candidates.append(p.parent)
    # Deduplicate and avoid nested duplicates where both csv and xlsx exist in same folder.
    seen = set()
    out = []
    for c in sorted(candidates):
        key = str(c.resolve())
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def read_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def read_sheet_if_exists(xlsx: Path, sheet_name: str) -> pd.DataFrame:
    if not xlsx.exists():
        return pd.DataFrame()
    try:
        return pd.read_excel(xlsx, sheet_name=sheet_name)
    except Exception:
        return pd.DataFrame()


def read_one_folder(folder: Path) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    videos = read_csv_if_exists(folder / "videos.csv")
    conversions = read_csv_if_exists(folder / "conversion_paths.csv")
    baselines = read_csv_if_exists(folder / "channel_baselines.csv")
    xlsx = folder / "youtube_kol_conversion_report.xlsx"
    if videos.empty:
        videos = read_sheet_if_exists(xlsx, "video_samples_all")
    if conversions.empty:
        conversions = read_sheet_if_exists(xlsx, "conversion_paths")
    if baselines.empty:
        baselines = read_sheet_if_exists(xlsx, "channel_baselines")
    return videos, conversions, baselines


def enrich_source(df: pd.DataFrame, folder: Path, root: Path) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["source_folder"] = str(folder)
    out["source_folder_name"] = safe_rel_name(root, folder)
    return out


def clean_videos(videos: pd.DataFrame, conversions: pd.DataFrame, config: Dict[str, Any]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    brands, official_by_handle, official_by_name = make_config_maps(config)
    if videos.empty:
        return videos.copy(), videos.copy()

    conv_cols = [
        "brand", "video_id", "all_urls", "official_urls", "buy_urls", "social_urls",
        "has_official_link", "has_buy_page", "has_referral_code", "has_discount_code",
        "has_social_link", "distribution_trace", "conversion_path_score"
    ]
    available = [c for c in conv_cols if c in conversions.columns]
    if not conversions.empty and {"brand", "video_id"}.issubset(conversions.columns):
        merged = videos.merge(conversions[available], on=["brand", "video_id"], how="left", suffixes=("", "_conv"))
    else:
        merged = videos.copy()

    keep_rows = []
    noise_rows = []
    for _, row in merged.iterrows():
        original_brand = str(row.get("brand", ""))
        ch_handle = norm_handle(row.get("channel_handle", ""))
        ch_name = str(row.get("channel_name", "")).strip().lower()
        official_brand = official_by_handle.get(ch_handle) or official_by_name.get(ch_name)
        text = "\n".join([
            str(row.get("title", "")),
            str(row.get("description", "")),
            str(row.get("all_urls", "")),
            str(row.get("official_urls", "")),
        ])
        clean_row = row.copy()
        clean_row["original_brand"] = original_brand
        clean_row["cleaning_rule_version"] = "2026-05-per-folder-strict-alias-domain-official-override"

        if official_brand:
            clean_row["brand"] = official_brand
            clean_row["clean_keep"] = True
            clean_row["clean_confidence"] = "high"
            clean_row["clean_reason"] = "official_channel_brand_override"
            keep_rows.append(clean_row)
            continue

        cfg = brands.get(original_brand, {})
        alias_ok = alias_match(text, cfg.get("aliases", []))
        domain_ok = domain_match(text, cfg.get("official_domains", []))
        if alias_ok or domain_ok:
            clean_row["clean_keep"] = True
            clean_row["clean_confidence"] = "high" if domain_ok else "medium_high"
            clean_row["clean_reason"] = "official_domain_match" if domain_ok else "exact_brand_alias_match"
            keep_rows.append(clean_row)
        else:
            clean_row["clean_keep"] = False
            clean_row["clean_confidence"] = "low"
            clean_row["clean_reason"] = "no_exact_brand_alias_or_official_domain"
            noise_rows.append(clean_row)

    clean = pd.DataFrame(keep_rows)
    noise = pd.DataFrame(noise_rows)
    if not clean.empty and {"brand", "video_id"}.issubset(clean.columns):
        clean = clean.drop_duplicates(subset=["brand", "video_id"], keep="first")
    if not noise.empty and {"original_brand", "video_id"}.issubset(noise.columns):
        noise = noise.drop_duplicates(subset=["original_brand", "video_id"], keep="first")
    return clean, noise


def recompute_brand_summary(clean: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if clean.empty or "brand" not in clean.columns:
        return pd.DataFrame(rows)
    for brand, g in clean.groupby("brand", dropna=False):
        official_flag = g.get("is_official_channel", pd.Series(False, index=g.index)).apply(truthy)
        rows.append({
            "brand": brand,
            "video_count": len(g),
            "unique_video_count": g["video_id"].nunique() if "video_id" in g.columns else len(g),
            "kol_video_count": int((~official_flag).sum()),
            "official_video_count": int(official_flag.sum()),
            "channel_count": g["channel_id"].nunique() if "channel_id" in g.columns else None,
            "kol_channel_count": g.loc[~official_flag, "channel_id"].nunique() if "channel_id" in g.columns else None,
            "official_channel_count": g.loc[official_flag, "channel_id"].nunique() if "channel_id" in g.columns else None,
            "total_views": int(g.get("views", pd.Series(0, index=g.index)).apply(num).sum()),
            "avg_views": round(g.get("views", pd.Series(dtype=float)).apply(num).mean(), 2) if "views" in g.columns else None,
            "median_views": med(g.get("views", pd.Series(dtype=float)).apply(num)) if "views" in g.columns else None,
            "avg_conversion_path_score": round(mean(g.get("conversion_path_score", pd.Series(dtype=float)).apply(num)) or 0, 4) if "conversion_path_score" in g.columns else None,
            "official_link_rate": bool_rate(g, "has_official_link"),
            "buy_page_direct_rate": bool_rate(g, "has_buy_page"),
            "referral_code_rate": bool_rate(g, "has_referral_code"),
            "discount_code_rate": bool_rate(g, "has_discount_code"),
            "social_redirect_rate": bool_rate(g, "has_social_link"),
            "distribution_trace_rate": bool_rate(g, "distribution_trace"),
        })
    return pd.DataFrame(rows)


def recompute_creator_summary(clean: pd.DataFrame, official_only: bool) -> pd.DataFrame:
    if clean.empty or "channel_id" not in clean.columns or "brand" not in clean.columns:
        return pd.DataFrame()
    flag = clean.get("is_official_channel", pd.Series(False, index=clean.index)).apply(truthy)
    df = clean[flag if official_only else ~flag].copy()
    if df.empty:
        return pd.DataFrame()
    brands_by_channel = df.groupby("channel_id")["brand"].apply(lambda s: " | ".join(sorted(set(map(str, s))))).to_dict()
    brand_counts = df.groupby("channel_id")["brand"].nunique().to_dict()
    rows = []
    for (ch, brand), g in df.groupby(["channel_id", "brand"], dropna=False):
        first = g.iloc[0]
        rows.append({
            "brand": brand,
            "channel_id": ch,
            "channel_name": first.get("channel_name", ""),
            "channel_handle": first.get("channel_handle", ""),
            "channel_url": first.get("channel_url", ""),
            "is_official_channel": official_only,
            "video_count_for_brand": len(g),
            "total_views_for_brand": int(g.get("views", pd.Series(0, index=g.index)).apply(num).sum()),
            "avg_views_for_brand": round(g.get("views", pd.Series(dtype=float)).apply(num).mean(), 2) if "views" in g.columns else None,
            "median_views_for_brand": med(g.get("views", pd.Series(dtype=float)).apply(num)) if "views" in g.columns else None,
            "avg_conversion_path_score": round(mean(g.get("conversion_path_score", pd.Series(dtype=float)).apply(num)) or 0, 4) if "conversion_path_score" in g.columns else None,
            "official_link_rate": bool_rate(g, "has_official_link"),
            "buy_page_direct_rate": bool_rate(g, "has_buy_page"),
            "referral_code_rate": bool_rate(g, "has_referral_code"),
            "discount_code_rate": bool_rate(g, "has_discount_code"),
            "social_redirect_rate": bool_rate(g, "has_social_link"),
            "distribution_trace_rate": bool_rate(g, "distribution_trace"),
            "brands_covered_by_this_channel_in_scope": brands_by_channel.get(ch, ""),
            "brand_count_for_this_channel_in_scope": brand_counts.get(ch, 0),
            "is_multi_brand_creator_in_scope": brand_counts.get(ch, 0) >= 2,
            "sample_video_urls": " | ".join(map(str, g.get("video_url", pd.Series(dtype=str)).dropna().head(5).tolist())) if "video_url" in g.columns else "",
        })
    return pd.DataFrame(rows)


def filter_baselines_for_clean(baselines: pd.DataFrame, clean: pd.DataFrame) -> pd.DataFrame:
    if baselines.empty or clean.empty or not {"brand", "video_id"}.issubset(baselines.columns) or not {"brand", "video_id"}.issubset(clean.columns):
        return pd.DataFrame()
    keys = set(zip(clean["brand"].astype(str), clean["video_id"].astype(str)))
    keep = baselines.apply(lambda r: (str(r.get("brand")), str(r.get("video_id"))) in keys, axis=1)
    return baselines[keep].drop_duplicates(subset=["brand", "video_id"], keep="first")


def write_one_cleaned(out: Path, clean: pd.DataFrame, noise: pd.DataFrame, baselines: pd.DataFrame, source_folder: Path) -> Dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    official_flag = clean.get("is_official_channel", pd.Series(False, index=clean.index)).apply(truthy) if not clean.empty else pd.Series(dtype=bool)
    kol = clean[~official_flag].copy() if not clean.empty else pd.DataFrame()
    official = clean[official_flag].copy() if not clean.empty else pd.DataFrame()
    brand_summary = recompute_brand_summary(clean)
    creator_summary = recompute_creator_summary(clean, official_only=False)
    official_summary = recompute_creator_summary(clean, official_only=True)
    cleaned_baselines = filter_baselines_for_clean(baselines, clean)

    clean.to_csv(out / "cleaned_videos.csv", index=False, encoding="utf-8-sig")
    kol.to_csv(out / "cleaned_kol_videos.csv", index=False, encoding="utf-8-sig")
    official.to_csv(out / "cleaned_official_videos.csv", index=False, encoding="utf-8-sig")
    noise.to_csv(out / "noise_videos.csv", index=False, encoding="utf-8-sig")
    brand_summary.to_csv(out / "cleaned_brand_summary.csv", index=False, encoding="utf-8-sig")
    creator_summary.to_csv(out / "cleaned_creator_brand_summary.csv", index=False, encoding="utf-8-sig")
    official_summary.to_csv(out / "cleaned_official_channel_summary.csv", index=False, encoding="utf-8-sig")
    if not cleaned_baselines.empty:
        cleaned_baselines.to_csv(out / "cleaned_channel_baselines.csv", index=False, encoding="utf-8-sig")

    summary = {
        "source_folder": str(source_folder),
        "output_folder": str(out),
        "raw_video_rows": int(len(clean) + len(noise)),
        "cleaned_video_rows": int(len(clean)),
        "noise_video_rows": int(len(noise)),
        "clean_rate": round(len(clean) / (len(clean) + len(noise)), 4) if (len(clean) + len(noise)) else None,
        "brand_counts_cleaned": clean["brand"].value_counts().to_dict() if not clean.empty and "brand" in clean.columns else {},
        "noise_counts_original_brand": noise["original_brand"].value_counts().to_dict() if not noise.empty and "original_brand" in noise.columns else {},
        "official_override_count": int((clean.get("clean_reason", pd.Series(dtype=str)) == "official_channel_brand_override").sum()) if not clean.empty else 0,
    }
    with (out / "cleaning_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    with pd.ExcelWriter(out / "cleaned_youtube_kol_report.xlsx", engine="openpyxl") as writer:
        brand_summary.to_excel(writer, sheet_name="cleaned_brand_summary", index=False)
        creator_summary.to_excel(writer, sheet_name="cleaned_creator_summary", index=False)
        official_summary.to_excel(writer, sheet_name="cleaned_official_summary", index=False)
        clean.to_excel(writer, sheet_name="cleaned_videos", index=False)
        kol.to_excel(writer, sheet_name="cleaned_kol_videos", index=False)
        official.to_excel(writer, sheet_name="cleaned_official_videos", index=False)
        noise.to_excel(writer, sheet_name="noise_videos", index=False)
        if not cleaned_baselines.empty:
            cleaned_baselines.to_excel(writer, sheet_name="cleaned_channel_baselines", index=False)
        pd.DataFrame([summary]).to_excel(writer, sheet_name="cleaning_summary", index=False)
        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for col in ws.columns:
                letter = col[0].column_letter
                max_len = max([len(str(c.value)) if c.value is not None else 0 for c in col[:200]] + [10])
                ws.column_dimensions[letter].width = min(max_len + 2, 60)
    return summary


def merge_cleaned(month_summaries: List[Dict[str, Any]], output_dir: Path) -> None:
    """Optional annual/combined merge, only when --also-merge is explicitly passed."""
    frames = []
    noises = []
    for s in month_summaries:
        folder = Path(s["output_folder"])
        cv = folder / "cleaned_videos.csv"
        nv = folder / "noise_videos.csv"
        if cv.exists():
            frames.append(pd.read_csv(cv, encoding="utf-8-sig"))
        if nv.exists():
            noises.append(pd.read_csv(nv, encoding="utf-8-sig"))
    if not frames:
        return
    merged_out = output_dir / "_merged_optional"
    merged_out.mkdir(parents=True, exist_ok=True)
    clean = pd.concat(frames, ignore_index=True)
    if {"brand", "video_id"}.issubset(clean.columns):
        clean = clean.drop_duplicates(subset=["brand", "video_id"], keep="first")
    noise = pd.concat(noises, ignore_index=True) if noises else pd.DataFrame()
    write_one_cleaned(merged_out, clean, noise, pd.DataFrame(), merged_out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-root", required=True, help="Folder containing four/monthly output folders, or a single output folder")
    ap.add_argument("--config", required=True)
    ap.add_argument("--output-dir", default="cleaned_output")
    ap.add_argument("--also-merge", action="store_true", help="Optional: also create _merged_optional after per-folder cleaning. Default is false.")
    args = ap.parse_args()

    root = Path(args.input_root)
    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    config = load_json(Path(args.config))

    input_folders = find_input_folders(root)
    if not input_folders:
        raise SystemExit(f"No input folders found under: {root}. Expected videos.csv or youtube_kol_conversion_report.xlsx.")

    summaries = []
    for folder in input_folders:
        videos, conversions, baselines = read_one_folder(folder)
        videos = enrich_source(videos, folder, root)
        conversions = enrich_source(conversions, folder, root)
        baselines = enrich_source(baselines, folder, root)
        if videos.empty:
            continue
        clean, noise = clean_videos(videos, conversions, config)
        out_name = safe_rel_name(root, folder)
        out_folder = output_root / out_name
        summary = write_one_cleaned(out_folder, clean, noise, baselines, folder)
        summaries.append(summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))

    index = {
        "mode": "per_folder_cleaning_default",
        "input_root": str(root),
        "output_root": str(output_root),
        "folder_count": len(summaries),
        "folders": summaries,
        "also_merge": bool(args.also_merge),
    }
    with (output_root / "cleaning_index.json").open("w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    if args.also_merge:
        merge_cleaned(summaries, output_root)

    print("\nDONE. Per-folder cleaned outputs are under:", output_root)
    print("No cross-folder merge was created unless --also-merge was used.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
