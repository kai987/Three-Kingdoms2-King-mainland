; main=8 sub=3: 电脑方行动桥接
; entry bank12 $BF19; file $019F29
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
019F29 b12:$BF19 AD 7E 00       LDA  $007E
019F2C b12:$BF1C F0 01          BEQ  $BF1F
019F2E b12:$BF1E 60             RTS
019F2F b12:$BF1F A9 00          LDA  #$00
019F31 b12:$BF21 85 12          STA  $12
019F33 b12:$BF23 20 CC D6       JSR  $D6CC ; enqueue_battle_unit_graphics
019F36 b12:$BF26 A9 00          LDA  #$00
019F38 b12:$BF28 85 00          STA  $00
019F3A b12:$BF2A 85 01          STA  $01
019F3C b12:$BF2C A9 01          LDA  #$01
019F3E b12:$BF2E 85 02          STA  $02
019F40 b12:$BF30 AD 8D 6F       LDA  $6F8D
019F43 b12:$BF33 29 01          AND  #$01
019F45 b12:$BF35 D0 04          BNE  $BF3B
019F47 b12:$BF37 A9 FF          LDA  #$FF
019F49 b12:$BF39 85 02          STA  $02
019F4B b12:$BF3B AD 8D 6F       LDA  $6F8D
019F4E b12:$BF3E 4A             LSR  A
019F4F b12:$BF3F 29 01          AND  #$01
019F51 b12:$BF41 49 01          EOR  #$01
019F53 b12:$BF43 AA             TAX
019F54 b12:$BF44 A5 02          LDA  $02
019F56 b12:$BF46 9D 00 00       STA  $0000,X
019F59 b12:$BF49 AC 09 05       LDY  $0509
019F5C b12:$BF4C B9 00 06       LDA  $0600,Y
019F5F b12:$BF4F 18             CLC
019F60 b12:$BF50 65 00          ADC  $00
019F62 b12:$BF52 99 00 06       STA  $0600,Y
019F65 b12:$BF55 B9 14 06       LDA  $0614,Y
019F68 b12:$BF58 18             CLC
019F69 b12:$BF59 65 01          ADC  $01
019F6B b12:$BF5B 99 14 06       STA  $0614,Y
019F6E b12:$BF5E C9 0F          CMP  #$0F
019F70 b12:$BF60 D0 16          BNE  $BF78
019F72 b12:$BF62 A5 01          LDA  $01
019F74 b12:$BF64 30 09          BMI  $BF6F
019F76 b12:$BF66 B9 14 06       LDA  $0614,Y
019F79 b12:$BF69 18             CLC
019F7A b12:$BF6A 69 01          ADC  #$01
019F7C b12:$BF6C 4C 75 BF       JMP  $BF75
019F7F b12:$BF6F B9 14 06       LDA  $0614,Y
019F82 b12:$BF72 38             SEC
019F83 b12:$BF73 E9 01          SBC  #$01
019F85 b12:$BF75 99 14 06       STA  $0614,Y
019F88 b12:$BF78 EE 01 05       INC  $0501
019F8B b12:$BF7B 60             RTS
