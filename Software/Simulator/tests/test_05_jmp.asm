; EXPECT: 42
; Test: JMP skips over instructions unconditionally
        JMP  SKIP
        LDAI 99     ; should not execute
        OUT         ; should not execute
SKIP:   LDAI 42
        OUT
        HLT
