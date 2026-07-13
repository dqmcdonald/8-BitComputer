/* Program Uploader for 8-Bit Computer
   ===================================

   Flashes a user program into the AT28C64 EEPROM (U1) on the ProgramROM board,
   in place, without pulling the chip. The host sends the program over USB
   serial; this sketch drives the board's programming header (J2).

   Hardware reference: ProgramROM/ProgramROM.kicad_sch and ProgramROM/NetPlan.txt.
   Host script:        Software/UploaderPython/program_upload.py

   ---------------------------------------------------------------------------
   BOARD OVERVIEW
   ---------------------------------------------------------------------------
   The EEPROM is an AT28C64 (8K x 8, A0-A12) -- NOT the AT28C16 an earlier
   version of this sketch assumed. Its 13 address lines are split in two:

     A0-A7   The 256-byte program itself. Muxed between two owners:
               RUN     - the computer, via the 74HC541 buffer (U2) from LBA0-7
               PROGRAM - this Arduino, via the 74HC595 shift register (U3)
     A8-A12  "Bank" select, from the 5-way DIP switch (SW1), in BOTH modes.
             The Arduino CANNOT drive these. The DIP picks which of the 32
             256-byte program slots you are running *and* flashing -- so you
             set the DIP by hand, then flash that slot.

   Everything hangs off one active-high mode signal, PROG (J2.1), which has a
   10k pull-down (R14) so RUN is the safe default whenever the Arduino is
   unplugged or unpowered:

     PROG=0  RUN      Computer owns the address and reads the ROM onto the bus.
                      The '595 outputs are tri-stated and the 74HC157 mux (U5)
                      forces the EEPROM's WE# to +5V, so no Arduino fault can
                      corrupt the ROM while the computer is running.
     PROG=1  PROGRAM  We own A0-A7, the data lines, OE# and WE#. The '541 and
                      the '245 (U4) are both disabled, isolating the computer,
                      and we assert HALT to stop the clock.

   Note there is NO shift-register-enable transistor and NO separate address-
   register-enable line (both of which the old sketch drove). The '595's OE# is
   wired to /PROG off the 74HC04 inverter (U6), so it enables itself whenever
   we enter PROGRAM mode.

   ---------------------------------------------------------------------------
   ARDUINO UNO PIN ASSIGNMENTS  (Arduino pin  <->  J2 pin  <->  board net)
   ---------------------------------------------------------------------------
   The data and shift-register pins deliberately match MicroCodeUploader.ino,
   so the same wiring habits (and the same ribbon cable) carry over.

     Arduino | J2 | Net        | Dir | Purpose
     --------+----+------------+-----+---------------------------------------
      D3     |  5 | ~AOE       | out | EEPROM OE# in PROGRAM mode (LOW = read)
      D4     |  6 | ~AWE       | out | EEPROM WE# in PROGRAM mode (pulse LOW)
      D5     | 16 | HALT       | out | Stop the computer's clock (active HIGH)
      D6     | 14 | EE_D7      | i/o | EEPROM data bit 7  (also the poll bit)
      D7     |  1 | PROG       | out | Mode select (HIGH = PROGRAM)
      D8     |  4 | ARD_RCLK   | out | '595 storage-register clock (latch)
      D9     | 13 | EE_D6      | i/o | EEPROM data bit 6
      D11    |  2 | ARD_SER    | out | '595 serial data in
      D12    |  3 | ARD_SRCLK  | out | '595 shift-register clock
      A0     |  7 | EE_D0      | i/o | EEPROM data bit 0 (LSB)
      A1     |  8 | EE_D1      | i/o |
      A2     |  9 | EE_D2      | i/o |
      A3     | 10 | EE_D3      | i/o |
      A4     | 11 | EE_D4      | i/o |
      A5     | 12 | EE_D5      | i/o |
      GND    | 15 | GND        |  -  | Only power pin shared with the board
     --------+----+------------+-----+---------------------------------------
     unused: D2, D10, D13 (D0/D1 are the USB serial port -- keep them clear)

   The board does NOT share 5V with the Arduino (J2 has no 5V pin). The computer
   powers the board; the Arduino is powered from USB. GND is the only common
   rail, so the board must be powered up for programming to work.

   '595 bit order: QA drives EE_A0 (LSB) ... QH drives EE_A7 (MSB), so the
   address is shifted out MSBFIRST. SRCLR# is tied to +5V (no clear line).

   ---------------------------------------------------------------------------
   IDLE / SAFE STATE
   ---------------------------------------------------------------------------
   Whenever we are not actively programming, the board is handed back to the
   computer and we make ourselves invisible on the shared nets:

     - PROG LOW          -> RUN mode: '541 on, '245 on, WE# forced to +5V.
     - Data pins INPUT   -> MANDATORY. EE_D0-7 are wired straight to the EEPROM
                            with no buffer in between, and in RUN mode the
                            EEPROM drives them. Leaving them as OUTPUT would
                            fight the EEPROM and corrupt the data bus.
     - HALT pin INPUT    -> Hi-Z, so we never fight the control logic's own HALT
                            driver while the computer runs. See NOTE 1 below.

   ---------------------------------------------------------------------------
   WRITE SEQUENCE (byte write with data polling)
   ---------------------------------------------------------------------------
     1. Shift A0-A7 into the '595 and latch it (RCLK).
     2. ~AOE HIGH, so the EEPROM is not driving the data lines.
     3. Data pins -> OUTPUT, drive the byte.
     4. Pulse ~AWE LOW for ~1us. The AT28C64 latches the address on WE#'s
        FALLING edge and the data on its RISING edge. (The old sketch pulsed
        the write line HIGH -- that was for the old transistor-driven board and
        is backwards for this one.)
     5. Data pins -> INPUT, then ~AOE LOW to let the EEPROM drive.
     6. Data polling on IO7 (EE_D7): while the internal write cycle runs the
        EEPROM returns the COMPLEMENT of the bit 7 we just wrote, then the true
        value once it finishes. Poll until it matches -- typically 1-3ms versus
        the 10ms worst-case tWC, so this is much faster than a blind delay.
        A 20ms timeout guards against an absent or stuck chip.

   READ SEQUENCE (verify)
     Data pins -> INPUT, ~AWE HIGH, set the address, ~AOE LOW, let the lines
     settle, sample, ~AOE HIGH.

   Page writes (up to 64 bytes/cycle) are possible in principle but are not
   used: consecutive bytes of a page must arrive within ~150us of each other,
   which a 115200-baud serial link cannot guarantee. Byte writes with data
   polling flash a full 256-byte bank in well under a second, which is plenty.

   ---------------------------------------------------------------------------
   SERIAL PROTOCOL  (binary, 115200 baud)
   ---------------------------------------------------------------------------
     '?'                 -> "PRG1"   identify (4 ASCII bytes)
     'P'                 -> 0x55     enter PROGRAM mode (asserts PROG + HALT)
     'X'                 -> 0x55     exit to RUN mode (releases both)
     'W' <addr> <data>   -> 0x55 ACK, or 0x4E NAK if data polling timed out
     'R' <addr>          -> <data>   read one byte back

   The address is a SINGLE byte: A0-A7 is all we can drive, and the bank (A8-A12)
   comes from the DIP switch. This is the one place the protocol deliberately
   differs from MicroCodeUploader.ino, which sends a two-byte address -- hence
   the '?' identify command, so the host can tell the two sketches apart instead
   of silently misparsing the address stream.

   'W' and 'R' enter PROGRAM mode automatically if it isn't already active. In
   RUN mode the '595 is tri-stated and WE# is held at +5V, so a write issued
   without PROG asserted would be a silent no-op -- auto-entering turns that
   whole class of bug into something that just works. Mode is only ever left via
   an explicit 'X' (or a reset), so we don't thrash PROG/HALT once per byte.

   ---------------------------------------------------------------------------
   NOTES / LIMITATIONS
   ---------------------------------------------------------------------------
   (1) HALT contention. HALT is a backplane net that the control logic also
       drives. We keep our HALT pin Hi-Z (INPUT) except while programming, so
       there is no conflict during normal operation. If the control logic's HALT
       driver is push-pull rather than an OR of sources, driving it HIGH here
       still contends with it -- that is the open hardware question raised in
       NetPlan.txt NOTE (1) and cannot be fixed in software.

   (2) Software Data Protection (SDP) is UNUSABLE on this board, by construction.
       The AT28C64 unlock sequence writes to addresses 0x1555 / 0x0AAA / 0x1555,
       whose A8-A12 bits differ per step -- but A8-A12 come from the DIP switch,
       not from us, so those addresses are physically unreachable. The same goes
       for the chip-erase sequence.

       In practice this is fine: AT28C64s ship with SDP disabled, and we never
       send the enable sequence. But it does mean that if SDP ever does get
       enabled, the chip cannot be unlocked in circuit and will need an external
       programmer. Do not add an SDP enable/unlock routine here expecting it to
       work.

   Quentin McDonald
   January 2025 (rewritten July 2026 for the AT28C64 ProgramROM board)
*/


