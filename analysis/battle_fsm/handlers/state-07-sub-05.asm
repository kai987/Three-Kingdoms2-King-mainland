; main=7 sub=5: 待機
; entry bank12 $BD41; file $019D51
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01821C b12:$A20C A9 00          LDA  #$00
01821E b12:$A20E 8D 01 05       STA  $0501
018221 b12:$A211 8D 00 05       STA  $0500
018224 b12:$A214 8D 24 04       STA  $0424
018227 b12:$A217 8D 25 04       STA  $0425
01822A b12:$A21A 60             RTS
019D51 b12:$BD41 AD 2E 05       LDA  $052E
019D54 b12:$BD44 D0 03          BNE  $BD49
019D56 b12:$BD46 4C 97 BD       JMP  $BD97
019D59 b12:$BD49 AC 2F 05       LDY  $052F
019D5C b12:$BD4C B9 A1 6F       LDA  $6FA1,Y
019D5F b12:$BD4F C9 FF          CMP  #$FF
019D61 b12:$BD51 F0 03          BEQ  $BD56
019D63 b12:$BD53 4C 97 BD       JMP  $BD97
019D66 b12:$BD56 A9 6D          LDA  #$6D
019D68 b12:$BD58 8D 2C 04       STA  $042C
019D6B b12:$BD5B 20 E9 DE       JSR  $DEE9 ; cpu_DEE9
019D6E b12:$BD5E B0 03          BCS  $BD63
019D70 b12:$BD60 4C 97 BD       JMP  $BD97
019D73 b12:$BD63 EE 01 05       INC  $0501
019D76 b12:$BD66 20 7F E5       JSR  $E57F ; ppu_reset_or_transition
019D79 b12:$BD69 A9 7B          LDA  #$7B
019D7B b12:$BD6B 20 8B E6       JSR  $E68B ; scene_sound_or_effect
019D7E b12:$BD6E 60             RTS
019DA7 b12:$BD97 AD 70 04       LDA  $0470
019DAA b12:$BD9A 85 00          STA  $00
019DAC b12:$BD9C AD 71 04       LDA  $0471
019DAF b12:$BD9F 85 02          STA  $02
019DB1 b12:$BDA1 20 5A DA       JSR  $DA5A ; tile_to_pixel_coordinates
019DB4 b12:$BDA4 A5 00          LDA  $00
019DB6 b12:$BDA6 8D 3F 6F       STA  $6F3F
019DB9 b12:$BDA9 A5 01          LDA  $01
019DBB b12:$BDAB 8D 40 6F       STA  $6F40
019DBE b12:$BDAE A5 02          LDA  $02
019DC0 b12:$BDB0 8D 41 6F       STA  $6F41
019DC3 b12:$BDB3 A5 03          LDA  $03
019DC5 b12:$BDB5 8D 42 6F       STA  $6F42
019DC8 b12:$BDB8 A9 05          LDA  #$05
019DCA b12:$BDBA 20 93 F2       JSR  $F293 ; queue_message_job_0
019DCD b12:$BDBD 4C 0C A2       JMP  $A20C
