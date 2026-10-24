#ifndef USER_USB_RAM
#error Select the CH552 user266 USB memory option.
#endif

#include <WS2812.h>
#include "config.h"
#include "src/userQmkCompatibleKeyboard/USBHIDKeyboardMouse.h"

void Consumer_pulse(uint8_t usage);

#define KEY_1_PIN 11
#define KEY_2_PIN 17
#define KEY_3_PIN 16
#define ENCODER_PUSH_PIN 33
#define ENCODER_A_PIN 30
#define ENCODER_B_PIN 31
#define LED_PIN 34

#define LED_COUNT 3
#define LED_BYTES (LED_COUNT * 3)
#define DEBOUNCE_MS 12
#define ENCODER_STEPS_PER_DETENT 4
#define LED_REFRESH_MS 35

__xdata uint8_t ledData[LED_BYTES];
__xdata uint8_t activeActions[4][CONFIG_ACTION_SIZE];

const uint8_t keyPins[4] = {
    KEY_1_PIN, KEY_2_PIN, KEY_3_PIN, ENCODER_PUSH_PIN};

uint8_t stableKeys = 0;
uint8_t sampledKeys = 0;
uint8_t appliedModifiers = 0;
uint8_t appliedMouseButtons = 0;
unsigned long keyChangedAt[4] = {0, 0, 0, 0};
uint8_t encoderPrevious = 0;
int8_t encoderSteps = 0;
uint8_t lightingPhase = 0;
uint8_t effectKey = 0;
uint8_t effectSeed = 47;
uint8_t effectSeen = 0;
unsigned long effectStartedAt = 0;
unsigned long lastLedRefresh = 0;

void syncModifiers() {
  uint8_t requested = 0;
  uint8_t index;
  uint8_t mask;
  for (index = 0; index < 4; index++) {
    if ((stableKeys & (1 << index)) &&
        activeActions[index][0] == ACTION_KEYBOARD) {
      requested |= activeActions[index][1];
    }
  }
  for (index = 0; index < 8; index++) {
    mask = 1 << index;
    if ((requested & mask) && !(appliedModifiers & mask)) {
      Keyboard_quantum_modifier_press(mask);
    } else if (!(requested & mask) && (appliedModifiers & mask)) {
      Keyboard_quantum_modifier_release(mask);
    }
  }
  appliedModifiers = requested;
}

void syncMouseButtons() {
  uint8_t requested = 0;
  uint8_t index;
  uint8_t mask;
  for (index = 0; index < 4; index++) {
    if ((stableKeys & (1 << index)) &&
        activeActions[index][0] == ACTION_MOUSE_BUTTON) {
      requested |= activeActions[index][2];
    }
  }
  for (index = 0; index < 3; index++) {
    mask = 1 << index;
    if ((requested & mask) && !(appliedMouseButtons & mask)) {
      Mouse_press(mask);
    } else if (!(requested & mask) && (appliedMouseButtons & mask)) {
      Mouse_release(mask);
    }
  }
  appliedMouseButtons = requested;
}

uint8_t keyHeldElsewhere(uint8_t source, uint8_t code) {
  uint8_t index;
  for (index = 0; index < 4; index++) {
    if (index != source && (stableKeys & (1 << index)) &&
        activeActions[index][0] == ACTION_KEYBOARD &&
        activeActions[index][2] == code) {
      return 1;
    }
  }
  return 0;
}

void keyChanged(uint8_t index, uint8_t pressed) {
  uint8_t offset = CONFIG_ACTION_START + index * CONFIG_ACTION_SIZE;
  uint8_t type;
  uint8_t code;
  if (pressed) {
    if (index < LED_COUNT) {
      effectKey = index;
      effectStartedAt = millis();
      effectSeen = 1;
    }
    activeActions[index][0] = configData[offset];
    activeActions[index][1] = configData[offset + 1];
    activeActions[index][2] = configData[offset + 2];
  }
  type = activeActions[index][0];
  code = activeActions[index][2];
  if (type == ACTION_KEYBOARD) {
    if (pressed) {
      syncModifiers();
      if (code && !keyHeldElsewhere(index, code)) {
        Keyboard_quantum_regular_press(code);
      }
    } else {
      if (code && !keyHeldElsewhere(index, code)) {
        Keyboard_quantum_regular_release(code);
      }
      syncModifiers();
    }
  } else if (type == ACTION_MOUSE_BUTTON) {
    syncMouseButtons();
  } else if (type == ACTION_SCROLL && pressed) {
    Mouse_scroll((int8_t)code);
    Mouse_scroll(0);
  } else if (type == ACTION_CONSUMER && pressed) {
    Consumer_pulse(code);
  }
}

void pulseAction(uint8_t index) {
  uint8_t offset = CONFIG_ACTION_START + index * CONFIG_ACTION_SIZE;
  uint8_t type = configData[offset];
  uint8_t modifiers = configData[offset + 1];
  uint8_t code = configData[offset + 2];
  uint8_t extra = modifiers & ~appliedModifiers;
  uint8_t bit;
  if (type == ACTION_KEYBOARD) {
    for (bit = 0; bit < 8; bit++) {
      if (extra & (1 << bit)) {
        Keyboard_quantum_modifier_press(1 << bit);
      }
    }
    if (code && !keyHeldElsewhere(0xFF, code)) {
      Keyboard_quantum_regular_press(code);
      Keyboard_quantum_regular_release(code);
    }
    for (bit = 0; bit < 8; bit++) {
      if (extra & (1 << bit)) {
        Keyboard_quantum_modifier_release(1 << bit);
      }
    }
  } else if (type == ACTION_SCROLL) {
    Mouse_scroll((int8_t)code);
    Mouse_scroll(0);
  } else if (type == ACTION_MOUSE_BUTTON &&
             !(appliedMouseButtons & code)) {
    Mouse_click(code);
  } else if (type == ACTION_CONSUMER) {
    Consumer_pulse(code);
  }
}

