; EXPECT: 42
; Test: NOP passes through without affecting registers
        NOP
        LDAI 42
        OUT
        HLT
