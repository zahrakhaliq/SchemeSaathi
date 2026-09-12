"""SchemeSaathi Source Maintenance Agent V2.

Conservative official-source maintenance for data/schemes.json.
- Handles redirects, HEAD/GET differences, 403/429 anti-bot responses.
- Validates Punjab government hosts instead of collapsing subdomains to gov.pk.
- Uses Tavily as evidence when direct HTTP is ambiguous or a URL is broken.
- Only replaces links when official-domain + scheme-name evidence is strong.
- Leaves unresolved source URLs untouched and never marks them verified.
"""
import json, os, re, time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
import requests

DATA_PATH = Path("data/schemes.json")
REPORT_PATH = Path("data/source_refresh_report.json")
TIMEOUT = 20
USER_AGENT = "Mozilla/5.0 (compatible; SchemeSaathi-SourceMaintenanceAgent/2.0)"

TRUSTED_HOSTS = {
    "punjab.gov.pk", "www.punjab.gov.pk", "hed.punjab.gov.pk",
    "energy.punjab.gov.pk", "agripunjab.punjab.gov.pk",
    "swd.punjab.gov.pk", "zakat.punjab.gov.pk", "psic.punjab.gov.pk",
    "pnd.punjab.gov.pk", "plc.punjab.gov.pk", "livestock.punjab.gov.pk",
    "dastak.punjab.gov.pk",
}

session = requests.Session()
session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.8",
})


def host_of(url):
    return urlparse(url).netloc.lower().split(":")[0].removeprefix("www.")


def is_official_punjab(url):
    host = host_of(url)
    return host == "punjab.gov.pk" or host.endswith(".punjab.gov.pk") or host in {h.removeprefix("www.") for h in TRUSTED_HOSTS}


def same_official_family(a, b):
    return is_official_punjab(a) and is_official_punjab(b)


def check_url(url):
    """Return (state, status, final_url, title/text evidence).
    state: working | ambiguous | broken
    """
    if not is_official_punjab(url):
        return "broken", None, url, ""
    try:
        # HEAD can be blocked even when GET works.
        try:
            h = session.head(url, timeout=TIMEOUT, allow_redirects=True)
            if 200 <= h.status_code < 400:
                return "working", h.status_code, h.url, ""
        except requests.RequestException:
            pass

        r = session.get(url, timeout=TIMEOUT, allow_redirects=True)
        text = r.text[:200000] if r.text else ""
        title = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
        title_text = re.sub(r"\s+", " ", title.group(1)).strip() if title else ""
        evidence = title_text + " " + re.sub(r"<[^>]+>", " ", text[:30000])
        if 200 <= r.status_code < 400:
            return "working", r.status_code, r.url, evidence
        # Anti-bot/rate-limit pages are ambiguous, not proof of a dead source.
        if r.status_code in {401, 403, 408, 429, 500, 502, 503, 504}:
            return "ambiguous", r.status_code, r.url, evidence
        return "broken", r.status_code, r.url, evidence
    except requests.RequestException as exc:
        return "ambiguous", None, url, str(exc)


def normalize(text):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", text.lower())).strip()


def similarity(name, candidate_text):
    generic = {"chief", "minister", "punjab", "program", "programme", "scheme", "initiative", "project", "cm", "government"}
    a = set(normalize(name).split()) - generic
    b = set(normalize(candidate_text).split()) - generic
    return len(a & b) / max(1, len(a))


def tavily_search(scheme, query_domain=None):
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        return []
    name = scheme.get("name", "")
    queries = [f'"{name}" site:punjab.gov.pk']
    if query_domain:
        queries.append(f'"{name}" site:{query_domain}')
    out = []
    seen = set()
    for query in queries:
        payload = {"api_key": key, "query": query, "search_depth": "advanced", "max_results": 8, "include_answer": False}
        try:
            r = requests.post("https://api.tavily.com/search", json=payload, timeout=30)
            r.raise_for_status()
            for x in r.json().get("results", []):
                u = x.get("url", "")
                if u and u not in seen:
                    seen.add(u); out.append(x)
        except requests.RequestException:
            continue
    return out


def find_replacement(scheme):
    old = scheme.get("official_url", "")
    results = tavily_search(scheme, host_of(old))
    best = (None, 0.0, "")
    for result in results:
        url = result.get("url", "")
        if not url or not is_official_punjab(url):
            continue
        evidence = " ".join([result.get("title", ""), result.get("content", ""), url])
        score = similarity(scheme.get("name", ""), evidence)
        state, status, final_url, page_evidence = check_url(url)
        if state == "broken":
            continue
        score = max(score, similarity(scheme.get("name", ""), page_evidence))
        if score > best[1]:
            best = (final_url if state == "working" else url, score,
                    f"Official Punjab search evidence; similarity={score:.2f}; HTTP={status}; state={state}.")
    if best[0] and best[1] >= 0.34:
        return best
    return None, best[1], "No high-confidence official replacement found."


def main():
    schemes = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    today = date.today().strftime("%B %Y")
    report = {"run_date": str(date.today()), "agent_version": "2.0", "checked": 0, "working": 0,
              "verified_via_search": 0, "repaired": 0, "unresolved": 0, "changes": []}
    changed = False

    for scheme in schemes:
        url = scheme.get("official_url", "")
        if not url: continue
        report["checked"] += 1
        state, status, final_url, evidence = check_url(url)

        if state == "working":
            report["working"] += 1
            if same_official_family(url, final_url) and final_url != url:
                scheme["official_url"] = final_url; changed = True
                report["changes"].append({"scheme": scheme["name"], "type": "redirect_canonicalized", "old_url": url, "new_url": final_url})
            scheme["last_verified"] = today
            scheme["source_refresh_status"] = "Verified by direct HTTP check; verify current eligibility before applying."
            continue

        replacement, score, reason = find_replacement(scheme)
        if replacement:
            # If search confirms the existing URL itself, do not replace it.
            if replacement.rstrip("/") == url.rstrip("/"):
                report["verified_via_search"] += 1
                scheme["last_verified"] = today
                scheme["source_refresh_status"] = "Verified through official search evidence; direct HTTP response was ambiguous."
                report["changes"].append({"scheme": scheme["name"], "type": "verified_via_search", "url": url, "confidence": round(score, 3), "reason": reason})
            else:
                scheme["official_url"] = replacement; scheme["last_verified"] = today
                scheme["source_refresh_status"] = "Repaired by maintenance agent; verify before application."
                report["repaired"] += 1; changed = True
                report["changes"].append({"scheme": scheme["name"], "type": "broken_link_repaired", "old_url": url, "new_url": replacement, "confidence": round(score, 3), "reason": reason})
        else:
            # Critical: preserve old URL and do NOT update last_verified.
            scheme["source_refresh_status"] = "Source could not be verified; URL left unchanged."
            report["unresolved"] += 1
            report["changes"].append({"scheme": scheme["name"], "type": "unresolved", "old_url": url, "confidence": round(score, 3), "reason": reason})
        time.sleep(0.2)

    if changed:
        DATA_PATH.write_text(json.dumps(schemes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
