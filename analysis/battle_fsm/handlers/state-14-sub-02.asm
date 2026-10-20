; main=14 sub=2: 胜方收容及超额武将转移
; entry bank13 $D34B; file $01B35B
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01B35A b13:$D34A 60             RTS
01B35B b13:$D34B 20 29 CC       JSR  $CC29 ; draw_postbattle_units
01B35E b13:$D34E AD 0A 05       LDA  $050A
01B361 b13:$D351 0A             ASL  A
01B362 b13:$D352 A8             TAY
01B363 b13:$D353 B9 9F BA       LDA  $BA9F,Y
01B366 b13:$D356 85 10          STA  $10
01B368 b13:$D358 B9 A0 BA       LDA  $BAA0,Y
01B36B b13:$D35B 85 11          STA  $11
01B36D b13:$D35D A9 00          LDA  #$00
01B36F b13:$D35F 85 12          STA  $12
01B371 b13:$D361 20 1E ED       JSR  $ED1E ; cpu_ED1E
01B374 b13:$D364 A9 6F          LDA  #$6F
01B376 b13:$D366 85 10          STA  $10
01B378 b13:$D368 A9 BB          LDA  #$BB
01B37A b13:$D36A 85 11          STA  $11
01B37C b13:$D36C A9 7F          LDA  #$7F
01B37E b13:$D36E 85 00          STA  $00
01B380 b13:$D370 A9 BB          LDA  #$BB
01B382 b13:$D372 85 01          STA  $01
01B384 b13:$D374 A5 12          LDA  $12
01B386 b13:$D376 20 F5 ED       JSR  $EDF5 ; cpu_EDF5
01B389 b13:$D379 20 27 DF       JSR  $DF27 ; text_jobs_idle
01B38C b13:$D37C 90 CC          BCC  $D34A
01B38E b13:$D37E A5 81          LDA  $81
01B390 b13:$D380 29 01          AND  #$01
01B392 b13:$D382 F0 2A          BEQ  $D3AE
01B394 b13:$D384 A4 12          LDY  $12
01B396 b13:$D386 B9 2C 04       LDA  $042C,Y
01B399 b13:$D389 8D 40 05       STA  $0540
01B39C b13:$D38C 8C 41 05       STY  $0541
01B39F b13:$D38F C9 1E          CMP  #$1E
01B3A1 b13:$D391 F0 07          BEQ  $D39A
01B3A3 b13:$D393 B9 50 05       LDA  $0550,Y
01B3A6 b13:$D396 C9 0A          CMP  #$0A
01B3A8 b13:$D398 B0 14          BCS  $D3AE
01B3AA b13:$D39A EE 01 05       INC  $0501
01B3AD b13:$D39D A9 DD          LDA  #$DD
01B3AF b13:$D39F AC 40 05       LDY  $0540
01B3B2 b13:$D3A2 C0 1E          CPY  #$1E
01B3B4 b13:$D3A4 D0 02          BNE  $D3A8
01B3B6 b13:$D3A6 A9 E5          LDA  #$E5
01B3B8 b13:$D3A8 20 83 F2       JSR  $F283 ; queue_message_job_1
01B3BB b13:$D3AB 20 C3 D0       JSR  $D0C3 ; cpu_D0C3
01B3BE b13:$D3AE 60             RTS
