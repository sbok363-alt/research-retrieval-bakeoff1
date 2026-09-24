# Adapter revision r1

Benchmark v0.1 fixtures, expected outputs, task weights, grader, and three-repeat rule are unchanged.

This revision fixes generic harness compatibility bugs discovered by run #19:

1. Scrapling and Crawl4AI pagination adapters no longer canonicalize away query strings when tracking visited pagination URLs.
2. Crawl4AI session retrieval judges adapter success from the returned HTTP status rather than Crawl4AI's internal `success` flag when a valid 200 response was retrieved.
3. Playwright CLI URL resolution avoids relying on the run-code host's missing global `URL`; URL parsing is performed in browser page context.

These are adapter corrections only. No candidate-specific expected answer, fixture, task weight, or grader rule was changed.
