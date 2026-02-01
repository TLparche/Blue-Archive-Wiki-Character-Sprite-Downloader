import time
import re
from pathlib import Path
from urllib.parse import urlencode, urlparse, unquote

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


BASE = "https://bluearchive.wiki"
API = f"{BASE}/w/api.php"

HEADERS = {
    "User-Agent": "BA-Sprite-Downloader/1.0",
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
}

TIMEOUT = 45
RATE_LIMIT_SEC = 0.25
RETRY = 3
RETRY_BACKOFF = 0.8

INVALID_FS_CHARS = set('<>:"/\\|?*')


def safe_name(name: str) -> str:
    name = (name or "").strip()
    out = []
    for ch in name:
        if ch in INVALID_FS_CHARS or ord(ch) < 32:
            out.append("_")
        else:
            out.append(ch)
    s = "".join(out)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:180] if len(s) > 180 else s


def build_url(api: str, params: dict) -> str:
    return f"{api}?{urlencode(params, doseq=True)}"


def http_get_json(session: requests.Session, url: str) -> dict:
    t0 = time.time()
    r = session.get(url, timeout=TIMEOUT, headers=HEADERS)
    dt = time.time() - t0
    print(f"[HTTP] GET {url}")
    print(f"[HTTP] -> {r.status_code} ({dt:.2f}s) content-type={r.headers.get('content-type')}")
    r.raise_for_status()
    return r.json()


def mw_api(session: requests.Session, params: dict) -> dict:
    p = dict(params)
    p["format"] = "json"
    url = build_url(API, p)
    return http_get_json(session, url)


def get_sections(session: requests.Session, page: str) -> list[dict]:
    data = mw_api(session, {"action": "parse", "page": page, "prop": "sections", "redirects": 1})
    return data.get("parse", {}).get("sections", []) or []


def get_section_html(session: requests.Session, page: str, section_index: str) -> str | None:
    for attempt in range(1, RETRY + 1):
        try:
            data = mw_api(
                session,
                {
                    "action": "parse",
                    "page": page,
                    "prop": "text",
                    "section": section_index,
                    "redirects": 1,
                },
            )
            return data["parse"]["text"]["*"]
        except Exception as e:
            print(f"[PARSE] page='{page}' section={section_index} attempt={attempt}/{RETRY} FAILED: {e}")
            time.sleep(RETRY_BACKOFF * attempt)
    return None


def extract_file_titles_from_html(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.select('a[href^="/wiki/File:"]'):
        href = a.get("href", "")
        t = href.split("/wiki/", 1)[-1]
        if t.startswith("File:"):
            out.append(t)
    seen = set()
    uniq = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def get_file_direct_url(session: requests.Session, file_title: str) -> str | None:
    for attempt in range(1, RETRY + 1):
        try:
            data = mw_api(
                session,
                {
                    "action": "query",
                    "titles": file_title,
                    "prop": "imageinfo",
                    "iiprop": "url",
                },
            )
            pages = data.get("query", {}).get("pages", {})
            for _, page in pages.items():
                ii = page.get("imageinfo")
                if ii and isinstance(ii, list) and "url" in ii[0]:
                    return ii[0]["url"]
        except Exception as e:
            print(f"[IMGINFO] file='{file_title}' attempt={attempt}/{RETRY} FAILED: {e}")
            time.sleep(RETRY_BACKOFF * attempt)
    return None


def filename_from_filetitle_or_url(file_title: str, url: str | None) -> str:
    ft = file_title.split("File:", 1)[-1]
    ft = unquote(ft)
    ft = safe_name(ft)
    if ft:
        return ft
    if url:
        base = Path(unquote(urlparse(url).path)).name
        base = safe_name(base)
        if base:
            return base
    return "image.bin"

def should_download_by_filename(char: str, file_title: str) -> bool:
    return char.lower() in file_title.split("File:", 1)[-1].lower()

def download_file(session: requests.Session, url: str, out_path: Path) -> bool:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, RETRY + 1):
        try:
            t0 = time.time()
            r = session.get(url, stream=True, timeout=TIMEOUT, headers=HEADERS)
            dt = time.time() - t0
            print(f"[DL] GET {url}")
            print(f"[DL] -> {r.status_code} ({dt:.2f}s) content-type={r.headers.get('content-type')}")
            r.raise_for_status()
            tmp_path = out_path.with_suffix(out_path.suffix + ".part")
            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)
            tmp_path.replace(out_path)
            return True
        except Exception as e:
            print(f"[DL] FAILED attempt={attempt}/{RETRY}: {e}")
            time.sleep(RETRY_BACKOFF * attempt)
    return False


