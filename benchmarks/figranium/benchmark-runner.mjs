import fs from "node:fs";
import path from "node:path";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const targetUrl = process.env.BENCH_TARGET_URL || "http://127.0.0.1:11346/";
const apiKey = process.env.FIGRANIUM_API_KEY;
if (!apiKey) throw new Error("FIGRANIUM_API_KEY missing");

const transport = new StdioClientTransport({
  command: "node",
  args: [path.resolve("dist/index.js")],
  env: { ...process.env, FIGRANIUM_BASE_URL: process.env.FIGRANIUM_BASE_URL || "http://127.0.0.1:11345", FIGRANIUM_API_KEY: apiKey }
});
const client = new Client({ name: "figranium-benchmark", version: "1.0.0" }, { capabilities: {} });

function textOf(result) {
  return (result?.content || []).filter(x => x.type === "text").map(x => x.text || "").join("\n");
}
function jsonOf(result) {
  const t = textOf(result);
  try { return JSON.parse(t); } catch { return { raw: t }; }
}
function findId(value) {
  if (!value || typeof value !== "object") return null;
  for (const key of ["id", "taskId", "task_id"]) {
    if (typeof value[key] === "string" && value[key]) return value[key];
  }
  if (value.task && typeof value.task === "object") {
    const nested = findId(value.task);
    if (nested) return nested;
  }
  for (const v of Object.values(value)) {
    const nested = findId(v);
    if (nested) return nested;
  }
  return null;
}
function findByKey(value, key, out = []) {
  if (!value || typeof value !== "object") return out;
  if (Object.prototype.hasOwnProperty.call(value, key)) out.push(value[key]);
  for (const v of Object.values(value)) findByKey(v, key, out);
  return out;
}

const checks = {};
const evidence = {};
let taskId = null;

try {
  await client.connect(transport);

  const tools = await client.listTools();
  const toolNames = (tools.tools || []).map(t => t.name);
  checks.toolsVisible = ["create_task", "task_update", "task_execute", "execution_list"].every(n => toolNames.includes(n));
  evidence.tools = toolNames;

  const resource = await client.readResource({ uri: "figranium://schemas/task-v1.json" });
  const schemaText = (resource.contents || []).map(c => c.text || "").join("\n");
  checks.schemaReadable = schemaText.includes('"actions"') && schemaText.includes('"mode"');
  evidence.schemaBytes = schemaText.length;

  const invalid = await client.callTool({
    name: "create_task",
    arguments: {
      name: "Benchmark Invalid Task",
      url: targetUrl,
      mode: "agent",
      actions: [{ type: "clikc", selector: "#go" }]
    }
  });
  const invalidText = textOf(invalid);
  checks.richDiagnostics = invalid.isError === true && invalidText.includes("Schema Validation Failed") && invalidText.includes("clikc");
  evidence.invalidDiagnostic = invalidText;

  const create = await client.callTool({
    name: "create_task",
    arguments: {
      name: "Figranium Benchmark Repair Loop",
      description: "Disposable local-only benchmark task",
      url: targetUrl,
      mode: "agent",
      wait: 0.2,
      statelessExecution: true,
      disableRecording: true,
      variables: {
        name: { type: "string", value: "Ada" }
      },
      actions: [
        { type: "type", selector: "#name", value: "{$name}", typeMode: "replace" },
        { type: "click", selector: "#go" },
        { type: "wait_selector", selector: "#result.ready" }
      ],
      extractionFormat: "json",
      extractionScript: "return { message: document.querySelector('#wrong-target')?.textContent?.trim() || '' };"
    }
  });
  checks.validTaskCreated = create.isError !== true;
  evidence.create = jsonOf(create);
  taskId = findId(evidence.create);

  if (!taskId) {
    const listed = await client.callTool({ name: "task_list", arguments: {} });
    evidence.taskListAfterCreate = jsonOf(listed);
    const listText = JSON.stringify(evidence.taskListAfterCreate);
    if (listText.includes("Figranium Benchmark Repair Loop")) {
      const candidates = [];
      const walk = (v) => {
        if (!v || typeof v !== "object") return;
        if (v.name === "Figranium Benchmark Repair Loop" && typeof v.id === "string") candidates.push(v.id);
        for (const x of Object.values(v)) walk(x);
      };
      walk(evidence.taskListAfterCreate);
      taskId = candidates[0] || null;
    }
  }
  checks.taskIdResolved = !!taskId;
  if (!taskId) throw new Error("Could not resolve created task ID");

  const firstRun = await client.callTool({
    name: "task_execute",
    arguments: { taskId, variables: { name: "Grace" } }
  });
  evidence.firstRun = jsonOf(firstRun);
  const firstText = JSON.stringify(evidence.firstRun);
  const firstOutcomes = findByKey(evidence.firstRun, "outcome").concat(findByKey(evidence.firstRun, "status"));
  checks.firstRunCompleted = firstRun.isError !== true;
  checks.semanticFailureDetected = !firstText.includes("Hello, Grace!");
  evidence.firstRunOutcomeCandidates = firstOutcomes;

  const update = await client.callTool({
    name: "task_update",
    arguments: {
      taskId,
      extractionScript: "return { message: document.querySelector('#result')?.textContent?.trim() || '' };"
    }
  });
  checks.repairPersisted = update.isError !== true;
  evidence.update = jsonOf(update);

  const repairedRun = await client.callTool({
    name: "task_execute",
    arguments: { taskId, variables: { name: "Grace" } }
  });
  evidence.repairedRun = jsonOf(repairedRun);
  const repairedText = JSON.stringify(evidence.repairedRun);
  checks.repairedRunCompleted = repairedRun.isError !== true;
  checks.repairedOutputCorrect = repairedText.includes("Hello, Grace!");

  const executions = await client.callTool({ name: "execution_list", arguments: {} });
  evidence.executions = jsonOf(executions);
  checks.executionHistoryPresent = JSON.stringify(evidence.executions).includes(taskId);

} finally {
  if (taskId) {
    try {
      const del = await client.callTool({ name: "task_delete", arguments: { taskId } });
      evidence.delete = jsonOf(del);
      checks.cleanup = del.isError !== true;
    } catch (e) {
      checks.cleanup = false;
      evidence.cleanupError = String(e);
    }
  }
  try { await client.close(); } catch {}
}

