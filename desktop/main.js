const { app, BrowserWindow, dialog } = require("electron");
const { spawn } = require("child_process");
const http = require("http");
const path = require("path");
const fs = require("fs");

const repoRoot = path.resolve(__dirname, "..");
const apiPort = Number(process.env.SOURCEPILOT_API_PORT || 8000);
const dashboardPort = Number(process.env.SOURCEPILOT_DASHBOARD_PORT || 8501);
const apiUrl = `http://127.0.0.1:${apiPort}`;
const dashboardUrl = `http://127.0.0.1:${dashboardPort}`;
const children = [];
let resolvedPython = null;

function venvPythonPath() {
  return process.platform === "win32"
    ? path.join(repoRoot, ".venv", "Scripts", "python.exe")
    : path.join(repoRoot, ".venv", "bin", "python");
}

function runSync(command, args, options = {}) {
  const result = require("child_process").spawnSync(command, args, {
    cwd: repoRoot,
    env: childEnv(),
    encoding: "utf8",
    windowsHide: true,
    ...options
  });
  return result;
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
      if (code === 0) {
        resolve(true);
      } else {
        reject(new Error(`${label} failed with exit code ${code}`));
      }
    });
  });
}

function findSystemPython() {
  if (process.env.SOURCEPILOT_PYTHON && fs.existsSync(process.env.SOURCEPILOT_PYTHON)) {
    return process.env.SOURCEPILOT_PYTHON;
  }

  const candidates = process.platform === "win32"
    ? [["py", ["-3.11", "-c", "import sys; print(sys.executable)"]], ["python", ["-c", "import sys; print(sys.executable)"]]]
    : [["python3", ["-c", "import sys; print(sys.executable)"]], ["python", ["-c", "import sys; print(sys.executable)"]]];

  for (const [command, args] of candidates) {
    const result = runSync(command, args);
    if (result.status !== 0) continue;
    const executable = (result.stdout || "").trim().split(/\r?\n/).pop();
    if (!executable) continue;
    const version = runSync(executable, ["-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"]);
    if (version.status === 0) {
      return executable;
    }
  }

  return null;
}

function dependenciesReady(python) {
  const result = runSync(python, [
    "-c",
    "import fastapi, streamlit, uvicorn, sqlalchemy, requests, pypdf, feedparser"
  ]);
  return result.status === 0;
}

async function ensurePythonEnvironment() {
  const venvPython = venvPythonPath();
  if (!fs.existsSync(venvPython)) {
    const systemPython = findSystemPython();
    if (!systemPython) {
      throw new Error(
        "Python 3.11 or newer was not found. Install Python from https://www.python.org/downloads/windows/, check 'Add python.exe to PATH', then run npm.cmd run dev again."
      );
    }
    await runCommand(systemPython, ["-m", "venv", ".venv"], "Creating Python virtual environment");
  }

  resolvedPython = venvPython;
  if (!dependenciesReady(resolvedPython)) {
    await runCommand(resolvedPython, ["-m", "pip", "install", "--upgrade", "pip"], "Upgrading pip");
    await runCommand(resolvedPython, ["-m", "pip", "install", "-e", "."], "Installing SourcePilot Python dependencies");
  }
}

function pythonExecutable() {
  return resolvedPython || venvPythonPath();
}

function childEnv() {
  return {
    ...process.env,
    SOURCEPILOT_API_PORT: String(apiPort),
    SOURCEPILOT_DASHBOARD_PORT: String(dashboardPort),
    SOURCEPILOT_API_BASE: apiUrl,
    PYTHONUNBUFFERED: "1"
  };
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
        if (response.statusCode && response.statusCode < 500) {
          resolve(true);
        } else {
          retry();
        }
      });
      request.on("error", retry);
      request.setTimeout(2500, () => {
        request.destroy();
        retry();
      });
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
  try {
    await waitForHttp(url, 1500);
    return true;
  } catch {
    return false;
  }
}

async function startServices() {
  await ensurePythonEnvironment();

  if (!(await serviceIsReady(`${apiUrl}/health`))) {
    spawnService("api", ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(apiPort)]);
    await waitForHttp(`${apiUrl}/health`);
  }

  if (!(await serviceIsReady(dashboardUrl))) {
    spawnService("dashboard", [
      "-m",
      "streamlit",
      "run",
      "dashboard/streamlit_app.py",
      "--server.headless",
      "true",
      "--server.port",
      String(dashboardPort),
      "--browser.gatherUsageStats",
      "false"
    ]);
    await waitForHttp(dashboardUrl);
  }
}

function createWindow() {
  const window = new BrowserWindow({
    width: 1320,
    height: 920,
    minWidth: 1100,
    minHeight: 760,
    title: "SourcePilot AI",
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  window.loadURL(dashboardUrl);
  return window;
}

function stopChildren() {
  for (const child of children) {
    if (!child.killed) {
      child.kill();
    }
  }
}

app.whenReady().then(async () => {
  try {
    await startServices();
    createWindow();
  } catch (error) {
    dialog.showErrorBox("SourcePilot AI failed to start", error.message);
    app.quit();
  }
});

app.on("window-all-closed", () => {
  stopChildren();
  app.quit();
});

app.on("before-quit", stopChildren);

module.exports = {
  pythonExecutable,
  waitForHttp,
  apiUrl,
  dashboardUrl
};