// --- Control lines (Arduino-only nets: safe to hold as OUTPUT permanently) ---
#define PROG_PIN 7       // J2.1  PROG      HIGH = PROGRAM mode, LOW = RUN
#define SER_PIN 11       // J2.2  ARD_SER   '595 serial data
#define SRCLK_PIN 12     // J2.3  ARD_SRCLK '595 shift clock
#define RCLK_PIN 8       // J2.4  ARD_RCLK  '595 latch clock
#define AOE_PIN 3        // J2.5  ~AOE      EEPROM OE#, active LOW
#define AWE_PIN 4        // J2.6  ~AWE      EEPROM WE#, active LOW

// --- Shared backplane net: held Hi-Z unless we are programming (see NOTE 1) ---
#define HALT_PIN 5       // J2.16 HALT      active HIGH

// EEPROM IO0..IO7 (J2.7..J2.14) wired directly to these pins, LSB first.
// Same assignment as MicroCodeUploader.ino.
const uint8_t DATA_PINS[8] = { A0, A1, A2, A3, A4, A5, 9, 6 };

// Serial protocol constants.
const byte ACK = 0x55;
const byte NAK = 0x4E;

// tWC is 10ms worst case on the AT28C64; a healthy byte write polls done in
// 1-3ms, so 20ms means "the chip is not responding" rather than "still busy".
const unsigned long WRITE_TIMEOUT_MS = 20;

