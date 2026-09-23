//! SPEC §2's isolation guarantee, made structural.
//!
//! > `refsol/`, `sham/` and `stub/` are gate-time only. The runner must never copy them into a
//! > workdir the subject can see; a loader that cannot guarantee that must refuse to run.
//!
//! "Must refuse to run" is the load-time half, and it is why this module rejects rather than
//! filters: a `fixture/` that *contains* a path the guarantee cannot cover is a corpus defect,
//! not a file to quietly skip. The runtime half is that `WorkdirPlan` is the only thing in the
//! crate that yields copyable paths, and it is built from `fixture/` alone — `Task` never hands
//! out the path of a gate-only directory at all.

use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicUsize, Ordering};

/// Directory names that must never reach the subject's work dir.
pub const GATE_ONLY: &[&str] = &["refsol", "sham", "stub"];

/// The exact file list to copy for one task, resolved at load time — or, for a `[fixture]` task
/// (SPEC §2, amendment 9), the one pinned tree of a real repository that stands in for it.
#[derive(Debug, Clone, Default)]
pub struct WorkdirPlan {
    files: Vec<PlannedFile>,
    archive: Option<Archive>,
}

/// A fixture that is a commit of a repository on this machine, exported without its history.
///
/// Exported, never cloned: a clone carries every ref the source has — later fixes to the very
/// defect under test, and abcc's own checkpoint refs from earlier attempts at it. What reaches
/// the work dir here is the tracked files of `rev` and nothing else; no `.git`, no refs, and no
/// untracked file (`FINDINGS.md` lives untracked in the source and must never be copied).
#[derive(Debug, Clone)]
pub struct Archive {
    pub repo: PathBuf,
    /// A full 40-hex commit id. Never a branch: a branch moves when a card's fix lands.
    pub rev: String,
}

impl Archive {
    /// Write `rev`'s tracked files under `dest` through a throwaway index, so neither the
    /// source's index nor its refs are touched.
    fn materialize(&self, dest: &Path) -> io::Result<()> {
        static N: AtomicUsize = AtomicUsize::new(0);
        let dest = std::path::absolute(dest)?;
        let index = std::env::temp_dir().join(format!(
            "w8-archive-{}-{}.index",
            std::process::id(),
            N.fetch_add(1, Ordering::Relaxed)
        ));
        let prefix = format!("--prefix={}/", dest.display().to_string().replace('\\', "/"));
        let result = self
            .git(&index, &["read-tree", &self.rev])
            .and_then(|()| self.git(&index, &["checkout-index", "-a", "-f", &prefix]));
        let _ = fs::remove_file(&index);
        result
    }

    fn git(&self, index: &Path, args: &[&str]) -> io::Result<()> {
        let out = Command::new("git")
            .arg("-C")
            .arg(&self.repo)
            .args(args)
            .env("GIT_INDEX_FILE", index)
            .stdin(Stdio::null())
            .output()?;
        if out.status.success() {
            Ok(())
        } else {
            Err(io::Error::other(format!(
                "git -C {} {} exited {:?}: {}",
                self.repo.display(),
                args.join(" "),
                out.status.code(),
                String::from_utf8_lossy(&out.stderr).trim()
            )))
        }
    }
}

#[derive(Debug, Clone)]
pub struct PlannedFile {
    /// Absolute source path under the task's `fixture/`.
    pub src: PathBuf,
    /// Destination path relative to the work dir root.
    pub dest: String,
}

impl WorkdirPlan {
    pub fn files(&self) -> &[PlannedFile] {
        &self.files
    }

    pub fn is_empty(&self) -> bool {
        self.files.is_empty() && self.archive.is_none()
    }

    pub fn archive(&self) -> Option<&Archive> {
        self.archive.as_ref()
    }

    /// Copy the fixture into `dest`, which must already exist and should be empty.
    pub fn materialize(&self, dest: &Path) -> io::Result<()> {
        if let Some(a) = &self.archive {
            a.materialize(dest)?;
        }
        for f in &self.files {
            let target = dest.join(&f.dest);
            if let Some(parent) = target.parent() {
                fs::create_dir_all(parent)?;
            }
            fs::copy(&f.src, &target)?;
        }
        Ok(())
    }
}

/// Why a `fixture/` could not be planned. Each maps onto a SPEC §2 sentence rather than an
/// `io::Error`, because "the corpus is malformed" and "the disk is broken" are different facts
/// and the loader's job is to tell them apart.
#[derive(Debug)]
pub enum PlanError {
    /// SPEC §2 lists `fixture/` as required.
    Missing,
    /// A symlink under `fixture/` can point at `../refsol`, so the guarantee cannot be made by
    /// inspecting names. Rejecting them is what keeps the guarantee cheap and total.
    Symlink(PathBuf),
    /// A directory named `refsol`/`sham`/`stub` nested inside the fixture.
    GateOnlyNested(PathBuf),
    /// A `[fixture]` task that also ships `fixture/`: two sources for one work dir.
    ArchiveAndFixture,
    Io(PathBuf, io::Error),
}

