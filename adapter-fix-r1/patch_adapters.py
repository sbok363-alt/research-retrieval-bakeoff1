from __future__ import annotations

import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
adapters = root / "adapters"

def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected exactly one match, got {text.count(old)}")
    path.write_text(text.replace(old, new, 1))

# B04 pagination must preserve ?page=N. Query stripping is correct for docs
# canonicalization, but wrong for pagination state.
for name in ("scrapling_adapter.py", "crawl4ai_adapter.py"):
    p = adapters / name
    replace_once(
        p,
        "while url and canonical_url(url) not in seen_pages:\n                seen_pages.add(canonical_url(url))",
        "while url and url not in seen_pages:\n                seen_pages.add(url)",
    )

# Crawl4AI returned the correct 200 response + extracted session fact while its
# internal success flag was false. The benchmark grades retrieval correctness,
# so adapter-level ok is based on an actual HTTP success plus extracted evidence;
# the contradictory library flag remains recorded for diagnosis.
p = adapters / "crawl4ai_adapter.py"
replace_once(
    p,
    "return result(bool(r2.success), out, visible, ops=2, attempts=2)",
    "ok = int(r2.status_code or 0) == 200 and first_fact(visible) is not None\n            return result(ok, out, visible, ops=2, attempts=2, notes=f\"crawl4ai success={bool(r2.success)}; error={getattr(r2, 'error_message', '')!r}\")",
)

# Playwright CLI run-code does not expose Node's global URL constructor.
# Perform URL parsing inside the browser page context instead.
p = adapters / "playwright_cli_adapter.py"
text = p.read_text()
start = text.index('        if tid == "B03":')
end = text.index('        if tid == "B04":', start)
b03 = '''        if tid == "B03":
            _open(session, abs_url("/docs/")); ops += 1
            out = _run_code_json(session, """
                const origin = await page.evaluate(() => location.origin);
                const q = [page.url()]; const seen = new Set(); const counts = {}; const facts = new Set(); const pages = new Set();
                while (q.length) {
                  const next=q.shift();
                  await page.goto(next); await page.waitForLoadState('domcontentloaded');
                  const meta=await page.evaluate(() => ({
                    canon: location.origin + location.pathname,
                    pathname: location.pathname,
                    links: [...document.querySelectorAll('a[href]')].map(a => ({href:a.href, origin:new URL(a.href).origin, pathname:new URL(a.href).pathname}))
                  }));
                  if(seen.has(meta.canon)) continue; seen.add(meta.canon);
                  counts[meta.pathname]=(counts[meta.pathname]||0)+1;
                  if(meta.pathname!='/docs/') {
                    pages.add(meta.pathname);
                    const text=await page.locator('body').innerText();
                    for(const m of text.matchAll(/\\b([A-Z][A-Z0-9_]*)=([^\\s<>{}\\[\\],;]+)/g)) facts.add(`${m[1]}=${m[2]}`);
                  }
                  for(const link of meta.links){ if(link.origin===origin && link.pathname.startsWith('/docs/')) { const canon=link.origin+link.pathname; if(!seen.has(canon)) q.push(canon); } }
                }
                return JSON.stringify({canonical_pages:[...pages].sort(),facts:[...facts].sort(),max_duplicate_canonical_fetches:Math.max(0,...Object.values(counts))});
            """)
            return result(True, out, json.dumps(out, sort_keys=True), ops=max(ops, len(out.get("canonical_pages", []))+1), attempts=max(1, len(out.get("canonical_pages", []))+1))

'''
text = text[:start] + b03 + text[end:]

start = text.index('        if tid == "B05":')
end = text.index('        if tid in ("B06", "B07"):', start)
b05 = '''        if tid == "B05":
            _open(session, abs_url("/session/start")); ops += 1
            out = _run_code_json(session, """
                const absoluteHref=await page.locator('a[href]').first().evaluate(a=>a.href);
                const response=await page.goto(absoluteHref); await page.waitForLoadState('domcontentloaded');
                const text=await page.locator('body').innerText();
                const m=text.match(/\\b([A-Z][A-Z0-9_]*)=([^\\s<>{}\\[\\],;]+)/);
                return JSON.stringify({status:response?.status()||0, secret_fact:m?`${m[1]}=${m[2]}`:null});
            """)
            visible = _snapshot(session)
            return result(True, out, visible, ops=2, attempts=2)

'''
text = text[:start] + b05 + text[end:]
p.write_text(text)

print("Applied adapter-only fixes:")
print("- Scrapling B04 query-preserving pagination")
print("- Crawl4AI B04 query-preserving pagination")
print("- Crawl4AI B05 retrieval-success semantics + diagnostic note")
print("- Playwright CLI B03/B05 URL handling in page context")
