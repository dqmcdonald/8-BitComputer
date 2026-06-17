; Test program — count down from 10 and halt
        LDBI 1          ; B = 1
        LDAI 10         ; A = 10
LOOP:   OUT             ; display A
        SUB             ; A = A - B
        JMZ  DONE       ; if zero, halt
        JMP  LOOP
DONE:   HLT
