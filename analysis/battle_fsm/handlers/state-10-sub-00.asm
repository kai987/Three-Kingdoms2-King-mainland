; main=10 sub=0: 下一方回合准备
; entry bank13 $C218; file $01A228
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01A228 b13:$C218 20 20 C6       JSR  $C620 ; round_resource_update
01A22B b13:$C21B EE 01 05       INC  $0501
01A22E b13:$C21E AD 0A 06       LDA  $060A
01A231 b13:$C221 85 00          STA  $00
01A233 b13:$C223 AD 1E 06       LDA  $061E
01A236 b13:$C226 85 02          STA  $02
01A238 b13:$C228 20 5A DA       JSR  $DA5A ; tile_to_pixel_coordinates
01A23B b13:$C22B A5 00          LDA  $00
01A23D b13:$C22D 8D 3F 6F       STA  $6F3F
01A240 b13:$C230 A5 01          LDA  $01
01A242 b13:$C232 8D 40 6F       STA  $6F40
01A245 b13:$C235 A5 02          LDA  $02
01A247 b13:$C237 8D 41 6F       STA  $6F41
01A24A b13:$C23A A5 03          LDA  $03
01A24C b13:$C23C 8D 42 6F       STA  $6F42
01A24F b13:$C23F 20 A0 C5       JSR  $C5A0 ; cpu_C5A0
01A252 b13:$C242 EE 06 05       INC  $0506
01A255 b13:$C245 AD 0D 05       LDA  $050D
01A258 b13:$C248 8D 05 05       STA  $0505
01A25B b13:$C24B 20 1E DC       JSR  $DC1E ; cpu_DC1E
01A25E b13:$C24E 60             RTS
