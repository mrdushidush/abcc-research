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

/// Directory names that must never reach the subject's work dir.
pub const GATE_ONLY: &[&str] = &["refsol", "sham", "stub"];

/// The exact file list to copy for one task, resolved at load time.
#[derive(Debug, Clone, Default)]
pub struct WorkdirPlan {
    files: Vec<PlannedFile>,
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
        self.files.is_empty()
    }

    /// Copy the fixture into `dest`, which must already exist and should be empty.
    pub fn materialize(&self, dest: &Path) -> io::Result<()> {
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
            PlanError::Io(p, e) => write!(f, "cannot read {}: {e}", p.display()),
        }
    }
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
    Ok(WorkdirPlan { files })
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
}
