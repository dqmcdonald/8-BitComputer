
from ctypes import c_uint
import numpy as np

MO = 0b0000000000000001
MI = 0b0100000000000000
RI = 0b0100000000000000
RO = 0b0000000001000000
TR = 0b0000000000100000

ucode = [
   [MO|RI, TR,0,0,0,0,0,0],
   [RO|RI, TR,0,0,0,0,0,0],
   [MI|RI, TR,0,0,0,0,0,0],
   [MO|RO, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MI|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [RO|RI, TR,0,0,0,0,0,0],
   [MI|RI, TR,0,0,0,0,0,0],
   [MO|RO, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MI|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0],
   [MO|RI, TR,0,0,0,0,0,0]
]

ucodes = [ ucode.copy(), ucode.copy(), ucode.copy(), ucode.copy()]

ud = np.array(ucodes, dtype=np.uint16)

for address in range(2048):
    flags       = (address & 0b11000000000) >> 9;
    byte_sel    = (address & 0b00100000000) >> 8;
    instruction = (address & 0b00011111000) >> 3;
    step        = (address & 0b00000000111);

    if byte_sel:
        print(bin(address), " ",
            bin((ud[flags][instruction][step])&0b0000000011111111))
    else:
        print(bin(address), " ", bin((ud[flags][instruction][step])>>8))
