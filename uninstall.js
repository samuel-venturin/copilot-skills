#!/usr/bin/env node
/**
 * copilot-skills-uninstall
 *
 * Removes skills previously installed by install.js from the user's
 * ~/.copilot/skills directory (or a custom target). Only removes skill
 * folders that exist in this repository (so it never touches unrelated
 * custom skills the user may have added on their own), unless --all is
 * passed together with --force.
 *
 * Usage:
 *   node uninstall.js [--target <dir>] [--only <name,...>] [--all] [--dry-run] [--yes] [--keep-backups]
 *
 * Zero external dependencies — same design as install.js, so this also runs
 * fine via `npx github:<owner>/copilot-skills uninstall` style invocations
 * (see package.json bin entries) or `node uninstall.js` after a clone.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");

const REPO_ROOT = __dirname;

function discoverSkills(root) {
  return fs
    .readdirSync(root, { withFileTypes: true })
    .filter((e) => e.isDirectory() && !e.name.startsWith("."))
    .map((e) => e.name)
    .filter((name) => fs.existsSync(path.join(root, name, "SKILL.md")))
    .sort();
}

function parseArgs(argv) {
  const opts = {
    target: process.env.COPILOT_SKILLS_DIR || path.join(os.homedir(), ".copilot", "skills"),
    only: null,
    all: false,
    dryRun: false,
    yes: false,
    keepBackups: false,
    help: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--target") opts.target = argv[++i];
    else if (a === "--only") opts.only = argv[++i].split(",").map((s) => s.trim());
    else if (a === "--all") opts.all = true;
    else if (a === "--dry-run") opts.dryRun = true;
    else if (a === "--yes" || a === "-y") opts.yes = true;
    else if (a === "--keep-backups") opts.keepBackups = true;
    else if (a === "-h" || a === "--help") opts.help = true;
  }
  return opts;
}

function printHelp() {
  console.log(`copilot-skills-uninstall

Removes skills installed by install.js from ~/.copilot/skills (or a custom
target directory). By default only removes skills that exist in this
repository, so any unrelated custom skill you added yourself is left alone.

Options:
  --target <dir>     Directory to remove skills from (default: ~/.copilot/skills,
                     or $COPILOT_SKILLS_DIR if set)
  --only <a,b,c>      Only remove the named skills (comma-separated)
  --all               Remove ALL skills found in --target, including ones not
                     from this repository (requires --yes or interactive confirm)
  --dry-run           Print what would be removed without changing anything
  --yes, -y           Skip the confirmation prompt
  --keep-backups      Do not delete this repo's _backup_* folders in --target
  -h, --help          Show this help
`);
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

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    printHelp();
    return 0;
  }

  if (!fs.existsSync(opts.target)) {
    console.log(`Nothing to do — target directory does not exist: ${opts.target}`);
    return 0;
  }

  const repoSkills = discoverSkills(REPO_ROOT);
  const installedEntries = fs.readdirSync(opts.target, { withFileTypes: true }).filter((e) => e.isDirectory());
  const backupDirs = installedEntries.filter((e) => e.name.startsWith("_backup_")).map((e) => e.name);
  let candidates = installedEntries.filter((e) => !e.name.startsWith("_backup_")).map((e) => e.name);

  if (opts.only) {
    const wanted = new Set(opts.only);
    candidates = candidates.filter((s) => wanted.has(s));
  } else if (!opts.all) {
    candidates = candidates.filter((s) => repoSkills.includes(s));
  }

  const unknown = candidates.filter((s) => !repoSkills.includes(s));
  if (unknown.length && !opts.all) {
    console.error(
      `✗ Skill(s) not found in this repository: ${unknown.join(", ")}. ` +
        `Re-run with --all to remove skills outside this repository too.`
    );
    return 1;
  }

  if (!candidates.length) {
    console.log(`Nothing to remove at: ${opts.target}`);
    return 0;
  }

  console.log(`\ncopilot-skills-uninstall`);
  console.log(`  Target: ${opts.target}${opts.dryRun ? "  (dry-run — no changes will be made)" : ""}\n`);
  console.log("  The following will be removed:");
  for (const s of candidates) console.log(`    - ${s}`);
  if (backupDirs.length && !opts.keepBackups) {
    console.log("  The following backup folders will also be removed:");
    for (const b of backupDirs) console.log(`    - ${b}`);
  }
  console.log("");

  if (!opts.dryRun) {
    let proceed = opts.yes;
    if (!proceed) {
      proceed = await askYesNo("  Proceed with removal? [y/N] ");
    }
    if (!proceed) {
      console.log("  ○ Cancelled. Nothing was removed.\n");
      return 0;
    }
  }

  const removed = [];
  const failed = [];
  for (const skill of candidates) {
    const dest = path.join(opts.target, skill);
    console.log(`  ✗ ${skill.padEnd(22)} removing`);
    if (!opts.dryRun) {
      try {
        fs.rmSync(dest, { recursive: true, force: true });
        removed.push(skill);
      } catch (err) {
        console.error(`    FAILED: ${err.message}`);
        failed.push(skill);
      }
    } else {
      removed.push(skill);
    }
  }

  if (!opts.keepBackups) {
    for (const b of backupDirs) {
      console.log(`  ✗ ${b.padEnd(22)} removing (backup)`);
      if (!opts.dryRun) {
        try {
          fs.rmSync(path.join(opts.target, b), { recursive: true, force: true });
        } catch (err) {
          console.error(`    FAILED: ${err.message}`);
        }
      }
    }
  }

  console.log(`\n  ${"─".repeat(52)}`);
  console.log(`  Removed: ${removed.length}  |  Failed: ${failed.length}`);
  console.log(`  ${"─".repeat(52)}\n`);

  if (failed.length) {
    console.error("✗ Some skills failed to remove. See errors above.");
    return 1;
  }

  console.log(opts.dryRun ? "✓ Dry-run complete. No changes were made.\n" : "✓ Done. Skills removed.\n");
  return 0;
}

main()
  .then((code) => process.exit(code))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
