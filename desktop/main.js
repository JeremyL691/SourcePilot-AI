const { app, BrowserWindow, Menu, dialog, shell } = require("electron");
const { spawn, spawnSync } = require("child_process");
const http = require("http");
const path = require("path");
const fs = require("fs");
const os = require("os");

// In dev: __dirname = .../desktop, repoRoot = project root (has app/, dashboard/).
// In packaged build (electron-builder): Python source ships under process.resourcesPath as
//   Resources/app, Resources/dashboard, Resources/runtime, Resources/pyproject.toml — so
//   that directory becomes our "repoRoot" for cwd / venv / -e install purposes.
const isPackaged = app.isPackaged;
const repoRoot = isPackaged ? process.resourcesPath : path.resolve(__dirname, "..");
const runtimeRoot = isPackaged ? path.join(process.resourcesPath, "runtime") : path.join(__dirname, "runtime");
const apiPort = Number(process.env.SOURCEHERO_API_PORT || 8000);
const dashboardPort = Number(process.env.SOURCEHERO_DASHBOARD_PORT || 8501);
const apiUrl = `http://127.0.0.1:${apiPort}`;
const dashboardUrl = `http://127.0.0.1:${dashboardPort}`;
const children = [];
let resolvedPython = null;
let mainWindow = null;
let splashWindow = null;
let captureWindow = null;

function platformKey() {
  if (process.platform === "win32") return "win";
  if (process.platform === "darwin") return "mac";
  return "linux";
}

function bundledPythonPath() {
  const base = path.join(runtimeRoot, `python-${platformKey()}`);
  return process.platform === "win32"
    ? path.join(base, "python.exe")
    : path.join(base, "bin", "python3");
}

function venvPythonPath() {
  return process.platform === "win32"
    ? path.join(repoRoot, ".venv", "Scripts", "python.exe")
    : path.join(repoRoot, ".venv", "bin", "python");
}

function dataDir() {
  if (process.env.SOURCEHERO_DATA_DIR) return process.env.SOURCEHERO_DATA_DIR;
  if (process.platform === "darwin") {
    return path.join(os.homedir(), "Library", "Application Support", "SourceHero");
  }
  if (process.platform === "win32") {
    return path.join(process.env.APPDATA || path.join(os.homedir(), "AppData", "Roaming"), "SourceHero");
  }
  return path.join(os.homedir(), ".local", "share", "SourceHero");
}

function runSync(command, args, options = {}) {
  return spawnSync(command, args, {
    cwd: repoRoot,
    env: childEnv(),
    encoding: "utf8",
    windowsHide: true,
    ...options
  });
}

function runCommand(command, args, label) {
  return new Promise((resolve, reject) => {
    console.log(`[setup] ${label}`);
    const child = spawn(command, args, {
      cwd: repoRoot,
      env: childEnv(),
      windowsHide: true,
      stdio: "pipe"
    });
    child.stdout.on("data", data => console.log(`[setup] ${data}`.trim()));
    child.stderr.on("data", data => console.error(`[setup] ${data}`.trim()));
    child.on("error", reject);
    child.on("exit", code => {
      if (code === 0) resolve(true);
      else reject(new Error(`${label} failed with exit code ${code}`));
    });
  });
}

function findSystemPython() {
  if (process.env.SOURCEHERO_PYTHON && fs.existsSync(process.env.SOURCEHERO_PYTHON)) {
    return process.env.SOURCEHERO_PYTHON;
  }

  const candidates = process.platform === "win32"
    ? [
        ["py", ["-3.11", "-c", "import sys; print(sys.executable)"]],
        ["py", ["-3.12", "-c", "import sys; print(sys.executable)"]],
        ["python", ["-c", "import sys; print(sys.executable)"]]
      ]
    : [
        ["python3.11", ["-c", "import sys; print(sys.executable)"]],
        ["python3.12", ["-c", "import sys; print(sys.executable)"]],
        ["python3", ["-c", "import sys; print(sys.executable)"]],
        ["/opt/homebrew/bin/python3.11", ["-c", "import sys; print(sys.executable)"]],
        ["/usr/local/bin/python3.11", ["-c", "import sys; print(sys.executable)"]]
      ];

  for (const [command, args] of candidates) {
    const result = runSync(command, args);
    if (result.status !== 0) continue;
    const executable = (result.stdout || "").trim().split(/\r?\n/).pop();
    if (!executable) continue;
    const version = runSync(executable, ["-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"]);
    if (version.status === 0) return executable;
  }

  return null;
}

