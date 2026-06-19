#include <Arduino.h>
#include <TM1637Display.h>

/** Display driver module for 8-Bit computer project. Converts a binary value on 8-data lines (read via pins)
    to a decimal number displayed on a TM16730 seven segment display

    D. Q McDonald
    January 2024

    */



#define CLK 2
#define DIO 3


TM1637Display display(CLK, DIO);

int pins[8] = { 0,1, 4, 5, 6, 7, 8, 9};  // Data values are read from these pins. LSB to MSB order. 
int place_digits[8] = { 1, 2, 4, 8, 16, 32, 64, 128 }; // Values used to convert binary to decimal

const int NUM_PINS = 8;

int sum = 0;

void setup() {
  
  display.setBrightness(0x04);

  for (int i = 0; i < NUM_PINS; i++) {
    pinMode(pins[i], INPUT);
  }


}

void loop() {
  

  sum = 0;
  for (int i = 0; i < NUM_PINS; i++) {
    if( digitalRead(pins[i]) == 1) {
      sum = sum + place_digits[i];
    }
  }
  display.showNumberDec(sum, true); 
    delay(500);
}
