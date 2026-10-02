#!/usr/bin/env node
/**
 * copilot-skills-update
 *
 * Updates skills previously installed by install.js (Copilot) or
 * install-cursor.js (Cursor) to the latest version in this repository, and
 * prints a changelog summary of what's new.
 *
 * How it works:
 *   1. Resolves the install target (explicit --target / --cursor, or auto-detect).
 *   2. Reads the install manifest (.copilot-skills-manifest.json or
 *      .cursor-skills-manifest.json).
 *   3. Clones the latest repo into a temp working copy and compares versions.
 *   4. Copilot target: refreshes only the skills listed in the manifest.
 *      Cursor target: re-runs install-cursor.js --force so skills, scripts,
 *      rules, and Agent Store stay in sync (and new skills are picked up).
 *
 * Usage:
 *   node update.js [--target <dir>] [--cursor] [--yes] [--dry-run] [--check-only]
 *
 * Zero external dependencies beyond `git` on PATH.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");
const { execSync, spawnSync } = require("child_process");

const REPO_ROOT = __dirname;
const REPO_SLUG = "samuel-venturin/copilot-skills";
const REPO_URL = `https://github.com/${REPO_SLUG}.git`;
const COPILOT_MANIFEST = ".copilot-skills-manifest.json";
const CURSOR_MANIFEST = ".cursor-skills-manifest.json";

function parseArgs(argv) {
  const opts = {
    target: null,
    cursor: false,
    yes: false,
    dryRun: false,
    checkOnly: false,
    help: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--target") opts.target = argv[++i];
    else if (a === "--cursor") opts.cursor = true;
    else if (a === "--yes" || a === "-y") opts.yes = true;
    else if (a === "--dry-run") opts.dryRun = true;
    else if (a === "--check-only") opts.checkOnly = true;
    else if (a === "-h" || a === "--help") opts.help = true;
  }
  return opts;
}

function printHelp() {
  console.log(`copilot-skills-update

Updates skills installed for GitHub Copilot CLI and/or Cursor to the latest
version in ${REPO_SLUG}, and prints a summary of what changed.

Options:
  --cursor          Update the Cursor install (~/.cursor/skills). Re-runs
                    install-cursor --force so scripts/rules/Agent Store sync too.
  --target <dir>    Directory to update (must contain a skills manifest)
  --check-only      Only report whether an update is available, don't apply it
  --dry-run         Show what would be updated without changing anything
  --yes, -y         Skip the confirmation prompt
  -h, --help        Show this help

Defaults:
  If --target / --cursor are omitted, auto-detects:
    1) ~/.cursor/skills when .cursor-skills-manifest.json exists
    2) else ~/.copilot/skills (or $COPILOT_SKILLS_DIR)
`);
}

function hasManifest(dir, fileName) {
  return fs.existsSync(path.join(dir, fileName));
}

function resolveInstall(opts) {
  const cursorDefault = path.join(os.homedir(), ".cursor", "skills");
  const copilotDefault =
    process.env.COPILOT_SKILLS_DIR || path.join(os.homedir(), ".copilot", "skills");

  if (opts.target) {
    const target = path.resolve(opts.target);
    if (hasManifest(target, CURSOR_MANIFEST)) {
      return { target, kind: "cursor", manifestFile: CURSOR_MANIFEST };
    }
    if (hasManifest(target, COPILOT_MANIFEST)) {
      return { target, kind: "copilot", manifestFile: COPILOT_MANIFEST };
    }
    return { target, kind: opts.cursor ? "cursor" : "copilot", manifestFile: null };
  }

  if (opts.cursor) {
    return {
      target: cursorDefault,
      kind: "cursor",
      manifestFile: hasManifest(cursorDefault, CURSOR_MANIFEST) ? CURSOR_MANIFEST : null,
    };
  }

  // Auto-detect: prefer Cursor when its manifest is present.
  if (hasManifest(cursorDefault, CURSOR_MANIFEST)) {
    return { target: cursorDefault, kind: "cursor", manifestFile: CURSOR_MANIFEST };
  }
  if (hasManifest(copilotDefault, COPILOT_MANIFEST)) {
    return { target: copilotDefault, kind: "copilot", manifestFile: COPILOT_MANIFEST };
  }

  // Fallbacks when nothing is installed yet (clearer errors later).
  if (fs.existsSync(cursorDefault)) {
    return { target: cursorDefault, kind: "cursor", manifestFile: null };
  }
  return { target: copilotDefault, kind: "copilot", manifestFile: null };
}

function readManifest(target, manifestFile) {
  if (!manifestFile) return null;
  try {
    return JSON.parse(fs.readFileSync(path.join(target, manifestFile), "utf8"));
  } catch {
    return null;
  }
}

function readRemoteVersion(repoRoot) {
  return JSON.parse(fs.readFileSync(path.join(repoRoot, "package.json"), "utf8")).version;
}

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
  execSync(`git clone --depth 1 --quiet ${REPO_URL} "${workDir}"`, {
    stdio: ["ignore", "ignore", "inherit"],
  });
  return workDir;
}

function changelogSince(changelogPath, sinceVersion) {
  if (!fs.existsSync(changelogPath)) return [];
  const text = fs.readFileSync(changelogPath, "utf8");
  const sections = text.split(/^## \[/m).slice(1);
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

const COPY_IGNORE = new Set([
  ".git",
  "node_modules",
  "__pycache__",
  ".venv",
  ".testid-cache",
  "state.json",
  "resolved_env.json",
]);

function applyCursorUpdate(workDir) {
  const installer = path.join(workDir, "install-cursor.js");
  if (!fs.existsSync(installer)) {
    throw new Error(`install-cursor.js missing in fetched repo (${installer})`);
  }
  const result = spawnSync(process.execPath, [installer, "--force", "--yes"], {
    stdio: "inherit",
    cwd: workDir,
  });
  if (result.status !== 0) {
    throw new Error(`install-cursor failed with exit code ${result.status}`);
  }
}

function applyCopilotUpdate(workDir, target, installedSkills, latestVersion) {
  const updated = [];
  const failed = [];
  for (const skill of installedSkills) {
    const src = path.join(workDir, skill);
    const dest = path.join(target, skill);
    if (!fs.existsSync(src)) {
      console.log(
        `  ○ ${skill.padEnd(22)} no longer exists in the repo — left untouched (use uninstall.js to remove it)`
      );
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
    skills: installedSkills.filter((s) => fs.existsSync(path.join(target, s, "SKILL.md"))).sort(),
  };
  fs.writeFileSync(path.join(target, COPILOT_MANIFEST), JSON.stringify(manifestOut, null, 2) + "\n");
  return { updated, failed };
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    printHelp();
    return 0;
  }

  const install = resolveInstall(opts);

  if (!fs.existsSync(install.target)) {
    console.error(
      `✗ Nothing installed yet at ${install.target} — run the installer first ` +
        `(npx github:${REPO_SLUG}${install.kind === "cursor" ? " install-cursor" : ""}).`
    );
    return 1;
  }

  const manifest = readManifest(install.target, install.manifestFile);
  const currentVersion = manifest ? manifest.version : null;
  const installedSkills = manifest && Array.isArray(manifest.skills) ? manifest.skills : null;

  if (!installedSkills || !installedSkills.length) {
    const expected =
      install.kind === "cursor" ? CURSOR_MANIFEST : COPILOT_MANIFEST;
    console.error(
      `✗ No install manifest (${expected}) found at ${install.target}. ` +
        `Reinstall first: npx github:${REPO_SLUG}` +
        `${install.kind === "cursor" ? " install-cursor" : ""}`
    );
    return 1;
  }

  console.log(`\ncopilot-skills-update`);
  console.log(`  Kind: ${install.kind}`);
  console.log(`  Target: ${install.target}`);
  console.log(`  Installed version: ${currentVersion || "(unknown)"}\n`);

  console.log("  Checking for updates...");
  const workDir = path.join(os.tmpdir(), `copilot-skills-update-${Date.now()}`);
  let latestVersion;
  try {
    fetchLatest(workDir);
    latestVersion = readRemoteVersion(workDir);
  } catch (err) {
    console.error(
      `✗ Could not fetch the latest version (is 'git' installed and is there network access?): ${err.message}`
    );
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
    console.log(
      install.kind === "cursor"
        ? `  Run 'npx github:${REPO_SLUG} update --cursor' (or --yes) to apply this update.\n`
        : `  Run 'npx github:${REPO_SLUG} update' (without --check-only) to apply this update.\n`
    );
    fs.rmSync(workDir, { recursive: true, force: true });
    return 0;
  }

  if (opts.dryRun) {
    if (install.kind === "cursor") {
      console.log(`  (dry-run) Would re-run install-cursor --force (skills + scripts + rules + Agent Store)\n`);
    } else {
      console.log(`  (dry-run) Would update: ${installedSkills.join(", ")}\n`);
    }
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

  try {
    if (install.kind === "cursor") {
      console.log("  Applying Cursor update via install-cursor --force...\n");
      applyCursorUpdate(workDir);
      fs.rmSync(workDir, { recursive: true, force: true });
      console.log(`\n✓ Done. Cursor install refreshed to v${latestVersion}.\n`);
      return 0;
    }

    const { updated, failed } = applyCopilotUpdate(
      workDir,
      install.target,
      installedSkills,
      latestVersion
    );
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
  } catch (err) {
    try {
      fs.rmSync(workDir, { recursive: true, force: true });
    } catch {
      /* ignore */
    }
    console.error(`✗ Update failed: ${err.message}`);
    return 1;
  }
}

main()
  .then((code) => process.exit(code))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