function dependenciesReady(python) {
  const result = runSync(python, [
    "-c",
    "import fastapi, streamlit, uvicorn, sqlalchemy, requests, pypdf, feedparser, platformdirs"
  ]);
  return result.status === 0;
}

async function ensurePythonEnvironment() {
  const bundled = bundledPythonPath();
  if (fs.existsSync(bundled)) {
    resolvedPython = bundled;
    return;
  }

  const venvPython = venvPythonPath();
  if (!fs.existsSync(venvPython)) {
    const systemPython = findSystemPython();
    if (!systemPython) {
      const installUrl = process.platform === "win32"
        ? "https://www.python.org/downloads/windows/"
        : "https://www.python.org/downloads/macos/";
      throw new Error(
        `Python 3.11+ not found.\n\n` +
        `Please install Python 3.11 or newer:\n  ${installUrl}\n` +
        (process.platform === "darwin" ? `\nOr via Homebrew:\n  brew install python@3.11\n` : "")
      );
    }
    await runCommand(systemPython, ["-m", "venv", ".venv"], "Creating Python virtual environment");
  }

  resolvedPython = venvPython;
  if (!dependenciesReady(resolvedPython)) {
    await runCommand(resolvedPython, ["-m", "pip", "install", "--upgrade", "pip"], "Upgrading pip");
    await runCommand(resolvedPython, ["-m", "pip", "install", "-e", "."], "Installing SourceHero Python dependencies");
  }
}

function pythonExecutable() {
  return resolvedPython || venvPythonPath();
}

function childEnv() {
  const env = {
    ...process.env,
    SOURCEHERO_API_PORT: String(apiPort),
    SOURCEHERO_DASHBOARD_PORT: String(dashboardPort),
    SOURCEHERO_API_BASE: apiUrl,
    PYTHONUNBUFFERED: "1"
  };
  // When packaged, app/ + dashboard/ live in resourcesPath and aren't pip-installed.
  // Prepend repoRoot to PYTHONPATH so `app.main:app` and the streamlit script resolve.
  if (isPackaged) {
    const sep = process.platform === "win32" ? ";" : ":";
    env.PYTHONPATH = repoRoot + (process.env.PYTHONPATH ? sep + process.env.PYTHONPATH : "");
  }
  return env;
}

function spawnService(name, args) {
  const child = spawn(pythonExecutable(), args, {
    cwd: repoRoot,
    env: childEnv(),
    windowsHide: true,
    stdio: "pipe"
  });
  child.stdout.on("data", data => console.log(`[${name}] ${data}`.trim()));
  child.stderr.on("data", data => console.error(`[${name}] ${data}`.trim()));
  child.on("exit", code => console.log(`[${name}] exited with ${code}`));
  children.push(child);
  return child;
}

function waitForHttp(url, timeoutMs = 60000) {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    const tick = () => {
      const request = http.get(url, response => {
        response.resume();
        if (response.statusCode && response.statusCode < 500) resolve(true);
        else retry();
      });
      request.on("error", retry);
      request.setTimeout(2500, () => { request.destroy(); retry(); });
    };
    const retry = () => {
      if (Date.now() - started > timeoutMs) {
        reject(new Error(`Timed out waiting for ${url}`));
      } else {
        setTimeout(tick, 800);
      }
    };
    tick();
  });
}

async function serviceIsReady(url) {
  try { await waitForHttp(url, 1500); return true; } catch { return false; }
}

async function startServices() {
  await ensurePythonEnvironment();

  if (!(await serviceIsReady(`${apiUrl}/health`))) {
    spawnService("api", ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(apiPort)]);
    await waitForHttp(`${apiUrl}/health`);
  }

  if (!(await serviceIsReady(dashboardUrl))) {
    spawnService("dashboard", [
      "-m", "streamlit", "run", "dashboard/streamlit_app.py",
      "--server.headless", "true",
      "--server.port", String(dashboardPort),
      "--browser.gatherUsageStats", "false"
    ]);
    await waitForHttp(dashboardUrl);
  }
}

