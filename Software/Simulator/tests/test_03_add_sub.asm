; EXPECT: 15 18 11 8
; Test: ADD, ADDI, SUB, SUBI
        LDAI 10
        LDBI 5
        ADD         ; A = 10 + 5 = 15
        OUT
        ADDI 3      ; A = 15 + 3 = 18 (clobbers B)
        OUT
        LDBI 7
        SUB         ; A = 18 - 7 = 11
        OUT
        SUBI 3      ; A = 11 - 3 = 8 (clobbers B)
        OUT
        HLT
