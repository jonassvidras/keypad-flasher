#include <Arduino.h>
#include "config.h"
#include "src/userQmkCompatibleKeyboard/USBHIDKeyboardMouse.h"

extern __xdata uint8_t Ep2Buffer[];

__xdata uint8_t configData[CONFIG_SIZE];
__xdata uint8_t candidateData[CONFIG_SIZE];
__data uint8_t configDirty = 0;
__data uint8_t activeBank = 0xFF;
volatile __data uint8_t commandPending = 0;

static uint8_t checksum(__xdata uint8_t *data) {
  uint8_t result = 0;
  uint8_t index;
  uint8_t bit;
  for (index = 0; index < CONFIG_SIZE - 1; index++) {
    result ^= data[index];
    for (bit = 0; bit < 8; bit++) {
      result = (result & 0x80) ? (result << 1) ^ 0x07 : result << 1;
    }
  }
  return result;
}

static uint8_t validConfig(__xdata uint8_t *data) {
  uint8_t action;
  if (data[0] != 'K' || data[1] != 'P' || data[2] != 1 ||
      data[4] > LED_MODE_MAX) {
    return 0;
  }
  for (action = 0; action < CONFIG_ACTION_COUNT; action++) {
    uint8_t offset = CONFIG_ACTION_START + action * CONFIG_ACTION_SIZE;
    uint8_t type = data[offset];
    uint8_t code = data[offset + 2];
    if (type > ACTION_CONSUMER) {
      return 0;
    }
    if (type == ACTION_KEYBOARD &&
        code != 0 && (code < 4 || (code >= 0xE0 && code <= 0xE7))) {
      return 0;
    }
    if (type == ACTION_SCROLL && (code == 0 || code == 0x80)) {
      return 0;
    }
    if (type == ACTION_MOUSE_BUTTON &&
        code != 1 && code != 2 && code != 4) {
      return 0;
    }
    if (type == ACTION_CONSUMER &&
        code != 0xCD && code != 0xB6 && code != 0xB5 &&
        code != 0xE2 && code != 0xE9 && code != 0xEA) {
      return 0;
    }
  }
  return 1;
}

static void defaults(void) {
  uint8_t index;
  for (index = 0; index < CONFIG_SIZE; index++) {
    configData[index] = 0;
  }
  configData[0] = 'K';
  configData[1] = 'P';
  configData[2] = 1;
  configData[4] = 1;
  configData[5] = 48;
  configData[6] = 0;
  configData[7] = 120;
  configData[8] = 255;
  configData[9] = 180;
  configData[10] = 0;
  configData[11] = 200;
  configData[12] = 255;
  configData[13] = 70;
  configData[14] = 0;
  for (index = 0; index < 4; index++) {
    configData[CONFIG_ACTION_START + index * CONFIG_ACTION_SIZE] = ACTION_KEYBOARD;
  }
  configData[17] = 0x04;
  configData[20] = 0x05;
  configData[23] = 0x06;
  configData[26] = 0x28;
  configData[27] = ACTION_SCROLL;
  configData[29] = (uint8_t)-1;
  configData[30] = ACTION_SCROLL;
  configData[32] = 1;
  configData[63] = checksum(configData);
}

static uint8_t loadBank(uint8_t bank, __xdata uint8_t *destination) {
  uint8_t index;
  for (index = 0; index < CONFIG_SIZE; index++) {
    destination[index] = eeprom_read_byte(bank * CONFIG_SIZE + index);
  }
  return validConfig(destination) && destination[63] == checksum(destination);
}

void config_load(void) {
  uint8_t firstValid = loadBank(0, configData);
  uint8_t secondValid = loadBank(1, candidateData);
  if (secondValid &&
      (!firstValid || (int8_t)(candidateData[3] - configData[3]) > 0)) {
    uint8_t index;
    for (index = 0; index < CONFIG_SIZE; index++) {
      configData[index] = candidateData[index];
    }
    activeBank = 1;
  } else if (firstValid) {
    activeBank = 0;
  } else {
    defaults();
    activeBank = 0xFF;
  }
  configDirty = 0;
}

