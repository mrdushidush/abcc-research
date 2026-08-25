// W6 item 7 — v1's review-scheduling decision, ported verbatim and run.
//
// The brief asks what verifies an artifact with no test. v1's answer is its
// graduated review, and the one artifact type in the family that is pure prose
// is `review` itself. This runs the donor's own decision function over the
// donor's own test inputs.
//
// Ported byte-for-byte from `packages/api/src/services/codeReviewService.ts`
// (donor `d5528ea`): the constants at :53-60 and `getReviewDecision` at
// :110-160, minus the Redis save (a no-op TODO at :104-106) and the logger.
// Nothing below is paraphrased.
//
//   node v1_review.mjs

// --- codeReviewService.ts:53-60, verbatim -------------------------------
const SKIP_REVIEW_TYPES = ['review', 'decomposition', 'debug'];
const OLLAMA_REVIEW_INTERVAL = parseInt(process.env.OLLAMA_REVIEW_INTERVAL || '5', 10);
const OPUS_REVIEW_INTERVAL = parseInt(process.env.OPUS_REVIEW_INTERVAL || '10', 10);
const OPUS_MIN_COMPLEXITY = 5;

class CodeReviewService {
  enabled = true;
  ollamaTaskCounter = 0;
  allTaskCounter = 0;

  // --- codeReviewService.ts:110-160, verbatim --------------------------
  getReviewDecision(task, executedByModel) {
    if (!this.enabled) {
      return { shouldReview: false, reviewer: null, reason: 'Review service disabled' };
    }

    // Skip certain task types
    if (SKIP_REVIEW_TYPES.includes(task.taskType || '')) {
      return { shouldReview: false, reviewer: null, reason: `Skipping ${task.taskType} task type` };
    }

    // Skip failed tasks
    if (task.status !== 'completed') {
      return { shouldReview: false, reviewer: null, reason: 'Task not completed' };
    }

    const complexity = task.complexity || 5;
    const isOllamaTask = executedByModel === 'ollama' || !executedByModel;

    this.allTaskCounter++;
    if (isOllamaTask) {
      this.ollamaTaskCounter++;
    }

    if (isOllamaTask && this.ollamaTaskCounter % OLLAMA_REVIEW_INTERVAL === 0) {
      return {
        shouldReview: true,
        reviewer: 'haiku',
        reason: `Haiku review: Ollama task #${this.ollamaTaskCounter} (every ${OLLAMA_REVIEW_INTERVAL}th)`,
      };
    }

    if (complexity > OPUS_MIN_COMPLEXITY && this.allTaskCounter % OPUS_REVIEW_INTERVAL === 0) {
      return {
        shouldReview: true,
        reviewer: 'opus',
        reason: `Opus review: Task #${this.allTaskCounter} (every ${OPUS_REVIEW_INTERVAL}th, complexity ${complexity.toFixed(1)} > ${OPUS_MIN_COMPLEXITY})`,
      };
    }

    return {
      shouldReview: false,
      reviewer: null,
      reason: `No review needed (Ollama: ${this.ollamaTaskCounter}/${OLLAMA_REVIEW_INTERVAL}, All: ${this.allTaskCounter}/${OPUS_REVIEW_INTERVAL})`,
    };
  }
}

// --- taskRouter.ts:200-213, verbatim ------------------------------------
function typeScore(task) {
  let score = 0;
  switch (task.taskType) {
    case 'code':
      score += 0.5;
      break;
    case 'test':
      score += 1.5;
      break;
    case 'review':
      score += 2.5;
      break;
    case 'decomposition':
      score += 3;
      break;
  }
  return score;
}

// --- shared/src/index.ts:53 and api/src/routes/tasks.ts:13 --------------
const TASK_TYPE_SHARED = ['code', 'test', 'review', 'debug', 'refactor'];
const TASK_TYPE_ROUTE = ['code', 'test', 'review', 'debug', 'refactor', 'decomposition'];

const out = { donor: 'd5528ea', cases: [], vocabulary: {}, type_score: {} };