const required = [
  "toolsVisible",
  "schemaReadable",
  "richDiagnostics",
  "validTaskCreated",
  "taskIdResolved",
  "firstRunCompleted",
  "semanticFailureDetected",
  "repairPersisted",
  "repairedRunCompleted",
  "repairedOutputCorrect",
  "executionHistoryPresent",
  "cleanup"
];
const passed = required.every(k => checks[k] === true);

const result = {
  passed,
  note: "The repair loop is driven by a deterministic benchmark client, not an LLM. It exercises the exact MCP interfaces an agent would use.",
  source: {
    figraniumRef: process.env.FIGRANIUM_REF || "unknown",
    figraniumSha: process.env.FIGRANIUM_SHA || "unknown",
    mcpRef: process.env.FIGRANIUM_MCP_REF || "unknown",
    mcpSha: process.env.FIGRANIUM_MCP_SHA || "unknown"
  },
  checks,
  evidence
};
fs.writeFileSync(process.env.BENCH_RESULT_JSON || "../figranium-benchmark-result.json", JSON.stringify(result, null, 2));

const rows = required.map(k => "| " + k + " | " + (checks[k] ? "PASS" : "FAIL") + " |").join("\n");
const md = [
  "# Figranium Benchmark #1",
  "",
  "**Overall: " + (passed ? "PASS" : "FAIL") + "**",
  "",
  "This is a real Figranium + Playwright + MCP execution against a local deterministic page.",
  "The repair decision is driven by a deterministic benchmark client rather than an LLM, so this proves the MCP repair loop mechanics, not model reasoning quality.",
  "",
  "| Check | Result |",
  "|---|---|",
  rows,
  "",
  "## Key interpretation",
  "",
  "- Invalid task input must produce structured schema diagnostics.",
  "- The first valid run is intentionally semantically wrong even if execution itself completes.",
  "- The task is then patched through task_update and executed again.",
  "- PASS requires the repaired run to contain the verified output: Hello, Grace!.",
  ""
].join("\n");
fs.writeFileSync(process.env.BENCH_SUMMARY_MD || "../figranium-benchmark-summary.md", md);
console.log(md);
if (!passed) process.exitCode = 1;
