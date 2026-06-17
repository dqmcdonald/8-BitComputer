; EXPECT: 5 1 2
; Test: CMP and CMPI set flags without modifying A
.code
        ; CMP non-equal: zero flag not set, A unchanged
        LDAI 5
        LDBI 3
        CMP             ; 5 - 3 = 2, zero=0, A still 5
        JMZ  SKIP1
        OUT             ; output 5 (A is still 5)
SKIP1:
        ; CMP equal: zero flag set
        LDAI 5
        LDBI 5
        CMP             ; 5 - 5 = 0, zero=1, A still 5
        JMZ  EQUAL
        LDAI 99         ; should not execute
        OUT
EQUAL:  LDAI 1
        OUT             ; output 1
        ; CMPI equal: zero flag set
        LDAI 10
        CMPI 10         ; 10 - 10 = 0, zero=1, A still 10
        JMZ  EQUAL2
        LDAI 99         ; should not execute
        OUT
EQUAL2: LDAI 2
        OUT             ; output 2
        HLT
