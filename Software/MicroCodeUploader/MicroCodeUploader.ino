/* Microcode Uploader for 8-Bit Computer
   Uses 3x 74HC595 Shift Registers to program a AT28C256 EEPROM. 
     The address and data are shifted onto the registers using pins 11, 12 and 8

     Pin 4 is pulsed HIGH for 1us to complete the write of the EEProm - there is a 10ms delay for this as well.

  Quentin McDonald
  January 2025
   */


#define DATA_PIN 11         // Data pin for shift registers
#define CLOCK_PIN 12        // Clock pin for shift registers
#define LATCH_PIN 8         // Latch pin for shift registers
#define EEPROM_WRITE_PIN 4  // Pulse HIGH 1us for Write (connected via NPN transistor)



void setup() {

  Serial.begin(9600);
  pinMode(DATA_PIN, OUTPUT);
  pinMode(CLOCK_PIN, OUTPUT);
  pinMode(LATCH_PIN, OUTPUT);
  pinMode(EEPROM_WRITE_PIN, OUTPUT);

  digitalWrite(EEPROM_WRITE_PIN, HIGH);
  delay(500);
}

void loop() {

  byte data1 = 0xff;
  byte data2 = 0x00;
  byte data3 = 0x55;


  // Shift data to registers:
  digitalWrite(LATCH_PIN, LOW);
  shiftOut(DATA_PIN, CLOCK_PIN, MSBFIRST, data1);
  shiftOut(DATA_PIN, CLOCK_PIN, MSBFIRST, data2);
  shiftOut(DATA_PIN, CLOCK_PIN, MSBFIRST, data3);
  digitalWrite(LATCH_PIN, HIGH);

  // // Pulse write pin
  // digitalWrite(EEPROM_WRITE_PIN, HIGH);
  // delayMicroseconds(1);
  // digitalWrite(EEPROM_WRITE_PIN, LOW);
  // delay(10);

  while (true) { delay(1000); }
}
