; EXPECT: 5 6
; Test: JMC fires when carry flag set, skips when not
        LDAI 200
        ADDI 100    ; 300 mod 256 = 44, carry set
        JMC  CARRY
        LDAI 1      ; should not execute
        OUT         ; should not execute
CARRY:  LDAI 5
        OUT
        LDAI 10
        ADDI 5      ; 15, no carry
        JMC  SKIP
        LDAI 6
        OUT
SKIP:   HLT