// True while PROG + HALT are asserted and we own the EEPROM.
bool in_program_mode = false;


void set_data_pins_mode(uint8_t mode) {
  for (uint8_t i = 0; i < 8; i++) {
    pinMode(DATA_PINS[i], mode);
    if (mode == INPUT) {
      // Switching OUTPUT->INPUT leaves the port bit set on any line we had
      // driven high, which on an AVR turns on that pin's internal pull-up.
      // Clear it so the data lines are genuinely Hi-Z -- these are wired
      // straight to the EEPROM and, in RUN mode, to the computer's data bus.
      digitalWrite(DATA_PINS[i], LOW);
    }
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

void set_address(byte address) {
  // Shift the 8-bit address (A0-A7) into the '595 and latch it. MSBFIRST
  // because QH drives EE_A7 and QA drives EE_A0. The bank bits A8-A12 come
  // from the DIP switch and are not ours to set.
  digitalWrite(RCLK_PIN, LOW);
  shiftOut(SER_PIN, SRCLK_PIN, MSBFIRST, address);
  digitalWrite(RCLK_PIN, HIGH);
}

void enter_program_mode() {
  // Take ownership of the EEPROM. Idempotent.
  if (in_program_mode) {
    return;
  }

  // Park the control lines inactive *before* the mux switches over to them,
  // so flipping PROG can't glitch a write.
  digitalWrite(AWE_PIN, HIGH);
  digitalWrite(AOE_PIN, HIGH);
  set_data_pins_mode(INPUT);

  // Preload a known address while the '595 outputs are still tri-stated --
  // its latch powers up with an arbitrary value, and we would rather not
  // present a random address to the EEPROM the instant PROG goes high.
  set_address(0);

  // Stop the clock first, so the computer isn't mid-cycle when the buses flip.
  // Set the level *before* switching to OUTPUT: going OUTPUT-first would drive
  // HALT LOW for a few microseconds (the port bit is still clear), briefly
  // fighting the control logic's own HALT driver.
  digitalWrite(HALT_PIN, HIGH);
  pinMode(HALT_PIN, OUTPUT);
  delayMicroseconds(10);

  digitalWrite(PROG_PIN, HIGH);
  delayMicroseconds(10);  // let the '541/'245/'595 finish changing over

  in_program_mode = true;
}

void exit_program_mode() {
  // Hand the EEPROM and the bus back to the computer. Idempotent.
  if (!in_program_mode) {
    return;
  }

  digitalWrite(AWE_PIN, HIGH);
  digitalWrite(AOE_PIN, HIGH);
  set_data_pins_mode(INPUT);  // must be Hi-Z before the EEPROM drives them again

  digitalWrite(PROG_PIN, LOW);
  delayMicroseconds(10);

  // Release HALT back to the control logic. INPUT first, then clear the port
  // bit to switch off the internal pull-up that OUTPUT-HIGH left behind, so
  // the pin ends up truly Hi-Z rather than weakly asserting HALT.
  pinMode(HALT_PIN, INPUT);
  digitalWrite(HALT_PIN, LOW);
  in_program_mode = false;
}

bool write_data(byte address, byte data) {
  // Write one byte to the current bank. Returns false if data polling timed out.
  enter_program_mode();

  set_address(address);

  // Keep the EEPROM's outputs off and drive the bus ourselves.
  digitalWrite(AOE_PIN, HIGH);
  set_data_pins_mode(OUTPUT);
  set_data_bus(data);

  // Address latches on the falling edge, data on the rising edge.
  digitalWrite(AWE_PIN, LOW);
  delayMicroseconds(1);
  digitalWrite(AWE_PIN, HIGH);

  // Data polling on IO7: release the bus, enable the EEPROM's outputs, and wait
  // for bit 7 to stop reading back inverted.
  byte expected_bit7 = (data >> 7) & 0x01;
  set_data_pins_mode(INPUT);
  digitalWrite(AOE_PIN, LOW);

  bool ok = true;
  unsigned long start = millis();
  while (digitalRead(DATA_PINS[7]) != expected_bit7) {
    if (millis() - start > WRITE_TIMEOUT_MS) {
      ok = false;
      break;
    }
  }

  digitalWrite(AOE_PIN, HIGH);
  return ok;
}

byte read_data(byte address) {
  // Read and return the byte stored at "address" in the current bank.
  enter_program_mode();

  // Release the bus so the EEPROM can drive it, and make sure we aren't writing.
  set_data_pins_mode(INPUT);
  digitalWrite(AWE_PIN, HIGH);

  set_address(address);

  digitalWrite(AOE_PIN, LOW);
  delayMicroseconds(1);  // let the IO lines settle
  byte value = read_data_bus();
  digitalWrite(AOE_PIN, HIGH);

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

  pinMode(PROG_PIN, OUTPUT);
  pinMode(SER_PIN, OUTPUT);
  pinMode(SRCLK_PIN, OUTPUT);
  pinMode(RCLK_PIN, OUTPUT);
  pinMode(AOE_PIN, OUTPUT);
  pinMode(AWE_PIN, OUTPUT);

  // Come up in RUN mode with both EEPROM strobes inactive, so a reset in the
  // middle of a session (opening the serial port toggles DTR and resets us)
  // always leaves the computer in control of its own ROM.
  digitalWrite(PROG_PIN, LOW);
  digitalWrite(AOE_PIN, HIGH);
  digitalWrite(AWE_PIN, HIGH);

  pinMode(HALT_PIN, INPUT);
  digitalWrite(HALT_PIN, LOW);  // pull-up off -> true Hi-Z, don't fight the control logic
  set_data_pins_mode(INPUT);    // Hi-Z: the EEPROM drives these in RUN mode
  in_program_mode = false;

  delay(500);
}

void loop() {

  if (Serial.available() < 1) {
    return;
  }

  byte cmd = Serial.read();

  if (cmd == 'W') {
    byte address = read_byte_blocking();
    byte data = read_byte_blocking();
    Serial.write(write_data(address, data) ? ACK : NAK);
  } else if (cmd == 'R') {
    byte address = read_byte_blocking();
    Serial.write(read_data(address));
  } else if (cmd == 'P') {
    enter_program_mode();
    Serial.write(ACK);
  } else if (cmd == 'X') {
    exit_program_mode();
    Serial.write(ACK);
  } else if (cmd == '?') {
    Serial.write("PRG1", 4);
  }
}
