# Script for uploading Microcode to the 28AT256 EEPROM via arduino
import serial

ser = serial.Serial('/dev/tty.usbmodem14101', 9600, timeout=2)

# Send a few fake pieces of data to kick start the serial communication
add1 = 0
add2 = 0
data = 0x0
values = bytearray([add1,add2,data])
ser.write(values)
resp = ser.read()
ser.write(values)
resp = ser.read()


for i in range(255):

    add1 = i
    add2 = 0 
    data = 254-i
    values = bytearray([add1,add2,data])
    ser.write(values)
    resp = ser.read()
    if resp != b'\x55':
        print(i,resp)
        raise RuntimeError("Microcode upload failed")
    if i%5 == 0:
        print(".",end="",flush=True)

print()


