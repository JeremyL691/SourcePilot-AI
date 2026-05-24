const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const extract = require("extract-zip");
const { downloadArtifact } = require("@electron/get");

const desktopRoot = path.resolve(__dirname, "..");
const electronRoot = path.join(desktopRoot, "node_modules", "electron");
const electronPackagePath = path.join(electronRoot, "package.json");
const distDir = path.join(electronRoot, "dist");
const pathTxt = path.join(electronRoot, "path.txt");

function platformBinaryPath() {
  if (process.platform === "win32") return "electron.exe";
  if (process.platform === "darwin") return "Electron.app/Contents/MacOS/Electron";
  return "electron";
}

function binaryPathFromPathTxt(relativeBinary) {
  return path.join(distDir, ...relativeBinary.split(/[\\/]/));
}

function isElectronReady() {
  if (!fs.existsSync(pathTxt)) return false;
  const relativeBinary = fs.readFileSync(pathTxt, "utf8").trim();
  if (!relativeBinary) return false;
  return fs.existsSync(binaryPathFromPathTxt(relativeBinary));
}

async function extractElectronZip(zipPath) {
  if (process.platform === "win32") {
    const psQuote = (value) => `'${value.replace(/'/g, "''")}'`;
    const result = spawnSync(
      "powershell.exe",
      [
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        `Expand-Archive -LiteralPath ${psQuote(zipPath)} -DestinationPath ${psQuote(distDir)} -Force`,
      ],
      { encoding: "utf8" },
    );

    if (result.status !== 0) {
      throw new Error(result.stderr || result.stdout || "PowerShell Expand-Archive failed.");
    }
    return;
  }

  await extract(zipPath, { dir: distDir });
}

async function main() {
  if (!fs.existsSync(electronPackagePath)) {
    throw new Error("Electron package is missing. Run `npm.cmd install` first.");
  }

  if (isElectronReady()) {
    console.log("Electron binary is ready.");
    return;
  }

  const electronPackage = JSON.parse(fs.readFileSync(electronPackagePath, "utf8"));
  const version = electronPackage.version;
  const relativeBinary = platformBinaryPath();

  console.log(`Repairing Electron ${version} binary for ${process.platform}-${process.arch}...`);
  const zipPath = await downloadArtifact({
    version,
    artifactName: "electron",
    platform: process.platform,
    arch: process.arch,
  });
  console.log(`Using Electron archive: ${zipPath}`);

  fs.rmSync(distDir, { recursive: true, force: true });
  fs.mkdirSync(distDir, { recursive: true });
  await extractElectronZip(zipPath);
  fs.writeFileSync(pathTxt, relativeBinary);

  if (!fs.existsSync(binaryPathFromPathTxt(relativeBinary))) {
    throw new Error(`Electron repair failed: ${binaryPathFromPathTxt(relativeBinary)} was not created.`);
  }

  console.log("Electron binary repaired.");
}

main().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
