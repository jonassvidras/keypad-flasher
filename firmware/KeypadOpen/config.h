#ifndef KEYPAD_OPEN_CONFIG_H
#define KEYPAD_OPEN_CONFIG_H

#include <stdint.h>

#define CONFIG_SIZE 64
#define CONFIG_ACTION_START 15
#define CONFIG_ACTION_SIZE 3
#define CONFIG_ACTION_COUNT 6

#define ACTION_NONE 0
#define ACTION_KEYBOARD 1
#define ACTION_SCROLL 2
#define ACTION_MOUSE_BUTTON 3
#define ACTION_CONSUMER 4

#define LED_MODE_MAX 11

extern __xdata uint8_t configData[CONFIG_SIZE];
extern __data uint8_t configDirty;

void config_load(void);
void config_process(void);
void raw_hid_receive(void);

#endif
