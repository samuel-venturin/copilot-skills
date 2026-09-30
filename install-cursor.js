#!/usr/bin/env node
/**
 * install-cursor.js
 *
 * Installs this repository's skills into Cursor-native locations, mirroring
 * how `install.js` targets ~/.copilot/skills for GitHub Copilot CLI.
 *
 * Default targets (auto-detected, no flags required):
 *   1) ~/.cursor/skills
 *   2) ~/.cursor/scripts          (bundled repo scripts + optional local extras)
 *   3) ~/.cursor/rules            (always-apply discovery rule)
 *   4) every personal Cursor Agent Store found on this machine
 *      (.../Cursor/AgentStores/cursor_agent_stores/<t*-u*>/files)
 *
 * Rewrites Copilot/Claude path prefixes to ~/.cursor/... and prefers `python`
 * on Windows while keeping Python tools/ intact.
 *
 * Usage (via npx, no clone):
 *   npx github:samuel-venturin/copilot-skills install-cursor
 *   npx github:samuel-venturin/copilot-skills cursor
 *
 * Or from a local clone:
 *   node install-cursor.js
 *   node install.js install-cursor
 */

"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");

const REPO_ROOT = __dirname;
const MANIFEST_FILE = ".cursor-skills-manifest.json";
const REPO_SLUG = "samuel-venturin/copilot-skills";

const SKIP_DIRS = new Set([
  ".git",
  ".github",
  "node_modules",
  "__pycache__",
  "scripts",
]);

function readLocalVersion() {
  try {
    return JSON.parse(fs.readFileSync(path.join(REPO_ROOT, "package.json"), "utf8")).version;
  } catch {
    return null;
  }
}

function parseArgs(argv) {
  const opts = {
    dryRun: false,
    force: false,
    skipExisting: false,
    only: null,
    target: path.join(os.homedir(), ".cursor", "skills"),
    scriptsTarget: path.join(os.homedir(), ".cursor", "scripts"),
    rulesTarget: path.join(os.homedir(), ".cursor", "rules"),
    agentStore: null, // explicit single store (files root)
    noAgentStore: false,
    help: false,
    yes: false,
  };

  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--dry-run") opts.dryRun = true;
    else if (a === "--force") opts.force = true;
    else if (a === "--skip-existing") opts.skipExisting = true;
    else if (a === "--no-agent-store") opts.noAgentStore = true;
    else if (a === "--yes" || a === "-y") opts.yes = true;
    else if (a === "--help" || a === "-h") opts.help = true;
    else if (a === "--target") opts.target = path.resolve(argv[++i]);
    else if (a === "--scripts-target") opts.scriptsTarget = path.resolve(argv[++i]);
    else if (a === "--rules-target") opts.rulesTarget = path.resolve(argv[++i]);
    else if (a === "--agent-store") opts.agentStore = path.resolve(argv[++i]);
    else if (a === "--only") {
      opts.only = new Set(
        String(argv[++i] || "")
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean)
      );
    } else {
      console.error(`Unknown argument: ${a}`);
      opts.help = true;
    }
  }
  return opts;
}

function printHelp() {
  console.log(`Usage: node install-cursor.js [options]

Installs Copilot Skills into Cursor Agent Skills locations on this machine.

Via npx (no clone):
  npx github:${REPO_SLUG} install-cursor
  npx github:${REPO_SLUG} cursor

Options:
  --target <dir>           Skills install dir (default: ~/.cursor/skills)
  --scripts-target <dir>   Shared scripts dir (default: ~/.cursor/scripts)
  --rules-target <dir>     Cursor rules dir (default: ~/.cursor/rules)
  --agent-store <dir>      Install into this Agent Store "files" root only
  --no-agent-store         Skip Agent Store install (skills/rules only)
  --only <a,b,c>           Install only named skills
  --force                  Overwrite existing skill folders in place
  --skip-existing          Never replace an existing skill folder
  --dry-run                Preview without writing
  --yes, -y                Non-interactive (reserved for future prompts)
  --help                   Show this help

Auto-detect:
  Personal Cursor Agent Stores are discovered under:
    %LOCALAPPDATA%\\\\Cursor\\\\AgentStores\\\\cursor_agent_stores\\\\t*-u*\\\\files   (Windows)
    ~/Library/Application Support/Cursor/AgentStores/cursor_agent_stores/t*-u*/files (macOS)
    ~/.config/Cursor/AgentStores/cursor_agent_stores/t*-u*/files                     (Linux)
`);
}

