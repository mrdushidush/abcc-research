// How much of v1's semantic score is substring noise?
//
// v1 matches keywords with `text.includes(k)` (taskRouter.ts:175-190) and BCF
// with `text.contains(k)` (router.rs:257-275).  Neither anchors.  The brief
// names two: 'api' inside "rapid", 'add' inside "address".
//
// A CRUDE anchored rule would manufacture a defect, because most unanchored
// hits are inflections ('returns' for 'return') that a keyword scorer plainly
// means to catch.  So every substring-only hit is classified into three, and
// the rescoring is reported for the conservative class alone:
//
//   INFLECTION  keyword at word start + a known English suffix   -> intended
//   COMPOUND    keyword at word start, remainder is other letters -> arguable
//   EMBEDDED    keyword does not start the word                   -> FALSE FIRE
//
// Only EMBEDDED is counted as a defect.  It cannot be argued for: the token the
// scorer matched is not the word it names.
import { readFileSync, readdirSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const CORPUS = 'D:/dev/ABCC_20_powerd_by_claudette/corpus/suites';

// Verbatim from taskRouter.ts:138-169 (dist and src agree).
const IND = {
  trivial: ['simple', 'basic', 'single', 'just', 'only', 'straightforward'],
  low: ['create', 'add', 'write', 'make', 'return', 'print', 'output'],
  moderate: ['handle', 'validate', 'check', 'multiple', 'combine', 'integrate',
    'parse', 'convert', 'transform', 'edge case', 'error handling',
    'if else', 'switch', 'conditional'],
  high: ['refactor', 'redesign', 'optimize', 'async', 'concurrent', 'parallel',
    'nested', 'recursive', 'complex', 'algorithm', 'data structure',
    'database', 'api', 'service', 'module', 'component',
    'cache', 'lru', 'linked list', 'hash map', 'hashmap', 'tree', 'graph',
    'queue', 'stack', 'heap', 'binary', 'sorting', 'searching',
    'o(1)', 'o(n)', 'o(log', 'time complexity', 'space complexity'],
  extreme: ['architect', 'design system', 'framework', 'infrastructure',
    'scalab', 'distributed', 'microservice', 'migration', 'legacy',
    'security', 'authentication', 'authorization', 'real-time'],
};

const SUFFIX = ['s', 'es', 'd', 'ed', 'ing', 'er', 'ers', 'ors', 'or', 'ly',
  'ion', 'ions', 'ive', 'ible', 'able', 'al', 'ility', 'ity', 'ance', 'ment'];

function words(text) {
  return text.match(/[a-z]+/g) || [];
}

// Classify EVERY occurrence of keyword k in text that is not a standalone word.
function classify(text, k) {
  const out = [];
  if (!/^[a-z]+$/.test(k)) return out;   // 'o(1)', 'edge case' etc: not word-like
  for (const w of new Set(words(text))) {
    if (w === k) continue;               // exact word: a real hit, not noise
    const i = w.indexOf(k);
    if (i < 0) continue;
    if (i > 0) { out.push({ word: w, cls: 'EMBEDDED' }); continue; }
    const rest = w.slice(k.length);
    out.push({ word: w, cls: SUFFIX.includes(rest) ? 'INFLECTION' : 'COMPOUND' });
  }
  return out;
}

// A hit under a given matcher.
const rawHit = (t, k) => t.includes(k);
// "clean" matcher: the keyword counts only if it appears as a whole word, or as
// an inflection/compound of it.  EMBEDDED occurrences alone never count.
function cleanHit(text, k) {
  if (!/^[a-z]+$/.test(k)) return text.includes(k);
  for (const w of new Set(words(text))) {
    if (w === k) return true;
    const i = w.indexOf(k);
    if (i === 0) return true;            // inflection or compound: allowed
  }
  return false;
}

// v1's tier arithmetic, so the delta is measurable in SCORE POINTS.
function tierScore(text, hit) {
  let max = 0;
  const ex = IND.extreme.filter((k) => hit(text, k)).length;
  if (ex >= 2) max = Math.max(max, 4); else if (ex === 1) max = Math.max(max, 3);
  const hi = IND.high.filter((k) => hit(text, k)).length;
  if (hi >= 3) max = Math.max(max, 3); else if (hi >= 1) max = Math.max(max, 2);
  const mo = IND.moderate.filter((k) => hit(text, k)).length;
  if (mo >= 2) max = Math.max(max, 2); else if (mo === 1) max = Math.max(max, 1);
  return max;
}

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

const counts = { INFLECTION: 0, COMPOUND: 0, EMBEDDED: 0 };
const embedded = [];
const perKeyword = new Map();
let tasks = 0, tasksEmbedded = 0, tierChanged = 0;
const changedTasks = [];

for (const suite of ['q56', 'u100', 'k']) {
  const tdir = join(CORPUS, suite, 'tasks');
  if (!existsSync(tdir)) continue;
  for (const id of readdirSync(tdir)) {
    const dir = join(tdir, id);
    if (!existsSync(join(dir, 'task.toml'))) continue;
    const toml = readFileSync(join(dir, 'task.toml'), 'utf8');
    const pp = join(dir, 'prompt.txt');
    const prompt = existsSync(pp) ? readFileSync(pp, 'utf8') : '';
    const title = tomlScalar(toml, 'title') ?? id;
    const text = `${title} ${prompt}`.toLowerCase();
    tasks++;
    let anyEmbedded = false;
    for (const [tier, ks] of Object.entries(IND)) {
      for (const k of ks) {
        if (!rawHit(text, k)) continue;
        const exact = words(text).includes(k);
        for (const c of classify(text, k)) {
          counts[c.cls]++;
          if (c.cls === 'EMBEDDED' && !exact) {
            anyEmbedded = true;
            embedded.push({ suite, id, tier, keyword: k, inside: c.word });
            perKeyword.set(k, (perKeyword.get(k) || 0) + 1);
          }
        }
      }
    }
    if (anyEmbedded) tasksEmbedded++;
    const a = tierScore(text, rawHit), b = tierScore(text, cleanHit);
    if (a !== b) { tierChanged++; changedTasks.push({ suite, id, raw: a, clean: b }); }
  }
}

console.log(`tasks scanned: ${tasks}`);
console.log(`substring occurrences by class: ${JSON.stringify(counts)}`);
console.log(`tasks with >=1 EMBEDDED-only keyword hit (a false fire): ${tasksEmbedded}`);
console.log(`tasks whose SEMANTIC tier score changes once EMBEDDED-only hits are dropped: ${tierChanged}`);
console.log(`  ${JSON.stringify(changedTasks)}`);
console.log('\nEMBEDDED false fires by keyword:');
for (const [k, n] of [...perKeyword].sort((a, b) => b[1] - a[1])) {
  const ex = [...new Set(embedded.filter((s) => s.keyword === k).map((s) => s.inside))];
  console.log(`  ${k.padEnd(12)} ${String(n).padStart(3)}  ${ex.slice(0, 8).join(', ')}`);
}
console.log('\nevery EMBEDDED false fire:');
for (const s of embedded) {
  console.log(`  ${s.suite}/${s.id.padEnd(28)} ${s.tier}:'${s.keyword}' inside '${s.inside}'`);
}
