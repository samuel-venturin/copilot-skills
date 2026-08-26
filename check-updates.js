#!/usr/bin/env node
/**
 * check-updates.js
 *
 * Lightweight, non-interactive version check meant to be run daily by the
 * OS scheduler (registered via schedule-check.js). Compares the installed
 * manifest's version against the latest version published on GitHub — using
 * the GitHub REST API to fetch just package.json's raw contents, so it
 * never clones the repository. If a newer version is found, it prints a
 * message and (where supported) shows a native desktop notification;
 * nothing is installed automatically.
 *
 * Usage:
 *   node check-updates.js [--target <dir>]
 */

"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");
const https = require("https");
const { execSync } = require("child_process");

const REPO_SLUG = "samuel-venturin/copilot-skills";
const RAW_PACKAGE_JSON_URL = `https://raw.githubusercontent.com/${REPO_SLUG}/main/package.json`;
const MANIFEST_FILE = ".copilot-skills-manifest.json";
const LOG_FILE = path.join(os.homedir(), ".copilot", "skills-update-check.log");

function log(line) {
  const stamped = `[${new Date().toISOString()}] ${line}`;
  console.log(stamped);
  try {
    fs.mkdirSync(path.dirname(LOG_FILE), { recursive: true });
    fs.appendFileSync(LOG_FILE, stamped + "\n");
  } catch {
    // Logging is best-effort only.
  }
}

function parseArgs(argv) {
  const opts = { target: process.env.COPILOT_SKILLS_DIR || path.join(os.homedir(), ".copilot", "skills") };
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--target") opts.target = argv[++i];
  }
  return opts;
}

function fetchText(url) {
  return new Promise((resolve, reject) => {
    https
      .get(url, { headers: { "User-Agent": "copilot-skills-update-check" } }, (res) => {
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          resolve(fetchText(res.headers.location));
          return;
        }
        if (res.statusCode !== 200) {
          reject(new Error(`HTTP ${res.statusCode} fetching ${url}`));
          return;
        }
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => resolve(data));
      })
      .on("error", reject);
  });
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

function notify(title, message) {
  try {
    if (process.platform === "win32") {
      const ps =
        `[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null; ` +
        `$t = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); ` +
        `$x = $t.GetElementsByTagName("text"); $x.Item(0).AppendChild($t.CreateTextNode(${JSON.stringify(title)})) > $null; ` +
        `$x.Item(1).AppendChild($t.CreateTextNode(${JSON.stringify(message)})) > $null; ` +
        `$toast = [Windows.UI.Notifications.ToastNotification]::new($t); ` +
        `[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("copilot-skills")::Show($toast)`;
      execSync(`powershell -NoProfile -Command "${ps.replace(/"/g, '\\"')}"`, { stdio: "ignore" });
    } else if (process.platform === "darwin") {
      const script = `display notification ${JSON.stringify(message)} with title ${JSON.stringify(title)}`;
      execSync(`osascript -e '${script.replace(/'/g, "'\\''")}'`, { stdio: "ignore" });
    } else {
      execSync(`notify-send ${JSON.stringify(title)} ${JSON.stringify(message)}`, { stdio: "ignore" });
    }
  } catch {
    // Desktop notifications are best-effort — the log/console output is the source of truth.
  }
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const manifestPath = path.join(opts.target, MANIFEST_FILE);

  if (!fs.existsSync(manifestPath)) {
    log(`No manifest at ${manifestPath} — skipping check (install the skills first).`);
    return 0;
  }

  let manifest;
  try {
    manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  } catch (err) {
    log(`Could not read manifest: ${err.message}`);
    return 1;
  }

  const currentVersion = manifest.version || null;

  let latestVersion;
  try {
    const raw = await fetchText(RAW_PACKAGE_JSON_URL);
    latestVersion = JSON.parse(raw).version;
  } catch (err) {
    log(`Could not check for updates (offline?): ${err.message}`);
    return 0; // Not an error worth surfacing loudly — likely just no network right now.
  }

  const isNewer = !currentVersion || compareVersions(latestVersion, currentVersion) > 0;
  if (!isNewer) {
    log(`Up to date (v${currentVersion}).`);
    return 0;
  }

  const msg = `copilot-skills update available: v${currentVersion || "?"} -> v${latestVersion}. Run 'node update.js' (or npx github:${REPO_SLUG} update) to apply it.`;
  log(msg);
  notify("copilot-skills update available", `v${currentVersion || "?"} → v${latestVersion}. Run update.js to apply.`);
  return 0;
}

main()
  .then((code) => process.exit(code))
  .catch((err) => {
    log(`Unexpected error: ${err.message}`);
    process.exit(1);
  });
