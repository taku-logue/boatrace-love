from __future__ import annotations

import hashlib
import os
import time
from datetime import date
from pathlib import Path

import httpx

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def _resolve_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "apps").exists() and (parent / "data").exists():
            return parent
        if (parent / "app").exists() and (parent / "pyproject.toml").exists():
            return parent
    return current.parents[-1]


REPO_ROOT = _resolve_repo_root()

HTML_PAGE_TYPE_DIRS = {
    "racelist": "race_cards",
    "beforeinfo": "exhibition",
    "oddstf": "odds",
}


def default_data_root() -> Path:
    env_value = os.environ.get("BOATRACE_DATA_DIR")
    if env_value:
        return Path(env_value)
    if Path("/data").exists():
        return Path("/data")
    return REPO_ROOT / "data"


def fetch_html(url: str, sleep_seconds: float = 1.0, timeout_seconds: float = 10.0) -> str | None:
    """公式HTMLを取得する。呼び出し側でretry/backoffを制御する。"""
    if sleep_seconds > 0:
        time.sleep(sleep_seconds)

    try:
        with httpx.Client(
            headers=HEADERS, timeout=timeout_seconds, follow_redirects=True
        ) as client:
            response = client.get(url)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as exc:
        print(f"HTML fetch failed ({url}): {exc}")
        return None


def html_storage_path(
    data_root: Path,
    target_date: date,
    page_type: str,
    venue_code: str,
    race_no: int,
) -> Path:
    date_str = target_date.strftime("%Y%m%d")
    category = HTML_PAGE_TYPE_DIRS.get(page_type, page_type)
    filename = f"{page_type}_{str(venue_code).zfill(2)}_{race_no:02d}.html"
    return data_root / "raw" / "html" / category / date_str / filename


def save_raw_html(
    html: str,
    target_date: date,
    page_type: str,
    venue_code: str,
    race_no: int,
    data_root: Path | None = None,
) -> Path:
    root = data_root or default_data_root()
    path = html_storage_path(root, target_date, page_type, venue_code, race_no)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def path_for_raw_file_record(path: Path, data_root: Path) -> str:
    try:
        return str(path.relative_to(data_root.parent))
    except ValueError:
        return str(path)