// 1. The donor's own two tests, verbatim from
//    packages/api/src/services/__tests__/codeReviewService.test.ts:34-48.
for (const t of [
  { name: "donor test 'should not review decomposition tasks'",
    task: { type: 'decomposition', status: 'completed' } },
  { name: "donor test 'should not review debug tasks'",
    task: { type: 'debug', status: 'completed' } },
]) {
  const s = new CodeReviewService();
  const d = s.getReviewDecision(t.task, 'ollama');
  out.cases.push({
    name: t.name, task: t.task, shouldReview: d.shouldReview,
    reason: d.reason,
    assertion_holds: d.shouldReview === false,
    skipped_for_the_stated_reason: d.reason.startsWith('Skipping'),
  });
}

// 2. The same tasks with the field the code actually reads.
for (const tt of ['decomposition', 'debug', 'review']) {
  const s = new CodeReviewService();
  const d = s.getReviewDecision({ taskType: tt, status: 'completed' }, 'ollama');
  out.cases.push({
    name: `taskType: '${tt}' (the field getReviewDecision reads)`,
    task: { taskType: tt, status: 'completed' },
    shouldReview: d.shouldReview, reason: d.reason,
    assertion_holds: d.shouldReview === false,
    skipped_for_the_stated_reason: d.reason.startsWith('Skipping'),
  });
}

// 3. Ten consecutive prose-producing tasks that are NOT in the skip list.
{
  const s = new CodeReviewService();
  const seen = [];
  for (let i = 1; i <= 10; i++) {
    const d = s.getReviewDecision(
      { taskType: 'refactor', status: 'completed', complexity: 9 }, 'ollama');
    seen.push(d.shouldReview ? d.reviewer : null);
  }
  out.cases.push({
    name: "ten 'refactor' tasks at complexity 9, one service instance",
    reviewers: seen,
    reviewed: seen.filter(Boolean).length,
  });
}

// 4. Can the Opus branch fire at all? Haiku is `ollamaTaskCounter % 5`, Opus is
//    `allTaskCounter % 10`. When every task is an Ollama task the two counters
//    are equal, and every multiple of 10 is a multiple of 5 — so the Haiku
//    branch returns first, every time. Run a pure stream and a mixed one.
for (const [name, models] of [
  ['30 tasks, all ollama', Array.from({ length: 30 }, () => 'ollama')],
  ['30 tasks, alternating sonnet / ollama',
    Array.from({ length: 30 }, (_, i) => (i % 2 ? 'ollama' : 'claude-sonnet-5'))],
  ['30 tasks, alternating ollama / sonnet (the same stream, other phase)',
    Array.from({ length: 30 }, (_, i) => (i % 2 ? 'claude-sonnet-5' : 'ollama'))],
  ['30 tasks, all sonnet',
    Array.from({ length: 30 }, () => 'claude-sonnet-5')],
]) {
  const s = new CodeReviewService();
  const seen = [];
  for (const m of models) {
    const d = s.getReviewDecision(
      { taskType: 'code', status: 'completed', complexity: 9 }, m);
    seen.push(d.shouldReview ? d.reviewer : null);
  }
  out.cases.push({
    name, haiku: seen.filter((r) => r === 'haiku').length,
    opus: seen.filter((r) => r === 'opus').length,
    unreviewed: seen.filter((r) => r === null).length,
  });
}

// 5. The default complexity, which is a falsy-coalesce.
for (const c of [undefined, 0, 5, 5.5, 9]) {
  const s = new CodeReviewService();
  s.allTaskCounter = 9;          // the next task is #10, the Opus tick
  s.ollamaTaskCounter = 9;
  const d = s.getReviewDecision(
    { taskType: 'code', status: 'completed', complexity: c }, 'claude-sonnet-5');
  out.cases.push({
    name: `complexity ${String(c)} on the Opus tick (task #10, non-ollama)`,
    reviewer: d.reviewer, reason: d.reason,
  });
}

out.vocabulary = {
  shared_TaskType: TASK_TYPE_SHARED,
  route_zod_enum: TASK_TYPE_ROUTE,
  in_route_not_in_type: TASK_TYPE_ROUTE.filter((t) => !TASK_TYPE_SHARED.includes(t)),
  skip_review_types: SKIP_REVIEW_TYPES,
  skip_entries_not_in_shared_type: SKIP_REVIEW_TYPES.filter(
    (t) => !TASK_TYPE_SHARED.includes(t)),
  documentation_task_type: TASK_TYPE_ROUTE.some((t) => /doc/i.test(t)),
};

out.type_score = Object.fromEntries(
  TASK_TYPE_ROUTE.map((t) => [t, typeScore({ taskType: t })]));

console.log(JSON.stringify(out, null, 1));
