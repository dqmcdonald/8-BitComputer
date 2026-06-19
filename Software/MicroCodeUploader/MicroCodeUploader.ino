/* Microcode Uploader for 8-Bit Computer
   Uses 3x 74HC595 Shift Registers to program a AT28C256 EEPROM.
     The address and data are shifted onto the registers using pins 11, 12 and 8
     (address1 = low byte A0-A7, address2 = high byte A8-A14, then the data byte).

     Pin 4 (WE) is pulsed LOW for 1us to trigger the write. The AT28C256 byte
     write cycle (tWC) is up to 10ms, so we wait 10ms after each write before
     starting the next one.

  Quentin McDonald
  January 2025
   */


#define DATA_PIN 11                 // Data pin for shift registers
#define CLOCK_PIN 12                // Clock pin for shift registers
#define LATCH_PIN 8                 // Latch pin for shift registers
#define EEPROM_WRITE_PIN 4          // Pulse LOW 1us to trigger Write
#define EEPROM_OUTPUT_ENABLE_PIN 3  // Turn high during this process

void write_data(byte address1, byte address2, byte data) {
  // write to the EEPROM "data" at address made from address1 and address2

  digitalWrite(LATCH_PIN, LOW);
  shiftOut(DATA_PIN, CLOCK_PIN, MSBFIRST, address1);
  shiftOut(DATA_PIN, CLOCK_PIN, MSBFIRST, address2);
  shiftOut(DATA_PIN, CLOCK_PIN, MSBFIRST, data);
  digitalWrite(LATCH_PIN, HIGH);

  // Pulse Write enable LOW to trigger the write (write occurs on rising edge)
  digitalWrite(EEPROM_WRITE_PIN, LOW);
  delayMicroseconds(1);
  digitalWrite(EEPROM_WRITE_PIN, HIGH);

  // Wait for the byte-write cycle to complete (AT28C256 tWC is up to 10ms).
  // The data lines aren't read back, so we can't use data polling here.
  delay(10);
}

void setup() {

  Serial.begin(9600);

  pinMode(DATA_PIN, OUTPUT);
  pinMode(CLOCK_PIN, OUTPUT);
  pinMode(LATCH_PIN, OUTPUT);
  pinMode(EEPROM_WRITE_PIN, OUTPUT);
  pinMode(EEPROM_OUTPUT_ENABLE_PIN, OUTPUT);

  digitalWrite(EEPROM_WRITE_PIN, HIGH);
  digitalWrite(EEPROM_OUTPUT_ENABLE_PIN, HIGH);  // Turn off output enable

  delay(500);
}

void loop() {

  if (Serial.available() >= 3) {

    byte add1 = Serial.read();
    byte add2 = Serial.read();
    byte data = Serial.read();

    write_data(add1, add2, data);

    Serial.write(0x55);
  }
}
