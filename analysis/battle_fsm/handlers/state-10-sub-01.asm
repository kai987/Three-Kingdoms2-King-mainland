; main=10 sub=1: 下一方回合准备
; entry bank13 $C24F; file $01A25F
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01A25F b13:$C24F AD 07 05       LDA  $0507
01A262 b13:$C252 29 0F          AND  #$0F
01A264 b13:$C254 20 68 F3       JSR  $F368 ; ruler_record_pointer
01A267 b13:$C257 A0 03          LDY  #$03
01A269 b13:$C259 B1 00          LDA  ($00),Y
01A26B b13:$C25B C9 03          CMP  #$03
01A26D b13:$C25D F0 27          BEQ  $C286
01A26F b13:$C25F 8D 44 6F       STA  $6F44
01A272 b13:$C262 A9 04          LDA  #$04
01A274 b13:$C264 8D 01 05       STA  $0501
01A277 b13:$C267 A9 02          LDA  #$02
01A279 b13:$C269 8D 0B 05       STA  $050B
01A27C b13:$C26C A9 00          LDA  #$00
01A27E b13:$C26E 8D 09 05       STA  $0509
01A281 b13:$C271 A9 F9          LDA  #$F9
01A283 b13:$C273 20 93 F2       JSR  $F293 ; queue_message_job_0
01A286 b13:$C276 AD 07 05       LDA  $0507
01A289 b13:$C279 29 0F          AND  #$0F
01A28B b13:$C27B 20 68 F3       JSR  $F368 ; ruler_record_pointer
01A28E b13:$C27E A0 00          LDY  #$00
01A290 b13:$C280 B1 00          LDA  ($00),Y
01A292 b13:$C282 8D 2C 04       STA  $042C
01A295 b13:$C285 60             RTS
01A296 b13:$C286 EE 01 05       INC  $0501
01A299 b13:$C289 60             RTS
