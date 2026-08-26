#!/usr/bin/env node
/**
 * copilot-skills-schedule-check
 *
 * Registers (or removes) a daily background task that checks whether a
 * newer version of this skills collection is available, and notifies the
 * user if so — without installing anything automatically. The actual check
 * is delegated to check-updates.js, run once a day by the OS scheduler:
 *   - Windows: Task Scheduler (schtasks)
 *   - macOS:   launchd (a per-user LaunchAgent plist)
 *   - Linux:   cron (a line appended to the current user's crontab)
 *
 * Usage:
 *   node schedule-check.js [--target <dir>] [--time HH:MM] [--remove]
 *
 * Zero external dependencies — only Node.js builtins plus the OS's own
 * scheduler CLI (schtasks / launchctl / crontab), all of which ship with
 * the OS itself.
 */

"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");
const { execSync } = require("child_process");

const REPO_ROOT = __dirname;
const TASK_NAME = "CopilotSkillsUpdateCheck";

function parseArgs(argv) {
  const opts = {
    target: process.env.COPILOT_SKILLS_DIR || path.join(os.homedir(), ".copilot", "skills"),
    time: "09:00",
    remove: false,
    help: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--target") opts.target = argv[++i];
    else if (a === "--time") opts.time = argv[++i];
    else if (a === "--remove") opts.remove = true;
    else if (a === "-h" || a === "--help") opts.help = true;
  }
  return opts;
}

function printHelp() {
  console.log(`copilot-skills-schedule-check

Registers a daily background check for new copilot-skills versions
(Task Scheduler on Windows, launchd on macOS, cron on Linux). The check only
notifies you — it never installs updates automatically. Run
'node update.js' yourself (or just wait to be reminded) to actually update.

Options:
  --target <dir>   Directory to check (default: ~/.copilot/skills, or
                   $COPILOT_SKILLS_DIR if set)
  --time HH:MM      Daily run time, 24h format (default: 09:00)
  --remove          Unregister the daily check instead of creating it
  -h, --help        Show this help
`);
}

