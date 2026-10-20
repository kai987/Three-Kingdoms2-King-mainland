; main=14 sub=1: 胜方收容及超额武将转移
; entry bank13 $D310; file $01B320
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01B320 b13:$D310 20 29 CC       JSR  $CC29 ; draw_postbattle_units
01B323 b13:$D313 20 27 DF       JSR  $DF27 ; text_jobs_idle
01B326 b13:$D316 90 32          BCC  $D34A
01B328 b13:$D318 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
01B32B b13:$D31B A5 81          LDA  $81
01B32D b13:$D31D 29 01          AND  #$01
01B32F b13:$D31F F0 29          BEQ  $D34A
01B331 b13:$D321 EE 01 05       INC  $0501
01B334 b13:$D324 A9 D7          LDA  #$D7
01B336 b13:$D326 20 83 F2       JSR  $F283 ; queue_message_job_1
01B339 b13:$D329 A9 00          LDA  #$00
01B33B b13:$D32B 8D 24 04       STA  $0424
01B33E b13:$D32E 8D 25 04       STA  $0425
01B341 b13:$D331 AD 0B 05       LDA  $050B
01B344 b13:$D334 29 10          AND  #$10
01B346 b13:$D336 0A             ASL  A
01B347 b13:$D337 0A             ASL  A
01B348 b13:$D338 0A             ASL  A
01B349 b13:$D339 8D 04 05       STA  $0504
01B34C b13:$D33C 20 84 BB       JSR  $BB84 ; cpu_BB84
01B34F b13:$D33F EE 0A 05       INC  $050A
01B352 b13:$D342 AC 0A 05       LDY  $050A
01B355 b13:$D345 A9 1E          LDA  #$1E
01B357 b13:$D347 99 2C 04       STA  $042C,Y
01B35A b13:$D34A 60             RTS