impl std::fmt::Display for PlanError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            PlanError::Missing => write!(f, "no fixture/ directory; SPEC §2 requires one"),
            PlanError::Symlink(p) => write!(
                f,
                "fixture/ contains a symlink ({}); it could resolve outside the fixture, so the \
                 §2 guarantee that refsol/, sham/ and stub/ never reach the work dir cannot be made",
                p.display()
            ),
            PlanError::GateOnlyNested(p) => write!(
                f,
                "fixture/ contains a gate-only directory ({}); refsol/, sham/ and stub/ are \
                 gate-time only and must never be copied into the subject's work dir",
                p.display()
            ),
            PlanError::ArchiveAndFixture => write!(
                f,
                "the task has both a [fixture] table and a fixture/ directory; the work dir is \
                 one or the other"
            ),
            PlanError::Io(p, e) => write!(f, "cannot read {}: {e}", p.display()),
        }
    }
}

/// The plan for a `[fixture]` task (SPEC §2, amendment 9). Nothing is read from the source
/// repository here: a missing repository or commit is a fact about this machine, reported by the
/// cell that tried to materialize it, not a malformed corpus.
pub fn plan_archive(task_dir: &Path, archive: Archive) -> Result<WorkdirPlan, PlanError> {
    if task_dir.join("fixture").exists() {
        return Err(PlanError::ArchiveAndFixture);
    }
    Ok(WorkdirPlan { files: Vec::new(), archive: Some(archive) })
}

/// Build the plan for one task directory.
///
/// Dotfiles are skipped, and that is a measured requirement rather than tidiness: 78 of the 90
/// U100 tasks generate their artifact from nothing and so ship an empty `fixture/` holding only a
/// `.gitkeep`, because git cannot carry an empty directory. Copying it would put a file in a work
/// dir the donor's runs did not have.
pub fn plan(task_dir: &Path) -> Result<WorkdirPlan, PlanError> {
    let fixture = task_dir.join("fixture");
    if !fixture.is_dir() {
        return Err(PlanError::Missing);
    }
    let mut files = Vec::new();
    walk(&fixture, &fixture, &mut files)?;
    files.sort_by(|a, b| a.dest.cmp(&b.dest));
    Ok(WorkdirPlan { files, archive: None })
}

fn walk(root: &Path, dir: &Path, out: &mut Vec<PlannedFile>) -> Result<(), PlanError> {
    let entries = fs::read_dir(dir).map_err(|e| PlanError::Io(dir.to_path_buf(), e))?;
    for entry in entries {
        let entry = entry.map_err(|e| PlanError::Io(dir.to_path_buf(), e))?;
        let path = entry.path();
        let name = entry.file_name().to_string_lossy().into_owned();

        // `symlink_metadata` does not follow the link, which is the point: a followed link to a
        // regular file outside the fixture would look like an ordinary file here.
        let meta = fs::symlink_metadata(&path).map_err(|e| PlanError::Io(path.clone(), e))?;
        if meta.file_type().is_symlink() {
            return Err(PlanError::Symlink(rel(root, &path)));
        }
        if meta.is_dir() && GATE_ONLY.contains(&name.as_str()) {
            return Err(PlanError::GateOnlyNested(rel(root, &path)));
        }
        if name.starts_with('.') {
            continue;
        }
        if meta.is_dir() {
            walk(root, &path, out)?;
        } else {
            out.push(PlannedFile { dest: rel(root, &path).to_string_lossy().replace('\\', "/"), src: path });
        }
    }
    Ok(())
}