function isSkillDir(dir) {
  return fs.existsSync(path.join(dir, "SKILL.md"));
}

function listRepoSkills() {
  return fs
    .readdirSync(REPO_ROOT, { withFileTypes: true })
    .filter((d) => d.isDirectory() && !SKIP_DIRS.has(d.name))
    .map((d) => path.join(REPO_ROOT, d.name))
    .filter(isSkillDir)
    .map((full) => ({ name: path.basename(full), full }));
}

function ensureDir(dir, dryRun) {
  if (dryRun) {
    console.log(`[dry-run] mkdir ${dir}`);
    return;
  }
  fs.mkdirSync(dir, { recursive: true });
}

function copyFile(src, dest, dryRun) {
  if (dryRun) {
    console.log(`[dry-run] copy ${src} -> ${dest}`);
    return;
  }
  ensureDir(path.dirname(dest), false);
  fs.copyFileSync(src, dest);
}

function copyDirRecursive(src, dest, dryRun) {
  ensureDir(dest, dryRun);
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    if (entry.name === "__pycache__" || entry.name === ".git") continue;
    const from = path.join(src, entry.name);
    const to = path.join(dest, entry.name);
    if (entry.isDirectory()) copyDirRecursive(from, to, dryRun);
    else copyFile(from, to, dryRun);
  }
}

function backupIfExists(targetPath, dryRun, force) {
  if (!fs.existsSync(targetPath)) return null;
  if (force) return null;
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const backupRoot = path.join(path.dirname(targetPath), `_backup_${stamp}`);
  const backupPath = path.join(backupRoot, path.basename(targetPath));
  if (dryRun) {
    console.log(`[dry-run] backup ${targetPath} -> ${backupPath}`);
    return backupPath;
  }
  ensureDir(backupRoot, false);
  fs.renameSync(targetPath, backupPath);
  return backupPath;
}

/** Rewrite skill markdown/config text for Cursor runtime paths. */
function rewriteCursorText(text) {
  return text
    .replaceAll("~/.claude/skills", "~/.cursor/skills")
    .replaceAll("~/.copilot/skills", "~/.cursor/skills")
    .replaceAll("~/.claude/scripts", "~/.cursor/scripts")
    .replaceAll("~/.copilot/docs", "~/.cursor/docs")
    .replaceAll("%USERPROFILE%\\.claude\\skills", "%USERPROFILE%\\.cursor\\skills")
    .replaceAll("%USERPROFILE%\\.copilot\\skills", "%USERPROFILE%\\.cursor\\skills")
    .replaceAll("python3 ~/.cursor/", "python ~/.cursor/")
    .replaceAll("python3 ~/.claude/", "python ~/.cursor/")
    .replaceAll("python3 ~/.copilot/", "python ~/.cursor/")
    .replace(/(^|[^\w])python3(\s+)/gm, "$1python$2");
}

function rewriteTree(rootDir, dryRun) {
  if (dryRun) {
    console.log(`[dry-run] rewrite paths under ${rootDir}`);
    return;
  }
  const stack = [rootDir];
  while (stack.length) {
    const dir = stack.pop();
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (entry.name !== "__pycache__") stack.push(full);
        continue;
      }
      if (!/\.(md|json|py|txt|yml|yaml)$/i.test(entry.name)) continue;
      const original = fs.readFileSync(full, "utf8");
      const updated = rewriteCursorText(original);
      if (updated !== original) fs.writeFileSync(full, updated, "utf8");
    }
  }
}

