; EXPECT: 2 3
; Test: JMZ fires when zero flag set, skips when not zero
        LDAI 5
        SUBI 5      ; A = 0, zero flag set
        JMZ  ZERO
        LDAI 1      ; should not execute
        OUT         ; should not execute
ZERO:   LDAI 2
        OUT
        LDAI 5
        SUBI 3      ; A = 2, zero flag clear
        JMZ  SKIP
        LDAI 3
        OUT
SKIP:   HLT
