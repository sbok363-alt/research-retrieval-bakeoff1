# Adapter fix r1

This changes **adapter implementation only**. The frozen v0.1 fixture server, task definitions, expected values, grading rules, candidate versions, and three-run median policy are unchanged.

Repairs after valid CI run 36046159316:

- B04: Scrapling and Crawl4AI adapters used the docs-style canonicalizer, which intentionally removes query strings. That collapsed `?page=1`, `?page=2`, and `?page=3` into one URL. Pagination now tracks the full navigation URL.
- Playwright CLI B03/B05: `run-code` does not expose Node's global `URL` constructor in that execution context. URL parsing is moved into page/browser context or avoided by reading the anchor's absolute `href`.
- Crawl4AI B05: scoring behavior is unchanged, but the adapter now records `success` and `error_message` so a 200/content result with `success=False` can be diagnosed.

Why a rerun is required: the first valid CI run contains adapter-caused false failures, so its affected-task scores must not be treated as final candidate capability scores.

Corrected source archive SHA-256: `bcc09c8efdce00ddf77e7a63be0206d86df18ad0336503d89a1c82114f8eb18a`.
