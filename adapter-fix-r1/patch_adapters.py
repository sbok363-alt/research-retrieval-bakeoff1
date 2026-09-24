from __future__ import annotations

import sys
from pathlib import Path

root = Path(sys.argv[1])
adapters = root / "adapters"


def replace_section(path: Path, start_marker: str, end_marker: str, replacement: str) -> None:
    text = path.read_text()
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    path.write_text(text[:start] + replacement + text[end:])


# Scrapling B04: preserve ?page=N while traversing pagination.
p = adapters / "scrapling_adapter.py"
replace_section(
    p,
    '    if tid == "B04":',
    '    if tid == "B05":',
    '''    if tid == "B04":
        ids: list[str] = []
        url = abs_url("/pagination?page=1")
        seen_pages: set[str] = set()
        visible_parts: list[str] = []
        ops = 0
        while url and url not in seen_pages:
            seen_pages.add(url)
            p = Fetcher.get(url)
            ops += 1
            ids.extend([str(x) for x in p.css("[data-id]::attr(data-id)").getall()])
            visible_parts.append(_visible_markdown(p))
            links = html_links(p.html_content, url)
            nxt = next((x["href"] for x in links if "next" in x["rel"].lower().split()), "")
            url = nxt
        out = {"item_ids": list(dict.fromkeys(ids)), "unique_count": len(set(ids))}
        return result(True, out, "\\n".join(visible_parts), ops=ops, attempts=ops)

''',
)

# Crawl4AI B04: same pagination correction.
p = adapters / "crawl4ai_adapter.py"
replace_section(
    p,
    '        if tid == "B04":',
    '        if tid == "B05":',
    '''        if tid == "B04":
            ids: list[str] = []
            url = abs_url("/pagination?page=1")
            seen_pages: set[str] = set()
            visible_parts: list[str] = []
            ops = 0
            while url and url not in seen_pages:
                seen_pages.add(url)
                r = await crawler.arun(url, config=base_cfg)
                ops += 1
                ids.extend(data_ids(r.html))
                visible_parts.append(_md_text(r.markdown))
                links = html_links(r.html, url)
                nxt = next((x["href"] for x in links if "next" in x["rel"].lower().split()), "")
                url = nxt
            out = {"item_ids": list(dict.fromkeys(ids)), "unique_count": len(set(ids))}
            return result(True, out, "\\n".join(visible_parts), ops=ops, attempts=ops)

''',
)

# Crawl4AI B05: the frozen task grades the returned HTTP response and evidence.
# Keep Crawl4AI's contradictory internal success flag in notes rather than
# converting a correct 200/evidence result into an adapter failure.
replace_section(
    p,
    '        if tid == "B05":',
    '        if tid in ("B06", "B07"):',
    '''        if tid == "B05":
            sid = "bakeoff-session"
            r1 = await crawler.arun(abs_url("/session/start"), config=base_cfg, session_id=sid)
            links = html_links(r1.html, r1.url)
            target = links[0]["href"] if links else abs_url("/session/private")
            r2 = await crawler.arun(target, config=base_cfg, session_id=sid)
            visible = _md_text(r2.markdown)
            out = {"status": int(r2.status_code or 0), "secret_fact": first_fact(visible)}
            try:
                await crawler.crawler_strategy.kill_session(sid)
            except Exception:
                pass
            ok = int(r2.status_code or 0) == 200 and first_fact(visible) is not None
            return result(ok, out, visible, ops=2, attempts=2, notes=f"crawl4ai success={bool(r2.success)}; error={getattr(r2, 'error_message', '')!r}")

''',
)

# Playwright CLI B03/B05: URL parsing must happen inside page context because
# the run-code execution scope does not expose Node's global URL constructor.
p = adapters / "playwright_cli_adapter.py"
replace_section(
    p,
    '        if tid == "B03":',
    '        if tid == "B04":',
    '''        if tid == "B03":
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
                    for(const m of text.matchAll(/\\\\b([A-Z][A-Z0-9_]*)=([^\\\\s<>{}\\\\[\\\\],;]+)/g)) facts.add(`${m[1]}=${m[2]}`);
                  }
                  for(const link of meta.links){ if(link.origin===origin && link.pathname.startsWith('/docs/')) { const canon=link.origin+link.pathname; if(!seen.has(canon)) q.push(canon); } }
                }
                return JSON.stringify({canonical_pages:[...pages].sort(),facts:[...facts].sort(),max_duplicate_canonical_fetches:Math.max(0,...Object.values(counts))});
            """)
            return result(True, out, json.dumps(out, sort_keys=True), ops=max(ops, len(out.get("canonical_pages", []))+1), attempts=max(1, len(out.get("canonical_pages", []))+1))

''',
)

replace_section(
    p,
    '        if tid == "B05":',
    '        if tid in ("B06", "B07"):',
    '''        if tid == "B05":
            _open(session, abs_url("/session/start")); ops += 1
            out = _run_code_json(session, """
                const absoluteHref=await page.locator('a[href]').first().evaluate(a=>a.href);
                const response=await page.goto(absoluteHref); await page.waitForLoadState('domcontentloaded');
                const text=await page.locator('body').innerText();
                const m=text.match(/\\\\b([A-Z][A-Z0-9_]*)=([^\\\\s<>{}\\\\[\\\\],;]+)/);
                return JSON.stringify({status:response?.status()||0, secret_fact:m?`${m[1]}=${m[2]}`:null});
            """)
            visible = _snapshot(session)
            return result(True, out, visible, ops=2, attempts=2)

''',
)

print("Applied adapter-only fixes")
