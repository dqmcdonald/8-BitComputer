; Test program — count down from 10 and halt
        LDI  10         ; A = 10
LOOP:   OUT             ; display A
        SUB             ; A = A - B  (B initialised to 1 below by hardware/RAM)
        JMZ  DONE       ; if zero, halt
        JMP  LOOP
DONE:   HLT
