from __future__ import annotations
import os
import pathlib
import xml.etree.ElementTree as ET

root = pathlib.Path(os.environ.get("BOSS_SOURCE", "boss-source"))
results = root / "composeApp" / "build" / "test-results" / "desktopTest"
out = pathlib.Path("benchmark-summary.md")

cases = {
    "McpToolRegistryCoreTest": "kill switch + invocation/RBAC boundary",
    "McpKillSwitchPersistenceTest": "kill-switch persistence/fail-closed corruption handling",
    "McpPolicyEngineTest": "ALLOW/ASK/DENY + provider-scoped session trust",
    "McpSessionTrustScopingTest": "same-name provider swap regression",
    "McpProviderPolicyTest": "provider-wide ALLOW/DENY precedence",
    "McpPolicyRevocationTest": "tool revocation race",
    "McpProviderRevocationTest": "provider revocation race",
    "McpGovernedInvocationTest": "governed invocation + approval behavior",
    "McpRiskGovernanceIntegrationTest": "risk/mutation classification",
    "McpDestructiveShellAllowTest": "destructive-shell prompt vs standing allow",
    "McpOperationLedgerTest": "ledger persistence/sanitization",
    "McpLedgerChainTest": "ledger tamper evidence and known limits",
}

suites = {}
failures = []
if results.exists():
    for xml_path in results.rglob("TEST-*.xml"):
        try:
            suite = ET.parse(xml_path).getroot()
        except ET.ParseError:
            continue
        name = suite.attrib.get("name", xml_path.stem)
        short = name.rsplit(".", 1)[-1]
        tests = int(float(suite.attrib.get("tests", "0")))
        failed = int(float(suite.attrib.get("failures", "0"))) + int(float(suite.attrib.get("errors", "0")))
        skipped = int(float(suite.attrib.get("skipped", "0")))
        suites[short] = (tests, failed, skipped)
        for tc in suite.findall("testcase"):
            node = tc.find("failure")
            if node is None:
                node = tc.find("error")
            if node is not None:
                failures.append((short, tc.attrib.get("name", "<unknown>"), (node.text or "")[:1500]))

lines = [
    "# BOSS Console Benchmark #1 - CI evidence",
    "",
    "- Requested source ref: " + os.environ.get("BOSS_REF", "unknown"),
    "- Resolved source SHA: " + os.environ.get("BOSS_SHA", "unknown"),
    "- Reported version: " + os.environ.get("BOSS_VERSION", "unknown"),
    "- Source available: " + os.environ.get("BOSS_AVAILABLE", "unknown"),
    "- Gradle test step outcome: " + os.environ.get("TEST_OUTCOME", "unknown"),
    "- Scope: real BOSS governance-core code on a GitHub-hosted Linux runner; not a packaged GUI end-to-end test.",
    "",
    "## Case results",
    "",
    "| Test class | Benchmark purpose | Result | Tests |",
    "|---|---|---:|---:|",
]

for cls, purpose in cases.items():
    data = suites.get(cls)
    if not data:
        result, count = "INCONCLUSIVE / not executed", 0
    else:
        tests, failed, skipped = data
        result = "PASS" if failed == 0 else "FAIL"
        if tests and skipped == tests:
            result = "INCONCLUSIVE / skipped"
        count = tests
    lines.append("| " + cls + " | " + purpose + " | " + result + " | " + str(count) + " |")

if failures:
    lines += ["", "## Failures", ""]
    for cls, name, detail in failures:
        lines += ["### " + cls + " :: " + name, "", detail, ""]

lines += [
    "",
    "## Interpretation guard",
    "",
    "Passing verifies the shipped governance core under deterministic dummy-provider fixtures.",
    "It does not prove OS sandboxing, hostile-plugin containment, GUI approval ergonomics, or packaged-app IPC behavior.",
]
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(out.read_text(encoding="utf-8"))
