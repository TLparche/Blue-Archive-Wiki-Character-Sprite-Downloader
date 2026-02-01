import time
import re
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


BASE = "https://bluearchive.wiki"
API = f"{BASE}/w/api.php"

HEADERS = {
    "User-Agent": "BA-Sprite-Section-Checker/1.0",
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
}

TIMEOUT = 30
RATE_LIMIT_SEC = 0.25


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
        print(f"[PARSE] page='{page}' section={section_index} FAILED: {e}")
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


def main():
    character_names = [
        "Kayoko",
        "Arisu",
    ]

    session = requests.Session()
    session.headers.update(HEADERS)

    test = mw_api(session, {"action": "query", "meta": "siteinfo"})
    if "query" not in test:
        raise RuntimeError("MediaWiki API 응답이 예상과 다릅니다.")

    for char in tqdm(character_names, desc="Characters"):
        page = f"{char}/gallery"
        print(f"\n[{char}] page={page}")

        sections = get_sections(session, page)
        time.sleep(RATE_LIMIT_SEC)

        sprites = None
        for s in sections:
            if (s.get("line") or "").strip().lower() == "sprites":
                sprites = s
                break

        if not sprites:
            print("  (Sprites section not found)")
            continue

        sprites_index = sprites["index"]
        sprites_level = int(sprites["level"])

        subs = []
        for s in sections:
            lvl = int(s.get("level", 0))
            if lvl == sprites_level + 1:
                subs.append(s)

        if not subs:
            html = get_section_html(session, page, sprites_index)
            time.sleep(RATE_LIMIT_SEC)
            if not html:
                print("  (Sprites section parse failed)")
                continue
            files = extract_file_titles_from_html(html)
            print(f"  ├─ Sprites ({len(files)})")
            for f in files:
                print(f"  │   └─ {f.split('File:', 1)[-1]}")
            continue

        for sub in subs:
            variant_name = sub.get("line", "").strip() or f"section_{sub.get('index')}"
            sub_index = sub["index"]

            html = get_section_html(session, page, sub_index)
            time.sleep(RATE_LIMIT_SEC)
            if not html:
                print(f"  ├─ {variant_name} (0)")
                continue

            files = extract_file_titles_from_html(html)
            print(f"  ├─ {variant_name} ({len(files)})")
            for f in files:
                print(f"  │   └─ {f.split('File:', 1)[-1]}")

        time.sleep(RATE_LIMIT_SEC)


if __name__ == "__main__":
    main()
