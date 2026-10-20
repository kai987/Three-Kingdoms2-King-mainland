; main=10 sub=3: 下一方回合准备
; entry bank13 $C2CD; file $01A2DD
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01A2DD b13:$C2CD A9 00          LDA  #$00
01A2DF b13:$C2CF 8D 00 05       STA  $0500
01A2E2 b13:$C2D2 A9 00          LDA  #$00
01A2E4 b13:$C2D4 8D 01 05       STA  $0501
01A2E7 b13:$C2D7 8D 08 05       STA  $0508
01A2EA b13:$C2DA 8D 09 05       STA  $0509
01A2ED b13:$C2DD 8D 0A 05       STA  $050A
01A2F0 b13:$C2E0 8D 0B 05       STA  $050B
01A2F3 b13:$C2E3 AD 07 05       LDA  $0507
01A2F6 b13:$C2E6 4A             LSR  A
01A2F7 b13:$C2E7 4A             LSR  A
01A2F8 b13:$C2E8 4A             LSR  A
01A2F9 b13:$C2E9 4A             LSR  A
01A2FA b13:$C2EA 29 0F          AND  #$0F
01A2FC b13:$C2EC 20 68 F3       JSR  $F368 ; ruler_record_pointer
01A2FF b13:$C2EF A0 03          LDY  #$03
01A301 b13:$C2F1 B1 00          LDA  ($00),Y
01A303 b13:$C2F3 8D 0F 05       STA  $050F
01A306 b13:$C2F6 60             RTS
