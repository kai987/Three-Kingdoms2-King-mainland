; main=8 sub=4: 电脑方行动桥接
; entry bank12 $BF7C; file $019F8C
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
019F8C b12:$BF7C A9 01          LDA  #$01
019F8E b12:$BF7E 85 12          STA  $12
019F90 b12:$BF80 20 CC D6       JSR  $D6CC ; enqueue_battle_unit_graphics
019F93 b12:$BF83 AD 05 05       LDA  $0505
019F96 b12:$BF86 38             SEC
019F97 b12:$BF87 ED 97 6F       SBC  $6F97
019F9A b12:$BF8A 8D 05 05       STA  $0505
019F9D b12:$BF8D A9 04          LDA  #$04
019F9F b12:$BF8F 8D 00 05       STA  $0500
019FA2 b12:$BF92 A9 02          LDA  #$02
019FA4 b12:$BF94 8D 01 05       STA  $0501
019FA7 b12:$BF97 60             RTS