fn rel(root: &Path, path: &Path) -> PathBuf {
    path.strip_prefix(root).unwrap_or(path).to_path_buf()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    fn tmp(name: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("w8-corpus-workdir-{name}"));
        let _ = fs::remove_dir_all(&d);
        fs::create_dir_all(d.join("fixture")).unwrap();
        d
    }

    #[test]
    fn missing_fixture_is_rejected() {
        let d = std::env::temp_dir().join("w8-corpus-workdir-nofixture");
        let _ = fs::remove_dir_all(&d);
        fs::create_dir_all(&d).unwrap();
        assert!(matches!(plan(&d), Err(PlanError::Missing)));
    }

    #[test]
    fn dotfiles_are_skipped_and_real_files_are_not() {
        let d = tmp("dotfiles");
        fs::write(d.join("fixture/.gitkeep"), "").unwrap();
        fs::write(d.join("fixture/sql_inject.py"), "x").unwrap();
        let p = plan(&d).unwrap();
        assert_eq!(p.files().len(), 1);
        assert_eq!(p.files()[0].dest, "sql_inject.py");
    }

    #[test]
    fn an_empty_fixture_plans_to_nothing_rather_than_failing() {
        // 78 of the 90 U100 tasks are exactly this: a `.gitkeep` and nothing else.
        let d = tmp("empty");
        fs::write(d.join("fixture/.gitkeep"), "").unwrap();
        assert!(plan(&d).unwrap().is_empty());
    }

    #[test]
    fn a_nested_gate_only_directory_is_rejected() {
        let d = tmp("nested");
        fs::create_dir_all(d.join("fixture/refsol")).unwrap();
        fs::write(d.join("fixture/refsol/answer.py"), "the answer").unwrap();
        match plan(&d) {
            Err(PlanError::GateOnlyNested(p)) => assert!(p.to_string_lossy().contains("refsol")),
            other => panic!("expected GateOnlyNested, got {other:?}"),
        }
    }

    #[test]
    fn subdirectories_are_walked_with_posix_destinations() {
        let d = tmp("subdirs");
        fs::create_dir_all(d.join("fixture/pkg")).unwrap();
        fs::write(d.join("fixture/pkg/mod.py"), "x").unwrap();
        let p = plan(&d).unwrap();
        assert_eq!(p.files()[0].dest, "pkg/mod.py");
    }

    #[test]
    fn materialize_copies_exactly_the_planned_files() {
        let d = tmp("materialize");
        fs::write(d.join("fixture/.gitkeep"), "").unwrap();
        fs::write(d.join("fixture/a.py"), "body").unwrap();
        let work = d.join("work");
        fs::create_dir_all(&work).unwrap();
        plan(&d).unwrap().materialize(&work).unwrap();
        assert_eq!(fs::read_to_string(work.join("a.py")).unwrap(), "body");
        assert!(!work.join(".gitkeep").exists());
    }

    #[test]
    fn an_archive_task_may_not_also_ship_a_fixture_directory() {
        let d = tmp("archive-and-fixture");
        let a = Archive { repo: d.clone(), rev: "0".repeat(40) };
        assert!(matches!(plan_archive(&d, a), Err(PlanError::ArchiveAndFixture)));
    }

    fn git(repo: &Path, args: &[&str]) -> String {
        let out = Command::new("git")
            .arg("-C")
            .arg(repo)
            .args(["-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"])
            .args(args)
            .output()
            .unwrap();
        assert!(out.status.success(), "git {args:?}: {}", String::from_utf8_lossy(&out.stderr));
        String::from_utf8_lossy(&out.stdout).trim().to_owned()
    }

    #[test]
    fn an_archive_exports_the_pinned_commit_and_nothing_else() {
        let d = std::env::temp_dir().join("w8-corpus-workdir-archive");
        let _ = fs::remove_dir_all(&d);
        let src = d.join("src");
        fs::create_dir_all(src.join("pkg")).unwrap();
        git(&src, &["init", "-q"]);
        fs::write(src.join("pkg/lib.rs"), "old").unwrap();
        git(&src, &["add", "-A"]);
        git(&src, &["commit", "-q", "-m", "base"]);
        let rev = git(&src, &["rev-parse", "HEAD"]);
        // A later fix, and an untracked file: neither may reach the work dir.
        fs::write(src.join("pkg/lib.rs"), "fixed").unwrap();
        git(&src, &["commit", "-q", "-am", "fix"]);
        fs::write(src.join("FINDINGS.md"), "secret").unwrap();

        let task = d.join("task");
        fs::create_dir_all(&task).unwrap();
        let p = plan_archive(&task, Archive { repo: src.clone(), rev }).unwrap();
        assert!(!p.is_empty());
        let work = d.join("work");
        fs::create_dir_all(&work).unwrap();
        p.materialize(&work).unwrap();

        assert_eq!(fs::read_to_string(work.join("pkg/lib.rs")).unwrap(), "old");
        assert!(!work.join("FINDINGS.md").exists());
        assert!(!work.join(".git").exists());
        assert_eq!(git(&src, &["status", "--porcelain"]), "?? FINDINGS.md");
    }

    #[test]
    fn an_archive_at_an_unknown_commit_fails_to_materialize() {
        let d = std::env::temp_dir().join("w8-corpus-workdir-archive-missing");
        let _ = fs::remove_dir_all(&d);
        fs::create_dir_all(&d).unwrap();
        git(&d, &["init", "-q"]);
        let p = plan_archive(&d.join("task"), Archive { repo: d.clone(), rev: "1".repeat(40) })
            .unwrap();
        let work = d.join("work");
        fs::create_dir_all(&work).unwrap();
        assert!(p.materialize(&work).is_err());
    }
}
