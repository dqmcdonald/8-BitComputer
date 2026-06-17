; EXPECT: 55 77
; Test: STA, STB, LDA, LDB memory operations
        LDAI 55
        STA  SLOT
        LDAI 0
        LDA  SLOT   ; reload A = 55
        OUT
        LDBI 77
        STB  SLOT
        LDB  SLOT   ; reload B = 77
        LDAI 0
        ADD         ; A = 0 + 77
        OUT
        HLT
SLOT:   0
