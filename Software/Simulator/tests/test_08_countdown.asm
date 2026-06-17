; EXPECT: 10 9 8 7 6 5 4 3 2 1
; Test: Countdown from 10 using SUB and conditional jumps (exercises JMZ, JMP, SUB)
        LDBI 1
        LDAI 10
LOOP:   OUT
        SUB
        JMZ  DONE
        JMP  LOOP
DONE:   HLT
