; EXPECT: 1 1 2 3 5 8 13 21 34 55 89 144 233
; Fibonacci series until 8-bit overflow (F14=377 > 255 → carry stops the loop).
; PREV and CURR are initialised to 1 by the .data preamble.
; After ADD: A = PREV+CURR (next), B = old CURR — used directly as new PREV.

.code
        LDA   PREV
        OUT             ; F(1) = 1
        LDA   CURR
        OUT             ; F(2) = 1

LOOP:   LDB   CURR      ; B = curr
        LDA   PREV      ; A = prev
        ADD             ; A = prev+curr, flags latched; B unchanged
        JMC   DONE      ; overflow → stop
        OUT             ; output next Fibonacci number
        STB   PREV      ; prev = old curr  (B still holds it)
        STA   CURR      ; curr = prev+curr (A holds the sum)
        JMP   LOOP

DONE:   HLT

.data
PREV:   1
CURR:   1
