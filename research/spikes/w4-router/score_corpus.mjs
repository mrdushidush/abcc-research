// Score every corpus task with the DONOR'S OWN COMPILED SCORER.
// Not a port: this imports v1's dist/services/taskRouter.js and calls
// TaskRouter.prototype.calculateComplexity, the same function routeTask() calls.
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const DONOR = 'file:///D:/dev/agent-battle-command-center/packages/api/dist/services/taskRouter.js';
const { TaskRouter } = await import(DONOR);
const router = new TaskRouter(null);

const CORPUS = 'D:/dev/ABCC_20_powerd_by_claudette/corpus/suites';

// Minimal TOML scalar reader: first top-level `key = "..."` line.
function tomlScalar(src, key) {
  for (const line of src.split(/\r?\n/)) {
    const t = line.trim();
    if (!t.startsWith(key)) continue;
    const rest = t.slice(key.length).trim();
    if (!rest.startsWith('=')) continue;
    const v = rest.slice(1).trim();
    if (v.startsWith('"') && v.length > 1) {
      const end = v.lastIndexOf('"');
      if (end > 0) return v.slice(1, end);
    }
    return null;
  }
  return null;
}

const rows = [];
for (const suite of ['q56', 'u100', 'k']) {
  const tdir = join(CORPUS, suite, 'tasks');
  if (!existsSync(tdir)) continue;
  for (const id of readdirSync(tdir)) {
    const dir = join(tdir, id);
    const tomlPath = join(dir, 'task.toml');
    if (!existsSync(tomlPath)) continue;
    const toml = readFileSync(tomlPath, 'utf8');
    const promptPath = join(dir, 'prompt.txt');
    const prompt = existsSync(promptPath) ? readFileSync(promptPath, 'utf8') : '';
    const title = tomlScalar(toml, 'title') ?? id;
    const lang = tomlScalar(toml, 'lang');
    const kind = tomlScalar(toml, 'kind');

    // v1's routing-time inputs: title + description, taskType, currentIteration=0.
    // The corpus has no taskType; every task here is code, which is v1's 'code' (+0.5).
    const withTitle = router.calculateComplexity({
      title, description: prompt, taskType: 'code', currentIteration: 0,
    });
    // Sensitivity: the corpus title is SYNTHESIZED from the prompt's first sentence
    // (SPEC caveat), so title+description double-counts. Score with no title too.
    const noTitle = router.calculateComplexity({
      title: '', description: prompt, taskType: 'code', currentIteration: 0,
    });
    // And with no taskType bonus, to separate the constant from the text.
    const noType = router.calculateComplexity({
      title, description: prompt, taskType: null, currentIteration: 0,
    });

    rows.push({
      suite, id, lang, kind,
      words: prompt.trim().split(/\s+/).filter(Boolean).length,
      chars: prompt.length,
      has_prompt: prompt.length > 0,
      score: withTitle, score_no_title: noTitle, score_no_type: noType,
    });
  }
}
process.stdout.write(rows.map((r) => JSON.stringify(r)).join('\n') + '\n');