uint8_t scaled(uint8_t channel) {
  return ((uint16_t)channel * configData[5]) / 255;
}

void setLed(uint8_t index, uint8_t red, uint8_t green, uint8_t blue) {
  set_pixel_for_GRB_LED(ledData, index, scaled(red), scaled(green),
                        scaled(blue));
}

uint8_t triangle(uint8_t phase) {
  return phase < 128 ? phase * 2 : (255 - phase) * 2;
}

void wheel(uint8_t index, uint8_t hue, uint8_t intensity) {
  uint8_t red = 0;
  uint8_t green = 0;
  uint8_t blue = 0;
  if (hue < 85) {
    red = 255 - hue * 3;
    green = hue * 3;
  } else if (hue < 170) {
    hue -= 85;
    green = 255 - hue * 3;
    blue = hue * 3;
  } else {
    hue -= 170;
    blue = 255 - hue * 3;
    red = hue * 3;
  }
  setLed(index, ((uint16_t)red * intensity) / 255,
         ((uint16_t)green * intensity) / 255,
         ((uint16_t)blue * intensity) / 255);
}

void palette(uint8_t index, uint8_t intensity) {
  uint8_t offset = 6 + index * 3;
  setLed(index, ((uint16_t)configData[offset] * intensity) / 255,
         ((uint16_t)configData[offset + 1] * intensity) / 255,
         ((uint16_t)configData[offset + 2] * intensity) / 255);
}

void renderLeds() {
  uint8_t index;
  uint8_t mode = configData[4];
  uint8_t position = lightingPhase / 28;
  unsigned long elapsed = millis() - effectStartedAt;
  if (mode == 0) {
    for (index = 0; index < LED_COUNT; index++) {
      setLed(index, 0, 0, 0);
    }
  } else if (mode == 1) {
    for (index = 0; index < LED_COUNT; index++) {
      palette(index, 255);
    }
  } else {
    for (index = 0; index < LED_COUNT; index++) {
      uint8_t distance = index > effectKey ? index - effectKey : effectKey - index;
      if (mode == 2) {
        wheel(index, lightingPhase + index * 85, 255);
      } else if (mode == 3) {
        palette(index, triangle(lightingPhase));
      } else if (mode == 4) {
        palette(index, triangle(lightingPhase + index * 85));
      } else if (mode == 5) {
        palette(index, index == position % LED_COUNT ? 255 : 18);
      } else if (mode == 6) {
        palette(index, effectSeen && index == effectKey && elapsed < 1200
                           ? (uint8_t)(255 - elapsed / 5) : 0);
      } else if (mode == 7) {
        unsigned long start = (unsigned long)distance * 160;
        palette(index, effectSeen && elapsed >= start && elapsed < start + 800
                           ? (uint8_t)(255 - (elapsed - start) / 4) : 0);
      } else if (mode == 8) {
        palette(index, index == effectSeed % LED_COUNT
                           ? triangle(lightingPhase * 2) : 8);
      } else if (mode == 9) {
        wheel(index, lightingPhase, 255);
      } else if (mode == 10) {
        palette(index, ((lightingPhase / 32 + index) & 1) ? 255 : 8);
      } else {
        wheel(index, index * 85, 255);
      }
    }
  }
  lightingPhase += 2;
  if (mode == 8 && lightingPhase % 64 == 0) {
    effectSeed = effectSeed * 33 + 17;
  }
  neopixel_show_P3_4(ledData, LED_BYTES);
}

void scanKeys(unsigned long now) {
  uint8_t index;
  for (index = 0; index < 4; index++) {
    uint8_t mask = 1 << index;
    uint8_t pressed = digitalRead(keyPins[index]) == LOW;
    if (pressed != ((sampledKeys & mask) != 0)) {
      sampledKeys ^= mask;
      keyChangedAt[index] = now;
    }
    if (pressed != ((stableKeys & mask) != 0) &&
        now - keyChangedAt[index] >= DEBOUNCE_MS) {
      stableKeys ^= mask;
      keyChanged(index, pressed);
    }
  }
}

void scanEncoder() {
  uint8_t current = (digitalRead(ENCODER_A_PIN) << 1) |
                    digitalRead(ENCODER_B_PIN);
  uint8_t transition = (encoderPrevious << 2) | current;
  encoderPrevious = current;

  switch (transition) {
    case 0x1:
    case 0x7:
    case 0xE:
    case 0x8:
      encoderSteps++;
      break;
    case 0x2:
    case 0xB:
    case 0xD:
    case 0x4:
      encoderSteps--;
      break;
    default:
      break;
  }

  if (encoderSteps >= ENCODER_STEPS_PER_DETENT) {
    pulseAction(5);
    encoderSteps = 0;
  } else if (encoderSteps <= -ENCODER_STEPS_PER_DETENT) {
    pulseAction(4);
    encoderSteps = 0;
  }
}

void setup() {
  uint8_t index;
  config_load();
  for (index = 0; index < 4; index++) {
    pinMode(keyPins[index], INPUT_PULLUP);
  }
  pinMode(ENCODER_A_PIN, INPUT_PULLUP);
  pinMode(ENCODER_B_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  encoderPrevious = (digitalRead(ENCODER_A_PIN) << 1) |
                    digitalRead(ENCODER_B_PIN);
  renderLeds();
  USBInit();
}

void loop() {
  unsigned long now = millis();
  config_process();
  scanKeys(now);
  scanEncoder();
  if (now - lastLedRefresh >= LED_REFRESH_MS) {
    lastLedRefresh = now;
    renderLeds();
  }
}