function runCmd(cmd, opts = {}) {
  return execSync(cmd, { stdio: opts.silent ? "pipe" : "inherit", ...opts });
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

// --- Windows: Task Scheduler -----------------------------------------------

// schtasks' /TR option has a ~261 character limit, and our node.exe + script
// paths can easily exceed that (e.g. under deeply nested npx cache dirs).
// Work around it by writing a short, stable wrapper script under
// %LOCALAPPDATA%\copilot-skills\ that itself contains the full paths, and
// pointing schtasks at that short wrapper path instead.
function wrapperDir() {
  return path.join(os.homedir(), "AppData", "Local", "copilot-skills");
}

function writeWindowsWrapper(opts) {
  const checker = path.join(REPO_ROOT, "check-updates.js");
  const dir = wrapperDir();
  fs.mkdirSync(dir, { recursive: true });
  const wrapperPath = path.join(dir, "run-check.cmd");
  const cmd = `@echo off\r\n"${process.execPath}" "${checker}" --target "${opts.target}"\r\n`;
  fs.writeFileSync(wrapperPath, cmd);
  return wrapperPath;
}

function scheduleWindows(opts) {
  const [hh, mm] = opts.time.split(":");

  if (opts.remove) {
    try {
      runCmd(`schtasks /Delete /TN "${TASK_NAME}" /F`, { silent: true });
      console.log(`✓ Removed scheduled task "${TASK_NAME}".`);
    } catch {
      console.log(`○ No scheduled task named "${TASK_NAME}" was found.`);
    }
    fs.rmSync(wrapperDir(), { recursive: true, force: true });
    return;
  }

  const wrapperPath = writeWindowsWrapper(opts);
  runCmd(`schtasks /Create /TN "${TASK_NAME}" /TR ${JSON.stringify(wrapperPath)} /SC DAILY /ST ${hh}:${mm} /F`);
  console.log(`✓ Scheduled a daily check at ${opts.time} via Task Scheduler (task "${TASK_NAME}").`);
  console.log(`  Runner script: ${wrapperPath}`);
  console.log(`  View it anytime with: schtasks /Query /TN "${TASK_NAME}" /V /FO LIST`);
}

// --- macOS: launchd ----------------------------------------------------

function launchAgentPath() {
  return path.join(os.homedir(), "Library", "LaunchAgents", `com.copilot-skills.update-check.plist`);
}

function scheduleMac(opts) {
  const plistPath = launchAgentPath();
  const label = "com.copilot-skills.update-check";

  if (opts.remove) {
    try {
      runCmd(`launchctl unload "${plistPath}"`, { silent: true });
    } catch {
      // Already unloaded / never loaded — fine.
    }
    fs.rmSync(plistPath, { force: true });
    console.log(`✓ Removed the daily launchd check (${label}).`);
    return;
  }

  const checker = path.join(REPO_ROOT, "check-updates.js");
  const [hh, mm] = opts.time.split(":").map((n) => parseInt(n, 10));
  const logDir = path.join(os.homedir(), ".copilot", "skills-update-check-logs");
  fs.mkdirSync(logDir, { recursive: true });

  const plist = `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${process.execPath}</string>
    <string>${checker}</string>
    <string>--target</string>
    <string>${opts.target}</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>${hh}</integer>
    <key>Minute</key><integer>${mm}</integer>
  </dict>
  <key>StandardOutPath</key><string>${path.join(logDir, "stdout.log")}</string>
  <key>StandardErrorPath</key><string>${path.join(logDir, "stderr.log")}</string>
</dict>
</plist>
`;
  fs.mkdirSync(path.dirname(plistPath), { recursive: true });
  fs.writeFileSync(plistPath, plist);
  try {
    runCmd(`launchctl unload "${plistPath}"`, { silent: true });
  } catch {
    // Not previously loaded — fine.
  }
  runCmd(`launchctl load "${plistPath}"`);
  console.log(`✓ Scheduled a daily check at ${opts.time} via launchd (${plistPath}).`);
  console.log(`  Logs: ${logDir}`);
}

// --- Linux: cron ------------------------------------------------------

function scheduleLinux(opts) {
  const checker = path.join(REPO_ROOT, "check-updates.js");
  const [hh, mm] = opts.time.split(":");
  const marker = "# copilot-skills-update-check";
  const line = `${mm} ${hh} * * * "${process.execPath}" "${checker}" --target "${opts.target}" ${marker}`;

  let existing = "";
  try {
    existing = execSync("crontab -l", { stdio: ["ignore", "pipe", "ignore"] }).toString();
  } catch {
    existing = "";
  }
  const filtered = existing
    .split("\n")
    .filter((l) => l.trim() && !l.includes(marker))
    .join("\n");

  if (opts.remove) {
    const next = filtered ? filtered + "\n" : "";
    execSync("crontab -", { input: next });
    console.log(`✓ Removed the daily cron check.`);
    return;
  }

  const next = (filtered ? filtered + "\n" : "") + line + "\n";
  execSync("crontab -", { input: next });
  console.log(`✓ Scheduled a daily check at ${opts.time} via cron.`);
  console.log(`  View it anytime with: crontab -l`);
}

function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    printHelp();
    return 0;
  }

  if (!/^\d{1,2}:\d{2}$/.test(opts.time)) {
    console.error(`✗ Invalid --time "${opts.time}" — expected HH:MM, e.g. 09:00`);
    return 1;
  }

  console.log(`\ncopilot-skills-schedule-check`);
  console.log(`  Platform: ${process.platform}`);
  console.log(`  Target:   ${opts.target}\n`);

  try {
    if (process.platform === "win32") {
      if (!commandExists("schtasks")) throw new Error("schtasks not found on PATH");
      scheduleWindows(opts);
    } else if (process.platform === "darwin") {
      scheduleMac(opts);
    } else {
      if (!commandExists("crontab")) throw new Error("crontab not found on PATH — install cron or schedule manually");
      scheduleLinux(opts);
    }
  } catch (err) {
    console.error(`✗ Could not ${opts.remove ? "remove" : "register"} the scheduled check: ${err.message}`);
    return 1;
  }

  console.log("");
  return 0;
}

process.exit(main());