function installSkill(skill, targetRoot, opts) {
  const dest = path.join(targetRoot, skill.name);
  if (fs.existsSync(dest) && opts.skipExisting) {
    console.log(`skip existing: ${skill.name}`);
    return { name: skill.name, status: "skipped" };
  }
  if (fs.existsSync(dest) && !opts.force) {
    backupIfExists(dest, opts.dryRun, false);
  } else if (fs.existsSync(dest) && opts.force && !opts.dryRun) {
    fs.rmSync(dest, { recursive: true, force: true });
  }

  console.log(`install skill: ${skill.name} -> ${dest}`);
  copyDirRecursive(skill.full, dest, opts.dryRun);
  rewriteTree(dest, opts.dryRun);
  return { name: skill.name, status: "installed", dest };
}

/**
 * Discover personal Cursor Agent Store "files" roots on this machine.
 * Personal stores use ids like `t29850340-u450696229` (not conversation UUIDs).
 */
function detectPersonalAgentStoreFilesRoots() {
  const roots = [];
  const localAppData = process.env.LOCALAPPDATA;
  if (localAppData) {
    roots.push(path.join(localAppData, "Cursor", "AgentStores", "cursor_agent_stores"));
  }
  roots.push(
    path.join(
      os.homedir(),
      "Library",
      "Application Support",
      "Cursor",
      "AgentStores",
      "cursor_agent_stores"
    )
  );
  roots.push(path.join(os.homedir(), ".config", "Cursor", "AgentStores", "cursor_agent_stores"));
  roots.push(path.join(os.homedir(), ".cursor", "AgentStores", "cursor_agent_stores"));

  const found = [];
  const seen = new Set();
  for (const root of roots) {
    if (!fs.existsSync(root)) continue;
    let entries = [];
    try {
      entries = fs.readdirSync(root, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      // Personal user stores look like t<digits>-u<digits>
      if (!/^t\d+-u\d+$/i.test(entry.name)) continue;
      const filesDir = path.join(root, entry.name, "files");
      if (!fs.existsSync(filesDir)) continue;
      const key = path.resolve(filesDir).toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      found.push(filesDir);
    }
  }
  return found;
}

function resolveAgentStoreTargets(opts) {
  if (opts.noAgentStore) return [];
  if (opts.agentStore) return [opts.agentStore];
  return detectPersonalAgentStoreFilesRoots();
}

function installSharedScripts(scriptsTarget, dryRun) {
  // Prefer bundled repo scripts so npx installs work for colleagues without ~/.claude.
  const candidates = [
    path.join(REPO_ROOT, "scripts"),
    path.join(os.homedir(), ".claude", "scripts"),
  ];
  const source = candidates.find((p) => fs.existsSync(p));
  ensureDir(scriptsTarget, dryRun);
  if (!source) {
    console.log(
      `warn: no shared scripts found (looked in ${candidates.join(", ")}). Skills that call task_manager.py / spec-extractor may need them.`
    );
    return [];
  }
  const installed = [];
  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    if (!entry.isFile()) continue;
    if (!/\.(py|md|sh|ps1)$/i.test(entry.name)) continue;
    const from = path.join(source, entry.name);
    const to = path.join(scriptsTarget, entry.name);
    console.log(`install script: ${entry.name} -> ${to}`);
    copyFile(from, to, dryRun);
    if (!dryRun) {
      const original = fs.readFileSync(to, "utf8");
      const updated = rewriteCursorText(original);
      if (updated !== original) fs.writeFileSync(to, updated, "utf8");
    }
    installed.push(entry.name);
  }
  return installed;
}

