/* Microcode Uploader for 8-Bit Computer
   Uses 2x 74HC595 Shift Registers to program a AT28C256 EEPROM.
     The address is shifted onto the registers using pins 11, 12 and 8
     (address1 = low byte A0-A7, address2 = high byte A8-A14).

    The data byte is driven directly from Arduino pins connected to the
    EEPROM IO lines as follows:
    IO0 -> A0
    IO1 -> A1
    IO2 -> A2
    IO3 -> A3
    IO4 -> A4
    IO5 -> A5
    IO6 -> D9
    IO7 -> D6

     Pin 4 (WE) is pulsed LOW for 1us to trigger the write. The AT28C256 byte
     write cycle (tWC) is up to 10ms. Rather than blindly waiting that long, we
     use IO7 data polling: during the internal write the EEPROM returns the
     complement of the last-written bit 7, then the true value once it is done.
     We poll IO7 until it matches, which usually finishes in 1-3ms.

     Because the data lines are now bidirectional we can also read the EEPROM
     back to verify a write. To read, the data pins are switched to inputs,
     output enable (pin 3) is driven LOW, and the IO lines are sampled.

     Serial protocol (binary, 115200 baud):
       'W' <addr_lo> <addr_hi> <data>  -> writes a byte, replies 0x55 (ACK)
       'R' <addr_lo> <addr_hi>         -> replies with the single data byte

  Quentin McDonald
  January 2025
   */


#define DATA_PIN 11                 // Data pin for shift registers
#define CLOCK_PIN 12                // Clock pin for shift registers
#define LATCH_PIN 8                 // Latch pin for shift registers
#define EEPROM_WRITE_PIN 4          // Pulse LOW 1us to trigger Write
#define EEPROM_OUTPUT_ENABLE_PIN 3  // LOW to read, HIGH otherwise

// EEPROM IO0..IO7 wired directly to these Arduino pins (LSB first).
const uint8_t DATA_PINS[8] = { A0, A1, A2, A3, A4, A5, 9, 6 };

void set_data_pins_mode(uint8_t mode) {
  for (uint8_t i = 0; i < 8; i++) {
    pinMode(DATA_PINS[i], mode);
  }
}

void set_data_bus(byte data) {
  // Drive the data bus with "data" (pins must already be OUTPUT).
  for (uint8_t i = 0; i < 8; i++) {
    digitalWrite(DATA_PINS[i], (data >> i) & 0x01);
  }
}

byte read_data_bus() {
  // Sample the data bus (pins must already be INPUT).
  byte value = 0;
  for (uint8_t i = 0; i < 8; i++) {
    if (digitalRead(DATA_PINS[i])) {
      value |= (1 << i);
    }
  }
  return value;
}

void set_address(byte address1, byte address2) {
  // Shift the 15-bit address onto the two daisy-chained 595s.
  digitalWrite(LATCH_PIN, LOW);
  shiftOut(DATA_PIN, CLOCK_PIN, MSBFIRST, address1);
  shiftOut(DATA_PIN, CLOCK_PIN, MSBFIRST, address2);
  digitalWrite(LATCH_PIN, HIGH);
}

void write_data(byte address1, byte address2, byte data) {
  // Write "data" to the EEPROM at the address made from address1/address2.

  set_address(address1, address2);

  // Keep the EEPROM outputs disabled and drive the bus ourselves.
  digitalWrite(EEPROM_OUTPUT_ENABLE_PIN, HIGH);
  set_data_pins_mode(OUTPUT);
  set_data_bus(data);

  // Pulse Write enable LOW to trigger the write (write occurs on rising edge)
  digitalWrite(EEPROM_WRITE_PIN, LOW);
  delayMicroseconds(1);
  digitalWrite(EEPROM_WRITE_PIN, HIGH);

  // Data polling: during the internal write cycle the EEPROM drives the
  // complement of the just-written bit 7 onto IO7, then the true value once
  // the cycle completes. Release the bus, enable the outputs, and poll IO7
  // until it matches. A safety timeout guards against a stuck/absent device
  // (tWC max is 10ms, so 20ms is comfortably beyond a healthy cycle).
  byte expected_bit7 = (data >> 7) & 0x01;
  set_data_pins_mode(INPUT);
  digitalWrite(EEPROM_OUTPUT_ENABLE_PIN, LOW);

  unsigned long start = millis();
  while (digitalRead(DATA_PINS[7]) != expected_bit7) {
    if (millis() - start > 20) {
      break;
    }
  }

  digitalWrite(EEPROM_OUTPUT_ENABLE_PIN, HIGH);  // disable EEPROM output
}

byte read_data(byte address1, byte address2) {
  // Read and return the byte stored at the given address.

  // Release the bus so the EEPROM can drive it, then enable its output.
  set_data_pins_mode(INPUT);
  digitalWrite(EEPROM_WRITE_PIN, HIGH);  // make sure we're not writing
  set_address(address1, address2);

  digitalWrite(EEPROM_OUTPUT_ENABLE_PIN, LOW);  // enable EEPROM output
  delayMicroseconds(1);                         // let the IO lines settle
  byte value = read_data_bus();
  digitalWrite(EEPROM_OUTPUT_ENABLE_PIN, HIGH);  // disable EEPROM output

  return value;
}

byte read_byte_blocking() {
  // Block until a byte is available on the serial port and return it.
  while (Serial.available() < 1) {
    // wait
  }
  return Serial.read();
}

void setup() {

  Serial.begin(115200);

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

  if (Serial.available() < 1) {
    return;
  }

  byte cmd = Serial.read();

  if (cmd == 'W') {
    byte add1 = read_byte_blocking();
    byte add2 = read_byte_blocking();
    byte data = read_byte_blocking();
    write_data(add1, add2, data);
    Serial.write(0x55);
  } else if (cmd == 'R') {
    byte add1 = read_byte_blocking();
    byte add2 = read_byte_blocking();
    Serial.write(read_data(add1, add2));
  }
}
