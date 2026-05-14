#!/usr/bin/env python3
"""
Clean and recompute YouTube KOL Conversion Chain Analyzer outputs.

Use cases:
1) Clean already collected monthly output folders without calling YouTube API.
2) Rebuild yearly/quarterly clean summaries from multiple monthly runs.
3) Remove high-risk false positives caused by ambiguous brand terms such as
   "VS Phone" and "Red Finger".
4) Reclassify regional brand accounts as official accounts and remove
   non-target small competitor channels from KOL analysis.

Inputs can be:
- a parent directory containing month folders, each with videos.csv etc.
- one run folder containing videos.csv etc.
- a .zip archive containing such folders.

Outputs:
- videos_clean.csv
- kol_videos_clean.csv
- official_videos_clean.csv
- review_videos.csv
- dropped_false_positives.csv
- conversion_paths_clean.csv
- channel_baselines_clean.csv
- brand_summary_clean.csv
- creator_brand_summary_clean.csv
- official_channel_summary_clean.csv
- youtube_kol_conversion_report_clean.xlsx
- monthly_cleaning_summary.csv
- cleaning_run_summary.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

OFFICIAL_CHANNELS = {
    "@ugphone": {"brand": "Ug", "role": "official", "label": "UgPhone Cloud Phone"},
    "@ugphone_tw": {"brand": "Ug", "role": "official", "label": "Ugphone雲手機"},
    "@ugphoneth": {"brand": "Ug", "role": "official", "label": "UgPhone ประเทศไทย"},
    "@ugscript": {"brand": "Ug", "role": "official", "label": "UgScript"},
    "@ugphone-indonesia": {"brand": "Ug", "role": "official", "label": "UgPhone Indonesia"},
    "@ugphonejp": {"brand": "Ug", "role": "official", "label": "UgPhone 日本公式チャンネル"},
    "@ugphonevn": {"brand": "Ug", "role": "official", "label": "UgPhone Vietnam Shop / Vietnam"},
    "@ugphonevietnam": {"brand": "Ug", "role": "official", "label": "UgPhone Vietnam"},
    "@ugphone_kr": {"brand": "Ug", "role": "official", "label": "UgPhone Korea"},
    "@vsphoneofficial": {"brand": "VS", "role": "official", "label": "VSPhone Official"},
    "@ldcloud": {"brand": "LD", "role": "official", "label": "LDCloud"},
    "@redfingerofficial": {"brand": "RF", "role": "official", "label": "RedfingerOfficial"},
    "@redfinger-cloud": {"brand": "RF", "role": "official", "label": "Redfinger"},
    "@redfinger888": {"brand": "RF", "role": "official", "label": "Redfinger Cloud Phone 紅手指雲手機"},
}

# Accounts that are not ordinary KOLs but also should not be grouped with the
# target brands' official/distribution ecosystem. They are treated as non-target
# small competitors/noise and removed from clean outputs.
EXCLUDED_CHANNELS = {
    "@botcloudphone": {"brand": "", "role": "exclude_channel", "label": "Bot Cloud Phone", "reason": "small competitor, not target-brand downstream channel"},
    "@maxcloudphone": {"brand": "", "role": "exclude_channel", "label": "Max Cloud Phone", "reason": "small competitor, not target-brand downstream channel"},
}

CONTEXT_TERMS = [
    "cloud phone", "cloudphone", "cloud mobile", "android cloud", "emulator", "cloud emulator",
    "afk", "auto farm", "autofarm", "farming", "roblox", "sailor piece", "seal m",
    "multi-instance", "multi instance", "24/7", "挂机", "掛機", "云手机", "雲手機", "云机", "雲機",
    "điện thoại đám mây", "cloud gaming", "buy", "coupon", "discount", "referral", "redeem", "code",
    "vsphone.com", "ugphone.com", "ldcloud.net", "cloudemulator.net", "redfinger.com"
]

VS_BAD_PATTERNS = [
    r"\b(pc|computer|laptop|tablet|ipad|iphone|android|mobile|camera|handcam|mouse|controller|console)\s+vs\s+phone\b",
    r"\bvs\s+phone\b.*\b(pc|computer|laptop|tablet|ipad|iphone|android|mobile|camera|handcam|mouse|controller|console)\b",
    r"\b(stapler|hydraulic press|nokia|wife|husband|family|biwi|realistic forest|demo|asmr|meme|prank)\b.*\bvs\s+phone\b",
    r"\bvs\s+phone\b.*\b(stapler|hydraulic press|nokia|wife|husband|family|biwi|realistic forest|demo|asmr|meme|prank)\b",
]

RF_BAD_PATTERNS = [
    r"\bred\s*finger\b.*\b(color song|nursery|kids|baby|children|asmr|lemon|challenge|ring|makeup|horror|scp|garten|skibidi)\b",
    r"\b(color song|nursery|kids|baby|children|asmr|lemon|challenge|ring|makeup|horror|scp|garten|skibidi)\b.*\bred\s*finger\b",
]

LD_REVIEW_PATTERNS = [
    r"\bld\s+cloud\b"
]

BOOL_TRUE = {"true", "1", "yes", "y", "t"}


def norm_handle(handle: Any) -> str:
    h = str(handle or "").strip()
    if not h or h.lower() == "nan":
        return ""
    h = h.rstrip("/")
    if "/" in h and "youtube" in h:
        h = h.split("/")[-1]
    if not h.startswith("@"):
        h = "@" + h
    return h.lower()


def norm_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value)


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in BOOL_TRUE


def row_text(row: pd.Series) -> str:
    parts = [
        row.get("title", ""), row.get("description", ""), row.get("channel_name", ""),
        row.get("channel_handle", ""), row.get("query_keyword", ""), row.get("video_url", "")
    ]
    return "\n".join(norm_text(x) for x in parts).lower()


def content_text(row: pd.Series) -> str:
    """Text actually visible on the video/channel. Excludes query_keyword to avoid
    validating a false positive simply because it was found by a brand query."""
    parts = [
        row.get("title", ""), row.get("description", ""), row.get("channel_name", ""),
        row.get("channel_handle", ""), row.get("video_url", "")
    ]
    return "\n".join(norm_text(x) for x in parts).lower()


def has_any(text: str, terms: Sequence[str]) -> bool:
    return any(t.lower() in text for t in terms if t)


def re_any(text: str, patterns: Sequence[str]) -> bool:
    return any(re.search(p, text, flags=re.I) for p in patterns)


def load_optional_config(path: Optional[Path]) -> Dict[str, Any]:
    if not path:
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_channel_maps(config: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, str]]]:
    """Build official and excluded channel maps.

    Current reporting policy has only three buckets:
    1) official/regional official accounts,
    2) ordinary KOL/creator accounts,
    3) excluded non-target/noise accounts.

    There is intentionally no dealer/agent/managed bucket in the clean outputs.
    """
    official = dict(OFFICIAL_CHANNELS)
    excluded = dict(EXCLUDED_CHANNELS)
    for item in config.get("official_channels", []):
        h = norm_handle(item.get("handle"))
        if h:
            official[h] = {
                "brand": item.get("brand", ""),
                "role": "official",
                "label": item.get("channel_name", h),
            }
            excluded.pop(h, None)
    # managed_channels is ignored on purpose for backward compatibility.
    # Add accounts either to official_channels or excluded_channels instead.
    for item in config.get("excluded_channels", []):
        h = norm_handle(item.get("handle"))
        if h and h not in official:
            excluded[h] = {
                "brand": item.get("brand", ""),
                "role": "exclude_channel",
                "label": item.get("channel_name", h),
                "reason": item.get("reason", "excluded channel"),
            }
    return official, excluded

def classify_channel(row: pd.Series, official: Dict[str, Dict[str, str]], excluded: Dict[str, Dict[str, str]]) -> Tuple[str, str, str]:
    """Return channel_role, role_reason, role_label.

    Clean policy buckets:
    - official: official and regional official brand accounts
    - exclude_channel: small competitors / non-target accounts to remove
    - kol_creator: ordinary third-party creators
    """
    h = norm_handle(row.get("channel_handle"))
    name = norm_text(row.get("channel_name")).strip().lower()
    is_official_flag = parse_bool(row.get("is_official_channel", False))

    if h in official:
        return "official", "matched_official_handle", official[h].get("label", h)
    if h in excluded:
        return "exclude_channel", "matched_excluded_handle", excluded[h].get("label", h)

    # Name fallback for rows missing handles.
    official_name_rules = [
        "ugphone indonesia",
        "ugphone 日本",
        "ugphone japan",
        "redfinger cloud phone",
        "紅手指雲手機",
        "ugphone korea",
        "유지폰",
        "ugphone vietnam",
        "ugphone viet nam shop",
        "ugphone vietnam shop",
    ]
    for token in official_name_rules:
        if token.lower() in name:
            return "official", "matched_official_name", token

    excluded_name_rules = [
        "bot cloud phone",
        "max cloud phone",
    ]
    for token in excluded_name_rules:
        if token.lower() in name:
            return "exclude_channel", "matched_excluded_name", token

    if is_official_flag:
        return "official", "existing_official_flag", norm_text(row.get("official_config_name")) or norm_text(row.get("channel_name"))
    return "kol_creator", "default_kol", ""

def validate_brand(row: pd.Series, channel_role: str) -> Tuple[str, str]:
    """Return clean_status, clean_reason."""
    brand = norm_text(row.get("brand")).strip()
    text = content_text(row)

    # Keep official channels unless the brand column is empty. They are handled outside KOL summaries.
    if channel_role == "exclude_channel":
        return "drop_false_positive", "excluded_small_competitor_channel"
    if channel_role == "official":
        return "keep", "channel_role=official"

    if brand == "Ug":
        if re.search(r"\bug\s*phone\b", text, flags=re.I) or "ugphone" in text or "ugphone.com" in text:
            return "keep", "ugphone_exact_or_domain"
        return "review", "ug_brand_not_confirmed"

    if brand == "VS":
        if "vsphone" in text or "vsphone.com" in text or "#vsphone" in text:
            return "keep", "vsphone_exact_or_domain"
        if re.search(r"\bvs\s+phone\b", text, flags=re.I):
            if re_any(text, VS_BAD_PATTERNS):
                return "drop_false_positive", "ambiguous_vs_phone_bad_pattern"
            if has_any(text, CONTEXT_TERMS):
                return "keep", "vs_phone_with_cloud_context"
            return "drop_false_positive", "vs_phone_without_cloud_context"
        return "drop_false_positive", "vs_brand_not_confirmed"

    if brand == "RF":
        # Drop obvious non-cloud-phone meanings before accepting exact-looking hashtags such as #RedFingerLemon.
        if re_any(text, RF_BAD_PATTERNS):
            return "drop_false_positive", "ambiguous_red_finger_bad_pattern"
        if "cloudemulator.net" in text or "redfinger.com" in text:
            return "keep", "redfinger_domain"
        if "redfinger" in text:
            if has_any(text, CONTEXT_TERMS):
                return "keep", "redfinger_exact_with_cloud_context"
            return "review", "redfinger_exact_without_cloud_context"
        if re.search(r"\bred\s+finger\b", text, flags=re.I):
            if has_any(text, CONTEXT_TERMS):
                return "keep", "red_finger_with_cloud_context"
            return "drop_false_positive", "red_finger_without_cloud_context"
        return "drop_false_positive", "rf_brand_not_confirmed"

    if brand == "LD":
        if "ldcloud" in text or "ldcloud.net" in text:
            return "keep", "ldcloud_exact_or_domain"
        if re.search(r"\bld\s+cloud\b", text, flags=re.I):
            if has_any(text, CONTEXT_TERMS):
                return "keep", "ld_cloud_with_context"
            return "review", "ld_cloud_without_context"
        return "review", "ld_brand_not_confirmed"

    return "review", "unknown_brand"


def read_csv_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def read_first_existing(run_dir: Path, filenames: Sequence[str]) -> pd.DataFrame:
    for name in filenames:
        p = run_dir / name
        if p.exists():
            return read_csv_if_exists(p)
    return pd.DataFrame()


def has_video_file(path: Path) -> bool:
    return (path / "videos.csv").exists() or (path / "cleaned_videos.csv").exists() or (path / "videos_clean.csv").exists()


def discover_run_dirs(input_path: Path) -> Tuple[List[Path], Optional[tempfile.TemporaryDirectory]]:
    tmp = None
    root = input_path
    if input_path.is_file() and input_path.suffix.lower() == ".zip":
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        with zipfile.ZipFile(input_path, "r") as z:
            z.extractall(root)
    if has_video_file(root):
        return [root], tmp
    runs = set()
    for filename in ["videos.csv", "cleaned_videos.csv", "videos_clean.csv"]:
        runs.update(p.parent for p in root.rglob(filename))
    return sorted(runs), tmp


def safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def safe_rate(df: pd.DataFrame, col: str) -> Optional[float]:
    if df.empty or col not in df.columns:
        return None
    vals = df[col].map(parse_bool)
    return round(float(vals.mean()), 4) if len(vals) else None


def avg_numeric(df: pd.DataFrame, col: str) -> Optional[float]:
    if df.empty or col not in df.columns:
        return None
    vals = safe_numeric(df[col]).dropna()
    if vals.empty:
        return None
    return round(float(vals.mean()), 6)


def median_numeric(df: pd.DataFrame, col: str) -> Optional[float]:
    if df.empty or col not in df.columns:
        return None
    vals = safe_numeric(df[col]).dropna()
    if vals.empty:
        return None
    return round(float(vals.median()), 6)


def clean_one_run(run_dir: Path, official: Dict[str, Dict[str, str]], excluded: Dict[str, Dict[str, str]], include_review: bool) -> Dict[str, pd.DataFrame]:
    # Accept both raw analyzer outputs and earlier cleaned monthly outputs.
    videos = read_first_existing(run_dir, ["videos.csv", "cleaned_videos.csv", "videos_clean.csv", "video_samples_all.csv"])
    conv = read_first_existing(run_dir, ["conversion_paths.csv", "cleaned_conversion_paths.csv", "conversion_paths_clean.csv"])
    base = read_first_existing(run_dir, ["channel_baselines.csv", "cleaned_channel_baselines.csv", "channel_baselines_clean.csv"])

    # Some older cleaned folders contain conversion fields directly in cleaned_videos.csv
    # but do not include conversion_paths.csv. In that case, use video rows as a fallback
    # conversion table so rate metrics can still be recomputed.
    conversion_cols = {
        "has_any_link", "has_official_link", "has_buy_page", "has_app_store_link",
        "has_referral_code", "has_discount_code", "has_shortlink", "has_social_link",
        "distribution_trace", "conversion_path_score", "brand", "video_id"
    }
    if conv.empty and not videos.empty and {"brand", "video_id"}.issubset(videos.columns):
        available = [c for c in videos.columns if c in conversion_cols or c in ["video_url", "title", "channel_id", "channel_name", "channel_handle", "channel_url"]]
        conv = videos[available].copy()

    if videos.empty:
        return {"videos": videos, "conversion": conv, "baselines": base}

    roles, role_reasons, role_labels, statuses, reasons = [], [], [], [], []
    for _, row in videos.iterrows():
        role, role_reason, role_label = classify_channel(row, official, excluded)
        status, reason = validate_brand(row, role)
        roles.append(role)
        role_reasons.append(role_reason)
        role_labels.append(role_label)
        statuses.append(status)
        reasons.append(reason)
    videos = videos.copy()
    videos["channel_role"] = roles
    videos["channel_role_reason"] = role_reasons
    videos["channel_role_label"] = role_labels
    videos["clean_status"] = statuses
    videos["clean_reason"] = reasons
    videos["is_kol_eligible"] = videos["channel_role"].eq("kol_creator") & videos["clean_status"].eq("keep")
    videos["is_official"] = videos["channel_role"].eq("official")
    videos["clean_keep"] = videos["clean_status"].eq("keep") | (include_review & videos["clean_status"].eq("review"))

    # Keys for filtering related tables.
    clean_keys = set(zip(videos.loc[videos["clean_keep"], "brand"].astype(str), videos.loc[videos["clean_keep"], "video_id"].astype(str)))

    def filter_by_keys(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or "brand" not in df.columns or "video_id" not in df.columns:
            return df.copy()
        mask = [(str(b), str(v)) in clean_keys for b, v in zip(df["brand"], df["video_id"])]
        return df.loc[mask].copy()

    conv_clean = filter_by_keys(conv)
    base_clean = filter_by_keys(base)

    # Add performance quality labels.
    if not base_clean.empty:
        vc = videos[["brand", "video_id", "video_age_days", "clean_status", "channel_role"]].drop_duplicates()
        base_clean = base_clean.merge(vc, on=["brand", "video_id"], how="left", suffixes=("", "_video"))
        bcnt = safe_numeric(base_clean.get("baseline_video_count", pd.Series(dtype=str)))
        bvpd = safe_numeric(base_clean.get("baseline_avg_views_per_day", pd.Series(dtype=str)))
        age = safe_numeric(base_clean.get("video_age_days", pd.Series(dtype=str)))
        perf = safe_numeric(base_clean.get("performance_index", pd.Series(dtype=str)))
        ok = (bcnt >= 5) & (bvpd >= 5) & (age >= 7) & perf.notna()
        base_clean["performance_quality_status"] = ok.map(lambda x: "usable" if x else "weak_baseline_or_young_video")
        base_clean["clean_performance_index"] = perf.where(ok, pd.NA)

    return {"videos": videos, "conversion": conv_clean, "baselines": base_clean}


def summarize_brand(videos: pd.DataFrame, conv: pd.DataFrame, base: pd.DataFrame) -> pd.DataFrame:
    if videos.empty:
        return pd.DataFrame()
    conv_map = conv.set_index(["brand", "video_id"]) if not conv.empty and {"brand", "video_id"}.issubset(conv.columns) else pd.DataFrame()
    base_map = base.set_index(["brand", "video_id"]) if not base.empty and {"brand", "video_id"}.issubset(base.columns) else pd.DataFrame()
    rows = []
    for brand, g in videos.groupby("brand", dropna=False):
        keys = list(zip(g["brand"].astype(str), g["video_id"].astype(str)))
        conv_rows = conv_map.loc[conv_map.index.intersection(keys)].reset_index() if not conv_map.empty else pd.DataFrame()
        base_rows = base_map.loc[base_map.index.intersection(keys)].reset_index() if not base_map.empty else pd.DataFrame()
        views = safe_numeric(g.get("views", pd.Series(dtype=str))).fillna(0)
        rows.append({
            "brand": brand,
            "video_count": len(g),
            "kol_video_count": int(g["channel_role"].eq("kol_creator").sum()) if "channel_role" in g.columns else None,
            "official_video_count": int(g["channel_role"].eq("official").sum()) if "channel_role" in g.columns else None,
            "channel_count": g["channel_id"].nunique() if "channel_id" in g.columns else None,
            "kol_channel_count": g.loc[g["channel_role"].eq("kol_creator"), "channel_id"].nunique() if "channel_role" in g.columns and "channel_id" in g.columns else None,
            "official_channel_count": g.loc[g["channel_role"].eq("official"), "channel_id"].nunique() if "channel_role" in g.columns and "channel_id" in g.columns else None,
            "total_views": int(views.sum()),
            "avg_views": round(float(views.mean()), 2) if len(views) else None,
            "median_views": round(float(views.median()), 2) if len(views) else None,
            "avg_views_per_day": avg_numeric(g, "views_per_day"),
            "link_rate": safe_rate(conv_rows, "has_any_link"),
            "official_link_rate": safe_rate(conv_rows, "has_official_link"),
            "buy_page_direct_rate": safe_rate(conv_rows, "has_buy_page"),
            "app_store_rate": safe_rate(conv_rows, "has_app_store_link"),
            "referral_code_rate": safe_rate(conv_rows, "has_referral_code"),
            "discount_code_rate": safe_rate(conv_rows, "has_discount_code"),
            "social_redirect_rate": safe_rate(conv_rows, "has_social_link"),
            "shortlink_rate": safe_rate(conv_rows, "has_shortlink"),
            "distribution_trace_rate": safe_rate(conv_rows, "distribution_trace"),
            "avg_conversion_path_score": avg_numeric(conv_rows, "conversion_path_score"),
            "avg_clean_performance_index": avg_numeric(base_rows, "clean_performance_index"),
            "median_clean_performance_index": median_numeric(base_rows, "clean_performance_index"),
            "usable_performance_sample_count": int(safe_numeric(base_rows.get("clean_performance_index", pd.Series(dtype=str))).notna().sum()) if not base_rows.empty else 0,
            "top_channel_roles": json.dumps(Counter(g.get("channel_role", pd.Series(dtype=str))).most_common(5), ensure_ascii=False),
            "top_clean_reasons": json.dumps(Counter(g.get("clean_reason", pd.Series(dtype=str))).most_common(5), ensure_ascii=False),
        })
    return pd.DataFrame(rows)


def summarize_channel_brand(videos: pd.DataFrame, conv: pd.DataFrame, base: pd.DataFrame, roles: Sequence[str]) -> pd.DataFrame:
    if videos.empty:
        return pd.DataFrame()
    df = videos[videos["channel_role"].isin(roles)].copy() if "channel_role" in videos.columns else videos.copy()
    if df.empty:
        return pd.DataFrame()
    conv_map = conv.set_index(["brand", "video_id"]) if not conv.empty and {"brand", "video_id"}.issubset(conv.columns) else pd.DataFrame()
    base_map = base.set_index(["brand", "video_id"]) if not base.empty and {"brand", "video_id"}.issubset(base.columns) else pd.DataFrame()
    brands_by_channel = df.groupby("channel_id")["brand"].apply(lambda s: sorted(set(map(str, s)))).to_dict()
    rows = []
    for (channel_id, brand), g in df.groupby(["channel_id", "brand"], dropna=False):
        keys = list(zip(g["brand"].astype(str), g["video_id"].astype(str)))
        conv_rows = conv_map.loc[conv_map.index.intersection(keys)].reset_index() if not conv_map.empty else pd.DataFrame()
        base_rows = base_map.loc[base_map.index.intersection(keys)].reset_index() if not base_map.empty else pd.DataFrame()
        views = safe_numeric(g.get("views", pd.Series(dtype=str))).fillna(0)
        first = g.iloc[0]
        dates = pd.to_datetime(g.get("publish_date", pd.Series(dtype=str)), errors="coerce", utc=True).dropna()
        covered = brands_by_channel.get(channel_id, [])
        rows.append({
            "brand": brand,
            "channel_id": channel_id,
            "channel_name": first.get("channel_name", ""),
            "channel_handle": first.get("channel_handle", ""),
            "channel_url": first.get("channel_url", ""),
            "channel_role": first.get("channel_role", ""),
            "channel_role_label": first.get("channel_role_label", ""),
            "channel_subscribers": first.get("channel_subscribers", ""),
            "video_count_for_brand": len(g),
            "total_views_for_brand": int(views.sum()),
            "avg_views_for_brand": round(float(views.mean()), 2) if len(views) else None,
            "median_views_for_brand": round(float(views.median()), 2) if len(views) else None,
            "avg_views_per_day_for_brand": avg_numeric(g, "views_per_day"),
            "earliest_brand_video_date": dates.min().isoformat() if len(dates) else "",
            "latest_brand_video_date": dates.max().isoformat() if len(dates) else "",
            "avg_conversion_path_score": avg_numeric(conv_rows, "conversion_path_score"),
            "link_rate": safe_rate(conv_rows, "has_any_link"),
            "buy_page_direct_rate": safe_rate(conv_rows, "has_buy_page"),
            "referral_code_rate": safe_rate(conv_rows, "has_referral_code"),
            "discount_code_rate": safe_rate(conv_rows, "has_discount_code"),
            "social_redirect_rate": safe_rate(conv_rows, "has_social_link"),
            "distribution_trace_rate": safe_rate(conv_rows, "distribution_trace"),
            "avg_clean_performance_index": avg_numeric(base_rows, "clean_performance_index"),
            "median_clean_performance_index": median_numeric(base_rows, "clean_performance_index"),
            "brands_covered_by_this_channel_in_scope": " | ".join(covered),
            "brand_count_for_this_channel_in_scope": len(covered),
            "is_multi_brand_creator_in_scope": len(covered) >= 2,
            "sample_video_urls": " | ".join(g.get("video_url", pd.Series(dtype=str)).astype(str).head(5).tolist()),
        })
    return pd.DataFrame(rows)


def write_excel(path: Path, sheets: Dict[str, pd.DataFrame]) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, df in sheets.items():
            # Excel sheet names cannot exceed 31 chars.
            sheet = name[:31]
            df.to_excel(writer, sheet_name=sheet, index=False)
        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            if ws.max_row and ws.max_column:
                ws.auto_filter.ref = ws.dimensions
            for col in ws.columns:
                letter = col[0].column_letter
                values = [len(str(c.value)) if c.value is not None else 0 for c in col[:200]]
                ws.column_dimensions[letter].width = min(max(values + [10]) + 2, 60)


def main() -> int:
    ap = argparse.ArgumentParser(description="Clean existing YouTube KOL analyzer outputs without using YouTube API")
    ap.add_argument("--input", required=True, help="Run folder, parent folder with monthly folders, or zip archive")
    ap.add_argument("--output", required=True, help="Output folder for cleaned combined results")
    ap.add_argument("--config", default=None, help="Optional cleaning config JSON")
    ap.add_argument("--include-review", action="store_true", help="Include review rows in clean summaries. Default: strict; review rows are excluded.")
    args = ap.parse_args()

    input_path = Path(args.input)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    config = load_optional_config(Path(args.config)) if args.config else {}
    official, excluded = build_channel_maps(config)

    run_dirs, tmp = discover_run_dirs(input_path)
    if not run_dirs:
        raise SystemExit(f"No videos.csv / cleaned_videos.csv / videos_clean.csv found under {input_path}")

    all_videos, all_conv, all_base = [], [], []
    monthly_rows = []
    for run_dir in run_dirs:
        result = clean_one_run(run_dir, official, excluded, include_review=args.include_review)
        videos, conv, base = result["videos"], result["conversion"], result["baselines"]
        if videos.empty:
            continue
        run_name = run_dir.name
        videos["source_run"] = run_name
        if not conv.empty:
            conv["source_run"] = run_name
        if not base.empty:
            base["source_run"] = run_name
        all_videos.append(videos)
        all_conv.append(conv)
        all_base.append(base)
        monthly_rows.append({
            "source_run": run_name,
            "raw_video_rows": len(videos),
            "clean_keep_rows": int(videos["clean_keep"].sum()),
            "kol_clean_rows": int((videos["clean_keep"] & videos["channel_role"].eq("kol_creator")).sum()),
            "official_rows": int((videos["clean_keep"] & videos["channel_role"].eq("official")).sum()),
            "excluded_channel_rows": int(videos["channel_role"].eq("exclude_channel").sum()),
            "drop_false_positive_rows": int(videos["clean_status"].eq("drop_false_positive").sum()),
            "review_rows": int(videos["clean_status"].eq("review").sum()),
            "drop_reasons": json.dumps(Counter(videos.loc[videos["clean_status"].eq("drop_false_positive"), "clean_reason"]).most_common(10), ensure_ascii=False),
        })

    videos_all = pd.concat(all_videos, ignore_index=True) if all_videos else pd.DataFrame()
    conv_all = pd.concat(all_conv, ignore_index=True) if all_conv else pd.DataFrame()
    base_all = pd.concat(all_base, ignore_index=True) if all_base else pd.DataFrame()

    # Deduplicate across months/runs using brand + video_id, keeping latest source occurrence.
    if not videos_all.empty and {"brand", "video_id"}.issubset(videos_all.columns):
        videos_all = videos_all.drop_duplicates(subset=["brand", "video_id"], keep="last")
    if not conv_all.empty and {"brand", "video_id"}.issubset(conv_all.columns):
        conv_all = conv_all.drop_duplicates(subset=["brand", "video_id"], keep="last")
    if not base_all.empty and {"brand", "video_id"}.issubset(base_all.columns):
        base_all = base_all.drop_duplicates(subset=["brand", "video_id"], keep="last")

    clean_videos = videos_all[videos_all["clean_keep"]].copy() if not videos_all.empty else pd.DataFrame()
    kol_videos = clean_videos[clean_videos["channel_role"].eq("kol_creator")].copy() if not clean_videos.empty else pd.DataFrame()
    official_videos = clean_videos[clean_videos["channel_role"].eq("official")].copy() if not clean_videos.empty else pd.DataFrame()
    dropped = videos_all[videos_all["clean_status"].eq("drop_false_positive")].copy() if not videos_all.empty else pd.DataFrame()
    excluded_videos = videos_all[videos_all["channel_role"].eq("exclude_channel")].copy() if not videos_all.empty else pd.DataFrame()
    review = videos_all[videos_all["clean_status"].eq("review")].copy() if not videos_all.empty else pd.DataFrame()

    clean_keys = set(zip(clean_videos.get("brand", pd.Series(dtype=str)).astype(str), clean_videos.get("video_id", pd.Series(dtype=str)).astype(str)))
    def by_keys(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or not {"brand", "video_id"}.issubset(df.columns):
            return df.copy()
        mask = [(str(b), str(v)) in clean_keys for b, v in zip(df["brand"], df["video_id"])]
        return df.loc[mask].copy()
    conv_clean = by_keys(conv_all)
    base_clean = by_keys(base_all)

    brand_summary = summarize_brand(clean_videos, conv_clean, base_clean)
    creator_summary = summarize_channel_brand(clean_videos, conv_clean, base_clean, roles=["kol_creator"])
    official_summary = summarize_channel_brand(clean_videos, conv_clean, base_clean, roles=["official"])
    monthly_summary = pd.DataFrame(monthly_rows)

    outputs = {
        "videos_clean.csv": clean_videos,
        "kol_videos_clean.csv": kol_videos,
        "official_videos_clean.csv": official_videos,
        "review_videos.csv": review,
        "dropped_false_positives.csv": dropped,
        "excluded_channels.csv": excluded_videos,
        "conversion_paths_clean.csv": conv_clean,
        "channel_baselines_clean.csv": base_clean,
        "brand_summary_clean.csv": brand_summary,
        "creator_brand_summary_clean.csv": creator_summary,
        "official_channel_summary_clean.csv": official_summary,
        "monthly_cleaning_summary.csv": monthly_summary,
    }
    for name, df in outputs.items():
        df.to_csv(output / name, index=False, encoding="utf-8-sig")

    run_summary = {
        "input": str(input_path),
        "output": str(output),
        "run_dirs_found": [str(p) for p in run_dirs],
        "include_review": args.include_review,
        "raw_video_rows_after_dedupe": len(videos_all),
        "clean_video_rows": len(clean_videos),
        "kol_video_rows_clean": len(kol_videos),
        "official_video_rows_clean": len(official_videos),
        "dropped_false_positive_rows": len(dropped),
        "excluded_channel_rows": len(excluded_videos),
        "review_rows": len(review),
        "cleaning_policy": "strict: review rows excluded unless --include-review is passed",
    }
    (output / "cleaning_run_summary.json").write_text(json.dumps(run_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    excel_sheets = {
        "brand_summary_clean": brand_summary,
        "creator_brand_summary_clean": creator_summary,
        "official_channel_summary_clean": official_summary,
        "video_samples_all_clean": clean_videos,
        "kol_videos_clean": kol_videos,
        "official_videos_clean": official_videos,
        "conversion_paths_clean": conv_clean,
        "channel_baselines_clean": base_clean,
        "review_videos": review,
        "dropped_false_positives": dropped,
        "excluded_channels": excluded_videos,
        "monthly_cleaning_summary": monthly_summary,
        "cleaning_run_summary": pd.DataFrame([run_summary]),
    }
    write_excel(output / "youtube_kol_conversion_report_clean.xlsx", excel_sheets)

    if tmp is not None:
        tmp.cleanup()

    print(json.dumps(run_summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
