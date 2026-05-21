#!/usr/bin/env python3
"""
YouTube KOL Conversion Chain Analyzer

Collects public YouTube Data API v3 video metadata for RF / LD / UgPhone / VSPhone,
separates official-channel videos from KOL/creator videos, extracts conversion-chain
signals from descriptions, and builds brand + creator/channel summaries.

Public data only. No login. No secret printing.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import re
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple
from urllib.parse import urlparse

import pandas as pd
import requests

try:
    from dotenv import load_dotenv
except Exception:  # optional
    load_dotenv = None

API_BASE = "https://www.googleapis.com/youtube/v3"
UTC = dt.timezone.utc

SHORTLINK_DOMAINS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "buff.ly", "cutt.ly",
    "rebrand.ly", "shorturl.at", "linktr.ee", "beacons.ai", "taplink.cc", "bio.link",
    "direct.me", "msha.ke", "solo.to"
}
SOCIAL_DOMAINS = {
    "discord.gg", "discord.com", "telegram.me", "t.me", "whatsapp.com", "wa.me",
    "facebook.com", "fb.com", "reddit.com", "twitter.com", "x.com", "instagram.com"
}
APP_STORE_DOMAINS = {"play.google.com", "apps.apple.com", "itunes.apple.com", "appgallery.huawei.com"}
BUY_PATH_KEYWORDS = [
    "buy", "purchase", "pricing", "price", "order", "checkout", "pay", "plans",
    "subscribe", "subscription", "vip", "recharge", "topup", "payment"
]
REFERRAL_TERMS = [
    "referral", "refer", "invite", "invitation", "affiliate", "partner", "commission",
    "ambassador", "sponsor", "sponsored", "promo", "promotion", "share"
]
DISCOUNT_TERMS = [
    "discount", "coupon", "voucher", "promo code", "promocode", "code", "邀请码",
    "優惠碼", "优惠码", "折扣码", "折扣碼", "คูปอง", "โค้ด", "mã giảm", "kode",
    "cupom", "código"
]
DISTRIBUTION_TERMS = [
    "reseller", "distributor", "dealer", "agent", "agency", "selling code", "redeem code",
    "device code", "code seller", "wholesale", "代购", "代購", "代理", "分销", "分銷",
    "销售", "銷售", "设备码", "設備碼", "兑换码", "兌換碼"
]
CTA_TERMS = [
    "download", "buy", "purchase", "use my code", "use code", "click", "join", "contact",
    "get", "try", "sign up", "register", "subscribe", "top up", "recharge",
    "下载", "購買", "购买", "使用我的", "加入", "联系", "聯繫", "注册", "註冊"
]

# Brand validation is intentionally stricter than search-term matching.
# Search queries can use broad terms, but rows are only kept when the video/channel
# text itself contains strong brand evidence. This prevents false positives such as
# generic "PC vs phone" videos being counted as VSPhone, or the game "Red Finger"
# being counted as Redfinger cloud phone.
VS_BAD_PATTERNS = [
    r"\b(pc|computer|laptop|tablet|ipad|iphone|android|mobile|camera|handcam|mouse|controller|console)\s+vs\s+phone\b",
    r"\bvs\s+phone\b.*\b(pc|computer|laptop|tablet|ipad|iphone|android|mobile|camera|handcam|mouse|controller|console)\b",
    r"\b(phone|ipad|iphone|samsung|vivo|oppo|redmi|realme|camera|battery|quality|recording|dollar)\b.*\bvs\b",
]
RF_BAD_PATTERNS = [
    r"\bred\s*finger\b.*\b(game|games|chapter|walkthrough|ending|boss|level|apk|mod|gameplay|roblox story|horror|scp|garten|skibidi|lemon|kids|nursery|color song|asmr|challenge|ring|makeup)\b",
    r"\b(game|games|chapter|walkthrough|ending|boss|level|apk|mod|gameplay|horror|scp|garten|skibidi|lemon|kids|nursery|color song|asmr|challenge|ring|makeup)\b.*\bred\s*finger\b",
]
RF_STRONG_CONTEXT_TERMS = [
    "cloud phone", "cloudphone", "cloud emulator", "cloudemulator", "android cloud",
    "雲手機", "云手机", "挂机", "掛機", "afk", "auto farm", "autofarm", "farming",
    "coupon", "discount", "referral", "invite", "promo code", "code",
    "cloudemulator.net", "redfinger.com"
]


def now_utc() -> dt.datetime:
    return dt.datetime.now(tz=UTC).replace(microsecond=0)


def iso_z(d: dt.datetime) -> str:
    return d.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso(s: str) -> dt.datetime:
    if not s:
        return now_utc()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return dt.datetime.fromisoformat(s).astimezone(UTC)


def safe_ts() -> str:
    return now_utc().strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)


def write_jsonl(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def chunks(seq: Sequence[Any], n: int) -> Iterable[Sequence[Any]]:
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def to_int(v: Any) -> Optional[int]:
    try:
        if v is None:
            return None
        return int(v)
    except Exception:
        return None


def normalize_handle(handle: str) -> str:
    h = (handle or "").strip()
    if not h:
        return ""
    if h.startswith("https://www.youtube.com/") or h.startswith("https://youtube.com/"):
        h = h.rstrip("/").split("/")[-1]
    if not h.startswith("@"):
        h = "@" + h
    return h


def video_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def channel_url(channel_id: str) -> str:
    return f"https://www.youtube.com/channel/{channel_id}" if channel_id else ""


def norm_domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def url_contains_domain(url: str, domains: Sequence[str]) -> bool:
    host = norm_domain(url)
    for d in domains:
        d = (d or "").lower().strip()
        if host == d or host.endswith("." + d):
            return True
    return False


def extract_urls(text: str) -> List[str]:
    if not text:
        return []
    urls = []
    for m in re.finditer(r"https?://[^\s)\]}>\"']+", text, flags=re.I):
        urls.append(m.group(0).rstrip(".,;:!?)]}>\"'"))
    return list(dict.fromkeys(urls))


def contains_any(text: str, terms: Sequence[str]) -> bool:
    t = (text or "").lower()
    return any((term or "").lower() in t for term in terms)


def find_lines_with_terms(text: str, terms: Sequence[str], max_lines: int = 6) -> str:
    lines = []
    for line in (text or "").splitlines():
        s = line.strip()
        if s and contains_any(s, terms):
            lines.append(s[:500])
            if len(lines) >= max_lines:
                break
    return " | ".join(lines)


def days_since(published_at: str, run_time: dt.datetime) -> float:
    try:
        return max((run_time - parse_iso(published_at)).total_seconds() / 86400.0, 0.001)
    except Exception:
        return 0.001


def date_windows(after_iso: str, before_iso: str, days: int) -> List[Tuple[str, str]]:
    after = parse_iso(after_iso)
    before = parse_iso(before_iso)
    step = dt.timedelta(days=max(1, int(days)))
    out = []
    cur = after
    while cur < before:
        nxt = min(cur + step, before)
        out.append((iso_z(cur), iso_z(nxt)))
        cur = nxt
    return out or [(after_iso, before_iso)]


def language_hint(text: str) -> str:
    t = text.lower()
    if re.search(r"[\u4e00-\u9fff]", t):
        return "zh"
    if re.search(r"[\u0e00-\u0e7f]", t):
        return "th"
    if any(w in t for w in ["cómo", "juego", "código", "gratis"]):
        return "es"
    if any(w in t for w in ["código", "grátis", "jogo", "telefone"]):
        return "pt"
    if any(w in t for w in ["mã", "điện thoại", "miễn phí"]):
        return "vi"
    if any(w in t for w in ["kode", "harga", "permainan"]):
        return "id"
    return "en_or_unknown"


def infer_content_type(title: str, desc: str) -> str:
    t = f"{title}\n{desc}".lower()
    if any(x in t for x in ["review", "test", "honest", "รีวิว", "reseña", "análise", "評測", "评测"]):
        return "review/test"
    if any(x in t for x in ["tutorial", "guide", "how to", "setup", "install", "วิธี", "cách", "教程", "教學", "como"]):
        return "tutorial/guide"
    if any(x in t for x in ["afk", "farm", "farming", "auto", "挂机", "掛機"]):
        return "afk/farming"
    if any(x in t for x in ["buy", "purchase", "price", "cheap", "discount", "coupon", "购买", "價格", "价格"]):
        return "purchase/price"
    if any(x in t for x in ["sponsored", "ad", "promo", "partner"]):
        return "promo/ad"
    return "unknown/general"


def infer_scene(title: str, desc: str, scene_terms: Sequence[str]) -> str:
    t = f"{title}\n{desc}".lower()
    scenes = []
    for s in scene_terms:
        if s.lower() in t:
            scenes.append(s)
    for key, label in [
        ("roblox", "Roblox"), ("seal m", "Seal M"), ("sailor piece", "Sailor Piece"),
        ("afk", "AFK"), ("cloud phone", "cloud phone")
    ]:
        if key in t:
            scenes.append(label)
    if "多开" in t or "多開" in t or "multi" in t:
        scenes.append("multi-instance")
    return "; ".join(list(dict.fromkeys(scenes))) or "unknown"


class YTClient:
    def __init__(self, api_key: str, sleep: float, retries: int, timeout: int):
        self.api_key = api_key
        self.sleep = sleep
        self.retries = retries
        self.timeout = timeout
        self.calls: List[Dict[str, Any]] = []
        self.units = 0

    def cost(self, endpoint: str) -> int:
        return 100 if endpoint == "search" else 1

    def get(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        params = {k: v for k, v in params.items() if v is not None and v != ""}
        params["key"] = self.api_key
        last = None
        for attempt in range(1, self.retries + 1):
            try:
                time.sleep(self.sleep)
                r = requests.get(f"{API_BASE}/{endpoint}", params=params, timeout=self.timeout)
                if r.status_code == 200:
                    self.calls.append({"method": endpoint, "status": "ok", "units_estimated": self.cost(endpoint)})
                    self.units += self.cost(endpoint)
                    return r.json()
                last = RuntimeError(f"HTTP {r.status_code}: {r.text[:800]}")
                if r.status_code in {403, 429, 500, 502, 503, 504} and attempt < self.retries:
                    time.sleep(1.5 * attempt)
                    continue
                raise last
            except Exception as exc:
                last = exc
                if attempt < self.retries:
                    time.sleep(1.5 * attempt)
                    continue
        self.calls.append({"method": endpoint, "status": "error", "units_estimated": self.cost(endpoint), "message": str(last)})
        self.units += self.cost(endpoint)
        raise RuntimeError(f"YouTube API {endpoint} failed: {last}")

    def preflight(self) -> bool:
        data = self.get("videos", {"part": "id", "id": "dQw4w9WgXcQ"})
        return bool(data.get("items"))

    def search_videos(self, q: str, max_results: int, after: str, before: str, region: Optional[str], lang: Optional[str], order: str) -> List[Dict[str, Any]]:
        out, token, remaining = [], None, max_results
        while remaining > 0:
            data = self.get("search", {
                "part": "snippet", "type": "video", "q": q, "maxResults": min(50, remaining),
                "order": order, "publishedAfter": after, "publishedBefore": before,
                "regionCode": region, "relevanceLanguage": lang, "pageToken": token,
            })
            items = data.get("items", [])
            out.extend(items)
            remaining -= len(items)
            token = data.get("nextPageToken")
            if not token or not items:
                break
        return out

    def videos_list(self, ids: Sequence[str]) -> List[Dict[str, Any]]:
        out = []
        for c in chunks(list(dict.fromkeys([x for x in ids if x])), 50):
            data = self.get("videos", {"part": "snippet,statistics,contentDetails", "id": ",".join(c)})
            out.extend(data.get("items", []))
        return out

    def channels_list(self, ids: Sequence[str]) -> List[Dict[str, Any]]:
        out = []
        for c in chunks(list(dict.fromkeys([x for x in ids if x])), 50):
            data = self.get("channels", {"part": "snippet,statistics,contentDetails", "id": ",".join(c)})
            out.extend(data.get("items", []))
        return out

    def channel_by_handle(self, handle: str) -> Optional[Dict[str, Any]]:
        data = self.get("channels", {"part": "snippet,statistics,contentDetails", "forHandle": normalize_handle(handle)})
        items = data.get("items", [])
        return items[0] if items else None

    def playlist_items(self, playlist_id: str, max_results: int) -> List[Dict[str, Any]]:
        out, token, remaining = [], None, max_results
        while remaining > 0:
            data = self.get("playlistItems", {
                "part": "snippet,contentDetails", "playlistId": playlist_id,
                "maxResults": min(50, remaining), "pageToken": token,
            })
            items = data.get("items", [])
            out.extend(items)
            remaining -= len(items)
            token = data.get("nextPageToken")
            if not token or not items:
                break
        return out


def channel_meta(ch: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    sn = ch.get("snippet", {})
    st = ch.get("statistics", {})
    cd = ch.get("contentDetails", {})
    custom_url = sn.get("customUrl", "")
    return {
        "channel_id": ch.get("id"),
        "title": sn.get("title", ""),
        "channel_handle": normalize_handle((cfg or {}).get("handle", "") or custom_url),
        "customUrl": custom_url,
        "country": sn.get("country", ""),
        "subscriberCount": to_int(st.get("subscriberCount")),
        "videoCount": to_int(st.get("videoCount")),
        "viewCount": to_int(st.get("viewCount")),
        "uploads_playlist": (cd.get("relatedPlaylists") or {}).get("uploads", ""),
        "official_config_name": (cfg or {}).get("channel_name", ""),
        "official_config_handle": normalize_handle((cfg or {}).get("handle", "")),
        "official_brand": (cfg or {}).get("brand", ""),
    }


def resolve_official_channels(client: YTClient, config: Dict[str, Any], log) -> Dict[str, Dict[str, Any]]:
    out = {}
    for cfg in config.get("official_channels", []):
        h = normalize_handle(cfg.get("handle", ""))
        try:
            ch = client.channel_by_handle(h)
        except Exception as exc:
            log(f"WARNING official handle resolve failed {h}: {exc}")
            ch = None
        if not ch:
            log(f"WARNING official handle not found: {h}")
            continue
        meta = channel_meta(ch, cfg)
        out[meta["channel_id"]] = meta
        log(f"Resolved official {cfg.get('brand')} {h} -> {meta['channel_id']} / {meta['title']}")
    return out


def visible_brand_text(title: str, desc: str, channel_name: str = "", channel_handle: str = "", urls: Sequence[str] = ()) -> str:
    return "\n".join([title or "", desc or "", channel_name or "", channel_handle or "", "\n".join(urls or [])]).lower()


def re_any(text: str, patterns: Sequence[str]) -> bool:
    return any(re.search(p, text, flags=re.I) for p in patterns)


def target_brand_match_status(brand: str, title: str, desc: str, channel_name: str = "", channel_handle: str = "", urls: Sequence[str] = ()) -> Tuple[bool, str]:
    """Validate whether a hydrated YouTube result really belongs to a target brand.

    Important: query_keyword is deliberately not part of this check. A video found by
    the query "VSPhone" or "RedFinger" is not enough; the visible video/channel text
    or URL must contain strong brand evidence.
    """
    text = visible_brand_text(title, desc, channel_name, channel_handle, urls)
    if brand == "Ug":
        if "ugphone" in text or "ugphone.com" in text or re.search(r"\bug\s*phone\b", text, flags=re.I):
            return True, "ugphone_exact_or_domain"
        return False, "ug_brand_not_confirmed"

    if brand == "LD":
        if "ldcloud" in text or "ldcloud.net" in text or re.search(r"\bld\s+cloud\b", text, flags=re.I):
            return True, "ldcloud_exact_or_domain"
        return False, "ld_brand_not_confirmed"

    if brand == "VS":
        # Do not accept separated "VS Phone" by itself. It is too ambiguous and
        # caused many false positives from generic phone-comparison videos.
        if "vsphone" in text or "vsphone.com" in text or "#vsphone" in text:
            return True, "vsphone_exact_or_domain"
        if re.search(r"\bvs\s+phone\b", text, flags=re.I):
            return False, "ambiguous_vs_phone_not_accepted"
        return False, "vs_brand_not_confirmed"

    if brand == "RF":
        if "cloudemulator.net" in text or "redfinger.com" in text:
            return True, "redfinger_domain"
        if re_any(text, RF_BAD_PATTERNS):
            return False, "red_finger_game_or_non_cloud_false_positive"
        if "redfinger" in text:
            if any(term in text for term in RF_STRONG_CONTEXT_TERMS):
                return True, "redfinger_exact_with_strong_context"
            return False, "redfinger_without_cloud_phone_context"
        if re.search(r"\bred\s+finger\b", text, flags=re.I):
            return False, "spaced_red_finger_ambiguous_not_accepted"
        return False, "rf_brand_not_confirmed"

    return False, "unknown_brand"


def collect_official_uploads(client: YTClient, official: Dict[str, Dict[str, Any]], after: str, before: str, max_per_channel: int, log) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Set[str]], Dict[Tuple[str, str], Set[str]]]:
    after_dt, before_dt = parse_iso(after), parse_iso(before)
    videos, vid_brands, queries = {}, defaultdict(set), defaultdict(set)
    for ch_id, meta in official.items():
        playlist = meta.get("uploads_playlist")
        if not playlist:
            continue
        try:
            items = client.playlist_items(playlist, max_per_channel)
        except Exception as exc:
            log(f"WARNING official uploads failed {ch_id}: {exc}")
            continue
        ids = []
        for it in items:
            vid = (it.get("contentDetails") or {}).get("videoId") or (((it.get("snippet") or {}).get("resourceId") or {}).get("videoId"))
            pub = (it.get("contentDetails") or {}).get("videoPublishedAt") or (it.get("snippet") or {}).get("publishedAt")
            if not vid or not pub:
                continue
            try:
                pdt = parse_iso(pub)
            except Exception:
                continue
            if after_dt <= pdt <= before_dt:
                ids.append(vid)
        if ids:
            for v in client.videos_list(ids):
                vid = v.get("id")
                videos[vid] = v
                brand = meta.get("official_brand")
                if brand:
                    vid_brands[vid].add(brand)
                    queries[(vid, brand)].add("official_uploads")
            log(f"Official uploads {meta.get('channel_handle')} in scope: {len(ids)}")
    return videos, vid_brands, queries


def analyze_conversion(title: str, desc: str, urls: Sequence[str], brand_domains: Sequence[str]) -> Dict[str, Any]:
    text = f"{title}\n{desc}".lower()
    official_urls = [u for u in urls if url_contains_domain(u, brand_domains)]
    buy_urls = [u for u in urls if any(k in (urlparse(u).path + "?" + urlparse(u).query).lower() for k in BUY_PATH_KEYWORDS)]
    app_urls = [u for u in urls if url_contains_domain(u, list(APP_STORE_DOMAINS))]
    social_urls = [u for u in urls if url_contains_domain(u, list(SOCIAL_DOMAINS))]
    short_urls = [u for u in urls if url_contains_domain(u, list(SHORTLINK_DOMAINS))]
    has_ref = contains_any(text, REFERRAL_TERMS)
    has_disc = contains_any(text, DISCOUNT_TERMS)
    has_dist = contains_any(text, DISTRIBUTION_TERMS) or has_ref or has_disc
    score = 0
    if urls or official_urls or app_urls:
        score = 1
    if buy_urls or social_urls or official_urls:
        score = max(score, 2)
    if has_ref or has_disc or buy_urls:
        score = max(score, 3)
    landing = []
    if buy_urls:
        landing.append("buy_page")
    if app_urls:
        landing.append("app_store")
    if official_urls:
        landing.append("official_site")
    if social_urls:
        landing.append("social/private")
    if short_urls:
        landing.append("shortlink")
    if not landing and urls:
        landing.append("other_link")
    if not landing:
        landing.append("none")
    return {
        "has_any_link": bool(urls),
        "has_official_link": bool(official_urls),
        "has_buy_page": bool(buy_urls),
        "has_app_store_link": bool(app_urls),
        "has_referral_code": has_ref,
        "has_discount_code": has_disc,
        "has_shortlink": bool(short_urls),
        "has_social_link": bool(social_urls),
        "distribution_trace": has_dist,
        "landing_type": "; ".join(landing),
        "conversion_path_score": score,
        "official_urls": " | ".join(official_urls[:5]),
        "buy_urls": " | ".join(buy_urls[:5]),
        "app_store_urls": " | ".join(app_urls[:5]),
        "social_urls": " | ".join(social_urls[:5]),
        "short_urls": " | ".join(short_urls[:5]),
        "cta_text": find_lines_with_terms(desc, CTA_TERMS + REFERRAL_TERMS + DISCOUNT_TERMS + DISTRIBUTION_TERMS),
        "all_urls": " | ".join(urls[:20]),
        "url_count": len(urls),
    }


def relationship_type(is_official: bool, conv: Dict[str, Any], title: str, desc: str) -> str:
    if is_official:
        return "official_channel"
    text = f"{title}\n{desc}".lower()
    if conv.get("has_referral_code") or conv.get("has_discount_code") or contains_any(text, DISTRIBUTION_TERMS):
        return "distribution/referral-like"
    if contains_any(text, ["sponsor", "sponsored", "paid promotion", "partner", "ambassador"]):
        return "explicit_or_likely_sponsored"
    if conv.get("has_buy_page") or conv.get("has_official_link") or conv.get("has_social_link"):
        return "conversion_link_present"
    return "organic_or_unclear"


def build_video_row(item: Dict[str, Any], brand: str, queries: Sequence[str], channels: Dict[str, Dict[str, Any]], config: Dict[str, Any], official: Dict[str, Dict[str, Any]], run_time: dt.datetime) -> Dict[str, Any]:
    sn = item.get("snippet", {})
    st = item.get("statistics", {})
    cd = item.get("contentDetails", {})
    vid = item.get("id")
    ch_id = sn.get("channelId", "")
    cm = channels.get(ch_id, {})
    is_off = ch_id in official
    off = official.get(ch_id, {})
    title, desc, pub = sn.get("title", ""), sn.get("description", ""), sn.get("publishedAt", "")
    age = days_since(pub, run_time)
    views = to_int(st.get("viewCount")) or 0
    likes = to_int(st.get("likeCount"))
    comments = to_int(st.get("commentCount"))
    return {
        "brand": brand,
        "video_id": vid,
        "video_url": video_url(vid),
        "title": title,
        "description": desc,
        "channel_id": ch_id,
        "channel_name": cm.get("title") or sn.get("channelTitle", ""),
        "channel_handle": cm.get("channel_handle", ""),
        "channel_url": channel_url(ch_id),
        "channel_subscribers": cm.get("subscriberCount"),
        "channel_video_count": cm.get("videoCount"),
        "channel_total_views": cm.get("viewCount"),
        "is_official_channel": is_off,
        "creator_type": "official" if is_off else "kol/creator",
        "official_config_name": off.get("official_config_name", ""),
        "official_config_handle": off.get("official_config_handle", ""),
        "publish_date": pub,
        "video_age_days": round(age, 3),
        "views": views,
        "likes": likes,
        "comments": comments,
        "views_per_day": round(views / max(age, 0.001), 6),
        "like_rate": round(likes / views, 8) if likes is not None and views else None,
        "comment_rate": round(comments / views, 8) if comments is not None and views else None,
        "duration_iso8601": cd.get("duration", ""),
        "query_keyword": " | ".join(sorted(set(queries))),
        "language_hint": language_hint(title + "\n" + desc),
        "region_guess": "",
        "game_scene": infer_scene(title, desc, config.get("scene_terms", [])),
        "content_type": infer_content_type(title, desc),
        "is_brand_video": True,
        "thumbnail_default": ((sn.get("thumbnails") or {}).get("default") or {}).get("url", ""),
        "collected_at_utc": iso_z(run_time),
    }


def avg(vals: Sequence[Optional[float]]) -> Optional[float]:
    clean = [v for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return sum(clean) / len(clean) if clean else None


def median(vals: Sequence[int]) -> Optional[int]:
    clean = sorted([int(v) for v in vals if v is not None])
    return clean[len(clean)//2] if clean else None


def bool_rate(rows: Sequence[Dict[str, Any]], key: str) -> Optional[float]:
    return round(sum(1 for r in rows if r.get(key)) / len(rows), 4) if rows else None


def collect_baselines(client: YTClient, video_rows: List[Dict[str, Any]], channels: Dict[str, Dict[str, Any]], brand_aliases: Dict[str, List[str]], baseline_count: int, run_time: dt.datetime) -> List[Dict[str, Any]]:
    by_channel = defaultdict(list)
    for r in video_rows:
        by_channel[r["channel_id"]].append(r)
    all_aliases = [a.lower() for aliases in brand_aliases.values() for a in aliases]
    out = []
    for ch_id, rows in by_channel.items():
        playlist = channels.get(ch_id, {}).get("uploads_playlist", "")
        if not playlist:
            continue
        try:
            pitems = client.playlist_items(playlist, max(baseline_count + 30, 20))
            ids = []
            for it in pitems:
                vid = (it.get("contentDetails") or {}).get("videoId") or (((it.get("snippet") or {}).get("resourceId") or {}).get("videoId"))
                if vid:
                    ids.append(vid)
            hydrated = client.videos_list(ids)
        except Exception as exc:
            for r in rows:
                out.append({"brand": r["brand"], "video_id": r["video_id"], "channel_id": ch_id, "channel_name": r["channel_name"], "channel_handle": r["channel_handle"], "baseline_status": "failed", "baseline_error": str(exc)[:500]})
            continue
        target_ids = {r["video_id"] for r in rows}
        base = []
        for it in hydrated:
            vid = it.get("id")
            sn = it.get("snippet", {})
            text = f"{sn.get('title','')}\n{sn.get('description','')}".lower()
            if vid in target_ids or any(a in text for a in all_aliases):
                continue
            st = it.get("statistics", {})
            views = to_int(st.get("viewCount")) or 0
            age = days_since(sn.get("publishedAt", ""), run_time)
            likes = to_int(st.get("likeCount"))
            comments = to_int(st.get("commentCount"))
            base.append({
                "views_per_day": views / max(age, 0.001),
                "like_rate": likes / views if likes is not None and views else None,
                "comment_rate": comments / views if comments is not None and views else None,
            })
            if len(base) >= baseline_count:
                break
        avg_vpd = avg([b["views_per_day"] for b in base])
        med_vpd = sorted([b["views_per_day"] for b in base])[len(base)//2] if base else None
        avg_like = avg([b["like_rate"] for b in base])
        avg_comment = avg([b["comment_rate"] for b in base])
        for r in rows:
            perf = r["views_per_day"] / avg_vpd if avg_vpd else None
            out.append({
                "brand": r["brand"],
                "video_id": r["video_id"],
                "video_url": r["video_url"],
                "title": r["title"],
                "channel_id": ch_id,
                "channel_name": r["channel_name"],
                "channel_handle": r["channel_handle"],
                "channel_url": r["channel_url"],
                "creator_type": r["creator_type"],
                "subscriber_count": r.get("channel_subscribers"),
                "baseline_video_count": len(base),
                "baseline_avg_views_per_day": round(avg_vpd, 6) if avg_vpd is not None else None,
                "baseline_median_views_per_day": round(med_vpd, 6) if med_vpd is not None else None,
                "brand_views_per_day": r["views_per_day"],
                "performance_index": round(perf, 6) if perf is not None else None,
                "like_rate_delta": round(r["like_rate"] - avg_like, 8) if r.get("like_rate") is not None and avg_like is not None else None,
                "comment_rate_delta": round(r["comment_rate"] - avg_comment, 8) if r.get("comment_rate") is not None and avg_comment is not None else None,
                "baseline_status": "ok" if base else "no_baseline",
                "baseline_error": "",
            })
    return out


def summarize_brand(videos: List[Dict[str, Any]], conv_map: Dict[Tuple[str, str], Dict[str, Any]], baselines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    baseline_map = {(b.get("video_id"), b.get("brand")): b for b in baselines}
    out = []
    for brand, rows in sorted(defaultdict(list, {b: [r for r in videos if r["brand"] == b] for b in {r["brand"] for r in videos}}).items()):
        convs = [conv_map.get((r["video_id"], r["brand"]), {}) for r in rows]
        perf = [baseline_map.get((r["video_id"], r["brand"]), {}).get("performance_index") for r in rows]
        perf = [p for p in perf if p is not None]
        views = [r.get("views") or 0 for r in rows]
        out.append({
            "brand": brand,
            "video_count": len(rows),
            "kol_video_count": sum(1 for r in rows if not r.get("is_official_channel")),
            "official_video_count": sum(1 for r in rows if r.get("is_official_channel")),
            "channel_count": len({r["channel_id"] for r in rows if r.get("channel_id")}),
            "kol_channel_count": len({r["channel_id"] for r in rows if r.get("channel_id") and not r.get("is_official_channel")}),
            "official_channel_count": len({r["channel_id"] for r in rows if r.get("channel_id") and r.get("is_official_channel")}),
            "total_views": sum(views),
            "avg_views": round(sum(views) / len(rows), 2) if rows else None,
            "median_views": median(views),
            "avg_views_per_day": round(avg([r.get("views_per_day") for r in rows]) or 0, 6) if rows else None,
            "link_rate": bool_rate(convs, "has_any_link"),
            "official_link_rate": bool_rate(convs, "has_official_link"),
            "buy_page_direct_rate": bool_rate(convs, "has_buy_page"),
            "app_store_rate": bool_rate(convs, "has_app_store_link"),
            "referral_code_rate": bool_rate(convs, "has_referral_code"),
            "discount_code_rate": bool_rate(convs, "has_discount_code"),
            "social_redirect_rate": bool_rate(convs, "has_social_link"),
            "shortlink_rate": bool_rate(convs, "has_shortlink"),
            "distribution_trace_rate": bool_rate(convs, "distribution_trace"),
            "avg_conversion_path_score": round(avg([c.get("conversion_path_score") for c in convs]) or 0, 4),
            "avg_performance_index": round(avg(perf) or 0, 6) if perf else None,
            "performance_index_gt_1_2_rate": round(sum(1 for p in perf if p > 1.2) / len(perf), 4) if perf else None,
            "performance_index_lt_0_8_rate": round(sum(1 for p in perf if p < 0.8) / len(perf), 4) if perf else None,
            "top_content_types": json.dumps(Counter(r.get("content_type") for r in rows).most_common(5), ensure_ascii=False),
            "top_scenes": json.dumps(Counter(r.get("game_scene") for r in rows).most_common(5), ensure_ascii=False),
        })
    return out


def summarize_creator_brand(videos: List[Dict[str, Any]], conv_map: Dict[Tuple[str, str], Dict[str, Any]], baselines: List[Dict[str, Any]], official_only: bool) -> List[Dict[str, Any]]:
    selected = [r for r in videos if bool(r.get("is_official_channel")) == official_only]
    baseline_map = {(b.get("video_id"), b.get("brand")): b for b in baselines}
    brands_by_channel = defaultdict(set)
    for r in selected:
        brands_by_channel[r["channel_id"]].add(r["brand"])
    grouped = defaultdict(list)
    for r in selected:
        grouped[(r["channel_id"], r["brand"])].append(r)
    out = []
    for (ch, brand), rows in sorted(grouped.items()):
        convs = [conv_map.get((r["video_id"], r["brand"]), {}) for r in rows]
        perf = [baseline_map.get((r["video_id"], r["brand"]), {}).get("performance_index") for r in rows]
        perf = [p for p in perf if p is not None]
        first = rows[0]
        dates = [parse_iso(r["publish_date"]) for r in rows if r.get("publish_date")]
        views = [r.get("views") or 0 for r in rows]
        covered = sorted(brands_by_channel.get(ch, set()))
        out.append({
            "brand": brand,
            "channel_id": ch,
            "channel_name": first.get("channel_name"),
            "channel_handle": first.get("channel_handle"),
            "channel_url": first.get("channel_url"),
            "creator_type": first.get("creator_type"),
            "is_official_channel": first.get("is_official_channel"),
            "official_config_name": first.get("official_config_name"),
            "official_config_handle": first.get("official_config_handle"),
            "channel_subscribers": first.get("channel_subscribers"),
            "channel_video_count": first.get("channel_video_count"),
            "channel_total_views": first.get("channel_total_views"),
            "video_count_for_brand": len(rows),
            "total_views_for_brand": sum(views),
            "avg_views_for_brand": round(sum(views) / len(rows), 2) if rows else None,
            "median_views_for_brand": median(views),
            "avg_views_per_day_for_brand": round(avg([r.get("views_per_day") for r in rows]) or 0, 6),
            "earliest_brand_video_date": iso_z(min(dates)) if dates else "",
            "latest_brand_video_date": iso_z(max(dates)) if dates else "",
            "avg_conversion_path_score": round(avg([c.get("conversion_path_score") for c in convs]) or 0, 4),
            "link_rate": bool_rate(convs, "has_any_link"),
            "buy_page_direct_rate": bool_rate(convs, "has_buy_page"),
            "referral_code_rate": bool_rate(convs, "has_referral_code"),
            "discount_code_rate": bool_rate(convs, "has_discount_code"),
            "social_redirect_rate": bool_rate(convs, "has_social_link"),
            "distribution_trace_rate": bool_rate(convs, "distribution_trace"),
            "avg_performance_index": round(avg(perf) or 0, 6) if perf else None,
            "brands_covered_by_this_channel_in_scope": " | ".join(covered),
            "brand_count_for_this_channel_in_scope": len(covered),
            "is_multi_brand_creator_in_scope": len(covered) >= 2,
            "top_content_types": json.dumps(Counter(r.get("content_type") for r in rows).most_common(5), ensure_ascii=False),
            "top_scenes": json.dumps(Counter(r.get("game_scene") for r in rows).most_common(5), ensure_ascii=False),
            "sample_video_urls": " | ".join(r.get("video_url", "") for r in rows[:5]),
        })
    return out


def write_outputs(outdir: Path, videos: List[Dict[str, Any]], conversions: List[Dict[str, Any]], baselines: List[Dict[str, Any]], brand_summary: List[Dict[str, Any]], creator_summary: List[Dict[str, Any]], official_summary: List[Dict[str, Any]], run_summary: Dict[str, Any], dropped_search_false_positives: Optional[List[Dict[str, Any]]] = None) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    kol_videos = [r for r in videos if not r.get("is_official_channel")]
    official_videos = [r for r in videos if r.get("is_official_channel")]
    files = {
        "videos.csv": videos,
        "kol_videos.csv": kol_videos,
        "official_videos.csv": official_videos,
        "conversion_paths.csv": conversions,
        "channel_baselines.csv": baselines,
        "brand_summary.csv": brand_summary,
        "creator_brand_summary.csv": creator_summary,
        "official_channel_summary.csv": official_summary,
        "dropped_search_false_positives.csv": dropped_search_false_positives or [],
    }
    for name, rows in files.items():
        pd.DataFrame(rows).to_csv(outdir / name, index=False, encoding="utf-8-sig")
    write_jsonl(outdir / "videos.jsonl", videos)
    save_json(outdir / "run_summary.json", run_summary)
    xlsx = outdir / "youtube_kol_conversion_report.xlsx"
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        for sheet, rows in [
            ("brand_summary", brand_summary),
            ("creator_brand_summary", creator_summary),
            ("official_channel_summary", official_summary),
            ("video_samples_all", videos),
            ("kol_videos", kol_videos),
            ("official_videos", official_videos),
            ("conversion_paths", conversions),
            ("channel_baselines", baselines),
            ("run_summary", [run_summary]),
            ("dropped_search_false_positives", dropped_search_false_positives or []),
        ]:
            pd.DataFrame(rows).to_excel(writer, sheet_name=sheet, index=False)
        for ws in writer.book.worksheets:
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for col in ws.columns:
                letter = col[0].column_letter
                max_len = max([len(str(c.value)) if c.value is not None else 0 for c in col[:200]] + [10])
                ws.column_dimensions[letter].width = min(max_len + 2, 60)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--output-dir", default=None)
    ap.add_argument("--env-file", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if load_dotenv:
        load_dotenv(args.env_file) if args.env_file else load_dotenv()

    config = load_json(Path(args.config))
    api_env = config.get("api_key_env", "YOUTUBE_API_KEY")
    api_key = os.environ.get(api_env)
    if not api_key:
        print(f"ERROR: missing API key env var {api_env}")
        return 2

    run_time = now_utc()
    outbase = Path(args.output_dir or config.get("output_dir") or "output")
    outdir = outbase / f"youtube_kol_run_{safe_ts()}"
    outdir.mkdir(parents=True, exist_ok=True)
    log_file = outdir / "run_log.txt"

    def log(msg: str) -> None:
        line = f"[{iso_z(now_utc())}] {msg}"
        print(line)
        with log_file.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    client = YTClient(api_key, float(config.get("sleep_seconds", 0.1)), int(config.get("retries", 3)), int(config.get("timeout_seconds", 30)))
    settings = config.get("settings", {})
    lookback = int(settings.get("lookback_days") or 365)
    published_before = settings.get("published_before") or iso_z(run_time)
    published_after = settings.get("published_after") or iso_z(run_time - dt.timedelta(days=lookback))
    summary: Dict[str, Any] = {
        "status": "started", "run_time_utc": iso_z(run_time), "config_file": str(args.config),
        "lookback_days": lookback, "published_after_effective": published_after,
        "published_before_effective": published_before, "public_data_only": True,
    }

    try:
        log("Preflight started.")
        summary["preflight_ok"] = client.preflight()
        official = resolve_official_channels(client, config, log)
        summary["official_channel_count_resolved"] = len(official)
        if args.dry_run:
            summary["status"] = "dry_run_ok"
            summary["estimated_quota_units"] = client.units
            save_json(outdir / "run_summary.json", summary)
            save_json(outdir / "api_call_log.json", client.calls)
            return 0

        brands = config.get("brands", [])
        brand_cfg = {b["brand"]: b for b in brands}
        brand_aliases = {b["brand"]: b.get("aliases", [b["brand"]]) for b in brands}
        video_items: Dict[str, Dict[str, Any]] = {}
        vid_brands: Dict[str, Set[str]] = defaultdict(set)
        vid_queries: Dict[Tuple[str, str], Set[str]] = defaultdict(set)

        official_items, official_brands, official_queries = collect_official_uploads(
            client, official, published_after, published_before,
            int(settings.get("official_uploads_max_per_channel", 500)), log
        )
        video_items.update(official_items)
        for vid, bs in official_brands.items():
            vid_brands[vid].update(bs)
        for key, qs in official_queries.items():
            vid_queries[key].update(qs)

        windows = date_windows(published_after, published_before, int(settings.get("search_window_days", 30))) if settings.get("use_search_date_windows", True) else [(published_after, published_before)]
        for b in brands:
            for q in b.get("search_terms", []):
                for after, before in windows:
                    limit = int(settings.get("max_results_per_query_per_window", 50)) if settings.get("use_search_date_windows", True) else int(settings.get("max_results_per_query", 300))
                    log(f"Search {b['brand']} | {q} | {after} -> {before}")
                    for it in client.search_videos(q, limit, after, before, settings.get("region_code"), settings.get("relevance_language"), settings.get("order", "date")):
                        vid = (it.get("id") or {}).get("videoId")
                        if not vid:
                            continue
                        video_items.setdefault(vid, it)
                        vid_brands[vid].add(b["brand"])
                        vid_queries[(vid, b["brand"])].add(q)

        log(f"Unique videos before hydration: {len(video_items)}")
        hydrated = client.videos_list(list(video_items.keys()))
        hydrated_by_id = {v["id"]: v for v in hydrated if v.get("id")}
        channel_ids = [v.get("snippet", {}).get("channelId") for v in hydrated if v.get("snippet", {}).get("channelId")]
        channel_rows = client.channels_list(channel_ids)
        channels = {}
        for ch in channel_rows:
            meta = channel_meta(ch)
            channels[meta["channel_id"]] = meta
        for ch_id, meta in official.items():
            channels[ch_id] = {**channels.get(ch_id, {}), **meta}

        rows, conv_rows, conv_map = [], [], {}
        dropped_search_false_positives: List[Dict[str, Any]] = []
        strict = bool(settings.get("strict_brand_filter", True))
        for vid, item in hydrated_by_id.items():
            for brand in sorted(vid_brands.get(vid, set())):
                sn = item.get("snippet", {})
                ch_id = sn.get("channelId", "")
                ch_meta = channels.get(ch_id, {})
                title, desc = sn.get("title", ""), sn.get("description", "")
                urls = extract_urls(desc)

                if ch_id in official and official[ch_id].get("official_brand") != brand:
                    dropped_search_false_positives.append({
                        "brand": brand, "video_id": vid, "video_url": video_url(vid), "title": title,
                        "channel_id": ch_id, "channel_name": ch_meta.get("title") or sn.get("channelTitle", ""),
                        "channel_handle": ch_meta.get("channel_handle", ""),
                        "query_keyword": " | ".join(sorted(vid_queries.get((vid, brand), []))),
                        "drop_reason": f"official_channel_belongs_to_{official[ch_id].get('official_brand')}"
                    })
                    continue

                if strict and ch_id not in official:
                    ok, reason = target_brand_match_status(
                        brand, title, desc, ch_meta.get("title") or sn.get("channelTitle", ""),
                        ch_meta.get("channel_handle", ""), urls
                    )
                    if not ok:
                        dropped_search_false_positives.append({
                            "brand": brand, "video_id": vid, "video_url": video_url(vid), "title": title,
                            "channel_id": ch_id, "channel_name": ch_meta.get("title") or sn.get("channelTitle", ""),
                            "channel_handle": ch_meta.get("channel_handle", ""),
                            "query_keyword": " | ".join(sorted(vid_queries.get((vid, brand), []))),
                            "drop_reason": reason
                        })
                        continue

                row = build_video_row(item, brand, vid_queries.get((vid, brand), []), channels, config, official, run_time)
                urls = extract_urls(row.get("description", ""))
                conv = analyze_conversion(row["title"], row.get("description", ""), urls, brand_cfg.get(brand, {}).get("official_domains", []))
                conv.update({
                    "brand": brand, "video_id": vid, "video_url": row["video_url"], "title": row["title"],
                    "channel_id": row["channel_id"], "channel_name": row["channel_name"], "channel_handle": row["channel_handle"],
                    "channel_url": row["channel_url"], "creator_type": row["creator_type"], "is_official_channel": row["is_official_channel"],
                    "creator_relationship_type": relationship_type(row["is_official_channel"], conv, row["title"], row.get("description", "")),
                })
                rows.append(row)
                conv_rows.append(conv)
                conv_map[(vid, brand)] = conv

        log(f"Final video rows: {len(rows)} | KOL rows: {sum(1 for r in rows if not r['is_official_channel'])} | official rows: {sum(1 for r in rows if r['is_official_channel'])}")
        baselines = collect_baselines(client, rows, channels, brand_aliases, int(settings.get("baseline_count", 10)), run_time)
        brand_summary = summarize_brand(rows, conv_map, baselines)
        creator_summary = summarize_creator_brand(rows, conv_map, baselines, official_only=False)
        official_summary = summarize_creator_brand(rows, conv_map, baselines, official_only=True)
        summary.update({
            "status": "ok", "output_dir": str(outdir), "video_row_count": len(rows),
            "unique_video_count": len({r["video_id"] for r in rows}),
            "kol_video_rows": sum(1 for r in rows if not r["is_official_channel"]),
            "official_video_rows": sum(1 for r in rows if r["is_official_channel"]),
            "creator_brand_summary_rows": len(creator_summary),
            "official_channel_summary_rows": len(official_summary),
            "estimated_quota_units": client.units,
            "api_call_counts": dict(Counter(c["method"] for c in client.calls)),
            "dropped_search_false_positive_rows": len(dropped_search_false_positives),
        })
        write_outputs(outdir, rows, conv_rows, baselines, brand_summary, creator_summary, official_summary, summary, dropped_search_false_positives)
        save_json(outdir / "api_call_log.json", client.calls)
        log(f"Done: {outdir}")
        return 0
    except Exception as exc:
        summary["status"] = "failed"
        summary["error"] = str(exc)
        summary["traceback"] = traceback.format_exc()
        summary["estimated_quota_units"] = client.units
        save_json(outdir / "run_summary.json", summary)
        save_json(outdir / "api_call_log.json", client.calls)
        with log_file.open("a", encoding="utf-8") as f:
            f.write("\n" + traceback.format_exc() + "\n")
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