static uint8_t saveConfig(void) {
  uint8_t index;
  uint8_t target;
  uint8_t oldGeneration;
  uint8_t oldChecksum;
  if (!validConfig(configData)) {
    return 2;
  }
  if (!configDirty && activeBank != 0xFF) {
    return 0;
  }
  target = activeBank == 0 ? 1 : 0;
  oldGeneration = configData[3];
  oldChecksum = configData[63];
  configData[3]++;
  configData[63] = checksum(configData);
  eeprom_write_byte(target * CONFIG_SIZE, 0);
  for (index = 1; index < CONFIG_SIZE; index++) {
    eeprom_write_byte(target * CONFIG_SIZE + index, configData[index]);
  }
  eeprom_write_byte(target * CONFIG_SIZE, configData[0]);
  if (!loadBank(target, candidateData)) {
    configData[3] = oldGeneration;
    configData[63] = oldChecksum;
    return 3;
  }
  for (index = 0; index < CONFIG_SIZE; index++) {
    if (candidateData[index] != configData[index]) {
      configData[3] = oldGeneration;
      configData[63] = oldChecksum;
      return 3;
    }
  }
  activeBank = target;
  configDirty = 0;
  return 0;
}

void raw_hid_receive(void) {
  commandPending = 1;
}

void config_process(void) {
  uint8_t command;
  uint8_t index;
  uint8_t offset;
  uint8_t count;
  uint8_t generation;
  if (!commandPending) {
    return;
  }
  commandPending = 0;
  command = Ep2Buffer[0];
  for (index = 0; index < 32; index++) {
    Ep2Buffer[64 + index] = 0;
  }
  Ep2Buffer[64] = command;
  switch (command) {
    case 1:
      Ep2Buffer[66] = 'K';
      Ep2Buffer[67] = 'P';
      Ep2Buffer[68] = 2;
      Ep2Buffer[69] = CONFIG_SIZE;
      Ep2Buffer[70] = activeBank;
      Ep2Buffer[71] = configDirty;
      break;
    case 2:
      offset = Ep2Buffer[1];
      count = Ep2Buffer[2];
      if (count > 28 || offset >= CONFIG_SIZE ||
          offset + count > CONFIG_SIZE) {
        Ep2Buffer[65] = 1;
        break;
      }
      Ep2Buffer[66] = offset;
      Ep2Buffer[67] = count;
      for (index = 0; index < count; index++) {
        Ep2Buffer[68 + index] = configData[offset + index];
      }
      break;
    case 3:
      offset = Ep2Buffer[1];
      count = Ep2Buffer[2];
      if (count == 0 || count > 29 || offset < 4 ||
          offset + count > CONFIG_ACTION_START +
                               CONFIG_ACTION_COUNT * CONFIG_ACTION_SIZE) {
        Ep2Buffer[65] = 1;
        break;
      }
      for (index = 0; index < CONFIG_SIZE; index++) {
        candidateData[index] = configData[index];
      }
      for (index = 0; index < count; index++) {
        candidateData[offset + index] = Ep2Buffer[3 + index];
      }
      if (!validConfig(candidateData)) {
        Ep2Buffer[65] = 2;
        break;
      }
      for (index = 4; index < CONFIG_ACTION_START +
                                 CONFIG_ACTION_COUNT * CONFIG_ACTION_SIZE;
           index++) {
        if (candidateData[index] != configData[index]) {
          configDirty = 1;
          break;
        }
      }
      candidateData[63] = checksum(candidateData);
      for (index = 0; index < CONFIG_SIZE; index++) {
        configData[index] = candidateData[index];
      }
      break;
    case 4:
      Ep2Buffer[65] = saveConfig();
      break;
    case 5:
      generation = configData[3];
      defaults();
      configData[3] = generation;
      configData[63] = checksum(configData);
      configDirty = 1;
      break;
    default:
      Ep2Buffer[65] = 0xFF;
      break;
  }
  USB_EP2_send();
}
