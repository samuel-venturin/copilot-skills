#!/usr/bin/env node
/**
 * copilot-skills-update
 *
 * Updates the skills previously installed by install.js to the latest
 * version available in this repository, and prints a summary of what's new
 * (read from CHANGELOG.md, filtered to versions newer than the one recorded
 * in the target's manifest).
 *
 * How it works:
 *   1. Clones (or re-fetches) the repository into a temp working copy.
 *   2. Compares its package.json version against the manifest already
 *      recorded at the target directory (written by install.js).
 *   3. If a newer version is found, re-installs every skill already present
 *      at the target (same set, so nothing new is added and nothing you
 *      removed comes back) using the same backup-on-conflict behavior as
 *      install.js, then prints the changelog entries between the two
 *      versions.
 *
 * Usage:
 *   node update.js [--target <dir>] [--yes] [--dry-run] [--check-only]
 *
 * Zero external dependencies beyond `git` on PATH (needed to fetch the
 * latest version) — everything else is Node.js builtins, so this also runs
 * via `npx github:<owner>/copilot-skills update`-style invocations.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");
const { execSync } = require("child_process");

const REPO_ROOT = __dirname;
const REPO_SLUG = "samuel-venturin/copilot-skills";
const REPO_URL = `https://github.com/${REPO_SLUG}.git`;
const MANIFEST_FILE = ".copilot-skills-manifest.json";

function parseArgs(argv) {
  const opts = {
    target: process.env.COPILOT_SKILLS_DIR || path.join(os.homedir(), ".copilot", "skills"),
    yes: false,
    dryRun: false,
    checkOnly: false,
    help: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--target") opts.target = argv[++i];
    else if (a === "--yes" || a === "-y") opts.yes = true;
    else if (a === "--dry-run") opts.dryRun = true;
    else if (a === "--check-only") opts.checkOnly = true;
    else if (a === "-h" || a === "--help") opts.help = true;
  }
  return opts;
}

function printHelp() {
  console.log(`copilot-skills-update

Updates the skills already installed at the target directory to the latest
version in ${REPO_SLUG}, and prints a summary of what changed since the
version you had installed.

Options:
  --target <dir>   Directory to update (default: ~/.copilot/skills, or
                   $COPILOT_SKILLS_DIR if set)
  --check-only      Only report whether an update is available, don't apply it
  --dry-run         Show what would be updated without changing anything
  --yes, -y         Skip the confirmation prompt
  -h, --help        Show this help
`);
}

function readManifest(target) {
  try {
    return JSON.parse(fs.readFileSync(path.join(target, MANIFEST_FILE), "utf8"));
  } catch {
    return null;
  }
}

function readRemoteVersion(repoRoot) {
  return JSON.parse(fs.readFileSync(path.join(repoRoot, "package.json"), "utf8")).version;
}

// Simple semver-ish comparison (major.minor.patch, numeric parts only).
function compareVersions(a, b) {
  const pa = String(a).split(".").map((n) => parseInt(n, 10) || 0);
  const pb = String(b).split(".").map((n) => parseInt(n, 10) || 0);
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const diff = (pa[i] || 0) - (pb[i] || 0);
    if (diff !== 0) return diff > 0 ? 1 : -1;
  }
  return 0;
}

function fetchLatest(workDir) {
  fs.rmSync(workDir, { recursive: true, force: true });
  execSync(`git clone --depth 1 --quiet ${REPO_URL} "${workDir}"`, { stdio: ["ignore", "ignore", "inherit"] });
  return workDir;
}

// Extracts the changelog sections for every version strictly newer than
// `sinceVersion` (or everything if sinceVersion is null), in file order
// (CHANGELOG.md is expected newest-first).
function changelogSince(changelogPath, sinceVersion) {
  if (!fs.existsSync(changelogPath)) return [];
  const text = fs.readFileSync(changelogPath, "utf8");
  const sections = text.split(/^## \[/m).slice(1); // drop the "# Changelog" preamble
  const entries = [];
  for (const section of sections) {
    const versionMatch = section.match(/^([^\]]+)\]/);
    if (!versionMatch) continue;
    const version = versionMatch[1];
    if (sinceVersion && compareVersions(version, sinceVersion) <= 0) break;
    const body = section.slice(versionMatch[0].length).trim();
    entries.push({ version, body });
  }
  return entries;
}

function printChangelog(entries) {
  if (!entries.length) {
    console.log("  (no changelog entries found)");
    return;
  }
  for (const { version, body } of entries) {
    console.log(`\n  ── v${version} ──`);
    for (const line of body.split("\n")) {
      if (line.trim()) console.log(`  ${line}`);
    }
  }
  console.log("");
}

function askYesNo(question) {
  if (!process.stdin.isTTY) return Promise.resolve(false);
  const readline = require("readline");
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      rl.close();
      resolve(/^y(es)?$/i.test(answer.trim()));
    });
  });
}

function copyRecursiveSync(src, dest, ignore) {
  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    fs.mkdirSync(dest, { recursive: true });
    for (const entry of fs.readdirSync(src)) {
      if (ignore.has(entry)) continue;
      copyRecursiveSync(path.join(src, entry), path.join(dest, entry), ignore);
    }
  } else {
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.copyFileSync(src, dest);
  }
}

const COPY_IGNORE = new Set([".git", "node_modules", "__pycache__", ".venv", ".testid-cache", "state.json", "resolved_env.json"]);

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    printHelp();
    return 0;
  }

  if (!fs.existsSync(opts.target)) {
    console.error(`✗ Nothing installed yet at ${opts.target} — run the installer first.`);
    return 1;
  }

  const manifest = readManifest(opts.target);
  const currentVersion = manifest ? manifest.version : null;
  const installedSkills = manifest && Array.isArray(manifest.skills) ? manifest.skills : null;

  if (!installedSkills || !installedSkills.length) {
    console.error(
      `✗ No install manifest found at ${opts.target}. This target wasn't installed with a version of ` +
        `install.js that records one — reinstall first (npx github:${REPO_SLUG}) so update.js has something to compare against.`
    );
    return 1;
  }

  console.log(`\ncopilot-skills-update`);
  console.log(`  Target: ${opts.target}`);
  console.log(`  Installed version: ${currentVersion || "(unknown)"}\n`);

  console.log("  Checking for updates...");
  const workDir = path.join(os.tmpdir(), `copilot-skills-update-${Date.now()}`);
  let latestVersion;
  try {
    fetchLatest(workDir);
    latestVersion = readRemoteVersion(workDir);
  } catch (err) {
    console.error(`✗ Could not fetch the latest version (is 'git' installed and is there network access?): ${err.message}`);
    return 1;
  }

  const isNewer = !currentVersion || compareVersions(latestVersion, currentVersion) > 0;

  if (!isNewer) {
    console.log(`  ✓ Already up to date (v${currentVersion}).\n`);
    fs.rmSync(workDir, { recursive: true, force: true });
    return 0;
  }

  console.log(`  ★ Update available: v${currentVersion || "?"} → v${latestVersion}\n`);

  const changelogEntries = changelogSince(path.join(workDir, "CHANGELOG.md"), currentVersion);
  console.log("  What's new:");
  printChangelog(changelogEntries);

  if (opts.checkOnly) {
    console.log(`  Run 'node update.js' (without --check-only) to apply this update.\n`);
    fs.rmSync(workDir, { recursive: true, force: true });
    return 0;
  }

  if (opts.dryRun) {
    console.log(`  (dry-run) Would update: ${installedSkills.join(", ")}\n`);
    fs.rmSync(workDir, { recursive: true, force: true });
    return 0;
  }

  let proceed = opts.yes;
  if (!proceed) {
    proceed = await askYesNo("  Apply this update now? [y/N] ");
  }
  if (!proceed) {
    console.log("  ○ Update skipped.\n");
    fs.rmSync(workDir, { recursive: true, force: true });
    return 0;
  }

  const updated = [];
  const failed = [];
  for (const skill of installedSkills) {
    const src = path.join(workDir, skill);
    const dest = path.join(opts.target, skill);
    if (!fs.existsSync(src)) {
      console.log(`  ○ ${skill.padEnd(22)} no longer exists in the repo — left untouched (use uninstall.js to remove it)`);
      continue;
    }
    try {
      fs.rmSync(dest, { recursive: true, force: true });
      copyRecursiveSync(src, dest, COPY_IGNORE);
      console.log(`  ✓ ${skill.padEnd(22)} updated`);
      updated.push(skill);
    } catch (err) {
      console.error(`  ✗ ${skill.padEnd(22)} FAILED: ${err.message}`);
      failed.push(skill);
    }
  }

  const manifestOut = {
    version: latestVersion,
    installedAt: new Date().toISOString(),
    repo: REPO_SLUG,
    skills: installedSkills.filter((s) => fs.existsSync(path.join(opts.target, s, "SKILL.md"))).sort(),
  };
  fs.writeFileSync(path.join(opts.target, MANIFEST_FILE), JSON.stringify(manifestOut, null, 2) + "\n");

  fs.rmSync(workDir, { recursive: true, force: true });

  console.log(`\n  ${"─".repeat(52)}`);
  console.log(`  Updated: ${updated.length}  |  Failed: ${failed.length}`);
  console.log(`  ${"─".repeat(52)}\n`);

  if (failed.length) {
    console.error("✗ Some skills failed to update. See errors above.");
    return 1;
  }

  console.log(`✓ Done. Now on v${latestVersion}.\n`);
  return 0;
}

main()
  .then((code) => process.exit(code))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
