import serial

ser = serial.Serial('/dev/tty.usbmodem14401', 9600, timeout=2)

# Send a few fake pieces of data to kick start the serial communication
address = 0
data = 0x0
values = bytearray([address,data])
ser.write(values)
resp = ser.read()
ser.write(values)
resp = ser.read()


for i in range(255):

    address = i
    data = i
    values = bytearray([address,data])
    ser.write(values)
    resp = ser.read()
    if resp != b'\x55':
        print(i,resp)
        raise RuntimeError("Progam upload failed")
    if i%5 == 0:
        print(".",end="",flush=True)

print()


