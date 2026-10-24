export const BOOTLOADER_VENDOR_ID = 0x4348;
export const BOOTLOADER_PRODUCT_ID = 0x55e0;

export const identifyRequest = Uint8Array.from([
  0xa1, 0x12, 0x00, 0x00, 0x00,
  ...new TextEncoder().encode("MCU ISP & WCH.CN"),
]);
export const configReadRequest = Uint8Array.from([0xa7, 0x02, 0x00, 0x1f, 0x00]);

export function readResponse(data, command, minimumPayload) {
  if (!data) throw new Error("The bootloader returned no data.");
  const bytes = new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
  if (bytes.length < 4 || bytes[0] !== command) {
    throw new Error("Unexpected USB ISP response.");
  }
  const length = bytes[2] | (bytes[3] << 8);
  if (length < minimumPayload || bytes.length < length + 4) {
    throw new Error("Incomplete USB ISP response.");
  }
  return bytes.slice(4, length + 4);
}

export function readIdentity(data) {
  const payload = readResponse(data, 0xa1, 2);
  if (payload[0] !== 0x52 || payload[1] !== 0x11) {
    throw new Error("This is not the expected CH552 (0x5211). Do not flash it.");
  }
  return "CH552 (0x5211)";
}

export function readConfiguration(data) {
  const payload = readResponse(data, 0xa7, 26);
  if (payload[0] !== 0x1f || payload[1] !== 0x00) {
    throw new Error("Unexpected configuration response.");
  }
  const version = payload.slice(14, 18);
  if (version[0] !== 0 || version[1] !== 2 || version[2] !== 5 || version[3] !== 0) {
    throw new Error("Bootloader version is not the tested 02.50.");
  }
  const uid = Array.from(payload.slice(18, 26), (value) => value.toString(16).padStart(2, "0").toUpperCase()).join("-");
  return { version: "02.50", uid };
}
