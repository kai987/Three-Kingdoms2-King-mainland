; main=7 sub=4: 待機
; entry bank12 $BD2C; file $019D3C
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
019D3C b12:$BD2C A9 01          LDA  #$01
019D3E b12:$BD2E 85 12          STA  $12
019D40 b12:$BD30 20 CC D6       JSR  $D6CC ; enqueue_battle_unit_graphics
019D43 b12:$BD33 EE 09 05       INC  $0509
019D46 b12:$BD36 AD 09 05       LDA  $0509
019D49 b12:$BD39 C9 14          CMP  #$14
019D4B b12:$BD3B 90 03          BCC  $BD40
019D4D b12:$BD3D EE 01 05       INC  $0501
019D50 b12:$BD40 60             RTS
