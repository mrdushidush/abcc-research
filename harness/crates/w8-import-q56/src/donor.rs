//! Stage 1 — extract. Reads Q56 out of a commit, never out of a working tree.
//!
//! The donor lives on Claudette's unmerged `battery/q50-quality-corpus` branch while `main` carries
//! a different, older A-K battery. Reading through `git show <commit>:<path>` rather than through
//! the filesystem is what lets the import name an exact commit, and it means the importer can never
//! be pointed at a dirty working copy by accident — the standing rule is that no donor is edited,
//! and this is the version of it that a program can enforce.

use std::collections::BTreeMap;
use std::path::Path;
use std::process::Command;

/// One row of `manifest-q50.tsv`. The manifest is the boundary of the suite, **not** the directory
/// listing: the same donor directory also holds the older A-K battery and four `T01`-`T04` tasks,
/// and importing by `ls` would silently pull in tasks that were never gated into Q56.
#[derive(Debug, Clone)]
pub struct Row {
    pub id: String,
    /// The donor's own column: `rust` | `python` | `js` | `ts` | `shell`.
    pub lang: String,
    pub kind: String,
    /// The fixture directory name. Equal to `id` for every current row; read rather than assumed.
    pub fixture_dir: String,
    pub timeout_s: u32,
    /// The whole tab-separated line, carried into `donor_tags` verbatim.
    pub raw: String,
}

pub struct Donor {
    repo: String,
    commit: String,
    base: String,
}

#[derive(Debug)]
pub struct DonorTask {
    pub row: Row,
    pub prompt: String,
    /// Relative path within the fixture -> contents.
    pub fixture: BTreeMap<String, String>,
    pub refsol: BTreeMap<String, String>,
    pub verify: String,
}

impl Donor {
    pub fn new(repo: &Path, commit: &str, base: &str) -> Self {
        Donor {
            repo: repo.display().to_string(),
            commit: commit.to_string(),
            base: base.trim_end_matches('/').to_string(),
        }
    }

    fn git(&self, args: &[&str]) -> Result<Vec<u8>, String> {
        let out = Command::new("git")
            .arg("-C")
            .arg(&self.repo)
            .args(args)
            .output()
            .map_err(|e| format!("cannot run git in {}: {e}", self.repo))?;
        if !out.status.success() {
            return Err(format!(
                "git {} failed: {}",
                args.join(" "),
                String::from_utf8_lossy(&out.stderr).trim()
            ));
        }
        Ok(out.stdout)
    }

    /// Read one blob. **Normalises CRLF to LF at read**, exactly as `w8-import::donor::read` does.
    /// The U100 donor was entirely CRLF and it silently emptied two reconstructed fixtures before
    /// anyone noticed (F22); it has since produced a false difference three more times. Q56 is LF
    /// today — checked, not assumed — and normalising anyway costs nothing and closes the class.
    pub fn read(&self, rel: &str) -> Result<String, String> {
        let spec = format!("{}:{}/{}", self.commit, self.base, rel);
        let bytes = self.git(&["show", &spec])?;
        let text = String::from_utf8(bytes).map_err(|e| format!("{rel} is not UTF-8: {e}"))?;
        Ok(text.replace("\r\n", "\n"))
    }

    /// Every path under `<base>/<rel>`, relative to that directory.
    pub fn list(&self, rel: &str) -> Result<Vec<String>, String> {
        let dir = format!("{}/{}", self.base, rel);
        let bytes = self.git(&["ls-tree", "-r", "--name-only", &self.commit, "--", &dir])?;
        let text = String::from_utf8_lossy(&bytes).replace("\r\n", "\n");
        let prefix = format!("{dir}/");
        Ok(text
            .lines()
            .filter_map(|l| l.strip_prefix(&prefix).map(str::to_string))
            .filter(|p| !p.is_empty())
            .collect())
    }

    pub fn manifest(&self) -> Result<Vec<Row>, String> {
        let text = self.read("manifest-q50.tsv")?;
        let mut rows = Vec::new();
        for (n, line) in text.lines().enumerate() {
            if line.trim().is_empty() {
                continue;
            }
            let f: Vec<&str> = line.split('\t').collect();
            if f.len() < 5 {
                return Err(format!("manifest line {}: expected 5 columns, got {}", n + 1, f.len()));
            }
            rows.push(Row {
                id: f[0].to_string(),
                lang: f[1].to_string(),
                kind: f[2].to_string(),
                fixture_dir: f[3].to_string(),
                timeout_s: f[4]
                    .trim()
                    .parse()
                    .map_err(|_| format!("manifest line {}: {:?} is not a timeout", n + 1, f[4]))?,
                raw: line.to_string(),
            });
        }
        Ok(rows)
    }

    fn read_dir(&self, rel: &str) -> Result<BTreeMap<String, String>, String> {
        let mut map = BTreeMap::new();
        for p in self.list(rel)? {
            // Dotfiles are placeholders, never content — the runner does not copy them into a work
            // dir and neither does this. F29's stale .gitkeep is the U100 version of the same thing.
            if p.split('/').any(|c| c.starts_with('.')) {
                continue;
            }
            let body = self.read(&format!("{rel}/{p}"))?;
            map.insert(p, body);
        }
        Ok(map)
    }

    pub fn task(&self, row: &Row) -> Result<DonorTask, String> {
        let fixture = self.read_dir(&format!("fixtures/{}", row.fixture_dir))?;
        if fixture.is_empty() {
            // F40 is the whole reason this donor was sourced: a task that starts from nothing
            // cannot fire a permission gate, and importing one here would quietly reintroduce
            // F38's hole into the suite that exists to close it.
            return Err(format!(
                "{}: fixture is empty. Every Q56 task must ship files — a task that starts from \
                 nothing can never fire a gate (F38/F40), which is why this suite exists",
                row.id
            ));
        }
        Ok(DonorTask {
            row: row.clone(),
            prompt: self.read(&format!("prompts/{}.txt", row.id))?,
            fixture,
            refsol: self.read_dir(&format!("refsol/{}", row.id))?,
            verify: self.read(&format!("verify/{}.sh", row.id))?,
        })
    }
}

/// SPEC §3's `lang` vocabulary, which is closed and enforced by the loader
/// (`w8-corpus/src/model.rs`). Four of the donor's five map cleanly.
///
/// **`shell` has no home in the vocabulary and 8 tasks are shell** (F47). It is returned as an
/// error rather than mapped onto `mixed`: `mixed` means "several languages in one task", so using
/// it here would put a false value in a field whose entire purpose is to be checkable. The fix is a
/// one-word SPEC amendment, and it is David's to make.
pub fn spec_lang(donor_lang: &str) -> Result<&'static str, String> {
    match donor_lang {
        "python" => Ok("python"),
        "rust" => Ok("rust"),
        "js" => Ok("node"),
        "ts" => Ok("typescript"),
        "shell" => Err(
            "SPEC §3's lang vocabulary has no `shell` (F47). Add it by amendment — do not map \
             these onto `mixed`, which means something else"
                .to_string(),
        ),
        other => Err(format!("unknown donor lang {other:?}")),
    }
}
