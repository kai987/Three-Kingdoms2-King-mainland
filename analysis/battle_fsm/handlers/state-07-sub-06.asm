; main=7 sub=6: 待機
; entry bank12 $BD6F; file $019D7F
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01821C b12:$A20C A9 00          LDA  #$00
01821E b12:$A20E 8D 01 05       STA  $0501
018221 b12:$A211 8D 00 05       STA  $0500
018224 b12:$A214 8D 24 04       STA  $0424
018227 b12:$A217 8D 25 04       STA  $0425
01822A b12:$A21A 60             RTS
019D7F b12:$BD6F 20 27 DF       JSR  $DF27 ; text_jobs_idle
019D82 b12:$BD72 90 1A          BCC  $BD8E
019D84 b12:$BD74 20 63 DC       JSR  $DC63 ; draw_dialog_highlight
019D87 b12:$BD77 A5 81          LDA  $81
019D89 b12:$BD79 29 03          AND  #$03
019D8B b12:$BD7B F0 11          BEQ  $BD8E
019D8D b12:$BD7D AD 2D 04       LDA  $042D
019D90 b12:$BD80 C9 FF          CMP  #$FF
019D92 b12:$BD82 F0 0B          BEQ  $BD8F
019D94 b12:$BD84 A9 FF          LDA  #$FF
019D96 b12:$BD86 8D 2D 04       STA  $042D
019D99 b12:$BD89 A9 4B          LDA  #$4B
019D9B b12:$BD8B 4C 93 F2       JMP  $F293 ; queue_message_job_0
019D9E b12:$BD8E 60             RTS
019D9F b12:$BD8F 20 7F E5       JSR  $E57F ; ppu_reset_or_transition
019DA2 b12:$BD92 A9 1D          LDA  #$1D
019DA4 b12:$BD94 20 73 E6       JSR  $E673 ; fade_or_scene_effect
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