function writeCursorRule(rulesTarget, skills, dryRun) {
  ensureDir(rulesTarget, dryRun);
  const rulePath = path.join(rulesTarget, "copilot-skills.mdc");
  const skillList = skills.map((s) => `- \`${s.name}\``).join("\n");
  const body = `---
description: Use personal Copilot-derived Cursor skills (interpret, execute, pr-maestro, refactor, local-stack, qa-test-tutorial, etc.) with their Python tools under ~/.cursor/skills.
alwaysApply: true
---

# Copilot Skills (Cursor)

Personal automation skills live in \`~/.cursor/skills/\` (and the Cursor Agent Store \`skills/\` when synced).

## When to use

If the user asks to interpret a Jira/spec, execute a planned task, open/update a PR, cut a release, refactor with analyzers, manage the local stack, extract testids, write a QA tutorial / capture evidence screenshots, or manage the task queue — **read and follow the matching skill's \`SKILL.md\`** before improvising.

## Skill root

- Skills: \`~/.cursor/skills/<skill-name>/SKILL.md\`
- Python tools: \`~/.cursor/skills/<skill-name>/tools/\`
- Shared scripts: \`~/.cursor/scripts/\` (e.g. \`task_manager.py\`, \`spec-extractor.tool.py\`)

On Windows, resolve \`~\` as \`%USERPROFILE%\` and run tools with \`python\` (not \`python3\`).

## Available skills

${skillList}

## Execution rules

1. Prefer the skill's documented Python entrypoints over hand-rolled \`gh\`/\`git\` sequences.
2. Keep skill \`tools/config.json\` values; only change them when the user asks.
3. Do not invent alternate workflows when a skill already covers the request.
`;

  if (dryRun) {
    console.log(`[dry-run] write rule ${rulePath}`);
    return rulePath;
  }
  fs.writeFileSync(rulePath, body, "utf8");
  console.log(`install rule: ${rulePath}`);
  return rulePath;
}

function writeManifest(targetRoot, payload, dryRun) {
  const file = path.join(targetRoot, MANIFEST_FILE);
  if (dryRun) {
    console.log(`[dry-run] write manifest ${file}`);
    return;
  }
  fs.writeFileSync(file, JSON.stringify(payload, null, 2) + "\n", "utf8");
}

function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    printHelp();
    process.exit(0);
  }

  let skills = listRepoSkills();
  if (opts.only) {
    skills = skills.filter((s) => opts.only.has(s.name));
  }
  if (!skills.length) {
    console.error("No skills to install.");
    process.exit(1);
  }

  const agentStores = resolveAgentStoreTargets(opts);

  console.log(`copilot-skills Cursor installer v${readLocalVersion() || "?"}`);
  console.log(`Cursor skills target: ${opts.target}`);
  console.log(`Scripts target:       ${opts.scriptsTarget}`);
  console.log(`Rules target:         ${opts.rulesTarget}`);
  if (agentStores.length) {
    console.log(`Agent store(s):`);
    for (const s of agentStores) console.log(`  - ${s}`);
  } else if (opts.noAgentStore) {
    console.log(`Agent store(s):      skipped (--no-agent-store)`);
  } else {
    console.log(
      `Agent store(s):      none found (will still install ~/.cursor/skills + rules)`
    );
  }

  ensureDir(opts.target, opts.dryRun);
  const installed = skills.map((s) => installSkill(s, opts.target, opts));
  const scripts = installSharedScripts(opts.scriptsTarget, opts.dryRun);
  writeCursorRule(
    opts.rulesTarget,
    installed.filter((s) => s.status === "installed" || s.status === "skipped"),
    opts.dryRun
  );

  const agentInstalledByStore = [];
  for (const storeFiles of agentStores) {
    const storeSkills = path.join(storeFiles, "skills");
    ensureDir(storeSkills, opts.dryRun);
    const results = skills.map((s) => installSkill(s, storeSkills, opts));
    agentInstalledByStore.push({ store: storeFiles, skills: results.map((r) => r.name) });
  }

  const manifest = {
    version: readLocalVersion(),
    installedAt: new Date().toISOString(),
    repo: REPO_SLUG,
    source: REPO_ROOT,
    target: opts.target,
    scriptsTarget: opts.scriptsTarget,
    rulesTarget: opts.rulesTarget,
    agentStores,
    skills: installed.map((s) => s.name).sort(),
    scripts,
    agentInstalledByStore,
  };
  writeManifest(opts.target, manifest, opts.dryRun);

  console.log("\nDone.");
  console.log(
    "Restart Cursor (or open a new Agent chat) so it reloads personal skills/rules."
  );
  console.log(`Re-run anytime: npx github:${REPO_SLUG} install-cursor`);
}

main();
