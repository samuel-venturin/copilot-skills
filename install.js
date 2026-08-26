#!/usr/bin/env node
/**
 * copilot-skills-install
 *
 * First-run installer for this repository's Copilot CLI skills.
 * Copies every top-level skill folder (any directory containing a SKILL.md)
 * into the user's ~/.copilot/skills directory, backing up anything that
 * already exists there, and reports which external tools each installed
 * skill expects on PATH.
 *
 * Usage:
 *   node install.js [--target <dir>] [--force] [--skip-existing] [--dry-run] [--only <name,...>]
 *
 * Zero external dependencies — only Node.js builtins are used, so this runs
 * fine via `npx github:<owner>/copilot-skills` without an install step.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");
const { execSync } = require("child_process");

const REPO_ROOT = __dirname;

const IGNORE_NAMES = new Set([
  ".git",
  "node_modules",
  "__pycache__",
  ".venv",
  ".testid-cache",
]);
const IGNORE_FILES = new Set(["state.json", "resolved_env.json"]);
const IGNORE_FILE_SUFFIXES = [".pyc", ".log", ".log.err"];

// Tools referenced by each skill (informational — checked, never installed automatically).
const SKILL_PREREQS = {
  "commit-changes": ["git"],
  execute: ["git"],
  "ideas-notes": [],
  interpret: [],
  "local-stack": ["python", "git", "wsl (Windows only)", "dotnet", "pnpm"],
  "playwright-cli": ["node", "npx"],
  "pr-maestro": ["python", "git", "gh"],
  refactor: ["python"],
  "release-maestro": ["python", "git", "gh"],
  tasks: [],
  "testid-extractor": ["python", "pnpm"],
  "update-error-catalog": [],
};

function parseArgs(argv) {
  const opts = {
    target: process.env.COPILOT_SKILLS_DIR || path.join(os.homedir(), ".copilot", "skills"),
    force: false,
    skipExisting: false,
    dryRun: false,
    only: null,
    help: false,
    yes: false,
    noTools: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--target") opts.target = argv[++i];
    else if (a === "--force") opts.force = true;
    else if (a === "--skip-existing") opts.skipExisting = true;
    else if (a === "--dry-run") opts.dryRun = true;
    else if (a === "--only") opts.only = argv[++i].split(",").map((s) => s.trim());
    else if (a === "--yes" || a === "-y") opts.yes = true;
    else if (a === "--no-tools") opts.noTools = true;
    else if (a === "-h" || a === "--help") opts.help = true;
  }
  return opts;
}

function printHelp() {
  console.log(`copilot-skills-install

Copies every skill in this repository into ~/.copilot/skills (or a custom
target directory), backing up any existing skill with the same name first.
Also offers to install the 'gh' and 'copilot' CLIs if either is missing.

Options:
  --target <dir>        Install destination (default: ~/.copilot/skills, or
                         $COPILOT_SKILLS_DIR if set)
  --only <a,b,c>         Only install the named skills (comma-separated)
  --force                Overwrite existing skills in place (no backup)
  --skip-existing        Do not touch skills that already exist at the target
  --dry-run              Print what would happen without changing anything
  --yes, -y              Auto-confirm installing missing gh/copilot CLIs
                         (no interactive prompt)
  --no-tools             Never offer to install gh/copilot, just report them
  -h, --help             Show this help
`);
}

function discoverSkills(root) {
  return fs
    .readdirSync(root, { withFileTypes: true })
    .filter((e) => e.isDirectory() && !IGNORE_NAMES.has(e.name))
    .map((e) => e.name)
    .filter((name) => fs.existsSync(path.join(root, name, "SKILL.md")))
    .sort();
}

function shouldIgnore(name) {
  if (IGNORE_NAMES.has(name) || IGNORE_FILES.has(name)) return true;
  return IGNORE_FILE_SUFFIXES.some((suf) => name.endsWith(suf));
}

function copyRecursiveSync(src, dest) {
  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    fs.mkdirSync(dest, { recursive: true });
    for (const entry of fs.readdirSync(src)) {
      if (shouldIgnore(entry)) continue;
      copyRecursiveSync(path.join(src, entry), path.join(dest, entry));
    }
  } else {
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.copyFileSync(src, dest);
  }
}

function timestamp() {
  return new Date().toISOString().replace(/[:.]/g, "-");
}

function commandExists(cmd) {
  const probe = process.platform === "win32" ? `where ${cmd}` : `command -v ${cmd}`;
  try {
    execSync(probe, { stdio: "ignore", shell: process.platform === "win32" ? undefined : "/bin/sh" });
    return true;
  } catch {
    return false;
  }
}

function runCmd(cmd) {
  try {
    execSync(cmd, { stdio: "inherit" });
    return true;
  } catch {
    return false;
  }
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

// Core CLIs the skills depend on. Unlike SKILL_PREREQS (informational-only),
// these two are offered for automatic installation when missing, with the
// user's explicit consent (via prompt, or --yes to skip the prompt).
const CORE_TOOLS = {
  gh: {
    label: "GitHub CLI (gh)",
    manualUrl: "https://github.com/cli/cli#installation",
    install() {
      if (process.platform === "win32" && commandExists("winget")) {
        return runCmd(
          "winget install --id GitHub.cli -e --source winget --scope user " +
            "--accept-source-agreements --accept-package-agreements"
        );
      }
      if (process.platform === "win32" && commandExists("choco")) {
        return runCmd("choco install gh -y");
      }
      if (commandExists("brew")) {
        return runCmd("brew install gh");
      }
      if (process.platform === "linux" && commandExists("apt-get")) {
        return runCmd("sudo apt-get update && sudo apt-get install -y gh");
      }
      if (process.platform === "linux" && commandExists("dnf")) {
        return runCmd("sudo dnf install -y gh");
      }
      return false;
    },
  },
  copilot: {
    label: "GitHub Copilot CLI (copilot)",
    manualUrl: "https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli",
    install() {
      return runCmd("npm install -g @github/copilot");
    },
  },
};

async function ensureCoreTools(opts) {
  const missing = Object.keys(CORE_TOOLS).filter((name) => !commandExists(name));
  if (!missing.length) {
    console.log("  ✓ gh and copilot CLIs are already installed\n");
    return;
  }

  if (opts.noTools || opts.dryRun) {
    const reason = opts.dryRun ? "dry-run" : "--no-tools set";
    console.log(`  ○ Missing tools (not installing, ${reason}): ${missing.join(", ")}\n`);
    return;
  }

  console.log(`  Missing tools: ${missing.map((m) => CORE_TOOLS[m].label).join(", ")}`);
  let proceed = opts.yes;
  if (!proceed) {
    proceed = await askYesNo("  Install them now? [y/N] ");
  }

  if (!proceed) {
    console.log("  ○ Skipped. Install manually if needed:");
    for (const name of missing) console.log(`    - ${CORE_TOOLS[name].label}: ${CORE_TOOLS[name].manualUrl}`);
    console.log("");
    return;
  }

  for (const name of missing) {
    console.log(`\n  → Installing ${CORE_TOOLS[name].label}...`);
    const ok = CORE_TOOLS[name].install();
    if (ok && commandExists(name)) {
      console.log(`  ✓ ${CORE_TOOLS[name].label} installed`);
    } else {
      console.log(`  ✗ Could not install ${CORE_TOOLS[name].label} automatically.`);
      console.log(`    Install manually: ${CORE_TOOLS[name].manualUrl}`);
    }
  }
  console.log("");
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    printHelp();
    return 0;
  }

  let skills = discoverSkills(REPO_ROOT);
  if (opts.only) {
    const wanted = new Set(opts.only);
    skills = skills.filter((s) => wanted.has(s));
    const missing = opts.only.filter((s) => !skills.includes(s));
    if (missing.length) {
      console.error(`✗ Unknown skill(s) requested via --only: ${missing.join(", ")}`);
      return 1;
    }
  }

  if (!skills.length) {
    console.error("✗ No skills found next to install.js (expected folders containing SKILL.md).");
    return 1;
  }

  console.log(`\ncopilot-skills-install`);
  console.log(`  Source: ${REPO_ROOT}`);
  console.log(`  Target: ${opts.target}${opts.dryRun ? "  (dry-run — no changes will be made)" : ""}\n`);

  if (!opts.dryRun) fs.mkdirSync(opts.target, { recursive: true });

  const results = { installed: [], backedUp: [], skipped: [], failed: [] };
  const backupDir = path.join(opts.target, `_backup_${timestamp()}`);
  let backupUsed = false;

  for (const skill of skills) {
    const src = path.join(REPO_ROOT, skill);
    const dest = path.join(opts.target, skill);
    const exists = fs.existsSync(dest);

    try {
      if (exists && opts.skipExisting) {
        results.skipped.push(skill);
        console.log(`  ○ ${skill.padEnd(22)} already exists — skipped`);
        continue;
      }

      if (exists && !opts.force) {
        const backupDest = path.join(backupDir, skill);
        console.log(`  ↺ ${skill.padEnd(22)} backing up existing copy`);
        if (!opts.dryRun) {
          fs.mkdirSync(path.dirname(backupDest), { recursive: true });
          fs.renameSync(dest, backupDest);
        }
        backupUsed = true;
        results.backedUp.push(skill);
      } else if (exists && opts.force) {
        if (!opts.dryRun) fs.rmSync(dest, { recursive: true, force: true });
      }

      console.log(`  ✓ ${skill.padEnd(22)} installing`);
      if (!opts.dryRun) copyRecursiveSync(src, dest);
      results.installed.push(skill);
    } catch (err) {
      console.error(`  ✗ ${skill.padEnd(22)} FAILED: ${err.message}`);
      results.failed.push(skill);
    }
  }

  console.log(`\n  ${"─".repeat(52)}`);
  console.log(
    `  Installed: ${results.installed.length}  |  Backed up: ${results.backedUp.length}  |  ` +
      `Skipped: ${results.skipped.length}  |  Failed: ${results.failed.length}`
  );
  if (backupUsed && !opts.dryRun) console.log(`  Previous copies saved under: ${backupDir}`);
  console.log(`  ${"─".repeat(52)}\n`);

  // Prerequisite check (informational only — never auto-installs anything).
  const allTools = new Set();
  for (const skill of results.installed) (SKILL_PREREQS[skill] || []).forEach((t) => allTools.add(t));
  if (allTools.size) {
    console.log("  Prerequisite tools for the installed skills:");
    for (const tool of allTools) {
      const base = tool.split(" ")[0];
      const ok = commandExists(base);
      console.log(`    ${ok ? "✓" : "✗"} ${tool}`);
    }
    console.log("");
  }

  if (results.failed.length) {
    console.error("✗ Some skills failed to install. See errors above.");
    return 1;
  }

  console.log(`✓ Done. Skills are ready at: ${opts.target}\n`);

  console.log("  Checking core CLIs (gh, copilot)...");
  await ensureCoreTools(opts);

  return 0;
}

main()
  .then((code) => process.exit(code))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
