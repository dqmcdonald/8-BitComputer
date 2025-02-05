/* Program Uploader for 8-Bit Computer
   Uses 2x 74HC595 Shift Registers to program a AT28C16 EEPROM. There are switches on the PCB to control one of 16 banks
   to store programs. Data from the program is received via a Serial connection from a Python script running on the
   host computer. Bytes are sent in pairs - first the address then the data. There will always be 255 bytes of data sent - anythig
   that is not program code will simply be zeros.

   The process for each pairs of bytes is:
     Pin 7 is set HIGH to enable the shift register
     Pin 6 is set HIGH to disable the address resgister
     Pin 5 is set HIGH to disable the EEPROM output
     
     The address and data are shifted onto the registers using pins 11, 12 and 8

     Pin 4 is pulsed HIGH for 1us to complete the write of the EEProm - there is a 10ms delay for this as well.

  Quentin McDonald
  January 2025
   */


#define DATA_PIN 11                    // Data pin for shift registers
#define CLOCK_PIN 12                   // Clock pin for shift registers
#define LATCH_PIN 8                    // Latch pin for shift registers
#define SHIFT_REGISTER_ENABLE_PIN 7    // Set LOW to disable shift registers, connected via NPN tranistor
#define ADDRESS_REGISTER_ENABLE_PIN 6  // Set HIGH to disable address register
#define EEPROM_OUTPUT_ENABLE_PIN 5     // Set HIGH to disable EEPROM Output
#define EEPROM_WRITE_PIN 4             // Pulse HIGH 1us for Write (connected via NPN transistor)


bool got_first_byte = false;

void setup() {

  Serial.begin(9600);
  pinMode(DATA_PIN, OUTPUT);
  pinMode(CLOCK_PIN, OUTPUT);
  pinMode(LATCH_PIN, OUTPUT);
  pinMode(SHIFT_REGISTER_ENABLE_PIN, OUTPUT);
  pinMode(ADDRESS_REGISTER_ENABLE_PIN, OUTPUT);
  pinMode(EEPROM_OUTPUT_ENABLE_PIN, OUTPUT);
  pinMode(EEPROM_WRITE_PIN, OUTPUT);

  digitalWrite(ADDRESS_REGISTER_ENABLE_PIN, LOW);
  digitalWrite(SHIFT_REGISTER_ENABLE_PIN, LOW);
  digitalWrite(EEPROM_WRITE_PIN, LOW);
  digitalWrite(EEPROM_OUTPUT_ENABLE_PIN, LOW);
  delay(500);
 
  
}

void loop() {


  if (Serial.available() > 1) {

    byte address = Serial.read();
    byte data = Serial.read();

    digitalWrite(ADDRESS_REGISTER_ENABLE_PIN, HIGH);
    digitalWrite(SHIFT_REGISTER_ENABLE_PIN, HIGH);
    digitalWrite(EEPROM_OUTPUT_ENABLE_PIN, HIGH);

    // Shift data to registers:
    digitalWrite(LATCH_PIN, LOW);
    shiftOut(DATA_PIN, CLOCK_PIN, MSBFIRST, address);
    shiftOut(DATA_PIN, CLOCK_PIN, MSBFIRST, data);
    digitalWrite(LATCH_PIN, HIGH);

    // Pulse write pin
    digitalWrite(EEPROM_WRITE_PIN, HIGH);
    delayMicroseconds(1);
    digitalWrite(EEPROM_WRITE_PIN, LOW);
    delay(10);

    digitalWrite(EEPROM_OUTPUT_ENABLE_PIN, LOW);
    digitalWrite(ADDRESS_REGISTER_ENABLE_PIN, LOW);
    digitalWrite(SHIFT_REGISTER_ENABLE_PIN, LOW);

    Serial.write(0x55);
    delay(20);
  }
}
