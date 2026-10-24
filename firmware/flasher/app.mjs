const byId = (id) => document.getElementById(id);
const images = {
  "owner-tested-v2": {
    sha256: "631c148775cec49ad15d1b5c2ae9d164493c9ff42332eb0aa6210d0e39fd8da5",
    confirmation: "REPLACE STOCK FIRMWARE",
  },
  "tested-v1": {
    sha256: "c4c2c0c185a3ac0ac13c79c9aa6236a05014c9c1cc39d96c55dfe328efebe5b5",
    confirmation: "REPLACE STOCK FIRMWARE",
  },
  "usb-name-candidate": {
    sha256: "89e26537091e8549df46e445f8ea0ab1f01506b89595f0301c633e034fedc8d6",
    confirmation: "TEST USB NAMES",
  },
};
let token = null;
let deviceUid = null;
let backendReady = false;
let busy = false;
let selectedImage = null;
const boardIds = ["board-chip", "board-r12", "board-layout"];

function boardChecks() {
  return boardIds.every((id) => byId(id).checked);
}

function updateButtons() {
  byId("probe").disabled = busy || !token || !backendReady;
  byId("windows-usb").disabled = busy || !token;
  byId("install-tool").disabled = busy || !token;
  byId("flash").disabled = busy || !deviceUid || !backendReady || !boardChecks() ||
    !byId("risk-check").checked ||
    byId("confirmation").value !== selectedImage?.confirmation;
}

function status(message, failed = false) {
  byId("status").textContent = message;
  byId("status").classList.toggle("failed", failed);
}

function appendLog(message) {
  const current = byId("log");
  if (current.textContent === "No device commands have run.") current.textContent = "";
  current.textContent += `${new Date().toLocaleTimeString()}  ${message}\n`;
  current.scrollTop = current.scrollHeight;
}

async function command(path, body = {}) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Installer-Token": token },
    body: JSON.stringify(body),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
  return result;
}

async function probe() {
  busy = true;
  deviceUid = null;
  byId("device").textContent = "Checking…";
  updateButtons();
  status("Reading the USB bootloader. This does not write to it.");
  try {
    const result = await command("/api/probe");
    deviceUid = result.uid;
    byId("device").textContent = "CH552 · bootloader 02.50";
    byId("uid").textContent = `UID ${deviceUid}`;
    appendLog(result.log);
    status("Read-only check passed. Review the warning before flashing.");
  } catch (error) {
    byId("device").textContent = "Not verified";
    byId("uid").textContent = "Check connection and driver";
    appendLog(`Probe failed: ${error.message}`);
    status(error.message, true);
  } finally {
    busy = false;
    updateButtons();
  }
}

async function flash() {
  if (!deviceUid || !boardChecks() || !byId("risk-check").checked ||
      byId("confirmation").value !== selectedImage?.confirmation) return;
  busy = true;
  updateButtons();
  status("Rechecking chip, then erasing, programming and verifying. Do not unplug USB.");
  appendLog("Flash requested. Rechecking exact image and chip identity.");
  try {
    const result = await command("/api/flash", {
      uid: deviceUid,
      confirmation: byId("confirmation").value,
      boardChecks: ["chip", "r12", "layout"],
      stockLossAcknowledged: byId("risk-check").checked,
    });
    appendLog(result.log);
    status("Verify OK. Unplug and reconnect normally, without bridging R12.");
  } catch (error) {
    appendLog(`Flash stopped: ${error.message}`);
    status(`Stopped: ${error.message}`, true);
  } finally {
    deviceUid = null;
    busy = false;
    updateButtons();
  }
}

async function installTool() {
  busy = true;
  updateButtons();
  status("Downloading the tested wchisp archive from GitHub and checking both SHA-256 digests…");
  try {
    const result = await command("/api/install-tool");
    backendReady = true;
    byId("tool-setup").hidden = true;
    appendLog(`Verified wchisp installed locally. SHA-256 ${result.sha256}`);
    status("Verified ISP tool is ready. No keypad commands were sent.");
  } catch (error) {
    appendLog(`Tool setup stopped: ${error.message}`);
    status(`Tool setup stopped: ${error.message}`, true);
  } finally {
    busy = false;
    updateButtons();
  }
}

