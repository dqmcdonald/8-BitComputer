; EXPECT: 10 20 7
; Test: LDAI and LDBI immediate loads
        LDAI 10
        OUT
        LDAI 20
        OUT
        LDBI 7
        LDAI 0
        ADD         ; A = 0 + B = 7
        OUT
        HLT
