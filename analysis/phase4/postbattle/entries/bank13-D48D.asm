; accept_remaining_current_city: Insert remaining<=10 into current city, erase first active/captive refs
; Source semantics are direct Python; this is exact ROM provenance.
01B49D b13:$D48D A0 00          LDY  #$00
01B49F b13:$D48F B9 2C 04       LDA  $042C,Y
01B4A2 b13:$D492 C9 FF          CMP  #$FF
01B4A4 b13:$D494 F0 07          BEQ  $D49D
01B4A6 b13:$D496 98             TYA
01B4A7 b13:$D497 48             PHA
01B4A8 b13:$D498 20 A3 D4       JSR  $D4A3
01B4AB b13:$D49B 68             PLA
01B4AC b13:$D49C A8             TAY
01B4AD b13:$D49D C8             INY
01B4AE b13:$D49E C0 14          CPY  #$14
01B4B0 b13:$D4A0 90 ED          BCC  $D48F
01B4B2 b13:$D4A2 60             RTS