function createSplash() {
  splashWindow = new BrowserWindow({
    width: 480,
    height: 280,
    frame: false,
    resizable: false,
    alwaysOnTop: true,
    skipTaskbar: false,
    title: "SourceHero AI",
    webPreferences: { contextIsolation: true, nodeIntegration: false }
  });
  const splashHtml = `
    <!doctype html><html><head><meta charset="utf-8"><style>
      body{margin:0;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;
           background:linear-gradient(135deg,#1e3a8a 0%,#7c3aed 100%);color:#fff;
           display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;}
      h1{margin:0 0 8px;font-size:32px;letter-spacing:1px;}
      p{margin:0;opacity:0.85;font-size:14px;}
      .spin{margin-top:24px;width:32px;height:32px;border:3px solid rgba(255,255,255,0.3);
            border-top-color:#fff;border-radius:50%;animation:spin 1s linear infinite;}
      @keyframes spin{to{transform:rotate(360deg)}}
    </style></head><body>
      <h1>SourceHero AI</h1>
      <p>Starting up…</p>
      <div class="spin"></div>
    </body></html>`;
  splashWindow.loadURL("data:text/html;charset=utf-8," + encodeURIComponent(splashHtml));
}

function buildMenu() {
  const isMac = process.platform === "darwin";
  const template = [
    ...(isMac ? [{
      label: "SourceHero",
      submenu: [
        { role: "about" },
        { type: "separator" },
        { role: "services" },
        { type: "separator" },
        { role: "hide" }, { role: "hideOthers" }, { role: "unhide" },
        { type: "separator" },
        { role: "quit" }
      ]
    }] : []),
    {
      label: "File",
      submenu: [
        {
          label: "Quick Capture",
          accelerator: "CmdOrCtrl+Shift+V",
          click: () => openQuickCaptureWindow()
        },
        { type: "separator" },
        {
          label: "Open Data Folder",
          click: () => shell.openPath(dataDir())
        },
        { type: "separator" },
        isMac ? { role: "close" } : { role: "quit" }
      ]
    },
    { label: "Edit", submenu: [{ role: "undo" }, { role: "redo" }, { type: "separator" }, { role: "cut" }, { role: "copy" }, { role: "paste" }, { role: "selectAll" }] },
    { label: "View", submenu: [{ role: "reload" }, { role: "forceReload" }, { role: "toggleDevTools" }, { type: "separator" }, { role: "resetZoom" }, { role: "zoomIn" }, { role: "zoomOut" }, { type: "separator" }, { role: "togglefullscreen" }] },
    {
      label: "Help",
      submenu: [
        { label: "GitHub", click: () => shell.openExternal("https://github.com/JeremyL691/SourceHero-AI") },
        { label: "Report Issue", click: () => shell.openExternal("https://github.com/JeremyL691/SourceHero-AI/issues") }
      ]
    }
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1320,
    height: 920,
    minWidth: 1100,
    minHeight: 760,
    title: "SourceHero AI",
    show: false,
    webPreferences: { contextIsolation: true, nodeIntegration: false }
  });
  mainWindow.loadURL(dashboardUrl);
  mainWindow.once("ready-to-show", () => {
    if (splashWindow) { splashWindow.close(); splashWindow = null; }
    mainWindow.show();
  });
}

function openQuickCaptureWindow() {
  if (captureWindow && !captureWindow.isDestroyed()) {
    captureWindow.focus();
    return;
  }
  captureWindow = new BrowserWindow({
    width: 720,
    height: 760,
    minWidth: 640,
    minHeight: 680,
    title: "Quick Capture",
    webPreferences: { contextIsolation: true, nodeIntegration: false }
  });
  captureWindow.on("closed", () => {
    captureWindow = null;
  });
  captureWindow.loadURL(`${dashboardUrl}?quick_capture=1`);
}

function stopChildren() {
  for (const child of children) if (!child.killed) child.kill();
}

function showFatalError(message) {
  if (splashWindow) { splashWindow.close(); splashWindow = null; }
  dialog.showErrorBox(
    "SourceHero AI failed to start",
    `${message}\n\n` +
    `Logs: ${path.join(dataDir(), "logs")}\n` +
    `Data folder: ${dataDir()}`
  );
}

app.whenReady().then(async () => {
  buildMenu();
  createSplash();
  try {
    await startServices();
    createMainWindow();
  } catch (error) {
    showFatalError(error.message);
    app.quit();
  }
});

app.on("window-all-closed", () => {
  stopChildren();
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", stopChildren);

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createMainWindow();
});

module.exports = { pythonExecutable, waitForHttp, apiUrl, dashboardUrl, dataDir, openQuickCaptureWindow };