async function watchUsb() {
  busy = true;
  updateButtons();
  status("Watching Windows for the USB bootloader. Connect using the R12 method now.");
  byId("usb-result").textContent = "Watching for up to 20 seconds…";
  try {
    const result = await command("/api/windows-usb");
    if (!result.devices.length) {
      byId("usb-result").textContent = "Not detected. Re-enter R12 bootloader mode and try again.";
      appendLog("Windows did not report a present 4348:55E0 device.");
      status("No bootloader found. This diagnostic did not change drivers.", true);
    } else {
      const details = result.devices.map((device) => `${device.name}: ${device.status} · ${device.instanceId}`).join("; ");
      byId("usb-result").textContent = details;
      appendLog(`Windows USB device: ${details}`);
      status(result.devices.every((device) => device.status === "OK")
        ? "Windows sees the bootloader. Use Check device for the actual ISP probe."
        : "Windows sees the bootloader but reports a device problem. Check its driver before proceeding.",
      !result.devices.every((device) => device.status === "OK"));
    }
  } catch (error) {
    byId("usb-result").textContent = "Could not read Windows USB status.";
    appendLog(`Windows USB check stopped: ${error.message}`);
    status(error.message, true);
  } finally {
    busy = false;
    updateButtons();
  }
}

for (const id of [...boardIds, "risk-check", "confirmation"]) {
  byId(id).addEventListener(id === "confirmation" ? "input" : "change", updateButtons);
}
byId("probe").addEventListener("click", probe);
byId("flash").addEventListener("click", flash);
byId("install-tool").addEventListener("click", installTool);
byId("windows-usb").addEventListener("click", watchUsb);
byId("copy").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(byId("log").textContent);
    status("Log copied to clipboard.");
  } catch (error) {
    status(`Could not copy log: ${error.message}`, true);
  }
});

try {
  const response = await fetch("/api/status", { cache: "no-store" });
  const result = await response.json();
  selectedImage = images[result.imageKind];
  if (!response.ok || !selectedImage || result.sha256 !== selectedImage.sha256 ||
      result.confirmation !== selectedImage.confirmation || !result.token) {
    throw new Error(result.error || "Image identity mismatch");
  }
  const recovery = result.imageKind === "tested-v1";
  const candidate = result.imageKind === "usb-name-candidate";
  byId("image-name").textContent = candidate ? "KeypadOpen · USB-name test" :
    recovery ? "KeypadOpen v1 · recovery" : "KeypadOpen v2 · owner-tested";
  byId("image-description").textContent = candidate
    ? "Local test image: new USB product and manufacturer names. It has not been flashed or hardware-tested yet."
    : recovery
      ? "This optional recovery mode flashes the earlier v1 image. It does not restore factory firmware."
      : "This package contains the pinned v2 image, tested on one matching keypad. Other board revisions remain unverified.";
  byId("flash-heading").textContent = candidate ? "Test the new USB names" :
    recovery ? "Flash the earlier version" : "Replace the stock program";
  byId("confirmation-text").textContent = selectedImage.confirmation;
  byId("confirmation").placeholder = selectedImage.confirmation;
  token = result.token;
  backendReady = result.backendReady === true;
  byId("windows-usb").hidden = result.platform !== "win32";
  byId("tool-setup").hidden = backendReady || !result.toolSetupAvailable;
  if (result.platform === "darwin") {
    byId("usb-result").textContent = "macOS: enter R12 mode, then use Check device. No driver change is performed.";
  }
  byId("digest").textContent = result.sha256;
  status(backendReady
    ? "Verified image ready. Check your board, then connect it in ISP mode."
    : result.backendError
      ? `${result.backendError}. Use the verified download before probing or flashing.`
      : result.toolSetupAvailable
        ? "Firmware image is verified. Download the tested wchisp tool when you are ready."
        : "Firmware image is verified. Restart this app with --wchisp pointing to a compatible local tool before probing.",
  !backendReady);
  updateButtons();
} catch (error) {
  byId("digest").textContent = "Unavailable";
  status(`Installer unavailable: ${error.message}`, true);
}
