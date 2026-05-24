const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const projectRoot = path.resolve(root, "..");
const required = [
  path.join(root, "package.json"),
  path.join(root, ".npmrc"),
  path.join(root, "main.js"),
  path.join(root, "scripts", "ensure-electron.js"),
  path.join(projectRoot, "Install-SourcePilot.bat"),
  path.join(projectRoot, "Start-SourcePilot.bat"),
  path.join(projectRoot, "scripts", "setup-windows.ps1"),
  path.join(projectRoot, "scripts", "start-windows.ps1"),
  path.join(projectRoot, "app", "main.py"),
  path.join(projectRoot, "dashboard", "streamlit_app.py")
];

for (const file of required) {
  if (!fs.existsSync(file)) {
    throw new Error(`Missing required file: ${file}`);
  }
}

const pkg = JSON.parse(fs.readFileSync(path.join(root, "package.json"), "utf8"));
if (!pkg.devDependencies || !pkg.devDependencies.electron) {
  throw new Error("Electron dependency is missing.");
}
if (!pkg.scripts.dev.includes("ensure-electron")) {
  throw new Error("Desktop dev script must prepare Electron before launch.");
}

const mainJs = fs.readFileSync(path.join(root, "main.js"), "utf8");
if (!mainJs.includes("ensurePythonEnvironment")) {
  throw new Error("Desktop main process must prepare the Python environment before launch.");
}

console.log("Electron desktop smoke check passed.");