def collect_sprites_by_variant(session: requests.Session, char: str) -> dict[str, list[str]]:
    page = f"{char}/gallery"
    sections = get_sections(session, page)
    time.sleep(RATE_LIMIT_SEC)

    sprites = None
    for s in sections:
        if (s.get("line") or "").strip().lower() == "sprites":
            sprites = s
            break
    if not sprites:
        return {}

    sprites_level = int(sprites.get("level", 0))
    sprites_index = sprites.get("index")

    sub_sections = []
    for s in sections:
        if int(s.get("level", 0)) == sprites_level + 1:
            sub_sections.append(s)

    variants: dict[str, list[str]] = {}

    if not sub_sections:
        html = get_section_html(session, page, sprites_index)
        time.sleep(RATE_LIMIT_SEC)
        if not html:
            return {}
        files = extract_file_titles_from_html(html)
        variants["Sprites"] = files
        return variants

    for sub in sub_sections:
        variant_name = (sub.get("line") or "").strip() or f"section_{sub.get('index')}"
        idx = sub.get("index")
        html = get_section_html(session, page, idx)
        time.sleep(RATE_LIMIT_SEC)
        if not html:
            variants[variant_name] = []
            continue
        files = extract_file_titles_from_html(html)
        variants[variant_name] = files

    return variants


def main():
    character_names = [
        "Koharu",
        "Hanako",
    ]

    root_out = Path("images")
    root_out.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(HEADERS)

    test = mw_api(session, {"action": "query", "meta": "siteinfo"})
    if "query" not in test:
        raise RuntimeError("MediaWiki API 응답이 예상과 다릅니다.")

    for char in tqdm(character_names, desc="Characters"):
        print(f"\n[{char}]")
        variants = collect_sprites_by_variant(session, char)

        if not variants:
            print("  (No Sprites section / files found)")
            continue

        char_dir = root_out / safe_name(char)

        for variant, files in variants.items():
            if char.lower() not in (variant or "").lower():
                print(f"  ├─ (skip:section-name-no-char) {variant}")
                continue

            variant_dir = char_dir / safe_name(variant if variant else "Default")

            print(f"  ├─ {variant} ({len(files)})")
            for file_title in files:
                fname = file_title.split("File:", 1)[-1]
                keep = should_download_by_filename(char, file_title)
                if not keep:
                    reason = "no char match"
                    print(f"  │   └─ (skip:{reason}) {fname}")
                    continue

                url = get_file_direct_url(session, file_title)
                time.sleep(RATE_LIMIT_SEC)
                if not url:
                    print(f"  │   └─ (skip:no-url) {fname}")
                    continue

                out_path = variant_dir / filename_from_filetitle_or_url(file_title, url)

                if out_path.exists() and out_path.stat().st_size > 0:
                    print(f"  │   └─ (exists) {out_path.name}")
                    continue

                ok = download_file(session, url, out_path)
                time.sleep(RATE_LIMIT_SEC)
                if ok:
                    print(f"  │   └─ (saved)  {out_path.name}")
                else:
                    print(f"  │   └─ (fail)   {out_path.name}")


if __name__ == "__main__":
    main()
