; main=14 sub=5: 胜方收容及超额武将转移
; entry bank13 $D3F7; file $01B407
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01B2F1 b13:$D2E1 20 29 CC       JSR  $CC29 ; draw_postbattle_units
01B2F4 b13:$D2E4 20 E1 D0       JSR  $D0E1 ; select_next_postbattle_officer
01B2F7 b13:$D2E7 A9 FF          LDA  #$FF
01B2F9 b13:$D2E9 9D 2C 04       STA  $042C,X
01B2FC b13:$D2EC 8E 0A 05       STX  $050A
01B2FF b13:$D2EF E0 0B          CPX  #$0B
01B301 b13:$D2F1 B0 11          BCS  $D304
01B303 b13:$D2F3 20 8D D4       JSR  $D48D ; postbattle_removal_operation
01B306 b13:$D2F6 A9 0F          LDA  #$0F
01B308 b13:$D2F8 8D 00 05       STA  $0500
01B30B b13:$D2FB AD 0B 05       LDA  $050B
01B30E b13:$D2FE 29 0F          AND  #$0F
01B310 b13:$D300 8D 01 05       STA  $0501
01B313 b13:$D303 60             RTS
01B314 b13:$D304 A9 DF          LDA  #$DF
01B316 b13:$D306 20 93 F2       JSR  $F293 ; queue_message_job_0
01B319 b13:$D309 20 C3 D0       JSR  $D0C3 ; cpu_D0C3
01B31C b13:$D30C EE 01 05       INC  $0501
01B31F b13:$D30F 60             RTS
01B407 b13:$D3F7 AD 0A 05       LDA  $050A
01B40A b13:$D3FA 0A             ASL  A
01B40B b13:$D3FB A8             TAY
01B40C b13:$D3FC B9 5E CF       LDA  $CF5E,Y
01B40F b13:$D3FF 85 10          STA  $10
01B411 b13:$D401 B9 5F CF       LDA  $CF5F,Y
01B414 b13:$D404 85 11          STA  $11
01B416 b13:$D406 A9 00          LDA  #$00
01B418 b13:$D408 85 12          STA  $12
01B41A b13:$D40A 20 23 ED       JSR  $ED23 ; cpu_ED23
01B41D b13:$D40D A9 34          LDA  #$34
01B41F b13:$D40F 85 10          STA  $10
01B421 b13:$D411 A9 CF          LDA  #$CF
01B423 b13:$D413 85 11          STA  $11
01B425 b13:$D415 A9 5D          LDA  #$5D
01B427 b13:$D417 85 00          STA  $00
01B429 b13:$D419 A9 D4          LDA  #$D4
01B42B b13:$D41B 85 01          STA  $01
01B42D b13:$D41D A5 12          LDA  $12
01B42F b13:$D41F 8D 08 05       STA  $0508
01B432 b13:$D422 20 F5 ED       JSR  $EDF5 ; cpu_EDF5
01B435 b13:$D425 20 67 D1       JSR  $D167 ; cpu_D167
01B438 b13:$D428 20 BC D1       JSR  $D1BC ; cpu_D1BC
01B43B b13:$D42B A5 81          LDA  $81
01B43D b13:$D42D 29 01          AND  #$01
01B43F b13:$D42F F0 2B          BEQ  $D45C
01B441 b13:$D431 AD 0A 05       LDA  $050A
01B444 b13:$D434 CD 08 05       CMP  $0508
01B447 b13:$D437 D0 23          BNE  $D45C
01B449 b13:$D439 A0 00          LDY  #$00
01B44B b13:$D43B A2 00          LDX  #$00
01B44D b13:$D43D B9 80 05       LDA  $0580,Y
01B450 b13:$D440 30 01          BMI  $D443
01B452 b13:$D442 E8             INX
01B453 b13:$D443 C8             INY
01B454 b13:$D444 C0 14          CPY  #$14
01B456 b13:$D446 90 F5          BCC  $D43D
01B458 b13:$D448 8A             TXA
01B459 b13:$D449 F0 28          BEQ  $D473
01B45B b13:$D44B A9 D8          LDA  #$D8
01B45D b13:$D44D AC 40 05       LDY  $0540
01B460 b13:$D450 C0 1E          CPY  #$1E
01B462 b13:$D452 D0 02          BNE  $D456
01B464 b13:$D454 A9 E6          LDA  #$E6
01B466 b13:$D456 20 83 F2       JSR  $F283 ; queue_message_job_1
01B469 b13:$D459 EE 01 05       INC  $0501
01B46C b13:$D45C 60             RTS
01B483 b13:$D473 A9 E1          LDA  #$E1
01B485 b13:$D475 85 E6          STA  $E6
01B487 b13:$D477 85 E7          STA  $E7
01B489 b13:$D479 A9 00          LDA  #$00
01B48B b13:$D47B 85 8E          STA  $8E
01B48D b13:$D47D A9 50          LDA  #$50
01B48F b13:$D47F 85 90          STA  $90
01B491 b13:$D481 A9 00          LDA  #$00
01B493 b13:$D483 8D 01 05       STA  $0501
01B496 b13:$D486 20 F9 D1       JSR  $D1F9 ; cpu_D1F9
01B499 b13:$D489 4C E1 D2       JMP  $D2E1
