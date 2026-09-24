# Freeze record

This benchmark definition is frozen as **v0.1** on **2026-09-24**.

A valid modification requires:

1. copy the suite to a new version directory;
2. increment the benchmark version;
3. record the reason for the change;
4. rerun every candidate from zero;
5. never compare v0.1 and modified-v0.1 scores as if they were the same benchmark.

Known design choice: wall-clock speed is deliberately informational only in v0.1 because host/browser startup variance can swamp small differences. The suite records model-visible characters and retrieval operations for analysis, but correctness and deterministic behavior dominate the score.

Source bundle SHA-256: `eaa8d4b69846011d3d4cce65a6189b63aa4632d48181c38e35379d614c419bc3`.
