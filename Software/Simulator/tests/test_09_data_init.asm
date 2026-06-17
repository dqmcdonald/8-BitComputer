; EXPECT: 10 11
; Test: .data section initializes RAM variables before code runs
.code
        LDB  ONE        ; B = 1 (from RAM, initialized by preamble)
        LDA  COUNT      ; A = 10
        OUT             ; output 10
        ADD             ; A = 10 + 1 = 11
        OUT             ; output 11
        HLT

.data
COUNT:  10
ONE:    1
