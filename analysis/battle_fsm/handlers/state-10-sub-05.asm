; main=10 sub=5: 下一方回合准备
; entry bank13 $C30E; file $01A31E
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01A31E b13:$C30E EE 0A 05       INC  $050A
01A321 b13:$C311 AD 0A 05       LDA  $050A
01A324 b13:$C314 C9 0A          CMP  #$0A
01A326 b13:$C316 90 10          BCC  $C328
01A328 b13:$C318 A9 09          LDA  #$09
01A32A b13:$C31A 85 BB          STA  $BB
01A32C b13:$C31C AD 0B 05       LDA  $050B
01A32F b13:$C31F 8D 01 05       STA  $0501
01A332 b13:$C322 A9 05          LDA  #$05
01A334 b13:$C324 4C 93 F2       JMP  $F293 ; queue_message_job_0
01A338 b13:$C328 AC 09 05       LDY  $0509
01A33B b13:$C32B B9 64 06       LDA  $0664,Y
01A33E b13:$C32E C9 FF          CMP  #$FF
01A340 b13:$C330 D0 06          BNE  $C338
01A342 b13:$C332 EE 09 05       INC  $0509
01A345 b13:$C335 4C 0E C3       JMP  $C30E
01A348 b13:$C338 8D 10 04       STA  $0410
01A34B b13:$C33B A9 08          LDA  #$08
01A34D b13:$C33D 85 BA          STA  $BA
01A34F b13:$C33F A9 00          LDA  #$00
01A351 b13:$C341 8D 0C 04       STA  $040C
01A354 b13:$C344 A9 00          LDA  #$00
01A356 b13:$C346 8D 0D 04       STA  $040D
01A359 b13:$C349 EE 01 05       INC  $0501
01A35C b13:$C34C 20 CB C3       JSR  $C3CB ; cpu_C3CB
01A35F b13:$C34F 60             RTS
