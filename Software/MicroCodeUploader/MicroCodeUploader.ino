/* Microcode Uploader for 8-Bit Computer
   Uses 3x 74HC595 Shift Registers to program a AT28C256 EEPROM. 
     The address and data are shifted onto the registers using pins 11, 12 and 8

     Pin 4 is pulsed HIGH for 1us to complete the write of the EEProm - there is a 10ms delay for this as well.

  Quentin McDonald
  January 2025
   */


#define DATA_PIN 11                 // Data pin for shift registers
#define CLOCK_PIN 12                // Clock pin for shift registers
#define LATCH_PIN 8                 // Latch pin for shift registers
#define EEPROM_WRITE_PIN 4          // Pulse HIGH 1us for Write
#define EEPROM_OUTPUT_ENABLE_PIN 3  // Turn high during this process

void write_data(byte address1, byte address2, byte data) {
  // write to the EEPROM "data" at address made from address1 and address2

  digitalWrite(LATCH_PIN, LOW);
  shiftOut(DATA_PIN, CLOCK_PIN, MSBFIRST, address1);
  shiftOut(DATA_PIN, CLOCK_PIN, MSBFIRST, address2);
  shiftOut(DATA_PIN, CLOCK_PIN, MSBFIRST, data);
  digitalWrite(LATCH_PIN, HIGH);

  // Pulse Write enable to do write
  digitalWrite(EEPROM_WRITE_PIN, LOW);
  delayMicroseconds(1);
  digitalWrite(EEPROM_WRITE_PIN, HIGH);
  delayMicroseconds(20);
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

  for (int i = 0; i < 255; i++) {
    byte a = byte(i);
    byte d = byte(i);
    write_data(a, a, d);
  }

  delay(500);

}

void loop() {

  if (Serial.available() > 1) {

    byte add1 = Serial.read();
    byte add2 = Serial.read();
    byte data = Serial.read();

    write_data(add1, add2, data);

    Serial.write(0x55);
    delay(20);
  }
}
