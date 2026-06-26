#include <Arduino.h>
#include <TM1637Display.h>

/** Display driver module for 8-Bit computer project. Converts a binary value on 8-data lines (read via pins)
    to a decimal number displayed on a TM1637 seven segment display

    D. Q McDonald
    June 2026

    */



#define CLK 2
#define DIO 3


TM1637Display display(CLK, DIO);

int pins[8] = { 0,1, 4, 5, 6, 7, 8, 9};  // Data values are read from these pins. LSB to MSB order.

const int NUM_PINS = sizeof(pins) / sizeof(pins[0]);

void setup() {
  
  display.setBrightness(0x04);

  for (int i = 0; i < NUM_PINS; i++) {
    pinMode(pins[i], INPUT);
  }


}

void loop() {
  

  int sum = 0;
  for (int i = 0; i < NUM_PINS; i++) {
    sum |= (digitalRead(pins[i]) << i);
  }
  display.showNumberDec(sum, true);
    delay(500);
}
