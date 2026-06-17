; Test STA and STB — store values to RAM then load them back

        LDAI  42        ; A = 42
        STA   SLOT      ; RAM[SLOT] = 42
        LDAI  0         ; wipe A to prove the load works
        LDA   SLOT      ; A = RAM[SLOT] = 42
        OUT             ; expect 42

        LDBI  99        ; B = 99
        STB   SLOT      ; RAM[SLOT] = 99
        LDBI  0         ; wipe B
        LDB   SLOT      ; B = RAM[SLOT] = 99
        LDAI  0         ; A = 0
        ADD             ; A = 0 + 99 = 99
        OUT             ; expect 99

        HLT
SLOT:   0x00            ; RAM address used as scratch storage
