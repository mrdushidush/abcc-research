#!/usr/bin/env node
// The last gate in v1's chain, ported byte-for-byte and run over the records the
// two probes upstream actually produced.
//
// `taskExecutor.ts:100-115` is the "SAFETY NET" the false-positive-completions
// fix added, and `taskExecutor.ts:513-528` is the predicate it asks.  Both are
// copied verbatim from the donor at d5528ea; the only edits are dropping the
// `this.` receiver and replacing the Prisma/handler calls with a recorded verdict,
// because what is under test is the decision and not the plumbing.
//
// Input: v1_output-results.json, whose rows are the AgentOutput objects v1's own
// parser returned for the six ways a test run can end.
//
// Usage:  node v1_safety_net.mjs

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));

// --- taskExecutor.ts:513-528, verbatim ------------------------------------
function detectTestFailures(agentOutput) {
  // Check 1: success field is explicitly false
  if (agentOutput.success === false) {
    return true;
  }

  // Check 2: test_results string contains FAILURE indicator
  if (typeof agentOutput.test_results === 'string') {
    const tr = agentOutput.test_results.toUpperCase();
    if (tr.includes('FAILURE -') && (tr.includes('FAILED') || tr.includes('ERRORS'))) {
      return true;
    }
  }

  return false;
}

// --- taskExecutor.ts:100-115, verbatim apart from the two awaits ----------
function handleTaskCompletion(result) {
  if (result.output && typeof result.output === 'string') {
    try {
      const agentOutput = JSON.parse(result.output);
      if (detectTestFailures(agentOutput)) {
        return 'redirected to handleTaskFailure';
      }
    } catch {
      // If output isn't valid JSON, skip validation
    }
  }
  return 'marked completed';
}

const rows = JSON.parse(readFileSync(join(here, 'v1_output-results.json'), 'utf8'));

// v1 ships the whole AgentOutput as `result.output`, JSON, from main.py:460.
// The probe upstream kept only the fields the net reads plus the ones an
// operator would see; rebuild the payload from those.
const out = rows.map((r) => {
  const agentOutput = {
    status: r.status,
    confidence: r.confidence,
    summary: r.summary,
    success: r.status === 'SUCCESS' || r.status === 'UNCERTAIN',
    test_results: r.test_results,
    failure_reason: r.failure_reason,
    requires_human_review: r.requires_human_review,
  };
  return {
    case: r.case,
    fn: r.fn,
    status: r.status,
    test_results: r.test_results,
    verdict: handleTaskCompletion({ output: JSON.stringify(agentOutput) }),
  };
});

console.log(JSON.stringify(out, null, 1));

const w = Math.max(...out.map((o) => o.case.length));
for (const o of out) {
  console.error(`${o.fn.padEnd(28)} ${o.case.padEnd(w)}  ${o.status.padEnd(10)}  ${o.verdict}`);
}
const redirected = out.filter((o) => o.verdict !== 'marked completed').length;
console.error(`\nrecords the safety net redirected: ${redirected} of ${out.length}`);
