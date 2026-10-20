; main=10 sub=2: 下一方回合准备
; entry bank13 $C28A; file $01A29A
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01A29A b13:$C28A AD 07 05       LDA  $0507
01A29D b13:$C28D 4A             LSR  A
01A29E b13:$C28E 4A             LSR  A
01A29F b13:$C28F 4A             LSR  A
01A2A0 b13:$C290 4A             LSR  A
01A2A1 b13:$C291 29 0F          AND  #$0F
01A2A3 b13:$C293 20 68 F3       JSR  $F368 ; ruler_record_pointer
01A2A6 b13:$C296 A0 03          LDY  #$03
01A2A8 b13:$C298 B1 00          LDA  ($00),Y
01A2AA b13:$C29A C9 03          CMP  #$03
01A2AC b13:$C29C F0 2B          BEQ  $C2C9
01A2AE b13:$C29E 8D 44 6F       STA  $6F44
01A2B1 b13:$C2A1 A9 04          LDA  #$04
01A2B3 b13:$C2A3 8D 01 05       STA  $0501
01A2B6 b13:$C2A6 A9 03          LDA  #$03
01A2B8 b13:$C2A8 8D 0B 05       STA  $050B
01A2BB b13:$C2AB A9 0A          LDA  #$0A
01A2BD b13:$C2AD 8D 09 05       STA  $0509
01A2C0 b13:$C2B0 A9 F9          LDA  #$F9
01A2C2 b13:$C2B2 20 93 F2       JSR  $F293 ; queue_message_job_0
01A2C5 b13:$C2B5 AD 07 05       LDA  $0507
01A2C8 b13:$C2B8 4A             LSR  A
01A2C9 b13:$C2B9 4A             LSR  A
01A2CA b13:$C2BA 4A             LSR  A
01A2CB b13:$C2BB 4A             LSR  A
01A2CC b13:$C2BC 29 0F          AND  #$0F
01A2CE b13:$C2BE 20 68 F3       JSR  $F368 ; ruler_record_pointer
01A2D1 b13:$C2C1 A0 00          LDY  #$00
01A2D3 b13:$C2C3 B1 00          LDA  ($00),Y
01A2D5 b13:$C2C5 8D 2C 04       STA  $042C
01A2D8 b13:$C2C8 60             RTS
01A2D9 b13:$C2C9 EE 01 05       INC  $0501
01A2DC b13:$C2CC 60             RTS
