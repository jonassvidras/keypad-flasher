import {
  BOOTLOADER_VENDOR_ID, BOOTLOADER_PRODUCT_ID, identifyRequest,
  configReadRequest, readIdentity, readConfiguration,
} from "./webusb-probe.mjs";

const button = document.getElementById("probe");
const status = document.getElementById("status");
const log = document.getElementById("log");
const copy = document.getElementById("copy");

function show(message, failed = false) {
  status.textContent = message;
  status.classList.toggle("failed", failed);
  log.textContent += `${new Date().toLocaleTimeString()}  ${message}\n`;
}

async function exchange(device, outgoing, command) {
  const sent = await device.transferOut(2, outgoing);
  if (sent.status !== "ok" || sent.bytesWritten !== outgoing.byteLength) {
    throw new Error("USB ISP request was not sent completely.");
  }
  const received = await device.transferIn(2, 64);
  if (received.status !== "ok") throw new Error("USB ISP response failed.");
  return command === 0xa1
    ? readIdentity(received.data)
    : readConfiguration(received.data);
}

button.addEventListener("click", async () => {
  button.disabled = true;
  let device;
  let claimedInterface;
  try {
    if (!navigator.usb) throw new Error("WebUSB is unavailable. Use desktop Chrome or Edge on macOS.");
    device = await navigator.usb.requestDevice({
      filters: [{ vendorId: BOOTLOADER_VENDOR_ID, productId: BOOTLOADER_PRODUCT_ID }],
    });
    show("Browser permission granted. Opening the USB ISP interface…");
    await device.open();
    if (!device.configuration) await device.selectConfiguration(1);
    const match = device.configuration.interfaces.find((usbInterface) =>
      usbInterface.alternates.some((alternate) =>
        alternate.interfaceClass === 0xff &&
        alternate.endpoints.some((endpoint) => endpoint.direction === "out" && endpoint.endpointNumber === 2) &&
        alternate.endpoints.some((endpoint) => endpoint.direction === "in" && endpoint.endpointNumber === 2)));
    if (!match) throw new Error("Expected vendor USB interface with endpoint 2 was not found.");
    claimedInterface = match.interfaceNumber;
    await device.claimInterface(claimedInterface);
    const identity = await exchange(device, identifyRequest, 0xa1);
    const configuration = await exchange(device, configReadRequest, 0xa7);
    show(`${identity}; bootloader ${configuration.version}; UID ${configuration.uid}. Read-only probe passed.`);
  } catch (error) {
    show(`Probe stopped: ${error.message}`, true);
  } finally {
    if (device?.opened) {
      if (claimedInterface !== undefined) {
        try { await device.releaseInterface(claimedInterface); } catch {}
      }
      try { await device.close(); } catch {}
    }
    button.disabled = false;
  }
});

copy.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(log.textContent);
    status.textContent = "Log copied to clipboard.";
  } catch (error) {
    show(`Could not copy log: ${error.message}`, true);
  }
});
