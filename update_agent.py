"""SchemeSaathi Source Maintenance Agent.

Checks every official source URL in data/schemes.json. If a URL is broken,
searches for a replacement on the same official government domain using Tavily,
validates the candidate, and updates only high-confidence URL replacements.

The agent is intentionally conservative: it never replaces a source with a
non-official domain and never deletes a scheme because a page is unavailable.
"""

import json
import os
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import requests

DATA_PATH = Path("data/schemes.json")
REPORT_PATH = Path("data/source_refresh_report.json")
TIMEOUT = 15
USER_AGENT = "SchemeSaathi-SourceMaintenanceAgent/1.0"


def domain_of(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def official_domain(url: str) -> str:
    host = domain_of(url)
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def check_url(url: str) -> tuple[bool, int | None, str]:
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
        ok = 200 <= r.status_code < 400
        return ok, r.status_code, r.url
    except requests.RequestException as exc:
        return False, None, str(exc)


def normalize_title(text: str) -> str:
    text = re.sub(r"[^a-z0-9 ]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def similarity(name: str, candidate_text: str) -> float:
    a = set(normalize_title(name).split())
    b = set(normalize_title(candidate_text).split())
    if not a or not b:
        return 0.0
    # Ignore generic government words when measuring evidence.
    generic = {"chief", "minister", "punjab", "program", "programme", "scheme", "initiative", "project", "cm"}
    a -= generic
    b -= generic
    return len(a & b) / max(1, len(a))


def tavily_search(scheme: dict, domain: str) -> list[dict]:
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        return []

    payload = {
        "api_key": key,
        "query": f'"{scheme["name"]}" site:{domain}',
        "search_depth": "advanced",
        "max_results": 8,
        "include_answer": False,
    }
    try:
        r = requests.post("https://api.tavily.com/search", json=payload,
                          headers={"User-Agent": USER_AGENT}, timeout=30)
        r.raise_for_status()
        return r.json().get("results", [])
    except requests.RequestException:
        return []


def find_replacement(scheme: dict) -> tuple[str | None, float, str]:
    old = scheme.get("official_url", "")
    domain = official_domain(old)
    results = tavily_search(scheme, domain)

    best_url = None
    best_score = 0.0
    reason = "No verified replacement found."

    for result in results:
        url = result.get("url", "")
        if not url or official_domain(url) != domain:
            continue

        # Only accept pages that are actually reachable.
        ok, status, final_url = check_url(url)
        if not ok:
            continue

        evidence = " ".join([
            result.get("title", ""),
            result.get("content", ""),
            result.get("url", ""),
        ])
        score = similarity(scheme.get("name", ""), evidence)
        if score > best_score:
            best_score = score
            best_url = final_url
            reason = f"Official-domain search candidate; name/evidence similarity={score:.2f}; HTTP {status}."

    # Conservative threshold: require at least one meaningful scheme-name token.
    if best_url and best_score >= 0.34:
        return best_url, best_score, reason
    return None, best_score, reason


def main() -> int:
    schemes = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    today = date.today().strftime("%B %Y")
    report = {
        "run_date": str(date.today()),
        "checked": 0,
        "working": 0,
        "repaired": 0,
        "unresolved": 0,
        "changes": [],
    }

    changed = False
    for scheme in schemes:
        url = scheme.get("official_url", "")
        if not url:
            continue

        report["checked"] += 1
        ok, status, final_url = check_url(url)
        if ok:
            report["working"] += 1
            # Keep redirects as the canonical source when they remain on the same
            # official domain. This quietly fixes old redirected URLs.
            if final_url and official_domain(final_url) == official_domain(url) and final_url != url:
                scheme["official_url"] = final_url
                changed = True
                report["changes"].append({
                    "scheme": scheme["name"], "type": "redirect_canonicalized",
                    "old_url": url, "new_url": final_url,
                })
            scheme["last_verified"] = today
            continue

        replacement, score, reason = find_replacement(scheme)
        if replacement:
            scheme["official_url"] = replacement
            scheme["last_verified"] = today
            scheme["source_refresh_status"] = "Repaired by maintenance agent; verify before application."
            changed = True
            report["repaired"] += 1
            report["changes"].append({
                "scheme": scheme["name"], "type": "broken_link_repaired",
                "old_url": url, "new_url": replacement, "confidence": round(score, 3),
                "reason": reason,
            })
        else:
            scheme["last_verified"] = today
            scheme["source_refresh_status"] = "Source unavailable; replacement not confidently found."
            changed = True
            report["unresolved"] += 1
            report["changes"].append({
                "scheme": scheme["name"], "type": "unresolved",
                "old_url": url, "confidence": round(score, 3), "reason": reason,
            })

        time.sleep(0.25)

    if changed:
        DATA_PATH.write_text(json.dumps(schemes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
