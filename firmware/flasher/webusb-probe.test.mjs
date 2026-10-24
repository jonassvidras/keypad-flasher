import assert from "node:assert/strict";
import test from "node:test";
import {
  identifyRequest, configReadRequest, readIdentity, readConfiguration,
} from "./webusb-probe.mjs";

function view(hex) {
  const bytes = Uint8Array.from(hex.match(/../g), (pair) => Number.parseInt(pair, 16));
  return new DataView(bytes.buffer);
}

test("only read-only USB ISP requests are exposed", () => {
  assert.equal(identifyRequest[0], 0xa1);
  assert.equal(configReadRequest[0], 0xa7);
  assert.equal(identifyRequest.length, 21);
});

test("recognizes a synthetic CH552 response", () => {
  assert.equal(readIdentity(view("a1bb02005211")), "CH552 (0x5211)");
  assert.deepEqual(readConfiguration(view(
    "a7bb1a001f00ffffffff23000000ff52f7ed000205001122334400000000"
  )), { version: "02.50", uid: "11-22-33-44-00-00-00-00" });
});

test("rejects a different chip or incomplete configuration", () => {
  assert.throws(() => readIdentity(view("a1bb02005111")), /not the expected CH552/);
  assert.throws(() => readConfiguration(view("a7bb1a001f00")), /Incomplete/);
});
