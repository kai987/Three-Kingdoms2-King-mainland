; Reachable duel handlers, physical bank23 A000/bank24 C000. Pointer tables excluded.
$B100 | b23 file $02F110 | LDY $04aa
$B103 | b23 file $02F113 | LDA $04ab,Y
$B106 | b23 file $02F116 | BPL $b10f
$B108 | b23 file $02F118 | TYA
$B109 | b23 file $02F119 | EOR #$01
$B10B | b23 file $02F11B | TAY
$B10C | b23 file $02F11C | LDA $04ab,Y
$B10F | b23 file $02F11F | STA $6f44
$B112 | b23 file $02F122 | LDA $04a8
$B115 | b23 file $02F125 | JSR $eade ; inline targets: $B144,$B34F,$B5C8,$B8C7,$BA6D,$BC3B,$BCE9,$BE78,$C08A,$C116,$B144,$B144,$B144,$C21C,$C2F6,$C464,$C498,$C689,$C949,$CB9E,$CC87,$CD3C
$B144 | b23 file $02F154 | LDA $04a9
$B147 | b23 file $02F157 | JSR $eade ; inline targets: $B15A,$B1A6,$B1BB,$B1D4,$B1EE,$B21C,$B230,$B2E0
$B15A | b23 file $02F16A | LDA $0087
$B15D | b23 file $02F16D | BMI $b160
$B15F | b23 file $02F16F | RTS
$B160 | b23 file $02F170 | INC $04a9
$B163 | b23 file $02F173 | LDX #$00
$B165 | b23 file $02F175 | LDA $04ad,X
$B168 | b23 file $02F178 | JSR $f2d7
$B16B | b23 file $02F17B | LDY #$00
$B16D | b23 file $02F17D | LDA ($00),Y
$B16F | b23 file $02F17F | STA $04b1,X
$B172 | b23 file $02F182 | JSR $b188
$B175 | b23 file $02F185 | INX
$B176 | b23 file $02F186 | CPX #$02
$B178 | b23 file $02F188 | BCC $b165
$B17A | b23 file $02F18A | LDA #$43
$B17C | b23 file $02F18C | STA $0000
$B17F | b23 file $02F18F | LDA $04af
$B182 | b23 file $02F192 | CLC
$B183 | b23 file $02F193 | ADC #$01
$B185 | b23 file $02F195 | JMP $cdfd
$B188 | b23 file $02F198 | LDY #$0a
$B18A | b23 file $02F19A | LDA ($00),Y
$B18C | b23 file $02F19C | AND #$1f
$B18E | b23 file $02F19E | CMP #$10
$B190 | b23 file $02F1A0 | BCC $b197
$B192 | b23 file $02F1A2 | LDA #$01
$B194 | b23 file $02F1A4 | JMP $b1a2
$B197 | b23 file $02F1A7 | CMP #$08
$B199 | b23 file $02F1A9 | BCC $b1a0
$B19B | b23 file $02F1AB | LDA #$00
$B19D | b23 file $02F1AD | JMP $b1a2
$B1A0 | b23 file $02F1B0 | LDA #$02
$B1A2 | b23 file $02F1B2 | STA $04af,X
$B1A5 | b23 file $02F1B5 | RTS
$B1A6 | b23 file $02F1B6 | LDA $007e
$B1A9 | b23 file $02F1B9 | AND #$04
$B1AB | b23 file $02F1BB | BNE $b1ba
$B1AD | b23 file $02F1BD | LDA #$e3
$B1AF | b23 file $02F1BF | STA $0000
$B1B2 | b23 file $02F1C2 | LDA #$04
$B1B4 | b23 file $02F1C4 | JSR $cdfd
$B1B7 | b23 file $02F1C7 | INC $04a9
$B1BA | b23 file $02F1CA | RTS
$B1BB | b23 file $02F1CB | LDA $007e
$B1BE | b23 file $02F1CE | AND #$04
$B1C0 | b23 file $02F1D0 | BNE $b1d3
$B1C2 | b23 file $02F1D2 | LDA #$55
$B1C4 | b23 file $02F1D4 | STA $0000
$B1C7 | b23 file $02F1D7 | LDA $04b0
$B1CA | b23 file $02F1DA | CLC
$B1CB | b23 file $02F1DB | ADC #$05
$B1CD | b23 file $02F1DD | JSR $cdfd
$B1D0 | b23 file $02F1E0 | INC $04a9
$B1D3 | b23 file $02F1E3 | RTS
$B1D4 | b23 file $02F1E4 | LDA $007e
$B1D7 | b23 file $02F1E7 | AND #$04
$B1D9 | b23 file $02F1E9 | BNE $b1ed
$B1DB | b23 file $02F1EB | LDA #$f5
$B1DD | b23 file $02F1ED | STA $0000
$B1E0 | b23 file $02F1F0 | LDA #$08
$B1E2 | b23 file $02F1F2 | JSR $cdfd
$B1E5 | b23 file $02F1F5 | INC $04a9
$B1E8 | b23 file $02F1F8 | LDA #$01
$B1EA | b23 file $02F1FA | STA $04aa
$B1ED | b23 file $02F1FD | RTS
$B1EE | b23 file $02F1FE | LDY #$31
$B1F0 | b23 file $02F200 | JSR $f25f
$B1F3 | b23 file $02F203 | LDX #$00
$B1F5 | b23 file $02F205 | LDA #$44
$B1F7 | b23 file $02F207 | STA $0003
$B1FA | b23 file $02F20A | LDA $04ad
$B1FD | b23 file $02F20D | JSR $cfa3
$B200 | b23 file $02F210 | LDA #$52
$B202 | b23 file $02F212 | STA $0003
$B205 | b23 file $02F215 | LDA $04ae
$B208 | b23 file $02F218 | JSR $cfa3
$B20B | b23 file $02F21B | LDA #$ff
$B20D | b23 file $02F21D | STA $0380,X
$B210 | b23 file $02F220 | INC $04a9
$B213 | b23 file $02F223 | LDA $007e
$B216 | b23 file $02F226 | ORA #$04
$B218 | b23 file $02F228 | STA $007e
$B21B | b23 file $02F22B | RTS
$B21C | b23 file $02F22C | JSR $d060
$B21F | b23 file $02F22F | LDA #$ff
$B221 | b23 file $02F231 | STA $0380,X
$B224 | b23 file $02F234 | INC $04a9
$B227 | b23 file $02F237 | LDA $007e
$B22A | b23 file $02F23A | ORA #$04
$B22C | b23 file $02F23C | STA $007e
$B22F | b23 file $02F23F | RTS
$B230 | b23 file $02F240 | LDX #$00
$B232 | b23 file $02F242 | LDA $04ad,X
$B235 | b23 file $02F245 | JSR $f2d7
$B238 | b23 file $02F248 | LDY #$0a
$B23A | b23 file $02F24A | LDA ($00),Y
$B23C | b23 file $02F24C | STA $0010
$B23F | b23 file $02F24F | LSR A
$B240 | b23 file $02F250 | LSR A
$B241 | b23 file $02F251 | LSR A
$B242 | b23 file $02F252 | LSR A
$B243 | b23 file $02F253 | LSR A
$B244 | b23 file $02F254 | CLC
$B245 | b23 file $02F255 | ADC #$18
$B247 | b23 file $02F257 | STA $0011
$B24A | b23 file $02F25A | LDA $0010
$B24D | b23 file $02F25D | AND #$1f
$B24F | b23 file $02F25F | STA $0010
$B252 | b23 file $02F262 | TAY
$B253 | b23 file $02F263 | LDA $b2c0,Y
$B256 | b23 file $02F266 | STA $0010
$B259 | b23 file $02F269 | LDY $0011
$B25C | b23 file $02F26C | LDA $b2c0,Y
$B25F | b23 file $02F26F | CLC
$B260 | b23 file $02F270 | ADC $0010
$B263 | b23 file $02F273 | STA $0010
$B266 | b23 file $02F276 | LDY #$00
$B268 | b23 file $02F278 | LDA ($00),Y
$B26A | b23 file $02F27A | STA $0002
$B26D | b23 file $02F27D | LDY #$01
$B26F | b23 file $02F27F | LDA ($00),Y
$B271 | b23 file $02F281 | CLC
$B272 | b23 file $02F282 | ADC $0002
$B275 | b23 file $02F285 | STA $0001
$B278 | b23 file $02F288 | LDA #$00
$B27A | b23 file $02F28A | STA $0002
$B27D | b23 file $02F28D | STA $0004
$B280 | b23 file $02F290 | LDA #$0a
$B282 | b23 file $02F292 | STA $0003
$B285 | b23 file $02F295 | JSR $ea7c
$B288 | b23 file $02F298 | LDA $0001
$B28B | b23 file $02F29B | CLC
$B28C | b23 file $02F29C | ADC #$14
$B28E | b23 file $02F29E | SEC
$B28F | b23 file $02F29F | SBC $0010
$B292 | b23 file $02F2A2 | STA $04b3,X
$B295 | b23 file $02F2A5 | JSR $e87a
$B298 | b23 file $02F2A8 | AND #$0f
$B29A | b23 file $02F2AA | CMP #$0b
$B29C | b23 file $02F2AC | BCS $b295
$B29E | b23 file $02F2AE | ADC $04b3,X
$B2A1 | b23 file $02F2B1 | STA $04bd,X
$B2A4 | b23 file $02F2B4 | INX
$B2A5 | b23 file $02F2B5 | CPX #$02
$B2A7 | b23 file $02F2B7 | BNE $b232
$B2A9 | b23 file $02F2B9 | LDX #$00
$B2AB | b23 file $02F2BB | LDA $04bd
$B2AE | b23 file $02F2BE | CMP $04be
$B2B1 | b23 file $02F2C1 | BCS $b2b4
$B2B3 | b23 file $02F2C3 | INX
$B2B4 | b23 file $02F2C4 | STX $04aa
$B2B7 | b23 file $02F2C7 | LDA #$00
$B2B9 | b23 file $02F2C9 | STA $04c0
$B2BC | b23 file $02F2CC | INC $04a9
$B2BF | b23 file $02F2CF | RTS
$B2E0 | b23 file $02F2F0 | LDY $04af
$B2E3 | b23 file $02F2F3 | LDA $b34c,Y
$B2E6 | b23 file $02F2F6 | STA $0000
$B2E9 | b23 file $02F2F9 | LDY $04b0
$B2EC | b23 file $02F2FC | LDA $b34c,Y
$B2EF | b23 file $02F2FF | STA $0001
$B2F2 | b23 file $02F302 | LDA $0000
$B2F5 | b23 file $02F305 | ASL A
$B2F6 | b23 file $02F306 | CLC
$B2F7 | b23 file $02F307 | ADC $0000
$B2FA | b23 file $02F30A | CLC
$B2FB | b23 file $02F30B | ADC $0001
$B2FE | b23 file $02F30E | TAY
$B2FF | b23 file $02F30F | LDA $b343,Y
$B302 | b23 file $02F312 | STA $04c5
$B305 | b23 file $02F315 | LDA $0001
$B308 | b23 file $02F318 | ASL A
$B309 | b23 file $02F319 | CLC
$B30A | b23 file $02F31A | ADC $0001
$B30D | b23 file $02F31D | CLC
$B30E | b23 file $02F31E | ADC $0000
$B311 | b23 file $02F321 | TAY
$B312 | b23 file $02F322 | LDA $b343,Y
$B315 | b23 file $02F325 | STA $04c6
$B318 | b23 file $02F328 | LDA #$02
$B31A | b23 file $02F32A | STA $04c3
$B31D | b23 file $02F32D | STA $04c4
$B320 | b23 file $02F330 | LDY $04aa
$B323 | b23 file $02F333 | LDA $04ad,Y
$B326 | b23 file $02F336 | STA $042c
$B329 | b23 file $02F339 | LDA #$3a
$B32B | b23 file $02F33B | STA $04bd
$B32E | b23 file $02F33E | LDA #$3b
$B330 | b23 file $02F340 | STA $04be
$B333 | b23 file $02F343 | LDA #$00
$B335 | b23 file $02F345 | STA $04bf
$B338 | b23 file $02F348 | LDA #$09
$B33A | b23 file $02F34A | STA $04a8
$B33D | b23 file $02F34D | LDA #$00
$B33F | b23 file $02F34F | STA $04a9
$B342 | b23 file $02F352 | RTS
$B34F | b23 file $02F35F | LDA $04a9
$B352 | b23 file $02F362 | JSR $eade ; inline targets: $B361,$B3F0,$B407,$B47E,$B552,$B569
$B361 | b23 file $02F371 | LDA $04c0
$B364 | b23 file $02F374 | BNE $b36e
$B366 | b23 file $02F376 | LDA $04aa
$B369 | b23 file $02F379 | EOR #$01
$B36B | b23 file $02F37B | STA $04aa
$B36E | b23 file $02F37E | INC $04c0
$B371 | b23 file $02F381 | LDA $04c0
$B374 | b23 file $02F384 | CMP #$03
$B376 | b23 file $02F386 | BCC $b37b
$B378 | b23 file $02F388 | JSR $b3c6
$B37B | b23 file $02F38B | LDA $04aa
$B37E | b23 file $02F38E | EOR #$01
$B380 | b23 file $02F390 | STA $04aa
$B383 | b23 file $02F393 | TAY
$B384 | b23 file $02F394 | LDA $04b5,Y
$B387 | b23 file $02F397 | AND #$7f
$B389 | b23 file $02F399 | BEQ $b391
$B38B | b23 file $02F39B | SEC
$B38C | b23 file $02F39C | SBC #$01
$B38E | b23 file $02F39E | STA $04b5,Y
$B391 | b23 file $02F3A1 | LDY $04aa
$B394 | b23 file $02F3A4 | LDA $04ab,Y
$B397 | b23 file $02F3A7 | BPL $b39f
$B399 | b23 file $02F3A9 | LDA #$02
$B39B | b23 file $02F3AB | STA $04a8
$B39E | b23 file $02F3AE | RTS
$B39F | b23 file $02F3AF | LDY $04aa
$B3A2 | b23 file $02F3B2 | LDA $04ad,Y
$B3A5 | b23 file $02F3B5 | STA $0000
$B3A8 | b23 file $02F3B8 | LDY #$3d
$B3AA | b23 file $02F3BA | JSR $ee07 ; inline far target $A030
$B3AF | b23 file $02F3BF | LDY $04aa
$B3B2 | b23 file $02F3C2 | LDA $04b5,Y
$B3B5 | b23 file $02F3C5 | AND #$7f
$B3B7 | b23 file $02F3C7 | BEQ $b3bb
$B3B9 | b23 file $02F3C9 | LDA #$02
$B3BB | b23 file $02F3CB | STA $00a4
$B3BE | b23 file $02F3CE | INC $04a9
$B3C1 | b23 file $02F3D1 | LDA #$2b
$B3C3 | b23 file $02F3D3 | JMP $f26d
$B3C6 | b23 file $02F3D6 | LDX #$00
$B3C8 | b23 file $02F3D8 | JSR $e87a
$B3CB | b23 file $02F3DB | AND #$0f
$B3CD | b23 file $02F3DD | CMP #$0b
$B3CF | b23 file $02F3DF | BCS $b3c8
$B3D1 | b23 file $02F3E1 | ADC $04b3,X
$B3D4 | b23 file $02F3E4 | STA $04bd,X
$B3D7 | b23 file $02F3E7 | INX
$B3D8 | b23 file $02F3E8 | CPX #$02
$B3DA | b23 file $02F3EA | BCC $b3c8
$B3DC | b23 file $02F3EC | LDX #$00
$B3DE | b23 file $02F3EE | LDA $04bd
$B3E1 | b23 file $02F3F1 | CMP $04be
$B3E4 | b23 file $02F3F4 | BCC $b3e7
$B3E6 | b23 file $02F3F6 | INX
$B3E7 | b23 file $02F3F7 | STX $04aa
$B3EA | b23 file $02F3FA | LDA #$01
$B3EC | b23 file $02F3FC | STA $04c0
$B3EF | b23 file $02F3FF | RTS
$B3F0 | b23 file $02F400 | JSR $d166
$B3F3 | b23 file $02F403 | JSR $d299
$B3F6 | b23 file $02F406 | BCC $b406
$B3F8 | b23 file $02F408 | LDA #$00
$B3FA | b23 file $02F40A | STA $0424
$B3FD | b23 file $02F40D | STA $0425
$B400 | b23 file $02F410 | INC $04a9
$B403 | b23 file $02F413 | JMP $d17c
$B406 | b23 file $02F416 | RTS
$B407 | b23 file $02F417 | JSR $d166
$B40A | b23 file $02F41A | LDA #$61
$B40C | b23 file $02F41C | STA $0010
$B40F | b23 file $02F41F | LDA #$b4
$B411 | b23 file $02F421 | STA $0011
$B414 | b23 file $02F424 | LDA #$00
$B416 | b23 file $02F426 | STA $0012
$B419 | b23 file $02F429 | JSR $ed1e
$B41C | b23 file $02F42C | LDA #$6b
$B41E | b23 file $02F42E | STA $0010
$B421 | b23 file $02F431 | LDA #$b4
$B423 | b23 file $02F433 | STA $0011
$B426 | b23 file $02F436 | LDA #$79
$B428 | b23 file $02F438 | STA $0000
$B42B | b23 file $02F43B | LDA #$b4
$B42D | b23 file $02F43D | STA $0001
$B430 | b23 file $02F440 | LDA $0012
$B433 | b23 file $02F443 | JSR $edf5
$B436 | b23 file $02F446 | LDA $0081
$B439 | b23 file $02F449 | LSR A
$B43A | b23 file $02F44A | BCC $b460
$B43C | b23 file $02F44C | INC $04a9
$B43F | b23 file $02F44F | LDA $0012
$B442 | b23 file $02F452 | STA $04bf
$B445 | b23 file $02F455 | CMP #$04
$B447 | b23 file $02F457 | BNE $b460
$B449 | b23 file $02F459 | LDY $04aa
$B44C | b23 file $02F45C | LDA $04b5,Y
$B44F | b23 file $02F45F | AND #$7f
$B451 | b23 file $02F461 | BNE $b45b
$B453 | b23 file $02F463 | INC $04a9
$B456 | b23 file $02F466 | LDA #$2c
$B458 | b23 file $02F468 | JMP $f26d
$B45B | b23 file $02F46B | LDA #$02
$B45D | b23 file $02F46D | STA $04a9
$B460 | b23 file $02F470 | RTS
$B47E | b23 file $02F48E | LDA $04bf
$B481 | b23 file $02F491 | BNE $b4a5
$B483 | b23 file $02F493 | LDA #$03
$B485 | b23 file $02F495 | STA $04bd
$B488 | b23 file $02F498 | LDA #$00
$B48A | b23 file $02F49A | STA $04be
$B48D | b23 file $02F49D | LDA #$10
$B48F | b23 file $02F49F | STA $04a8
$B492 | b23 file $02F4A2 | LDA #$00
$B494 | b23 file $02F4A4 | STA $04a9
$B497 | b23 file $02F4A7 | LDY $04aa
$B49A | b23 file $02F4AA | LDA $04ad,Y
$B49D | b23 file $02F4AD | STA $042c
$B4A0 | b23 file $02F4B0 | LDA #$23
$B4A2 | b23 file $02F4B2 | JMP $f28b
$B4A5 | b23 file $02F4B5 | CMP #$01
$B4A7 | b23 file $02F4B7 | BNE $b4b8
$B4A9 | b23 file $02F4B9 | LDA #$04
$B4AB | b23 file $02F4BB | STA $04a8
$B4AE | b23 file $02F4BE | LDA #$00
$B4B0 | b23 file $02F4C0 | STA $04a9
$B4B3 | b23 file $02F4C3 | LDA #$00
$B4B5 | b23 file $02F4C5 | JMP $f28b
$B4B8 | b23 file $02F4C8 | CMP #$02
$B4BA | b23 file $02F4CA | BNE $b4de
$B4BC | b23 file $02F4CC | LDA #$03
$B4BE | b23 file $02F4CE | STA $04bd
$B4C1 | b23 file $02F4D1 | LDA #$00
$B4C3 | b23 file $02F4D3 | STA $04be
$B4C6 | b23 file $02F4D6 | LDA #$11
$B4C8 | b23 file $02F4D8 | STA $04a8
$B4CB | b23 file $02F4DB | LDA #$00
$B4CD | b23 file $02F4DD | STA $04a9
$B4D0 | b23 file $02F4E0 | LDY $04aa
$B4D3 | b23 file $02F4E3 | LDA $04ad,Y
$B4D6 | b23 file $02F4E6 | STA $042c
$B4D9 | b23 file $02F4E9 | LDA #$21
$B4DB | b23 file $02F4EB | JMP $f28b
$B4DE | b23 file $02F4EE | CMP #$03
$B4E0 | b23 file $02F4F0 | BNE $b4fa
$B4E2 | b23 file $02F4F2 | JSR $d262
$B4E5 | b23 file $02F4F5 | BCC $b4eb
$B4E7 | b23 file $02F4F7 | DEC $04a9
$B4EA | b23 file $02F4FA | RTS
$B4EB | b23 file $02F4FB | LDA #$06
$B4ED | b23 file $02F4FD | STA $04a8
$B4F0 | b23 file $02F500 | LDA #$00
$B4F2 | b23 file $02F502 | STA $04a9
$B4F5 | b23 file $02F505 | LDA #$00
$B4F7 | b23 file $02F507 | JMP $f28b
$B4FA | b23 file $02F50A | CMP #$05
$B4FC | b23 file $02F50C | BNE $b512
$B4FE | b23 file $02F50E | LDA #$05
$B500 | b23 file $02F510 | STA $04a8
$B503 | b23 file $02F513 | LDA #$00
$B505 | b23 file $02F515 | STA $04a9
$B508 | b23 file $02F518 | LDA $04aa
$B50B | b23 file $02F51B | STA $04be
$B50E | b23 file $02F51E | STA $04bf
$B511 | b23 file $02F521 | RTS
$B512 | b23 file $02F522 | CMP #$06
$B514 | b23 file $02F524 | BNE $b538
$B516 | b23 file $02F526 | LDA #$03
$B518 | b23 file $02F528 | STA $04bd
$B51B | b23 file $02F52B | LDA #$00
$B51D | b23 file $02F52D | STA $04be
$B520 | b23 file $02F530 | LDA #$12
$B522 | b23 file $02F532 | STA $04a8
$B525 | b23 file $02F535 | LDA #$00
$B527 | b23 file $02F537 | STA $04a9
$B52A | b23 file $02F53A | LDY $04aa
$B52D | b23 file $02F53D | LDA $04ad,Y
$B530 | b23 file $02F540 | STA $042c
$B533 | b23 file $02F543 | LDA #$24
$B535 | b23 file $02F545 | JMP $f28b
$B538 | b23 file $02F548 | CMP #$07
$B53A | b23 file $02F54A | BNE $b547
$B53C | b23 file $02F54C | LDA #$07
$B53E | b23 file $02F54E | STA $04a8
$B541 | b23 file $02F551 | LDA #$00
$B543 | b23 file $02F553 | STA $04a9
$B546 | b23 file $02F556 | RTS
$B547 | b23 file $02F557 | LDA #$08
$B549 | b23 file $02F559 | STA $04a8
$B54C | b23 file $02F55C | LDA #$00
$B54E | b23 file $02F55E | STA $04a9
$B551 | b23 file $02F561 | RTS
$B552 | b23 file $02F562 | JSR $d166
$B555 | b23 file $02F565 | JSR $d299
$B558 | b23 file $02F568 | BCC $b568
$B55A | b23 file $02F56A | INC $04a9
$B55D | b23 file $02F56D | LDA #$00
$B55F | b23 file $02F56F | STA $0424
$B562 | b23 file $02F572 | STA $0425
$B565 | b23 file $02F575 | JMP $d17c
$B568 | b23 file $02F578 | RTS
$B569 | b23 file $02F579 | JSR $d166
$B56C | b23 file $02F57C | LDA #$bb
$B56E | b23 file $02F57E | STA $0010
$B571 | b23 file $02F581 | LDA #$b5
$B573 | b23 file $02F583 | STA $0011
$B576 | b23 file $02F586 | LDA #$00
$B578 | b23 file $02F588 | STA $0012
$B57B | b23 file $02F58B | JSR $ed1e
$B57E | b23 file $02F58E | LDA #$bf
$B580 | b23 file $02F590 | STA $0010
$B583 | b23 file $02F593 | LDA #$b5
$B585 | b23 file $02F595 | STA $0011
$B588 | b23 file $02F598 | LDA #$c3
$B58A | b23 file $02F59A | STA $0000
$B58D | b23 file $02F59D | LDA #$b5
$B58F | b23 file $02F59F | STA $0001
$B592 | b23 file $02F5A2 | LDA $0012
$B595 | b23 file $02F5A5 | JSR $edf5
$B598 | b23 file $02F5A8 | LDA $0081
$B59B | b23 file $02F5AB | LSR A
$B59C | b23 file $02F5AC | BCC $b5ad
$B59E | b23 file $02F5AE | LDA $0012
$B5A1 | b23 file $02F5B1 | CLC
$B5A2 | b23 file $02F5B2 | ADC #$07
$B5A4 | b23 file $02F5B4 | STA $04bf
$B5A7 | b23 file $02F5B7 | LDA #$03
$B5A9 | b23 file $02F5B9 | STA $04a9
$B5AC | b23 file $02F5BC | RTS
$B5AD | b23 file $02F5BD | LSR A
$B5AE | b23 file $02F5BE | BCC $b5ba
$B5B0 | b23 file $02F5C0 | LDA #$01
$B5B2 | b23 file $02F5C2 | STA $04a9
$B5B5 | b23 file $02F5C5 | LDA #$2b
$B5B7 | b23 file $02F5C7 | JMP $f26d
$B5BA | b23 file $02F5CA | RTS
$B5C8 | b23 file $02F5D8 | LDA $04a9
$B5CB | b23 file $02F5DB | JSR $eade ; inline targets: $B5D8,$B626,$B659,$B689,$B719
$B5D8 | b23 file $02F5E8 | LDA $04aa
$B5DB | b23 file $02F5EB | EOR #$01
$B5DD | b23 file $02F5ED | TAY
$B5DE | b23 file $02F5EE | LDA $04b1,Y
$B5E1 | b23 file $02F5F1 | STA $0010
$B5E4 | b23 file $02F5F4 | LDY $04aa
$B5E7 | b23 file $02F5F7 | LDA $04ad,Y
$B5EA | b23 file $02F5FA | JSR $f387
$B5ED | b23 file $02F5FD | LDY #$00
$B5EF | b23 file $02F5FF | LDA ($00),Y
$B5F1 | b23 file $02F601 | LSR A
$B5F2 | b23 file $02F602 | STA $0011
$B5F5 | b23 file $02F605 | LDY $04aa
$B5F8 | b23 file $02F608 | LDA $04b1,Y
$B5FB | b23 file $02F60B | CMP $0011
$B5FE | b23 file $02F60E | BCS $b61f
$B600 | b23 file $02F610 | CMP $0010
$B603 | b23 file $02F613 | BCS $b622
$B605 | b23 file $02F615 | JSR $d262
$B608 | b23 file $02F618 | BCS $b622
$B60A | b23 file $02F61A | JSR $b7b3
$B60D | b23 file $02F61D | CMP $0010
$B610 | b23 file $02F620 | BCS $b622
$B612 | b23 file $02F622 | LDA $0010
$B615 | b23 file $02F625 | BEQ $b622
$B617 | b23 file $02F627 | LDA #$03
$B619 | b23 file $02F629 | STA $04bf
$B61C | b23 file $02F62C | JMP $b7a8
$B61F | b23 file $02F62F | INC $04a9
$B622 | b23 file $02F632 | INC $04a9
$B625 | b23 file $02F635 | RTS
$B626 | b23 file $02F636 | LDA $04aa
$B629 | b23 file $02F639 | EOR #$01
$B62B | b23 file $02F63B | TAY
$B62C | b23 file $02F63C | LDA $04b1,Y
$B62F | b23 file $02F63F | STA $0010
$B632 | b23 file $02F642 | LDY $04aa
$B635 | b23 file $02F645 | LDA $04b1,Y
$B638 | b23 file $02F648 | CLC
$B639 | b23 file $02F649 | ADC #$1e
$B63B | b23 file $02F64B | CMP $0010
$B63E | b23 file $02F64E | BCS $b655
$B640 | b23 file $02F650 | JSR $b7dd
$B643 | b23 file $02F653 | CMP $0010
$B646 | b23 file $02F656 | BCS $b655
$B648 | b23 file $02F658 | LDA $0010
$B64B | b23 file $02F65B | BEQ $b655
$B64D | b23 file $02F65D | LDA #$06
$B64F | b23 file $02F65F | STA $04bf
$B652 | b23 file $02F662 | JMP $b7a8
$B655 | b23 file $02F665 | INC $04a9
$B658 | b23 file $02F668 | RTS
$B659 | b23 file $02F669 | LDY $04aa
$B65C | b23 file $02F66C | LDA $04b1,Y
$B65F | b23 file $02F66F | CMP #$1e
$B661 | b23 file $02F671 | BCS $b685
$B663 | b23 file $02F673 | LDY $04aa
$B666 | b23 file $02F676 | EOR #$01
$B668 | b23 file $02F678 | TAY
$B669 | b23 file $02F679 | LDA $04b1,Y
$B66C | b23 file $02F67C | CMP #$32
$B66E | b23 file $02F67E | BCC $b685
$B670 | b23 file $02F680 | JSR $b816
$B673 | b23 file $02F683 | CMP $0010
$B676 | b23 file $02F686 | BCS $b685
$B678 | b23 file $02F688 | LDA $0010
$B67B | b23 file $02F68B | BEQ $b685
$B67D | b23 file $02F68D | LDA #$02
$B67F | b23 file $02F68F | STA $04bf
$B682 | b23 file $02F692 | JMP $b7a8
$B685 | b23 file $02F695 | INC $04a9
$B688 | b23 file $02F698 | RTS
$B689 | b23 file $02F699 | LDY $04aa
$B68C | b23 file $02F69C | LDA $04b5,Y
$B68F | b23 file $02F69F | AND #$7f
$B691 | b23 file $02F6A1 | BEQ $b696
$B693 | b23 file $02F6A3 | JMP $b715
$B696 | b23 file $02F6A6 | LDA $04ad,Y
$B699 | b23 file $02F6A9 | JSR $f2d7
$B69C | b23 file $02F6AC | LDY #$02
$B69E | b23 file $02F6AE | LDA ($00),Y
$B6A0 | b23 file $02F6B0 | STA $0010
$B6A3 | b23 file $02F6B3 | LDA $04aa
$B6A6 | b23 file $02F6B6 | EOR #$01
$B6A8 | b23 file $02F6B8 | TAY
$B6A9 | b23 file $02F6B9 | LDA $04ad,Y
$B6AC | b23 file $02F6BC | JSR $f2d7
$B6AF | b23 file $02F6BF | LDY #$02
$B6B1 | b23 file $02F6C1 | LDA ($00),Y
$B6B3 | b23 file $02F6C3 | CMP $0010
$B6B6 | b23 file $02F6C6 | BCS $b6cd
$B6B8 | b23 file $02F6C8 | JSR $b851
$B6BB | b23 file $02F6CB | CMP $0010
$B6BE | b23 file $02F6CE | BCS $b6cd
$B6C0 | b23 file $02F6D0 | LDA $0010
$B6C3 | b23 file $02F6D3 | BEQ $b6cd
$B6C5 | b23 file $02F6D5 | LDA #$07
$B6C7 | b23 file $02F6D7 | STA $04bf
$B6CA | b23 file $02F6DA | JMP $b7a8
$B6CD | b23 file $02F6DD | LDY $04aa
$B6D0 | b23 file $02F6E0 | LDA $04ad,Y
$B6D3 | b23 file $02F6E3 | JSR $f2d7
$B6D6 | b23 file $02F6E6 | LDY #$01
$B6D8 | b23 file $02F6E8 | LDA ($00),Y
$B6DA | b23 file $02F6EA | STA $0010
$B6DD | b23 file $02F6ED | LDA $04aa
$B6E0 | b23 file $02F6F0 | EOR #$01
$B6E2 | b23 file $02F6F2 | TAY
$B6E3 | b23 file $02F6F3 | LDA $04ad,Y
$B6E6 | b23 file $02F6F6 | JSR $f2d7
$B6E9 | b23 file $02F6F9 | LDY #$01
$B6EB | b23 file $02F6FB | LDA ($00),Y
$B6ED | b23 file $02F6FD | CMP $0010
$B6F0 | b23 file $02F700 | BCC $b715
$B6F2 | b23 file $02F702 | JSR $b89b
$B6F5 | b23 file $02F705 | CMP $0010
$B6F8 | b23 file $02F708 | BCS $b715
$B6FA | b23 file $02F70A | LDY $04aa
$B6FD | b23 file $02F70D | LDA $04b5,Y
$B700 | b23 file $02F710 | BMI $b715
$B702 | b23 file $02F712 | TYA
$B703 | b23 file $02F713 | EOR #$01
$B705 | b23 file $02F715 | TAY
$B706 | b23 file $02F716 | LDA $04b5,Y
$B709 | b23 file $02F719 | AND #$7f
$B70B | b23 file $02F71B | BNE $b715
$B70D | b23 file $02F71D | LDA #$08
$B70F | b23 file $02F71F | STA $04bf
$B712 | b23 file $02F722 | JMP $b7a8
$B715 | b23 file $02F725 | INC $04a9
$B718 | b23 file $02F728 | RTS
$B719 | b23 file $02F729 | LDX #$00
$B71B | b23 file $02F72B | LDA $04aa
$B71E | b23 file $02F72E | EOR #$01
$B720 | b23 file $02F730 | TAY
$B721 | b23 file $02F731 | LDA $04b1,Y
$B724 | b23 file $02F734 | CMP #$1f
$B726 | b23 file $02F736 | BCC $b730
$B728 | b23 file $02F738 | LDX #$18
$B72A | b23 file $02F73A | CMP #$3d
$B72C | b23 file $02F73C | BCC $b730
$B72E | b23 file $02F73E | LDX #$30
$B730 | b23 file $02F740 | LDY $04aa
$B733 | b23 file $02F743 | LDA $04b1,Y
$B736 | b23 file $02F746 | CMP #$1f
$B738 | b23 file $02F748 | BCC $b74b
$B73A | b23 file $02F74A | TXA
$B73B | b23 file $02F74B | CLC
$B73C | b23 file $02F74C | ADC #$08
$B73E | b23 file $02F74E | TAX
$B73F | b23 file $02F74F | LDA $04b1,Y
$B742 | b23 file $02F752 | CMP #$3d
$B744 | b23 file $02F754 | BCC $b74b
$B746 | b23 file $02F756 | TXA
$B747 | b23 file $02F757 | CLC
$B748 | b23 file $02F758 | ADC #$08
$B74A | b23 file $02F75A | TAX
$B74B | b23 file $02F75B | JSR $e856
$B74E | b23 file $02F75E | STA $0000
$B751 | b23 file $02F761 | TXA
$B752 | b23 file $02F762 | CLC
$B753 | b23 file $02F763 | ADC $0000
$B756 | b23 file $02F766 | TAX
$B757 | b23 file $02F767 | LDA $b760,X
$B75A | b23 file $02F76A | STA $04bf
$B75D | b23 file $02F76D | JMP $b7a8
$B7A8 | b23 file $02F7B8 | LDA #$01
$B7AA | b23 file $02F7BA | STA $04a8
$B7AD | b23 file $02F7BD | LDA #$03
$B7AF | b23 file $02F7BF | STA $04a9
$B7B2 | b23 file $02F7C2 | RTS
$B7B3 | b23 file $02F7C3 | LDY $04aa
$B7B6 | b23 file $02F7C6 | LDA $04b1,Y
$B7B9 | b23 file $02F7C9 | STA $0010
$B7BC | b23 file $02F7CC | LDA $04ad,Y
$B7BF | b23 file $02F7CF | JMP $f2d7
$B7DD | b23 file $02F7ED | LDY $04aa
$B7E0 | b23 file $02F7F0 | LDA $04ad,Y
$B7E3 | b23 file $02F7F3 | JSR $f2d7
$B7E6 | b23 file $02F7F6 | LDY #$01
$B7E8 | b23 file $02F7F8 | LDA ($00),Y
$B7EA | b23 file $02F7FA | STA $0010
$B7ED | b23 file $02F7FD | LDY #$02
$B7EF | b23 file $02F7FF | LDA ($00),Y
$B7F1 | b23 file $02F801 | CMP $0010
$B7F4 | b23 file $02F804 | BCC $b7f9
$B7F6 | b23 file $02F806 | STA $0010
$B7F9 | b23 file $02F809 | LDY $04aa
$B7FC | b23 file $02F80C | LDA $04b1,Y
$B7FF | b23 file $02F80F | CLC
$B800 | b23 file $02F810 | ADC $0010
$B803 | b23 file $02F813 | STA $0010
$B806 | b23 file $02F816 | LDA #$7c
$B808 | b23 file $02F818 | SEC
$B809 | b23 file $02F819 | SBC $0010
$B80C | b23 file $02F81C | BPL $b810
$B80E | b23 file $02F81E | LDA #$00
$B810 | b23 file $02F820 | STA $0010
$B813 | b23 file $02F823 | JMP $e843
$B816 | b23 file $02F826 | LDA $04aa
$B819 | b23 file $02F829 | EOR #$01
$B81B | b23 file $02F82B | TAY
$B81C | b23 file $02F82C | LDA $04ad,Y
$B81F | b23 file $02F82F | JSR $f2d7
$B822 | b23 file $02F832 | LDY #$01
$B824 | b23 file $02F834 | LDA ($00),Y
$B826 | b23 file $02F836 | STA $0010
$B829 | b23 file $02F839 | LDY $04aa
$B82C | b23 file $02F83C | LDA $04ad,Y
$B82F | b23 file $02F83F | JSR $f2d7
$B832 | b23 file $02F842 | LDY #$01
$B834 | b23 file $02F844 | LDA ($00),Y
$B836 | b23 file $02F846 | SEC
$B837 | b23 file $02F847 | SBC $0010
$B83A | b23 file $02F84A | BPL $b83e
$B83C | b23 file $02F84C | LDA #$00
$B83E | b23 file $02F84E | STA $0010
$B841 | b23 file $02F851 | LDA #$32
$B843 | b23 file $02F853 | SEC
$B844 | b23 file $02F854 | SBC $0010
$B847 | b23 file $02F857 | BPL $b84b
$B849 | b23 file $02F859 | LDA #$00
$B84B | b23 file $02F85B | STA $0010
$B84E | b23 file $02F85E | JMP $e843
$B851 | b23 file $02F861 | LDY $04aa
$B854 | b23 file $02F864 | LDA $04ad,Y
$B857 | b23 file $02F867 | JSR $f2d7
$B85A | b23 file $02F86A | LDY #$02
$B85C | b23 file $02F86C | LDA ($00),Y
$B85E | b23 file $02F86E | STA $0010
$B861 | b23 file $02F871 | LDY #$04
$B863 | b23 file $02F873 | LDA ($00),Y
$B865 | b23 file $02F875 | CLC
$B866 | b23 file $02F876 | ADC $0010
$B869 | b23 file $02F879 | STA $0010
$B86C | b23 file $02F87C | LDY #$01
$B86E | b23 file $02F87E | LDA ($00),Y
$B870 | b23 file $02F880 | STA $0011
$B873 | b23 file $02F883 | LDA $04aa
$B876 | b23 file $02F886 | EOR #$01
$B878 | b23 file $02F888 | TAY
$B879 | b23 file $02F889 | LDA $04ad,Y
$B87C | b23 file $02F88C | JSR $f2d7
$B87F | b23 file $02F88F | LDY #$03
$B881 | b23 file $02F891 | LDA ($00),Y
$B883 | b23 file $02F893 | CLC
$B884 | b23 file $02F894 | ADC $0011
$B887 | b23 file $02F897 | STA $0011
$B88A | b23 file $02F89A | LDA $0010
$B88D | b23 file $02F89D | SEC
$B88E | b23 file $02F89E | SBC $0011
$B891 | b23 file $02F8A1 | BPL $b895
$B893 | b23 file $02F8A3 | LDA #$00
$B895 | b23 file $02F8A5 | STA $0010
$B898 | b23 file $02F8A8 | JMP $e843
$B89B | b23 file $02F8AB | LDA $04aa
$B89E | b23 file $02F8AE | EOR #$01
$B8A0 | b23 file $02F8B0 | TAY
$B8A1 | b23 file $02F8B1 | LDA $04ad,Y
$B8A4 | b23 file $02F8B4 | JSR $f2d7
$B8A7 | b23 file $02F8B7 | LDY #$02
$B8A9 | b23 file $02F8B9 | LDA ($00),Y
$B8AB | b23 file $02F8BB | STA $0010
$B8AE | b23 file $02F8BE | LDY #$01
$B8B0 | b23 file $02F8C0 | LDA ($00),Y
$B8B2 | b23 file $02F8C2 | SEC
$B8B3 | b23 file $02F8C3 | SBC $0010
$B8B6 | b23 file $02F8C6 | BCS $b8ba
$B8B8 | b23 file $02F8C8 | LDA #$00
$B8BA | b23 file $02F8CA | CLC
$B8BB | b23 file $02F8CB | ADC #$0a
$B8BD | b23 file $02F8CD | BPL $b8c1
$B8BF | b23 file $02F8CF | LDA #$00
$B8C1 | b23 file $02F8D1 | STA $0010
$B8C4 | b23 file $02F8D4 | JMP $e843
$B8C7 | b23 file $02F8D7 | LDA $04a9
$B8CA | b23 file $02F8DA | JSR $eade ; inline targets: $B8D3,$B9A5,$B9C8
$B8D3 | b23 file $02F8E3 | INC $04a9
$B8D6 | b23 file $02F8E6 | JSR $ba15
$B8D9 | b23 file $02F8E9 | LDY $04aa
$B8DC | b23 file $02F8EC | LDA $04b5,Y
$B8DF | b23 file $02F8EF | AND #$7f
$B8E1 | b23 file $02F8F1 | BEQ $b909
$B8E3 | b23 file $02F8F3 | LDA $0010
$B8E6 | b23 file $02F8F6 | CLC
$B8E7 | b23 file $02F8F7 | ADC #$14
$B8E9 | b23 file $02F8F9 | STA $0010
$B8EC | b23 file $02F8FC | LDA $0001
$B8EF | b23 file $02F8FF | ASL A
$B8F0 | b23 file $02F900 | CLC
$B8F1 | b23 file $02F901 | ADC $0001
$B8F4 | b23 file $02F904 | STA $0002
$B8F7 | b23 file $02F907 | LDA $0002
$B8FA | b23 file $02F90A | CMP #$0a
$B8FC | b23 file $02F90C | BCC $b909
$B8FE | b23 file $02F90E | SBC #$0a
$B900 | b23 file $02F910 | STA $0002
$B903 | b23 file $02F913 | INC $0001
$B906 | b23 file $02F916 | JMP $b8f7
$B909 | b23 file $02F919 | LDA $04bf
$B90C | b23 file $02F91C | BNE $b92b
$B90E | b23 file $02F91E | LDA $0010
$B911 | b23 file $02F921 | CMP #$64
$B913 | b23 file $02F923 | BCC $b918
$B915 | b23 file $02F925 | JMP $b9a0
$B918 | b23 file $02F928 | LDA #$03
$B91A | b23 file $02F92A | STA $0003
$B91D | b23 file $02F92D | LDA #$00
$B91F | b23 file $02F92F | STA $0002
$B922 | b23 file $02F932 | STA $0004
$B925 | b23 file $02F935 | JSR $ea7c
$B928 | b23 file $02F938 | JMP $b96d
$B92B | b23 file $02F93B | CMP #$06
$B92D | b23 file $02F93D | BNE $b962
$B92F | b23 file $02F93F | LDA $0010
$B932 | b23 file $02F942 | CMP #$1e
$B934 | b23 file $02F944 | BCS $b940
$B936 | b23 file $02F946 | LDA $0001
$B939 | b23 file $02F949 | ASL A
$B93A | b23 file $02F94A | STA $0001
$B93D | b23 file $02F94D | JMP $b96d
$B940 | b23 file $02F950 | JSR $e87a
$B943 | b23 file $02F953 | AND #$1f
$B945 | b23 file $02F955 | CMP #$15
$B947 | b23 file $02F957 | BCS $b909
$B949 | b23 file $02F959 | ADC #$0a
$B94B | b23 file $02F95B | STA $0000
$B94E | b23 file $02F95E | LDY $04aa
$B951 | b23 file $02F961 | LDA $04b1,Y
$B954 | b23 file $02F964 | SEC
$B955 | b23 file $02F965 | SBC $0000
$B958 | b23 file $02F968 | BPL $b95c
$B95A | b23 file $02F96A | LDA #$00
$B95C | b23 file $02F96C | STA $04b1,Y
$B95F | b23 file $02F96F | JMP $b9a0
$B962 | b23 file $02F972 | LDY $04aa
$B965 | b23 file $02F975 | LDA $0010
$B968 | b23 file $02F978 | CMP $04c5,Y
$B96B | b23 file $02F97B | BCS $b9a0
$B96D | b23 file $02F97D | LDA $0001
$B970 | b23 file $02F980 | BEQ $b99b
$B972 | b23 file $02F982 | BMI $b99b
$B974 | b23 file $02F984 | LDA $04aa
$B977 | b23 file $02F987 | EOR #$01
$B979 | b23 file $02F989 | TAY
$B97A | b23 file $02F98A | LDA $04b1,Y
$B97D | b23 file $02F98D | SEC
$B97E | b23 file $02F98E | SBC $0001
$B981 | b23 file $02F991 | BCS $b985
$B983 | b23 file $02F993 | LDA #$00
$B985 | b23 file $02F995 | STA $04b1,Y
$B988 | b23 file $02F998 | LDA $0001
$B98B | b23 file $02F99B | STA $042c
$B98E | b23 file $02F99E | LDA #$00
$B990 | b23 file $02F9A0 | STA $042d
$B993 | b23 file $02F9A3 | STA $042e
$B996 | b23 file $02F9A6 | LDA #$22
$B998 | b23 file $02F9A8 | JMP $f28b
$B99B | b23 file $02F9AB | LDA #$39
$B99D | b23 file $02F9AD | JMP $f28b
$B9A0 | b23 file $02F9B0 | LDA #$25
$B9A2 | b23 file $02F9B2 | JMP $f26d
$B9A5 | b23 file $02F9B5 | JSR $d299
$B9A8 | b23 file $02F9B8 | BCC $b9c7
$B9AA | b23 file $02F9BA | JSR $d13d
$B9AD | b23 file $02F9BD | LDA $0081
$B9B0 | b23 file $02F9C0 | AND #$03
$B9B2 | b23 file $02F9C2 | BEQ $b9c7
$B9B4 | b23 file $02F9C4 | JSR $d060
$B9B7 | b23 file $02F9C7 | LDA #$ff
$B9B9 | b23 file $02F9C9 | STA $0380,X
$B9BC | b23 file $02F9CC | INC $04a9
$B9BF | b23 file $02F9CF | LDA $007e
$B9C2 | b23 file $02F9D2 | ORA #$04
$B9C4 | b23 file $02F9D4 | STA $007e
$B9C7 | b23 file $02F9D7 | RTS
$B9C8 | b23 file $02F9D8 | LDA $007e
$B9CB | b23 file $02F9DB | AND #$04
$B9CD | b23 file $02F9DD | BNE $b9ec
$B9CF | b23 file $02F9DF | LDY $04aa
$B9D2 | b23 file $02F9E2 | LDA $04b1,Y
$B9D5 | b23 file $02F9E5 | BEQ $b9ed
$B9D7 | b23 file $02F9E7 | LDA $04aa
$B9DA | b23 file $02F9EA | EOR #$01
$B9DC | b23 file $02F9EC | TAY
$B9DD | b23 file $02F9ED | LDA $04b1,Y
$B9E0 | b23 file $02F9F0 | BEQ $b9ed
$B9E2 | b23 file $02F9F2 | LDA #$01
$B9E4 | b23 file $02F9F4 | STA $04a8
$B9E7 | b23 file $02F9F7 | LDA #$00
$B9E9 | b23 file $02F9F9 | STA $04a9
$B9EC | b23 file $02F9FC | RTS
$B9ED | b23 file $02F9FD | STY $04aa
$B9F0 | b23 file $02FA00 | LDA $04ad,Y
$B9F3 | b23 file $02FA03 | STA $042c
$B9F6 | b23 file $02FA06 | CPY #$01
$B9F8 | b23 file $02FA08 | BNE $b9fc
$B9FA | b23 file $02FA0A | LDY #$02
$B9FC | b23 file $02FA0C | LDA #$02
$B9FE | b23 file $02FA0E | STA $0515,Y
$BA01 | b23 file $02FA11 | TYA
$BA02 | b23 file $02FA12 | EOR #$02
$BA04 | b23 file $02FA14 | TAY
$BA05 | b23 file $02FA15 | LDA #$00
$BA07 | b23 file $02FA17 | STA $0515,Y
$BA0A | b23 file $02FA1A | LDA #$0d
$BA0C | b23 file $02FA1C | STA $04a8
$BA0F | b23 file $02FA1F | LDA #$00
$BA11 | b23 file $02FA21 | STA $04a9
$BA14 | b23 file $02FA24 | RTS
$BA15 | b23 file $02FA25 | JSR $e843
$BA18 | b23 file $02FA28 | STA $0010
$BA1B | b23 file $02FA2B | LDY #$00
$BA1D | b23 file $02FA2D | LDX $04aa
$BA20 | b23 file $02FA30 | LDA $04ad,X
$BA23 | b23 file $02FA33 | CMP $0560
$BA26 | b23 file $02FA36 | BEQ $ba2a
$BA28 | b23 file $02FA38 | LDY #$01
$BA2A | b23 file $02FA3A | LDA $04c1,Y
$BA2D | b23 file $02FA3D | STA $0001
$BA30 | b23 file $02FA40 | LDA $0570,Y
$BA33 | b23 file $02FA43 | CLC
$BA34 | b23 file $02FA44 | ADC $0001
$BA37 | b23 file $02FA47 | LSR A
$BA38 | b23 file $02FA48 | STA $0001
$BA3B | b23 file $02FA4B | TYA
$BA3C | b23 file $02FA4C | EOR #$01
$BA3E | b23 file $02FA4E | TAY
$BA3F | b23 file $02FA4F | LDA $056e,Y
$BA42 | b23 file $02FA52 | STA $0002
$BA45 | b23 file $02FA55 | LDA $0001
$BA48 | b23 file $02FA58 | SEC
$BA49 | b23 file $02FA59 | SBC $0002
$BA4C | b23 file $02FA5C | STA $0001
$BA4F | b23 file $02FA5F | JSR $e87a
$BA52 | b23 file $02FA62 | AND #$0f
$BA54 | b23 file $02FA64 | CMP #$0b
$BA56 | b23 file $02FA66 | BCS $ba4f
$BA58 | b23 file $02FA68 | SEC
$BA59 | b23 file $02FA69 | SBC #$05
$BA5B | b23 file $02FA6B | STA $0002
$BA5E | b23 file $02FA6E | LDA $0001
$BA61 | b23 file $02FA71 | CLC
$BA62 | b23 file $02FA72 | ADC $0002
$BA65 | b23 file $02FA75 | BPL $ba69
$BA67 | b23 file $02FA77 | LDA #$00
$BA69 | b23 file $02FA79 | STA $0001
$BA6C | b23 file $02FA7C | RTS
$BA6D | b23 file $02FA7D | LDA $04a9
$BA70 | b23 file $02FA80 | JSR $eade ; inline targets: $BA87,$BAA5,$BAC0,$BADA,$BB03,$BB41,$BB5B,$BB93,$BBC0,$BC00
$BA87 | b23 file $02FA97 | JSR $d299
$BA8A | b23 file $02FA9A | BCC $baa4
$BA8C | b23 file $02FA9C | INC $04a9
$BA8F | b23 file $02FA9F | LDY $04aa
$BA92 | b23 file $02FAA2 | LDA $04ad,Y
$BA95 | b23 file $02FAA5 | STA $0000
$BA98 | b23 file $02FAA8 | LDY #$3d
$BA9A | b23 file $02FAAA | JSR $ee07 ; inline far target $A030
$BA9F | b23 file $02FAAF | LDA #$29
$BAA1 | b23 file $02FAB1 | JMP $f26d
$BAA4 | b23 file $02FAB4 | RTS
$BAA5 | b23 file $02FAB5 | JSR $d166
$BAA8 | b23 file $02FAB8 | JSR $d299
$BAAB | b23 file $02FABB | BCC $babf
$BAAD | b23 file $02FABD | JSR $d13d
$BAB0 | b23 file $02FAC0 | LDA $0081
$BAB3 | b23 file $02FAC3 | AND #$03
$BAB5 | b23 file $02FAC5 | BEQ $babf
$BAB7 | b23 file $02FAC7 | INC $04a9
$BABA | b23 file $02FACA | LDA #$00
$BABC | b23 file $02FACC | JMP $f28b
$BABF | b23 file $02FACF | RTS
$BAC0 | b23 file $02FAD0 | JSR $d299
$BAC3 | b23 file $02FAD3 | BCC $bad9
$BAC5 | b23 file $02FAD5 | LDA #$04
$BAC7 | b23 file $02FAD7 | STA $04bd
$BACA | b23 file $02FADA | LDA #$03
$BACC | b23 file $02FADC | STA $04be
$BACF | b23 file $02FADF | LDA #$14
$BAD1 | b23 file $02FAE1 | STA $04a8
$BAD4 | b23 file $02FAE4 | LDA #$00
$BAD6 | b23 file $02FAE6 | STA $04a9
$BAD9 | b23 file $02FAE9 | RTS
$BADA | b23 file $02FAEA | JSR $d299
$BADD | b23 file $02FAED | BCC $bb02
$BADF | b23 file $02FAEF | LDA $04aa
$BAE2 | b23 file $02FAF2 | EOR #$01
$BAE4 | b23 file $02FAF4 | STA $04aa
$BAE7 | b23 file $02FAF7 | TAY
$BAE8 | b23 file $02FAF8 | LDA $04ad,Y
$BAEB | b23 file $02FAFB | STA $0000
$BAEE | b23 file $02FAFE | LDY #$3d
$BAF0 | b23 file $02FB00 | JSR $ee07 ; inline far target $A030
$BAF5 | b23 file $02FB05 | LDA #$02
$BAF7 | b23 file $02FB07 | STA $00a4
$BAFA | b23 file $02FB0A | INC $04a9
$BAFD | b23 file $02FB0D | LDA #$2a
$BAFF | b23 file $02FB0F | JMP $f26d
$BB02 | b23 file $02FB12 | RTS
$BB03 | b23 file $02FB13 | LDA $04aa
$BB06 | b23 file $02FB16 | JSR $d166
$BB09 | b23 file $02FB19 | JSR $d299
$BB0C | b23 file $02FB1C | BCC $bb40
$BB0E | b23 file $02FB1E | JSR $d13d
$BB11 | b23 file $02FB21 | LDA $0081
$BB14 | b23 file $02FB24 | AND #$03
$BB16 | b23 file $02FB26 | BEQ $bb40
$BB18 | b23 file $02FB28 | LDA $04aa
$BB1B | b23 file $02FB2B | EOR #$01
$BB1D | b23 file $02FB2D | TAY
$BB1E | b23 file $02FB2E | LDA $04b3,Y
$BB21 | b23 file $02FB31 | ASL A
$BB22 | b23 file $02FB32 | CLC
$BB23 | b23 file $02FB33 | STA $0011
$BB26 | b23 file $02FB36 | JSR $e843
$BB29 | b23 file $02FB39 | CMP $0011
$BB2C | b23 file $02FB3C | BCS $bb38
$BB2E | b23 file $02FB3E | LDA #$09
$BB30 | b23 file $02FB40 | STA $04a9
$BB33 | b23 file $02FB43 | LDA #$3c
$BB35 | b23 file $02FB45 | JMP $f26d
$BB38 | b23 file $02FB48 | INC $04a9
$BB3B | b23 file $02FB4B | LDA #$00
$BB3D | b23 file $02FB4D | JMP $f28b
$BB40 | b23 file $02FB50 | RTS
$BB41 | b23 file $02FB51 | JSR $d299
$BB44 | b23 file $02FB54 | BCC $bb5a
$BB46 | b23 file $02FB56 | LDA #$04
$BB48 | b23 file $02FB58 | STA $04bd
$BB4B | b23 file $02FB5B | LDA #$06
$BB4D | b23 file $02FB5D | STA $04be
$BB50 | b23 file $02FB60 | LDA #$15
$BB52 | b23 file $02FB62 | STA $04a8
$BB55 | b23 file $02FB65 | LDA #$00
$BB57 | b23 file $02FB67 | STA $04a9
$BB5A | b23 file $02FB6A | RTS
$BB5B | b23 file $02FB6B | LDA #$0a
$BB5D | b23 file $02FB6D | JSR $e862
$BB60 | b23 file $02FB70 | CLC
$BB61 | b23 file $02FB71 | ADC #$05
$BB63 | b23 file $02FB73 | STA $042f
$BB66 | b23 file $02FB76 | LDA #$00
$BB68 | b23 file $02FB78 | STA $0430
$BB6B | b23 file $02FB7B | STA $0431
$BB6E | b23 file $02FB7E | LDA $04aa
$BB71 | b23 file $02FB81 | EOR #$01
$BB73 | b23 file $02FB83 | TAY
$BB74 | b23 file $02FB84 | LDA $04ad,Y
$BB77 | b23 file $02FB87 | STA $042c
$BB7A | b23 file $02FB8A | JSR $f2d7
$BB7D | b23 file $02FB8D | LDY #$00
$BB7F | b23 file $02FB8F | LDA ($00),Y
$BB81 | b23 file $02FB91 | SEC
$BB82 | b23 file $02FB92 | SBC $042f
$BB85 | b23 file $02FB95 | BPL $bb89
$BB87 | b23 file $02FB97 | LDA #$00
$BB89 | b23 file $02FB99 | STA ($00),Y
$BB8B | b23 file $02FB9B | INC $04a9
$BB8E | b23 file $02FB9E | LDA #$3d
$BB90 | b23 file $02FBA0 | JMP $f28b
$BB93 | b23 file $02FBA3 | JSR $d299
$BB96 | b23 file $02FBA6 | BCC $bbbf
$BB98 | b23 file $02FBA8 | JSR $d13d
$BB9B | b23 file $02FBAB | LDA $0081
$BB9E | b23 file $02FBAE | AND #$03
$BBA0 | b23 file $02FBB0 | BEQ $bbbf
$BBA2 | b23 file $02FBB2 | LDA $04aa
$BBA5 | b23 file $02FBB5 | EOR #$01
$BBA7 | b23 file $02FBB7 | TAY
$BBA8 | b23 file $02FBB8 | LDA $04ad,Y
$BBAB | b23 file $02FBBB | JSR $f2d7
$BBAE | b23 file $02FBBE | LDY #$00
$BBB0 | b23 file $02FBC0 | LDA ($00),Y
$BBB2 | b23 file $02FBC2 | BEQ $bbb7
$BBB4 | b23 file $02FBC4 | JMP $bc16
$BBB7 | b23 file $02FBC7 | INC $04a9
$BBBA | b23 file $02FBCA | LDA #$26
$BBBC | b23 file $02FBCC | JMP $f28b
$BBBF | b23 file $02FBCF | RTS
$BBC0 | b23 file $02FBD0 | JSR $d299
$BBC3 | b23 file $02FBD3 | BCC $bbcf
$BBC5 | b23 file $02FBD5 | JSR $d13d
$BBC8 | b23 file $02FBD8 | LDA $0081
$BBCB | b23 file $02FBDB | AND #$03
$BBCD | b23 file $02FBDD | BNE $bbd0
$BBCF | b23 file $02FBDF | RTS
$BBD0 | b23 file $02FBE0 | LDA $04aa
$BBD3 | b23 file $02FBE3 | EOR #$01
$BBD5 | b23 file $02FBE5 | TAY
$BBD6 | b23 file $02FBE6 | LDA $04ad,Y
$BBD9 | b23 file $02FBE9 | STA $042c
$BBDC | b23 file $02FBEC | CPY #$01
$BBDE | b23 file $02FBEE | BNE $bbe2
$BBE0 | b23 file $02FBF0 | LDY #$02
$BBE2 | b23 file $02FBF2 | LDA #$02
$BBE4 | b23 file $02FBF4 | STA $0515,Y
$BBE7 | b23 file $02FBF7 | TYA
$BBE8 | b23 file $02FBF8 | EOR #$02
$BBEA | b23 file $02FBFA | TAY
$BBEB | b23 file $02FBFB | LDA #$00
$BBED | b23 file $02FBFD | STA $0515,Y
$BBF0 | b23 file $02FC00 | LDA #$0e
$BBF2 | b23 file $02FC02 | STA $04a8
$BBF5 | b23 file $02FC05 | LDA #$00
$BBF7 | b23 file $02FC07 | STA $04a9
$BBFA | b23 file $02FC0A | LDA #$ff
$BBFC | b23 file $02FC0C | STA $04c0
$BBFF | b23 file $02FC0F | RTS
$BC00 | b23 file $02FC10 | LDA $04aa
$BC03 | b23 file $02FC13 | JSR $d166
$BC06 | b23 file $02FC16 | JSR $d299
$BC09 | b23 file $02FC19 | BCC $bc15
$BC0B | b23 file $02FC1B | JSR $d13d
$BC0E | b23 file $02FC1E | LDA $0081
$BC11 | b23 file $02FC21 | AND #$03
$BC13 | b23 file $02FC23 | BNE $bc16
$BC15 | b23 file $02FC25 | RTS
$BC16 | b23 file $02FC26 | LDA $04aa
$BC19 | b23 file $02FC29 | EOR #$01
$BC1B | b23 file $02FC2B | STA $04aa
$BC1E | b23 file $02FC2E | BEQ $bc22
$BC20 | b23 file $02FC30 | LDY #$02
$BC22 | b23 file $02FC32 | LDA #$01
$BC24 | b23 file $02FC34 | STA $0515,Y
$BC27 | b23 file $02FC37 | TYA
$BC28 | b23 file $02FC38 | EOR #$02
$BC2A | b23 file $02FC3A | TAY
$BC2B | b23 file $02FC3B | LDA #$00
$BC2D | b23 file $02FC3D | STA $0515,Y
$BC30 | b23 file $02FC40 | LDA #$0f
$BC32 | b23 file $02FC42 | STA $04a8
$BC35 | b23 file $02FC45 | LDA #$00
$BC37 | b23 file $02FC47 | STA $04a9
$BC3A | b23 file $02FC4A | RTS
$BC3B | b23 file $02FC4B | LDA $04a9
$BC3E | b23 file $02FC4E | JSR $eade ; inline targets: $BC47,$BC5C,$BC8C
$BC47 | b23 file $02FC57 | INC $04a9
$BC4A | b23 file $02FC5A | LDA #$00
$BC4C | b23 file $02FC5C | STA $040c
$BC4F | b23 file $02FC5F | STA $040d
$BC52 | b23 file $02FC62 | LDY $04be
$BC55 | b23 file $02FC65 | LDA $04ad,Y
$BC58 | b23 file $02FC68 | STA $0410
$BC5B | b23 file $02FC6B | RTS
$BC5C | b23 file $02FC6C | LDA $04be
$BC5F | b23 file $02FC6F | STA $04aa
$BC62 | b23 file $02FC72 | JSR $d166
$BC65 | b23 file $02FC75 | LDA $04bf
$BC68 | b23 file $02FC78 | STA $04aa
$BC6B | b23 file $02FC7B | LDY #$39
$BC6D | b23 file $02FC7D | JSR $ee07 ; inline far target $A012
$BC72 | b23 file $02FC82 | LDA $040d
$BC75 | b23 file $02FC85 | CMP #$ff
$BC77 | b23 file $02FC87 | BNE $bc8b
$BC79 | b23 file $02FC89 | LDA #$06
$BC7B | b23 file $02FC8B | STA $00bb
$BC7E | b23 file $02FC8E | INC $04a9
$BC81 | b23 file $02FC91 | LDA #$00
$BC83 | b23 file $02FC93 | STA $0098
$BC86 | b23 file $02FC96 | LDA #$01
$BC88 | b23 file $02FC98 | STA $0097
$BC8B | b23 file $02FC9B | RTS
$BC8C | b23 file $02FC9C | LDA $04be
$BC8F | b23 file $02FC9F | STA $04aa
$BC92 | b23 file $02FCA2 | JSR $d166
$BC95 | b23 file $02FCA5 | LDA $04bf
$BC98 | b23 file $02FCA8 | STA $04aa
$BC9B | b23 file $02FCAB | LDA $040d
$BC9E | b23 file $02FCAE | BPL $bcbe
$BCA0 | b23 file $02FCB0 | LDA $0081
$BCA3 | b23 file $02FCB3 | STA $0010
$BCA6 | b23 file $02FCB6 | AND #$02
$BCA8 | b23 file $02FCB8 | BNE $bcbf
$BCAA | b23 file $02FCBA | LDA $0010
$BCAD | b23 file $02FCBD | AND #$30
$BCAF | b23 file $02FCBF | BEQ $bcbe
$BCB1 | b23 file $02FCC1 | LDA $04be
$BCB4 | b23 file $02FCC4 | EOR #$01
$BCB6 | b23 file $02FCC6 | STA $04be
$BCB9 | b23 file $02FCC9 | LDA #$00
$BCBB | b23 file $02FCCB | STA $04a9
$BCBE | b23 file $02FCCE | RTS
$BCBF | b23 file $02FCCF | LDA #$01
$BCC1 | b23 file $02FCD1 | STA $04a8
$BCC4 | b23 file $02FCD4 | LDA #$02
$BCC6 | b23 file $02FCD6 | STA $04a9
$BCC9 | b23 file $02FCD9 | LDA $04bf
$BCCC | b23 file $02FCDC | STA $04aa
$BCCF | b23 file $02FCDF | LDA #$09
$BCD1 | b23 file $02FCE1 | STA $00bb
$BCD4 | b23 file $02FCE4 | LDA #$06
$BCD6 | b23 file $02FCE6 | STA $00bc
$BCD9 | b23 file $02FCE9 | LDA #$0c
$BCDB | b23 file $02FCEB | STA $00bd
$BCDE | b23 file $02FCEE | LDA #$00
$BCE0 | b23 file $02FCF0 | STA $0097
$BCE3 | b23 file $02FCF3 | LDA #$a0
$BCE5 | b23 file $02FCF5 | STA $0098
$BCE8 | b23 file $02FCF8 | RTS
$BCE9 | b23 file $02FCF9 | LDA $04a9
$BCEC | b23 file $02FCFC | JSR $eade ; inline targets: $BCFB,$BD1E,$BD40,$BD5D,$BDA9,$BE3F
$BCFB | b23 file $02FD0B | JSR $d299
$BCFE | b23 file $02FD0E | BCC $bd1d
$BD00 | b23 file $02FD10 | INC $04a9
$BD03 | b23 file $02FD13 | LDY $04aa
$BD06 | b23 file $02FD16 | LDA $04ad,Y
$BD09 | b23 file $02FD19 | STA $0000
$BD0C | b23 file $02FD1C | LDY #$3d
$BD0E | b23 file $02FD1E | JSR $ee07 ; inline far target $A030
$BD13 | b23 file $02FD23 | LDA #$04
$BD15 | b23 file $02FD25 | STA $00a4
$BD18 | b23 file $02FD28 | LDA #$27
$BD1A | b23 file $02FD2A | JMP $f26d
$BD1D | b23 file $02FD2D | RTS
$BD1E | b23 file $02FD2E | JSR $d166
$BD21 | b23 file $02FD31 | JSR $d299
$BD24 | b23 file $02FD34 | BCC $bd5c
$BD26 | b23 file $02FD36 | JSR $d13d
$BD29 | b23 file $02FD39 | LDA $0081
$BD2C | b23 file $02FD3C | AND #$03
$BD2E | b23 file $02FD3E | BEQ $bd5c
$BD30 | b23 file $02FD40 | INC $04a9
$BD33 | b23 file $02FD43 | JSR $e57f
$BD36 | b23 file $02FD46 | LDA #$6c
$BD38 | b23 file $02FD48 | JSR $e683
$BD3B | b23 file $02FD4B | LDA #$00
$BD3D | b23 file $02FD4D | JMP $f28b
$BD40 | b23 file $02FD50 | JSR $d299
$BD43 | b23 file $02FD53 | BCC $bd5c
$BD45 | b23 file $02FD55 | INC $04a9
$BD48 | b23 file $02FD58 | LDA #$43
$BD4A | b23 file $02FD5A | STA $0000
$BD4D | b23 file $02FD5D | LDY $04aa
$BD50 | b23 file $02FD60 | BEQ $bd57
$BD52 | b23 file $02FD62 | LDA #$55
$BD54 | b23 file $02FD64 | STA $0000
$BD57 | b23 file $02FD67 | LDA #$00
$BD59 | b23 file $02FD69 | JMP $cdfd
$BD5C | b23 file $02FD6C | RTS
$BD5D | b23 file $02FD6D | LDA #$98
$BD5F | b23 file $02FD6F | STA $00c6
$BD62 | b23 file $02FD72 | STA $00ce
$BD65 | b23 file $02FD75 | STA $00d6
$BD68 | b23 file $02FD78 | LDA #$99
$BD6A | b23 file $02FD7A | STA $00c7
$BD6D | b23 file $02FD7D | STA $00cf
$BD70 | b23 file $02FD80 | STA $00d7
$BD73 | b23 file $02FD83 | LDA #$02
$BD75 | b23 file $02FD85 | STA $00c8
$BD78 | b23 file $02FD88 | STA $00d0
$BD7B | b23 file $02FD8B | STA $00d8
$BD7E | b23 file $02FD8E | LDA #$00
$BD80 | b23 file $02FD90 | STA $04b8
$BD83 | b23 file $02FD93 | LDA #$5f
$BD85 | b23 file $02FD95 | STA $04ba
$BD88 | b23 file $02FD98 | INC $04a9
$BD8B | b23 file $02FD9B | LDA #$18
$BD8D | b23 file $02FD9D | STA $04bb
$BD90 | b23 file $02FDA0 | LDA #$e3
$BD92 | b23 file $02FDA2 | STA $0000
$BD95 | b23 file $02FDA5 | LDY $04aa
$BD98 | b23 file $02FDA8 | BEQ $bda4
$BD9A | b23 file $02FDAA | LDA #$a8
$BD9C | b23 file $02FDAC | STA $04bb
$BD9F | b23 file $02FDAF | LDA #$f5
$BDA1 | b23 file $02FDB1 | STA $0000
$BDA4 | b23 file $02FDB4 | LDA #$00
$BDA6 | b23 file $02FDB6 | JMP $cdfd
$BDA9 | b23 file $02FDB9 | INC $04b8
$BDAC | b23 file $02FDBC | LDA $04b8
$BDAF | b23 file $02FDBF | LSR A
$BDB0 | b23 file $02FDC0 | LSR A
$BDB1 | b23 file $02FDC1 | LSR A
$BDB2 | b23 file $02FDC2 | LSR A
$BDB3 | b23 file $02FDC3 | LSR A
$BDB4 | b23 file $02FDC4 | AND #$07
$BDB6 | b23 file $02FDC6 | CMP #$05
$BDB8 | b23 file $02FDC8 | BNE $bdcb
$BDBA | b23 file $02FDCA | INC $04a9
$BDBD | b23 file $02FDCD | LDY $04aa
$BDC0 | b23 file $02FDD0 | LDA $04ad,Y
$BDC3 | b23 file $02FDD3 | STA $042c
$BDC6 | b23 file $02FDD6 | LDA #$28
$BDC8 | b23 file $02FDD8 | JMP $f28b
$BDCB | b23 file $02FDDB | STA $0010
$BDCE | b23 file $02FDDE | STA $0011
$BDD1 | b23 file $02FDE1 | LDA $04aa
$BDD4 | b23 file $02FDE4 | BNE $bddf
$BDD6 | b23 file $02FDE6 | LDA $0010
$BDD9 | b23 file $02FDE9 | CLC
$BDDA | b23 file $02FDEA | ADC #$1a
$BDDC | b23 file $02FDEC | STA $0010
$BDDF | b23 file $02FDEF | LDA #$00
$BDE1 | b23 file $02FDF1 | STA $0002
$BDE4 | b23 file $02FDF4 | LDA $0010
$BDE7 | b23 file $02FDF7 | CLC
$BDE8 | b23 file $02FDF8 | ADC #$a8
$BDEA | b23 file $02FDFA | JSR $cea5
$BDED | b23 file $02FDFD | LDA $04aa
$BDF0 | b23 file $02FE00 | CLC
$BDF1 | b23 file $02FE01 | ADC #$01
$BDF3 | b23 file $02FE03 | STA $0002
$BDF6 | b23 file $02FE06 | LDY $04aa
$BDF9 | b23 file $02FE09 | LDA $04af,Y
$BDFC | b23 file $02FE0C | STA $0000
$BDFF | b23 file $02FE0F | ASL A
$BE00 | b23 file $02FE10 | ASL A
$BE01 | b23 file $02FE11 | CLC
$BE02 | b23 file $02FE12 | ADC $0000
$BE05 | b23 file $02FE15 | ADC $0010
$BE08 | b23 file $02FE18 | ADC #$ad
$BE0A | b23 file $02FE1A | JSR $cea5
$BE0D | b23 file $02FE1D | LDA $0010
$BE10 | b23 file $02FE20 | SEC
$BE11 | b23 file $02FE21 | SBC $0011
$BE14 | b23 file $02FE24 | STA $0010
$BE17 | b23 file $02FE27 | LDA #$00
$BE19 | b23 file $02FE29 | STA $0002
$BE1C | b23 file $02FE2C | LDA $0011
$BE1F | b23 file $02FE2F | CMP #$02
$BE21 | b23 file $02FE31 | BCC $be3e
$BE23 | b23 file $02FE33 | LDY #$bc
$BE25 | b23 file $02FE35 | CMP #$02
$BE27 | b23 file $02FE37 | BEQ $be2b
$BE29 | b23 file $02FE39 | LDY #$bf
$BE2B | b23 file $02FE3B | STY $0000
$BE2E | b23 file $02FE3E | LDY $04aa
$BE31 | b23 file $02FE41 | LDA $04af,Y
$BE34 | b23 file $02FE44 | CLC
$BE35 | b23 file $02FE45 | ADC $0010
$BE38 | b23 file $02FE48 | ADC $0000
$BE3B | b23 file $02FE4B | JMP $cea5
$BE3E | b23 file $02FE4E | RTS
$BE3F | b23 file $02FE4F | LDA #$04
$BE41 | b23 file $02FE51 | JSR $bdcb
$BE44 | b23 file $02FE54 | JSR $d299
$BE47 | b23 file $02FE57 | BCC $be77
$BE49 | b23 file $02FE59 | JSR $d13d
$BE4C | b23 file $02FE5C | LDA $0081
$BE4F | b23 file $02FE5F | AND #$03
$BE51 | b23 file $02FE61 | BEQ $be77
$BE53 | b23 file $02FE63 | LDY $04aa
$BE56 | b23 file $02FE66 | BEQ $be5a
$BE58 | b23 file $02FE68 | LDY #$02
$BE5A | b23 file $02FE6A | LDA #$03
$BE5C | b23 file $02FE6C | STA $0515,Y
$BE5F | b23 file $02FE6F | TYA
$BE60 | b23 file $02FE70 | EOR #$02
$BE62 | b23 file $02FE72 | TAY
$BE63 | b23 file $02FE73 | LDA #$00
$BE65 | b23 file $02FE75 | STA $0515,Y
$BE68 | b23 file $02FE78 | LDA #$80
$BE6A | b23 file $02FE7A | STA $04c0
$BE6D | b23 file $02FE7D | LDA #$0e
$BE6F | b23 file $02FE7F | STA $04a8
$BE72 | b23 file $02FE82 | LDA #$00
$BE74 | b23 file $02FE84 | STA $04a9
$BE77 | b23 file $02FE87 | RTS
$BE78 | b23 file $02FE88 | LDA $04a9
$BE7B | b23 file $02FE8B | JSR $eade ; inline targets: $BE86,$BF43,$BF66,$BF7E
$BE86 | b23 file $02FE96 | LDA $04aa
$BE89 | b23 file $02FE99 | EOR #$01
$BE8B | b23 file $02FE9B | TAY
$BE8C | b23 file $02FE9C | LDA $04ad,Y
$BE8F | b23 file $02FE9F | JSR $f2d7
$BE92 | b23 file $02FEA2 | LDY #$03
$BE94 | b23 file $02FEA4 | LDA ($00),Y
$BE96 | b23 file $02FEA6 | STA $0010
$BE99 | b23 file $02FEA9 | LDY #$00
$BE9B | b23 file $02FEAB | LDA ($00),Y
$BE9D | b23 file $02FEAD | STA $0011
$BEA0 | b23 file $02FEB0 | LDY $04aa
$BEA3 | b23 file $02FEB3 | LDA $04ad,Y
$BEA6 | b23 file $02FEB6 | JSR $f2d7
$BEA9 | b23 file $02FEB9 | LDY #$02
$BEAB | b23 file $02FEBB | LDA ($00),Y
$BEAD | b23 file $02FEBD | STA $0012
$BEB0 | b23 file $02FEC0 | LDY #$04
$BEB2 | b23 file $02FEC2 | LDA ($00),Y
$BEB4 | b23 file $02FEC4 | CLC
$BEB5 | b23 file $02FEC5 | ADC $0012
$BEB8 | b23 file $02FEC8 | STA $0012
$BEBB | b23 file $02FECB | LDX #$00
$BEBD | b23 file $02FECD | LDA $0010
$BEC0 | b23 file $02FED0 | CMP #$50
$BEC2 | b23 file $02FED2 | BCS $bed5
$BEC4 | b23 file $02FED4 | TXA
$BEC5 | b23 file $02FED5 | CLC
$BEC6 | b23 file $02FED6 | ADC #$18
$BEC8 | b23 file $02FED8 | TAX
$BEC9 | b23 file $02FED9 | LDA $0010
$BECC | b23 file $02FEDC | CMP #$32
$BECE | b23 file $02FEDE | BCS $bed5
$BED0 | b23 file $02FEE0 | TXA
$BED1 | b23 file $02FEE1 | CLC
$BED2 | b23 file $02FEE2 | ADC #$18
$BED4 | b23 file $02FEE4 | TAX
$BED5 | b23 file $02FEE5 | LDA $0011
$BED8 | b23 file $02FEE8 | CMP #$50
$BEDA | b23 file $02FEEA | BCS $beed
$BEDC | b23 file $02FEEC | TXA
$BEDD | b23 file $02FEED | CLC
$BEDE | b23 file $02FEEE | ADC #$08
$BEE0 | b23 file $02FEF0 | TAX
$BEE1 | b23 file $02FEF1 | LDA $0011
$BEE4 | b23 file $02FEF4 | CMP #$32
$BEE6 | b23 file $02FEF6 | BCS $beed
$BEE8 | b23 file $02FEF8 | TXA
$BEE9 | b23 file $02FEF9 | CLC
$BEEA | b23 file $02FEFA | ADC #$08
$BEEC | b23 file $02FEFC | TAX
$BEED | b23 file $02FEFD | LDA $0012
$BEF0 | b23 file $02FF00 | CMP #$b4
$BEF2 | b23 file $02FF02 | BCS $bf05
$BEF4 | b23 file $02FF04 | TXA
$BEF5 | b23 file $02FF05 | CLC
$BEF6 | b23 file $02FF06 | ADC #$48
$BEF8 | b23 file $02FF08 | TAX
$BEF9 | b23 file $02FF09 | LDA $0012
$BEFC | b23 file $02FF0C | CMP #$82
$BEFE | b23 file $02FF0E | BCS $bf05
$BF00 | b23 file $02FF10 | TXA
$BF01 | b23 file $02FF11 | CLC
$BF02 | b23 file $02FF12 | ADC #$48
$BF04 | b23 file $02FF14 | TAX
$BF05 | b23 file $02FF15 | JSR $e856
$BF08 | b23 file $02FF18 | STA $0010
$BF0B | b23 file $02FF1B | TXA
$BF0C | b23 file $02FF1C | CLC
$BF0D | b23 file $02FF1D | ADC $0010
$BF10 | b23 file $02FF20 | TAX
$BF11 | b23 file $02FF21 | LDA $bfb2,X
$BF14 | b23 file $02FF24 | STA $04bf
$BF17 | b23 file $02FF27 | CLC
$BF18 | b23 file $02FF28 | ADC #$33
$BF1A | b23 file $02FF2A | STA $04be
$BF1D | b23 file $02FF2D | LDA $04bf
$BF20 | b23 file $02FF30 | CLC
$BF21 | b23 file $02FF31 | ADC #$2f
$BF23 | b23 file $02FF33 | STA $04bd
$BF26 | b23 file $02FF36 | LDA $04bf
$BF29 | b23 file $02FF39 | CMP #$03
$BF2B | b23 file $02FF3B | BCS $bf38
$BF2D | b23 file $02FF3D | LDA $04aa
$BF30 | b23 file $02FF40 | EOR #$01
$BF32 | b23 file $02FF42 | TAY
$BF33 | b23 file $02FF43 | LDA #$02
$BF35 | b23 file $02FF45 | STA $04c3,Y
$BF38 | b23 file $02FF48 | LDA #$09
$BF3A | b23 file $02FF4A | STA $04a8
$BF3D | b23 file $02FF4D | LDA #$00
$BF3F | b23 file $02FF4F | STA $04a9
$BF42 | b23 file $02FF52 | RTS
$BF43 | b23 file $02FF53 | LDA $04aa
$BF46 | b23 file $02FF56 | EOR #$01
$BF48 | b23 file $02FF58 | TAY
$BF49 | b23 file $02FF59 | BEQ $bf4d
$BF4B | b23 file $02FF5B | LDY #$02
$BF4D | b23 file $02FF5D | LDA #$01
$BF4F | b23 file $02FF5F | STA $0515,Y
$BF52 | b23 file $02FF62 | TYA
$BF53 | b23 file $02FF63 | EOR #$02
$BF55 | b23 file $02FF65 | TAY
$BF56 | b23 file $02FF66 | LDA #$00
$BF58 | b23 file $02FF68 | STA $0515,Y
$BF5B | b23 file $02FF6B | LDA #$0f
$BF5D | b23 file $02FF6D | STA $04a8
$BF60 | b23 file $02FF70 | LDA #$00
$BF62 | b23 file $02FF72 | STA $04a9
$BF65 | b23 file $02FF75 | RTS
$BF66 | b23 file $02FF76 | LDA #$00
$BF68 | b23 file $02FF78 | STA $0515
$BF6B | b23 file $02FF7B | STA $0517
$BF6E | b23 file $02FF7E | LDA #$0e
$BF70 | b23 file $02FF80 | STA $04a8
$BF73 | b23 file $02FF83 | LDA #$00
$BF75 | b23 file $02FF85 | STA $04a9
$BF78 | b23 file $02FF88 | LDA #$ff
$BF7A | b23 file $02FF8A | STA $04c0
$BF7D | b23 file $02FF8D | RTS
$BF7E | b23 file $02FF8E | JSR $d299
$BF81 | b23 file $02FF91 | BCC $bfb1
$BF83 | b23 file $02FF93 | JSR $d13d
$BF86 | b23 file $02FF96 | LDA $0081
$BF89 | b23 file $02FF99 | AND #$03
$BF8B | b23 file $02FF9B | BEQ $bfb1
$BF8D | b23 file $02FF9D | LDY $04aa
$BF90 | b23 file $02FFA0 | BEQ $bf94
$BF92 | b23 file $02FFA2 | LDY #$02
$BF94 | b23 file $02FFA4 | LDA #$00
$BF96 | b23 file $02FFA6 | STA $0515,Y
$BF99 | b23 file $02FFA9 | TYA
$BF9A | b23 file $02FFAA | EOR #$02
$BF9C | b23 file $02FFAC | TAY
$BF9D | b23 file $02FFAD | LDA #$04
$BF9F | b23 file $02FFAF | STA $0515,Y
$BFA2 | b23 file $02FFB2 | LDA #$0e
$BFA4 | b23 file $02FFB4 | STA $04a8
$BFA7 | b23 file $02FFB7 | LDA #$00
$BFA9 | b23 file $02FFB9 | STA $04a9
$BFAC | b23 file $02FFBC | LDA #$ff
$BFAE | b23 file $02FFBE | STA $04c0
$BFB1 | b23 file $02FFC1 | RTS
$C08A | b24 file $03009A | LDY $04aa
$C08D | b24 file $03009D | LDA #$80
$C08F | b24 file $03009F | STA $04b5,Y
$C092 | b24 file $0300A2 | TYA
$C093 | b24 file $0300A3 | EOR #$01
$C095 | b24 file $0300A5 | TAY
$C096 | b24 file $0300A6 | LDA $04ad,Y
$C099 | b24 file $0300A9 | JSR $f2d7
$C09C | b24 file $0300AC | LDY #$02
$C09E | b24 file $0300AE | LDA ($00),Y
$C0A0 | b24 file $0300B0 | STA $0011
$C0A3 | b24 file $0300B3 | LDY $04aa
$C0A6 | b24 file $0300B6 | LDA $04ad,Y
$C0A9 | b24 file $0300B9 | JSR $f2d7
$C0AC | b24 file $0300BC | LDY #$02
$C0AE | b24 file $0300BE | LDA ($00),Y
$C0B0 | b24 file $0300C0 | STA $0010
$C0B3 | b24 file $0300C3 | LDY #$04
$C0B5 | b24 file $0300C5 | LDA ($00),Y
$C0B7 | b24 file $0300C7 | CLC
$C0B8 | b24 file $0300C8 | ADC $0010
$C0BB | b24 file $0300CB | SEC
$C0BC | b24 file $0300CC | SBC $0011
$C0BF | b24 file $0300CF | BCS $c0c3
$C0C1 | b24 file $0300D1 | LDA #$00
$C0C3 | b24 file $0300D3 | STA $0010
$C0C6 | b24 file $0300D6 | INC $0010
$C0C9 | b24 file $0300D9 | JSR $e85c
$C0CC | b24 file $0300DC | CMP #$0a
$C0CE | b24 file $0300DE | BCS $c0c9
$C0D0 | b24 file $0300E0 | ADC $0010
$C0D3 | b24 file $0300E3 | CMP #$6e
$C0D5 | b24 file $0300E5 | BCS $c0df
$C0D7 | b24 file $0300E7 | LDA #$2f
$C0D9 | b24 file $0300E9 | STA $04be
$C0DC | b24 file $0300EC | JMP $c103
$C0DF | b24 file $0300EF | JSR $e850
$C0E2 | b24 file $0300F2 | STA $0010
$C0E5 | b24 file $0300F5 | BEQ $c0df
$C0E7 | b24 file $0300F7 | INC $0010
$C0EA | b24 file $0300FA | INC $0010
$C0ED | b24 file $0300FD | LDA $04aa
$C0F0 | b24 file $030100 | EOR #$01
$C0F2 | b24 file $030102 | TAY
$C0F3 | b24 file $030103 | LDA $0010
$C0F6 | b24 file $030106 | STA $04b5,Y
$C0F9 | b24 file $030109 | LDA #$02
$C0FB | b24 file $03010B | STA $04c3,Y
$C0FE | b24 file $03010E | LDA #$2e
$C100 | b24 file $030110 | STA $04be
$C103 | b24 file $030113 | LDA #$2d
$C105 | b24 file $030115 | STA $04bd
$C108 | b24 file $030118 | LDA #$09
$C10A | b24 file $03011A | STA $04a8
$C10D | b24 file $03011D | LDA #$00
$C10F | b24 file $03011F | STA $04a9
$C112 | b24 file $030122 | STA $04bf
$C115 | b24 file $030125 | RTS
$C116 | b24 file $030126 | LDA $04a9
$C119 | b24 file $030129 | JSR $eade ; inline targets: $C124,$C13A,$C14A,$C187
$C124 | b24 file $030134 | JSR $d299
$C127 | b24 file $030137 | BCC $c139
$C129 | b24 file $030139 | INC $04a9
$C12C | b24 file $03013C | LDA $04ad
$C12F | b24 file $03013F | STA $0000
$C132 | b24 file $030142 | LDY #$3d
$C134 | b24 file $030144 | JSR $ee07 ; inline far target $A030
$C139 | b24 file $030149 | RTS
$C13A | b24 file $03014A | INC $04a9
$C13D | b24 file $03014D | LDY #$3d
$C13F | b24 file $03014F | JSR $ee07 ; inline far target $A033
$C144 | b24 file $030154 | LDA $04bd
$C147 | b24 file $030157 | JMP $d283
$C14A | b24 file $03015A | LDY $04aa
$C14D | b24 file $03015D | LDA $04c3,Y
$C150 | b24 file $030160 | STA $0010,Y
$C153 | b24 file $030163 | TYA
$C154 | b24 file $030164 | EOR #$01
$C156 | b24 file $030166 | TAY
$C157 | b24 file $030167 | LDA #$80
$C159 | b24 file $030169 | STA $0010,Y
$C15C | b24 file $03016C | JSR $c1e2
$C15F | b24 file $03016F | JSR $d299
$C162 | b24 file $030172 | BCC $c186
$C164 | b24 file $030174 | JSR $d13d
$C167 | b24 file $030177 | LDA $0081
$C16A | b24 file $03017A | AND #$03
$C16C | b24 file $03017C | BEQ $c186
$C16E | b24 file $03017E | INC $04a9
$C171 | b24 file $030181 | LDA $04aa
$C174 | b24 file $030184 | EOR #$01
$C176 | b24 file $030186 | STA $04aa
$C179 | b24 file $030189 | TAY
$C17A | b24 file $03018A | LDA $04ad,Y
$C17D | b24 file $03018D | STA $042c
$C180 | b24 file $030190 | LDA $04be
$C183 | b24 file $030193 | JMP $d283
$C186 | b24 file $030196 | RTS
$C187 | b24 file $030197 | LDY $04aa
$C18A | b24 file $03019A | LDA $04c3,Y
$C18D | b24 file $03019D | STA $0010,Y
$C190 | b24 file $0301A0 | TYA
$C191 | b24 file $0301A1 | EOR #$01
$C193 | b24 file $0301A3 | TAY
$C194 | b24 file $0301A4 | LDA #$80
$C196 | b24 file $0301A6 | STA $0010,Y
$C199 | b24 file $0301A9 | JSR $c1e2
$C19C | b24 file $0301AC | JSR $d299
$C19F | b24 file $0301AF | BCC $c1e1
$C1A1 | b24 file $0301B1 | JSR $d13d
$C1A4 | b24 file $0301B4 | LDA $0081
$C1A7 | b24 file $0301B7 | AND #$03
$C1A9 | b24 file $0301B9 | BEQ $c1e1
$C1AB | b24 file $0301BB | LDA $04aa
$C1AE | b24 file $0301BE | EOR #$01
$C1B0 | b24 file $0301C0 | STA $04aa
$C1B3 | b24 file $0301C3 | LDA $04bf
$C1B6 | b24 file $0301C6 | CMP #$02
$C1B8 | b24 file $0301C8 | BCC $c1d1
$C1BA | b24 file $0301CA | STA $04a9
$C1BD | b24 file $0301CD | DEC $04a9
$C1C0 | b24 file $0301D0 | LDA #$07
$C1C2 | b24 file $0301D2 | STA $04a8
$C1C5 | b24 file $0301D5 | LDA $04bf
$C1C8 | b24 file $0301D8 | CMP #$04
$C1CA | b24 file $0301DA | BNE $c1e1
$C1CC | b24 file $0301DC | LDA #$38
$C1CE | b24 file $0301DE | JMP $f28b
$C1D1 | b24 file $0301E1 | LDA #$01
$C1D3 | b24 file $0301E3 | STA $04a8
$C1D6 | b24 file $0301E6 | LDA #$00
$C1D8 | b24 file $0301E8 | STA $04a9
$C1DB | b24 file $0301EB | STA $04c3
$C1DE | b24 file $0301EE | STA $04c4
$C1E1 | b24 file $0301F1 | RTS
$C1E2 | b24 file $0301F2 | LDA #$a5
$C1E4 | b24 file $0301F4 | STA $000a
$C1E7 | b24 file $0301F7 | LDX #$00
$C1E9 | b24 file $0301F9 | LDA $04ad
$C1EC | b24 file $0301FC | STA $0000
$C1EF | b24 file $0301FF | LDA $0010
$C1F2 | b24 file $030202 | STA $00a4
$C1F5 | b24 file $030205 | LDY #$39
$C1F7 | b24 file $030207 | JSR $ee07 ; inline far target $A000
$C1FC | b24 file $03020C | LDX #$01
$C1FE | b24 file $03020E | LDA #$c8
$C200 | b24 file $030210 | STA $04bc
$C203 | b24 file $030213 | LDA $04ae
$C206 | b24 file $030216 | STA $0000
$C209 | b24 file $030219 | LDA $0011
$C20C | b24 file $03021C | STA $00a4
$C20F | b24 file $03021F | LDY #$39
$C211 | b24 file $030221 | JSR $ee07 ; inline far target $A000
$C216 | b24 file $030226 | LDA #$00
$C218 | b24 file $030228 | STA $04bc
$C21B | b24 file $03022B | RTS
$C21C | b24 file $03022C | LDA $04a9
$C21F | b24 file $03022F | JSR $eade ; inline targets: $C22A,$C256,$C28E,$C2AA
$C22A | b24 file $03023A | JSR $e57f
$C22D | b24 file $03023D | LDA #$71
$C22F | b24 file $03023F | JSR $e683
$C232 | b24 file $030242 | LDA #$91
$C234 | b24 file $030244 | STA $00cc
$C237 | b24 file $030247 | STA $00d4
$C23A | b24 file $03024A | STA $00dc
$C23D | b24 file $03024D | INC $04a9
$C240 | b24 file $030250 | LDA #$43
$C242 | b24 file $030252 | STA $0000
$C245 | b24 file $030255 | LDA #$13
$C247 | b24 file $030257 | LDY $04aa
$C24A | b24 file $03025A | BEQ $c253
$C24C | b24 file $03025C | LDA #$55
$C24E | b24 file $03025E | STA $0000
$C251 | b24 file $030261 | LDA #$15
$C253 | b24 file $030263 | JMP $cdfd
$C256 | b24 file $030266 | LDA #$90
$C258 | b24 file $030268 | STA $00c6
$C25B | b24 file $03026B | STA $00ce
$C25E | b24 file $03026E | STA $00d6
$C261 | b24 file $030271 | LDA #$00
$C263 | b24 file $030273 | STA $04b8
$C266 | b24 file $030276 | LDA #$4f
$C268 | b24 file $030278 | STA $04ba
$C26B | b24 file $03027B | INC $04a9
$C26E | b24 file $03027E | LDA #$18
$C270 | b24 file $030280 | STA $04bb
$C273 | b24 file $030283 | LDA #$e3
$C275 | b24 file $030285 | STA $0000
$C278 | b24 file $030288 | LDA #$14
$C27A | b24 file $03028A | LDY $04aa
$C27D | b24 file $03028D | BEQ $c28b
$C27F | b24 file $03028F | LDA #$a8
$C281 | b24 file $030291 | STA $04bb
$C284 | b24 file $030294 | LDA #$f5
$C286 | b24 file $030296 | STA $0000
$C289 | b24 file $030299 | LDA #$16
$C28B | b24 file $03029B | JMP $cdfd
$C28E | b24 file $03029E | INC $04b8
$C291 | b24 file $0302A1 | LDA $04b8
$C294 | b24 file $0302A4 | ROL A
$C295 | b24 file $0302A5 | ROL A
$C296 | b24 file $0302A6 | ROL A
$C297 | b24 file $0302A7 | AND #$03
$C299 | b24 file $0302A9 | CMP #$02
$C29B | b24 file $0302AB | BNE $c2cc
$C29D | b24 file $0302AD | LDA #$01
$C29F | b24 file $0302AF | JSR $c2cc
$C2A2 | b24 file $0302B2 | INC $04a9
$C2A5 | b24 file $0302B5 | LDA #$26
$C2A7 | b24 file $0302B7 | JMP $f28b
$C2AA | b24 file $0302BA | LDA #$01
$C2AC | b24 file $0302BC | JSR $c2cc
$C2AF | b24 file $0302BF | JSR $d299
$C2B2 | b24 file $0302C2 | BCC $c2cb
$C2B4 | b24 file $0302C4 | JSR $d13d
$C2B7 | b24 file $0302C7 | LDA $0081
$C2BA | b24 file $0302CA | AND #$03
$C2BC | b24 file $0302CC | BEQ $c2cb
$C2BE | b24 file $0302CE | LDA #$0e
$C2C0 | b24 file $0302D0 | STA $04a8
$C2C3 | b24 file $0302D3 | LDA #$00
$C2C5 | b24 file $0302D5 | STA $04a9
$C2C8 | b24 file $0302D8 | STA $04c0
$C2CB | b24 file $0302DB | RTS
$C2CC | b24 file $0302DC | STA $0010
$C2CF | b24 file $0302DF | LDA $04aa
$C2D2 | b24 file $0302E2 | BEQ $c2dd
$C2D4 | b24 file $0302E4 | LDA $0010
$C2D7 | b24 file $0302E7 | CLC
$C2D8 | b24 file $0302E8 | ADC #$06
$C2DA | b24 file $0302EA | STA $0010
$C2DD | b24 file $0302ED | LDA $04aa
$C2E0 | b24 file $0302F0 | CLC
$C2E1 | b24 file $0302F1 | ADC #$01
$C2E3 | b24 file $0302F3 | STA $0002
$C2E6 | b24 file $0302F6 | LDY $04aa
$C2E9 | b24 file $0302F9 | LDA $04af,Y
$C2EC | b24 file $0302FC | ASL A
$C2ED | b24 file $0302FD | CLC
$C2EE | b24 file $0302FE | ADC $0010
$C2F1 | b24 file $030301 | ADC #$6a
$C2F3 | b24 file $030303 | JMP $cea5
$C2F6 | b24 file $030306 | LDA $04c0
$C2F9 | b24 file $030309 | BMI $c300
$C2FB | b24 file $03030B | LDA #$01
$C2FD | b24 file $03030D | JSR $c2cc
$C300 | b24 file $030310 | LDA $04a9
$C303 | b24 file $030313 | JSR $eade ; inline targets: $C30E,$C33B,$C35D,$C44F
$C30E | b24 file $03031E | LDA $04ad
$C311 | b24 file $030321 | STA $0514
$C314 | b24 file $030324 | LDA $04ae
$C317 | b24 file $030327 | STA $0516
$C31A | b24 file $03032A | LDY #$00
$C31C | b24 file $03032C | LDA $0515
$C31F | b24 file $03032F | CMP #$02
$C321 | b24 file $030331 | BEQ $c332
$C323 | b24 file $030333 | LDY #$02
$C325 | b24 file $030335 | LDA $0517
$C328 | b24 file $030338 | CMP #$02
$C32A | b24 file $03033A | BEQ $c332
$C32C | b24 file $03033C | INC $04a9
$C32F | b24 file $03033F | JMP $ecee
$C332 | b24 file $030342 | STY $04bd
$C335 | b24 file $030345 | LDA #$02
$C337 | b24 file $030347 | STA $04a9
$C33A | b24 file $03034A | RTS
$C33B | b24 file $03034B | LDA $0087
$C33E | b24 file $03034E | BPL $c35c
$C340 | b24 file $030350 | LDA #$0b
$C342 | b24 file $030352 | STA $0500
$C345 | b24 file $030355 | LDA #$00
$C347 | b24 file $030357 | STA $0501
$C34A | b24 file $03035A | LDA $050f
$C34D | b24 file $03035D | CMP #$03
$C34F | b24 file $03035F | BEQ $c354
$C351 | b24 file $030361 | STA $6f44
$C354 | b24 file $030364 | LDA #$03
$C356 | b24 file $030366 | STA $007a
$C359 | b24 file $030369 | JMP $ecbf
$C35C | b24 file $03036C | RTS
$C35D | b24 file $03036D | LDX $04bd
$C360 | b24 file $030370 | LDA $0514,X
$C363 | b24 file $030373 | CMP #$83
$C365 | b24 file $030375 | BNE $c36a
$C367 | b24 file $030377 | JMP $c3aa
$C36A | b24 file $03037A | CMP #$ad
$C36C | b24 file $03037C | BNE $c371
$C36E | b24 file $03037E | JMP $c3c0
$C371 | b24 file $030381 | CMP #$b6
$C373 | b24 file $030383 | BNE $c378
$C375 | b24 file $030385 | JMP $c401
$C378 | b24 file $030388 | CMP #$de
$C37A | b24 file $03038A | BNE $c37f
$C37C | b24 file $03038C | JMP $c42e
$C37F | b24 file $03038F | LDA $6fe1
$C382 | b24 file $030392 | AND #$01
$C384 | b24 file $030394 | BNE $c3a4
$C386 | b24 file $030396 | LDA #$00
$C388 | b24 file $030398 | STA $0010
$C38B | b24 file $03039B | JSR $f368
$C38E | b24 file $03039E | LDY #$00
$C390 | b24 file $0303A0 | LDA ($00),Y
$C392 | b24 file $0303A2 | CMP $0514,X
$C395 | b24 file $0303A5 | BNE $c39a
$C397 | b24 file $0303A7 | JMP $c3e3
$C39A | b24 file $0303AA | INC $0010
$C39D | b24 file $0303AD | LDA $0010
$C3A0 | b24 file $0303B0 | CMP #$07
$C3A2 | b24 file $0303B2 | BCC $c38b
$C3A4 | b24 file $0303B4 | LDA #$01
$C3A6 | b24 file $0303B6 | STA $04a9
$C3A9 | b24 file $0303B9 | RTS
$C3AA | b24 file $0303BA | LDA #$64
$C3AC | b24 file $0303BC | JSR $e862
$C3AF | b24 file $0303BF | CMP #$1e
$C3B1 | b24 file $0303C1 | BCS $c3a4
$C3B3 | b24 file $0303C3 | LDA #$06
$C3B5 | b24 file $0303C5 | STA $0010
$C3B8 | b24 file $0303C8 | LDA #$3f
$C3BA | b24 file $0303CA | STA $0011
$C3BD | b24 file $0303CD | JMP $c40b
$C3C0 | b24 file $0303D0 | LDA $04bd
$C3C3 | b24 file $0303D3 | EOR #$02
$C3C5 | b24 file $0303D5 | TAX
$C3C6 | b24 file $0303D6 | LDA $0514,X
$C3C9 | b24 file $0303D9 | JSR $f2d7
$C3CC | b24 file $0303DC | LDY #$0b
$C3CE | b24 file $0303DE | LDA ($00),Y
$C3D0 | b24 file $0303E0 | AND #$f0
$C3D2 | b24 file $0303E2 | CMP #$20
$C3D4 | b24 file $0303E4 | BCS $c3a4
$C3D6 | b24 file $0303E6 | LDA #$07
$C3D8 | b24 file $0303E8 | STA $0010
$C3DB | b24 file $0303EB | LDA #$40
$C3DD | b24 file $0303ED | STA $0011
$C3E0 | b24 file $0303F0 | JMP $c40b
$C3E3 | b24 file $0303F3 | LDA #$64
$C3E5 | b24 file $0303F5 | JSR $e862
$C3E8 | b24 file $0303F8 | CMP #$32
$C3EA | b24 file $0303FA | BCS $c3a4
$C3EC | b24 file $0303FC | LDA $6fe1
$C3EF | b24 file $0303FF | ORA #$01
$C3F1 | b24 file $030401 | STA $6fe1
$C3F4 | b24 file $030404 | LDA #$0e
$C3F6 | b24 file $030406 | STA $0010
$C3F9 | b24 file $030409 | LDA #$41
$C3FB | b24 file $03040B | STA $0011
$C3FE | b24 file $03040E | JMP $c40b
$C401 | b24 file $030411 | LDA #$05
$C403 | b24 file $030413 | STA $0010
$C406 | b24 file $030416 | LDA #$3e
$C408 | b24 file $030418 | STA $0011
$C40B | b24 file $03041B | LDA $04bd
$C40E | b24 file $03041E | EOR #$02
$C410 | b24 file $030420 | TAX
$C411 | b24 file $030421 | LDA $0514,X
$C414 | b24 file $030424 | STA $042c
$C417 | b24 file $030427 | JSR $f2d7
$C41A | b24 file $03042A | LDY #$0a
$C41C | b24 file $03042C | LDA ($00),Y
$C41E | b24 file $03042E | AND #$e0
$C420 | b24 file $030430 | ORA $0010
$C423 | b24 file $030433 | STA ($00),Y
$C425 | b24 file $030435 | INC $04a9
$C428 | b24 file $030438 | LDA $0011
$C42B | b24 file $03043B | JMP $f28b
$C42E | b24 file $03043E | LDA $04bd
$C431 | b24 file $030441 | EOR #$02
$C433 | b24 file $030443 | TAX
$C434 | b24 file $030444 | LDA $0514,X
$C437 | b24 file $030447 | STA $042c
$C43A | b24 file $03044A | JSR $f2d7
$C43D | b24 file $03044D | LDY #$0a
$C43F | b24 file $03044F | LDA ($00),Y
$C441 | b24 file $030451 | AND #$1f
$C443 | b24 file $030453 | ORA #$e0
$C445 | b24 file $030455 | STA ($00),Y
$C447 | b24 file $030457 | INC $04a9
$C44A | b24 file $03045A | LDA #$42
$C44C | b24 file $03045C | JMP $f28b
$C44F | b24 file $03045F | JSR $d299
$C452 | b24 file $030462 | BCC $c463
$C454 | b24 file $030464 | JSR $d13d
$C457 | b24 file $030467 | LDA $0081
$C45A | b24 file $03046A | AND #$03
$C45C | b24 file $03046C | BEQ $c463
$C45E | b24 file $03046E | LDA #$01
$C460 | b24 file $030470 | STA $04a9
$C463 | b24 file $030473 | RTS
$C464 | b24 file $030474 | LDA $04a9
$C467 | b24 file $030477 | JSR $eade ; inline targets: $C46E,$C480
$C46E | b24 file $03047E | LDA $04ad
$C471 | b24 file $030481 | STA $0514
$C474 | b24 file $030484 | LDA $04ae
$C477 | b24 file $030487 | STA $0516
$C47A | b24 file $03048A | INC $04a9
$C47D | b24 file $03048D | JMP $ecee
$C480 | b24 file $030490 | LDA $0087
$C483 | b24 file $030493 | BPL $c497
$C485 | b24 file $030495 | LDA $050f
$C488 | b24 file $030498 | CMP #$03
$C48A | b24 file $03049A | BEQ $c48f
$C48C | b24 file $03049C | STA $6f44
$C48F | b24 file $03049F | LDA #$05
$C491 | b24 file $0304A1 | STA $007a
$C494 | b24 file $0304A4 | JMP $ecbf
$C497 | b24 file $0304A7 | RTS
$C498 | b24 file $0304A8 | LDA $04a9
$C49B | b24 file $0304AB | JSR $eade ; inline targets: $C4AC,$C4C3,$C4E9,$C55A,$C598,$C5D2,$C66B
$C4AC | b24 file $0304BC | INC $04a9
$C4AF | b24 file $0304BF | LDA #$43
$C4B1 | b24 file $0304C1 | STA $0000
$C4B4 | b24 file $0304C4 | LDA $04aa
$C4B7 | b24 file $0304C7 | BEQ $c4be
$C4B9 | b24 file $0304C9 | LDA #$55
$C4BB | b24 file $0304CB | STA $0000
$C4BE | b24 file $0304CE | LDA #$00
$C4C0 | b24 file $0304D0 | JMP $cdfd
$C4C3 | b24 file $0304D3 | LDA #$00
$C4C5 | b24 file $0304D5 | STA $04b8
$C4C8 | b24 file $0304D8 | INC $04a9
$C4CB | b24 file $0304DB | LDA #$18
$C4CD | b24 file $0304DD | STA $04bb
$C4D0 | b24 file $0304E0 | LDA #$e3
$C4D2 | b24 file $0304E2 | STA $0000
$C4D5 | b24 file $0304E5 | LDA $04aa
$C4D8 | b24 file $0304E8 | BEQ $c4e4
$C4DA | b24 file $0304EA | LDA #$a8
$C4DC | b24 file $0304EC | STA $04bb
$C4DF | b24 file $0304EF | LDA #$f5
$C4E1 | b24 file $0304F1 | STA $0000
$C4E4 | b24 file $0304F4 | LDA #$00
$C4E6 | b24 file $0304F6 | JMP $cdfd
$C4E9 | b24 file $0304F9 | LDA $04aa
$C4EC | b24 file $0304FC | BEQ $c4f8
$C4EE | b24 file $0304FE | LDA $04bb
$C4F1 | b24 file $030501 | CMP #$58
$C4F3 | b24 file $030503 | BEQ $c513
$C4F5 | b24 file $030505 | JMP $c4ff
$C4F8 | b24 file $030508 | LDA $04bb
$C4FB | b24 file $03050B | CMP #$68
$C4FD | b24 file $03050D | BEQ $c513
$C4FF | b24 file $03050F | LDA $04aa
$C502 | b24 file $030512 | STA $0011
$C505 | b24 file $030515 | BEQ $c50d
$C507 | b24 file $030517 | DEC $04bb
$C50A | b24 file $03051A | JMP $cee1
$C50D | b24 file $03051D | INC $04bb
$C510 | b24 file $030520 | JMP $cee1
$C513 | b24 file $030523 | INC $04a9
$C516 | b24 file $030526 | LDA $04aa
$C519 | b24 file $030529 | BEQ $c525
$C51B | b24 file $03052B | LDA #$4b
$C51D | b24 file $03052D | STA $0000
$C520 | b24 file $030530 | LDA #$18
$C522 | b24 file $030532 | JMP $c52c
$C525 | b24 file $030535 | LDA #$4d
$C527 | b24 file $030537 | STA $0000
$C52A | b24 file $03053A | LDA #$17
$C52C | b24 file $03053C | JSR $cdfd
$C52F | b24 file $03053F | LDA #$02
$C531 | b24 file $030541 | STA $03b7
$C534 | b24 file $030544 | LDA #$23
$C536 | b24 file $030546 | STA $03b8
$C539 | b24 file $030549 | LDA #$db
$C53B | b24 file $03054B | STA $03b9
$C53E | b24 file $03054E | LDA $04aa
$C541 | b24 file $030551 | ASL A
$C542 | b24 file $030552 | TAY
$C543 | b24 file $030553 | LDA $c556,Y
$C546 | b24 file $030556 | STA $03ba
$C549 | b24 file $030559 | INY
$C54A | b24 file $03055A | LDA $c556,Y
$C54D | b24 file $03055D | STA $03bb
$C550 | b24 file $030560 | LDA #$ff
$C552 | b24 file $030562 | STA $03bc
$C555 | b24 file $030565 | RTS
$C55A | b24 file $03056A | LDA #$92
$C55C | b24 file $03056C | STA $00c7
$C55F | b24 file $03056F | STA $00cf
$C562 | b24 file $030572 | STA $00d7
$C565 | b24 file $030575 | LDA #$84
$C567 | b24 file $030577 | STA $00c8
$C56A | b24 file $03057A | STA $00d0
$C56D | b24 file $03057D | STA $00d8
$C570 | b24 file $030580 | LDA #$ff
$C572 | b24 file $030582 | STA $04b8
$C575 | b24 file $030585 | LDA #$00
$C577 | b24 file $030587 | STA $04b9
$C57A | b24 file $03058A | LDA #$4f
$C57C | b24 file $03058C | STA $04ba
$C57F | b24 file $03058F | INC $04a9
$C582 | b24 file $030592 | LDA #$ed
$C584 | b24 file $030594 | STA $0000
$C587 | b24 file $030597 | LDA #$04
$C589 | b24 file $030599 | LDY $04aa
$C58C | b24 file $03059C | BEQ $c595
$C58E | b24 file $03059E | LDA #$eb
$C590 | b24 file $0305A0 | STA $0000
$C593 | b24 file $0305A3 | LDA #$08
$C595 | b24 file $0305A5 | JMP $cdfd
$C598 | b24 file $0305A8 | LDA #$90
$C59A | b24 file $0305AA | STA $00cc
$C59D | b24 file $0305AD | STA $00d4
$C5A0 | b24 file $0305B0 | STA $00dc
$C5A3 | b24 file $0305B3 | INC $04a9
$C5A6 | b24 file $0305B6 | LDA $04aa
$C5A9 | b24 file $0305B9 | EOR #$01
$C5AB | b24 file $0305BB | TAY
$C5AC | b24 file $0305BC | LDA $04af,Y
$C5AF | b24 file $0305BF | STA $0001
$C5B2 | b24 file $0305C2 | CPY #$01
$C5B4 | b24 file $0305C4 | BEQ $c5c4
$C5B6 | b24 file $0305C6 | LDA #$43
$C5B8 | b24 file $0305C8 | STA $0000
$C5BB | b24 file $0305CB | LDA #$0d
$C5BD | b24 file $0305CD | CLC
$C5BE | b24 file $0305CE | ADC $0001
$C5C1 | b24 file $0305D1 | JMP $cdfd
$C5C4 | b24 file $0305D4 | LDA #$55
$C5C6 | b24 file $0305D6 | STA $0000
$C5C9 | b24 file $0305D9 | LDA #$10
$C5CB | b24 file $0305DB | CLC
$C5CC | b24 file $0305DC | ADC $0001
$C5CF | b24 file $0305DF | JMP $cdfd
$C5D2 | b24 file $0305E2 | LDA $04b8
$C5D5 | b24 file $0305E5 | LSR A
$C5D6 | b24 file $0305E6 | LSR A
$C5D7 | b24 file $0305E7 | LSR A
$C5D8 | b24 file $0305E8 | LSR A
$C5D9 | b24 file $0305E9 | AND #$01
$C5DB | b24 file $0305EB | STA $0012
$C5DE | b24 file $0305EE | INC $04b8
$C5E1 | b24 file $0305F1 | LDA $04b8
$C5E4 | b24 file $0305F4 | LSR A
$C5E5 | b24 file $0305F5 | LSR A
$C5E6 | b24 file $0305F6 | LSR A
$C5E7 | b24 file $0305F7 | LSR A
$C5E8 | b24 file $0305F8 | AND #$07
$C5EA | b24 file $0305FA | CMP #$05
$C5EC | b24 file $0305FC | BNE $c622
$C5EE | b24 file $0305FE | INC $04a9
$C5F1 | b24 file $030601 | LDA #$4b
$C5F3 | b24 file $030603 | STA $0000
$C5F6 | b24 file $030606 | LDA $04aa
$C5F9 | b24 file $030609 | BNE $c600
$C5FB | b24 file $03060B | LDA #$4d
$C5FD | b24 file $03060D | STA $0000
$C600 | b24 file $030610 | LDA #$00
$C602 | b24 file $030612 | JSR $cdfd
$C605 | b24 file $030615 | LDA #$02
$C607 | b24 file $030617 | STA $03b7
$C60A | b24 file $03061A | LDA #$23
$C60C | b24 file $03061C | STA $03b8
$C60F | b24 file $03061F | LDA #$db
$C611 | b24 file $030621 | STA $03b9
$C614 | b24 file $030624 | LDA #$00
$C616 | b24 file $030626 | STA $03ba
$C619 | b24 file $030629 | STA $03bb
$C61C | b24 file $03062C | LDA #$ff
$C61E | b24 file $03062E | STA $03bc
$C621 | b24 file $030631 | RTS
$C622 | b24 file $030632 | AND #$01
$C624 | b24 file $030634 | STA $0010
$C627 | b24 file $030637 | STA $0011
$C62A | b24 file $03063A | BNE $c636
$C62C | b24 file $03063C | CMP $0012
$C62F | b24 file $03063F | BEQ $c636
$C631 | b24 file $030641 | LDA #$62
$C633 | b24 file $030643 | JSR $e693
$C636 | b24 file $030646 | LDA $04aa
$C639 | b24 file $030649 | BEQ $c644
$C63B | b24 file $03064B | LDA $0010
$C63E | b24 file $03064E | CLC
$C63F | b24 file $03064F | ADC #$06
$C641 | b24 file $030651 | STA $0010
$C644 | b24 file $030654 | LDA $04aa
$C647 | b24 file $030657 | CLC
$C648 | b24 file $030658 | ADC #$01
$C64A | b24 file $03065A | STA $0002
$C64D | b24 file $03065D | LDY $04aa
$C650 | b24 file $030660 | LDA $04af,Y
$C653 | b24 file $030663 | ASL A
$C654 | b24 file $030664 | CLC
$C655 | b24 file $030665 | ADC $0010
$C658 | b24 file $030668 | ADC #$5e
$C65A | b24 file $03066A | JSR $cea5
$C65D | b24 file $03066D | LDA $0011
$C660 | b24 file $030670 | BNE $c66a
$C662 | b24 file $030672 | LDA #$76
$C664 | b24 file $030674 | STA $0010
$C667 | b24 file $030677 | JMP $d235
$C66A | b24 file $03067A | RTS
$C66B | b24 file $03067B | LDA #$13
$C66D | b24 file $03067D | STA $04a8
$C670 | b24 file $030680 | LDA #$00
$C672 | b24 file $030682 | STA $04a9
$C675 | b24 file $030685 | LDA #$ed
$C677 | b24 file $030687 | STA $0000
$C67A | b24 file $03068A | LDY $04aa
$C67D | b24 file $03068D | BEQ $c684
$C67F | b24 file $03068F | LDA #$eb
$C681 | b24 file $030691 | STA $0000
$C684 | b24 file $030694 | LDA #$00
$C686 | b24 file $030696 | JMP $cdfd
$C689 | b24 file $030699 | LDA $04a9
$C68C | b24 file $03069C | JSR $eade ; inline targets: $C69F,$C6B6,$C6DC,$C72D,$C773,$C809,$C84A,$C884
$C69F | b24 file $0306AF | INC $04a9
$C6A2 | b24 file $0306B2 | LDA #$43
$C6A4 | b24 file $0306B4 | STA $0000
$C6A7 | b24 file $0306B7 | LDA $04aa
$C6AA | b24 file $0306BA | BEQ $c6b1
$C6AC | b24 file $0306BC | LDA #$55
$C6AE | b24 file $0306BE | STA $0000
$C6B1 | b24 file $0306C1 | LDA #$00
$C6B3 | b24 file $0306C3 | JMP $cdfd
$C6B6 | b24 file $0306C6 | LDA #$00
$C6B8 | b24 file $0306C8 | STA $04b8
$C6BB | b24 file $0306CB | INC $04a9
$C6BE | b24 file $0306CE | LDA #$18
$C6C0 | b24 file $0306D0 | STA $04bb
$C6C3 | b24 file $0306D3 | LDA #$e3
$C6C5 | b24 file $0306D5 | STA $0000
$C6C8 | b24 file $0306D8 | LDA $04aa
$C6CB | b24 file $0306DB | BEQ $c6d7
$C6CD | b24 file $0306DD | LDA #$a8
$C6CF | b24 file $0306DF | STA $04bb
$C6D2 | b24 file $0306E2 | LDA #$f5
$C6D4 | b24 file $0306E4 | STA $0000
$C6D7 | b24 file $0306E7 | LDA #$00
$C6D9 | b24 file $0306E9 | JMP $cdfd
$C6DC | b24 file $0306EC | LDA $04aa
$C6DF | b24 file $0306EF | BEQ $c6eb
$C6E1 | b24 file $0306F1 | LDA $04bb
$C6E4 | b24 file $0306F4 | CMP #$58
$C6E6 | b24 file $0306F6 | BNE $c719
$C6E8 | b24 file $0306F8 | JMP $c6f2
$C6EB | b24 file $0306FB | LDA $04bb
$C6EE | b24 file $0306FE | CMP #$68
$C6F0 | b24 file $030700 | BNE $c719
$C6F2 | b24 file $030702 | LDA #$8f
$C6F4 | b24 file $030704 | STA $00cc
$C6F7 | b24 file $030707 | STA $00d4
$C6FA | b24 file $03070A | STA $00dc
$C6FD | b24 file $03070D | INC $04a9
$C700 | b24 file $030710 | LDA $04aa
$C703 | b24 file $030713 | BEQ $c70f
$C705 | b24 file $030715 | LDA #$4b
$C707 | b24 file $030717 | STA $0000
$C70A | b24 file $03071A | LDA #$0b
$C70C | b24 file $03071C | JMP $cdfd
$C70F | b24 file $03071F | LDA #$4d
$C711 | b24 file $030721 | STA $0000
$C714 | b24 file $030724 | LDA #$09
$C716 | b24 file $030726 | JMP $cdfd
$C719 | b24 file $030729 | LDA $04aa
$C71C | b24 file $03072C | STA $0011
$C71F | b24 file $03072F | BEQ $c727
$C721 | b24 file $030731 | DEC $04bb
$C724 | b24 file $030734 | JMP $cee1
$C727 | b24 file $030737 | INC $04bb
$C72A | b24 file $03073A | JMP $cee1
$C72D | b24 file $03073D | LDA #$83
$C72F | b24 file $03073F | STA $00c9
$C732 | b24 file $030742 | STA $00d1
$C735 | b24 file $030745 | STA $00d9
$C738 | b24 file $030748 | LDY $04aa
$C73B | b24 file $03074B | LDA $04af,Y
$C73E | b24 file $03074E | BEQ $c74b
$C740 | b24 file $030750 | LDA #$84
$C742 | b24 file $030752 | STA $00c6
$C745 | b24 file $030755 | STA $00ce
$C748 | b24 file $030758 | STA $00d6
$C74B | b24 file $03075B | LDA #$ff
$C74D | b24 file $03075D | STA $04b8
$C750 | b24 file $030760 | LDA #$00
$C752 | b24 file $030762 | STA $04b9
$C755 | b24 file $030765 | LDA #$4f
$C757 | b24 file $030767 | STA $04ba
$C75A | b24 file $03076A | INC $04a9
$C75D | b24 file $03076D | LDA #$ed
$C75F | b24 file $03076F | STA $0000
$C762 | b24 file $030772 | LDA #$0a
$C764 | b24 file $030774 | LDY $04aa
$C767 | b24 file $030777 | BEQ $c770
$C769 | b24 file $030779 | LDA #$eb
$C76B | b24 file $03077B | STA $0000
$C76E | b24 file $03077E | LDA #$0c
$C770 | b24 file $030780 | JMP $cdfd
$C773 | b24 file $030783 | LDA $04b8
$C776 | b24 file $030786 | LSR A
$C777 | b24 file $030787 | LSR A
$C778 | b24 file $030788 | LSR A
$C779 | b24 file $030789 | AND #$03
$C77B | b24 file $03078B | STA $0012
$C77E | b24 file $03078E | INC $04b8
$C781 | b24 file $030791 | LDA $04b8
$C784 | b24 file $030794 | LSR A
$C785 | b24 file $030795 | LSR A
$C786 | b24 file $030796 | LSR A
$C787 | b24 file $030797 | AND #$03
$C789 | b24 file $030799 | CMP #$03
$C78B | b24 file $03079B | BNE $c7b3
$C78D | b24 file $03079D | LDA #$00
$C78F | b24 file $03079F | STA $04b8
$C792 | b24 file $0307A2 | INC $04b9
$C795 | b24 file $0307A5 | LDY $04b9
$C798 | b24 file $0307A8 | CPY #$03
$C79A | b24 file $0307AA | BNE $c7b3
$C79C | b24 file $0307AC | INC $04a9
$C79F | b24 file $0307AF | LDA #$4b
$C7A1 | b24 file $0307B1 | STA $0000
$C7A4 | b24 file $0307B4 | LDA $04aa
$C7A7 | b24 file $0307B7 | BNE $c7ae
$C7A9 | b24 file $0307B9 | LDA #$4d
$C7AB | b24 file $0307BB | STA $0000
$C7AE | b24 file $0307BE | LDA #$00
$C7B0 | b24 file $0307C0 | JMP $cdfd
$C7B3 | b24 file $0307C3 | STA $0010
$C7B6 | b24 file $0307C6 | CMP #$01
$C7B8 | b24 file $0307C8 | BNE $c7c4
$C7BA | b24 file $0307CA | CMP $0012
$C7BD | b24 file $0307CD | BEQ $c7c4
$C7BF | b24 file $0307CF | LDA #$61
$C7C1 | b24 file $0307D1 | JSR $e609
$C7C4 | b24 file $0307D4 | LDA $04aa
$C7C7 | b24 file $0307D7 | BNE $c7d2
$C7C9 | b24 file $0307D9 | LDA $0010
$C7CC | b24 file $0307DC | CLC
$C7CD | b24 file $0307DD | ADC #$0f
$C7CF | b24 file $0307DF | STA $0010
$C7D2 | b24 file $0307E2 | LDA #$00
$C7D4 | b24 file $0307E4 | STA $0002
$C7D7 | b24 file $0307E7 | LDA $0010
$C7DA | b24 file $0307EA | CLC
$C7DB | b24 file $0307EB | ADC #$22
$C7DD | b24 file $0307ED | JSR $cea5
$C7E0 | b24 file $0307F0 | LDA $04aa
$C7E3 | b24 file $0307F3 | CLC
$C7E4 | b24 file $0307F4 | ADC #$01
$C7E6 | b24 file $0307F6 | STA $0002
$C7E9 | b24 file $0307F9 | LDA $0010
$C7EC | b24 file $0307FC | CLC
$C7ED | b24 file $0307FD | ADC #$25
$C7EF | b24 file $0307FF | JSR $cea5
$C7F2 | b24 file $030802 | LDY $04aa
$C7F5 | b24 file $030805 | LDA $04af,Y
$C7F8 | b24 file $030808 | STA $0011
$C7FB | b24 file $03080B | ASL A
$C7FC | b24 file $03080C | CLC
$C7FD | b24 file $03080D | ADC $0011
$C800 | b24 file $030810 | CLC
$C801 | b24 file $030811 | ADC $0010
$C804 | b24 file $030814 | ADC #$28
$C806 | b24 file $030816 | JMP $cea5
$C809 | b24 file $030819 | LDA #$00
$C80B | b24 file $03081B | STA $04b8
$C80E | b24 file $03081E | LDA #$57
$C810 | b24 file $030820 | STA $04ba
$C813 | b24 file $030823 | LDA #$80
$C815 | b24 file $030825 | STA $00c6
$C818 | b24 file $030828 | STA $00ce
$C81B | b24 file $03082B | STA $00d6
$C81E | b24 file $03082E | LDY $04aa
$C821 | b24 file $030831 | LDA $04af,Y
$C824 | b24 file $030834 | CMP #$01
$C826 | b24 file $030836 | BNE $c833
$C828 | b24 file $030838 | LDA #$96
$C82A | b24 file $03083A | STA $00c9
$C82D | b24 file $03083D | STA $00d1
$C830 | b24 file $030840 | STA $00d9
$C833 | b24 file $030843 | INC $04a9
$C836 | b24 file $030846 | LDA #$eb
$C838 | b24 file $030848 | STA $0000
$C83B | b24 file $03084B | LDA $04aa
$C83E | b24 file $03084E | BNE $c845
$C840 | b24 file $030850 | LDA #$ed
$C842 | b24 file $030852 | STA $0000
$C845 | b24 file $030855 | LDA #$00
$C847 | b24 file $030857 | JMP $cdfd
$C84A | b24 file $03085A | LDA #$90
$C84C | b24 file $03085C | STA $00cc
$C84F | b24 file $03085F | STA $00d4
$C852 | b24 file $030862 | STA $00dc
$C855 | b24 file $030865 | INC $04a9
$C858 | b24 file $030868 | LDA $04aa
$C85B | b24 file $03086B | EOR #$01
$C85D | b24 file $03086D | TAY
$C85E | b24 file $03086E | LDA $04af,Y
$C861 | b24 file $030871 | STA $0001
$C864 | b24 file $030874 | CPY #$01
$C866 | b24 file $030876 | BEQ $c876
$C868 | b24 file $030878 | LDA #$43
$C86A | b24 file $03087A | STA $0000
$C86D | b24 file $03087D | LDA #$0d
$C86F | b24 file $03087F | CLC
$C870 | b24 file $030880 | ADC $0001
$C873 | b24 file $030883 | JMP $cdfd
$C876 | b24 file $030886 | LDA #$55
$C878 | b24 file $030888 | STA $0000
$C87B | b24 file $03088B | LDA #$10
$C87D | b24 file $03088D | CLC
$C87E | b24 file $03088E | ADC $0001
$C881 | b24 file $030891 | JMP $cdfd
$C884 | b24 file $030894 | LDA $04b8
$C887 | b24 file $030897 | LSR A
$C888 | b24 file $030898 | LSR A
$C889 | b24 file $030899 | LSR A
$C88A | b24 file $03089A | AND #$07
$C88C | b24 file $03089C | STA $0012
$C88F | b24 file $03089F | INC $04b8
$C892 | b24 file $0308A2 | LDA $04b8
$C895 | b24 file $0308A5 | LSR A
$C896 | b24 file $0308A6 | LSR A
$C897 | b24 file $0308A7 | LSR A
$C898 | b24 file $0308A8 | AND #$07
$C89A | b24 file $0308AA | CMP #$03
$C89C | b24 file $0308AC | BCC $c8af
$C89E | b24 file $0308AE | CMP #$05
$C8A0 | b24 file $0308B0 | BCC $c8ad
$C8A2 | b24 file $0308B2 | LDA #$13
$C8A4 | b24 file $0308B4 | STA $04a8
$C8A7 | b24 file $0308B7 | LDA #$00
$C8A9 | b24 file $0308B9 | STA $04a9
$C8AC | b24 file $0308BC | RTS
$C8AD | b24 file $0308BD | LDA #$02
$C8AF | b24 file $0308BF | STA $0010
$C8B2 | b24 file $0308C2 | STA $0011
$C8B5 | b24 file $0308C5 | CMP #$01
$C8B7 | b24 file $0308C7 | BNE $c8c3
$C8B9 | b24 file $0308C9 | CMP $0012
$C8BC | b24 file $0308CC | BEQ $c8c3
$C8BE | b24 file $0308CE | LDA #$69
$C8C0 | b24 file $0308D0 | JSR $e609
$C8C3 | b24 file $0308D3 | LDA $04aa
$C8C6 | b24 file $0308D6 | BNE $c8d1
$C8C8 | b24 file $0308D8 | LDA $0010
$C8CB | b24 file $0308DB | CLC
$C8CC | b24 file $0308DC | ADC #$0f
$C8CE | b24 file $0308DE | STA $0010
$C8D1 | b24 file $0308E1 | LDA #$00
$C8D3 | b24 file $0308E3 | STA $0002
$C8D6 | b24 file $0308E6 | LDA #$40
$C8D8 | b24 file $0308E8 | STA $0001
$C8DB | b24 file $0308EB | LDY $04aa
$C8DE | b24 file $0308EE | LDA $04af,Y
$C8E1 | b24 file $0308F1 | CMP #$01
$C8E3 | b24 file $0308F3 | BNE $c8ea
$C8E5 | b24 file $0308F5 | LDA #$4c
$C8E7 | b24 file $0308F7 | STA $0001
$C8EA | b24 file $0308FA | LDA $0010
$C8ED | b24 file $0308FD | CLC
$C8EE | b24 file $0308FE | ADC $0001
$C8F1 | b24 file $030901 | JSR $cea5
$C8F4 | b24 file $030904 | LDA $04aa
$C8F7 | b24 file $030907 | CLC
$C8F8 | b24 file $030908 | ADC #$01
$C8FA | b24 file $03090A | STA $0002
$C8FD | b24 file $03090D | LDY $04aa
$C900 | b24 file $030910 | LDA $04af,Y
$C903 | b24 file $030913 | STA $0001
$C906 | b24 file $030916 | ASL A
$C907 | b24 file $030917 | CLC
$C908 | b24 file $030918 | ADC $0001
$C90B | b24 file $03091B | CLC
$C90C | b24 file $03091C | ADC $0010
$C90F | b24 file $03091F | ADC #$43
$C911 | b24 file $030921 | JSR $cea5
$C914 | b24 file $030924 | LDY $04aa
$C917 | b24 file $030927 | LDA $04af,Y
$C91A | b24 file $03092A | CMP #$01
$C91C | b24 file $03092C | BEQ $c930
$C91E | b24 file $03092E | LDA $04b8
$C921 | b24 file $030931 | CMP #$11
$C923 | b24 file $030933 | BNE $c930
$C925 | b24 file $030935 | LDA #$84
$C927 | b24 file $030937 | STA $00c9
$C92A | b24 file $03093A | STA $00d1
$C92D | b24 file $03093D | STA $00d9
$C930 | b24 file $030940 | LDA $0011
$C933 | b24 file $030943 | CMP #$02
$C935 | b24 file $030945 | BNE $c948
$C937 | b24 file $030947 | LDY $04aa
$C93A | b24 file $03094A | LDA $04af,Y
$C93D | b24 file $03094D | AND #$01
$C93F | b24 file $03094F | CLC
$C940 | b24 file $030950 | ADC #$77
$C942 | b24 file $030952 | STA $0010
$C945 | b24 file $030955 | JMP $d235
$C948 | b24 file $030958 | RTS
$C949 | b24 file $030959 | LDA $04a9
$C94C | b24 file $03095C | JSR $eade ; inline targets: $C95F,$C976,$C99C,$C9ED,$CA50,$CAB8,$CAD4,$CB0E
$C95F | b24 file $03096F | INC $04a9
$C962 | b24 file $030972 | LDA #$55
$C964 | b24 file $030974 | STA $0000
$C967 | b24 file $030977 | LDA $04aa
$C96A | b24 file $03097A | BNE $c971
$C96C | b24 file $03097C | LDA #$43
$C96E | b24 file $03097E | STA $0000
$C971 | b24 file $030981 | LDA #$00
$C973 | b24 file $030983 | JMP $cdfd
$C976 | b24 file $030986 | LDA #$00
$C978 | b24 file $030988 | STA $04b8
$C97B | b24 file $03098B | INC $04a9
$C97E | b24 file $03098E | LDA #$a8
$C980 | b24 file $030990 | STA $04bb
$C983 | b24 file $030993 | LDA #$f5
$C985 | b24 file $030995 | STA $0000
$C988 | b24 file $030998 | LDA $04aa
$C98B | b24 file $03099B | BNE $c997
$C98D | b24 file $03099D | LDA #$18
$C98F | b24 file $03099F | STA $04bb
$C992 | b24 file $0309A2 | LDA #$e3
$C994 | b24 file $0309A4 | STA $0000
$C997 | b24 file $0309A7 | LDA #$00
$C999 | b24 file $0309A9 | JMP $cdfd
$C99C | b24 file $0309AC | LDA $04aa
$C99F | b24 file $0309AF | BEQ $c9ab
$C9A1 | b24 file $0309B1 | LDA $04bb
$C9A4 | b24 file $0309B4 | CMP #$58
$C9A6 | b24 file $0309B6 | BNE $c9d9
$C9A8 | b24 file $0309B8 | JMP $c9b2
$C9AB | b24 file $0309BB | LDA $04bb
$C9AE | b24 file $0309BE | CMP #$68
$C9B0 | b24 file $0309C0 | BNE $c9d9
$C9B2 | b24 file $0309C2 | LDA #$8f
$C9B4 | b24 file $0309C4 | STA $00cc
$C9B7 | b24 file $0309C7 | STA $00d4
$C9BA | b24 file $0309CA | STA $00dc
$C9BD | b24 file $0309CD | INC $04a9
$C9C0 | b24 file $0309D0 | LDA $04aa
$C9C3 | b24 file $0309D3 | BEQ $c9cf
$C9C5 | b24 file $0309D5 | LDA #$4b
$C9C7 | b24 file $0309D7 | STA $0000
$C9CA | b24 file $0309DA | LDA #$0b
$C9CC | b24 file $0309DC | JMP $cdfd
$C9CF | b24 file $0309DF | LDA #$4d
$C9D1 | b24 file $0309E1 | STA $0000
$C9D4 | b24 file $0309E4 | LDA #$09
$C9D6 | b24 file $0309E6 | JMP $cdfd
$C9D9 | b24 file $0309E9 | LDA $04aa
$C9DC | b24 file $0309EC | STA $0011
$C9DF | b24 file $0309EF | BEQ $c9e7
$C9E1 | b24 file $0309F1 | DEC $04bb
$C9E4 | b24 file $0309F4 | JMP $cee1
$C9E7 | b24 file $0309F7 | INC $04bb
$C9EA | b24 file $0309FA | JMP $cee1
$C9ED | b24 file $0309FD | LDA #$3f
$C9EF | b24 file $0309FF | STA $04ba
$C9F2 | b24 file $030A02 | LDA #$86
$C9F4 | b24 file $030A04 | STA $00be
$C9F7 | b24 file $030A07 | STA $00c6
$C9FA | b24 file $030A0A | STA $00ce
$C9FD | b24 file $030A0D | STA $00d6
$CA00 | b24 file $030A10 | LDA #$87
$CA02 | b24 file $030A12 | STA $00bf
$CA05 | b24 file $030A15 | STA $00c7
$CA08 | b24 file $030A18 | STA $00cf
$CA0B | b24 file $030A1B | STA $00d7
$CA0E | b24 file $030A1E | LDA #$93
$CA10 | b24 file $030A20 | STA $00c0
$CA13 | b24 file $030A23 | STA $00c8
$CA16 | b24 file $030A26 | STA $00d0
$CA19 | b24 file $030A29 | STA $00d8
$CA1C | b24 file $030A2C | LDA #$94
$CA1E | b24 file $030A2E | STA $00c1
$CA21 | b24 file $030A31 | STA $00c9
$CA24 | b24 file $030A34 | STA $00d1
$CA27 | b24 file $030A37 | STA $00d9
$CA2A | b24 file $030A3A | LDA #$00
$CA2C | b24 file $030A3C | STA $04b8
$CA2F | b24 file $030A3F | STA $04b9
$CA32 | b24 file $030A42 | INC $04a9
$CA35 | b24 file $030A45 | LDA #$61
$CA37 | b24 file $030A47 | JSR $e609
$CA3A | b24 file $030A4A | LDA #$ed
$CA3C | b24 file $030A4C | STA $0000
$CA3F | b24 file $030A4F | LDA #$0a
$CA41 | b24 file $030A51 | LDY $04aa
$CA44 | b24 file $030A54 | BEQ $ca4d
$CA46 | b24 file $030A56 | LDA #$eb
$CA48 | b24 file $030A58 | STA $0000
$CA4B | b24 file $030A5B | LDA #$0c
$CA4D | b24 file $030A5D | JMP $cdfd
$CA50 | b24 file $030A60 | INC $04b8
$CA53 | b24 file $030A63 | LDA $04b8
$CA56 | b24 file $030A66 | LSR A
$CA57 | b24 file $030A67 | LSR A
$CA58 | b24 file $030A68 | LSR A
$CA59 | b24 file $030A69 | LSR A
$CA5A | b24 file $030A6A | AND #$01
$CA5C | b24 file $030A6C | BEQ $ca7a
$CA5E | b24 file $030A6E | LDA #$00
$CA60 | b24 file $030A70 | STA $04b8
$CA63 | b24 file $030A73 | INC $04a9
$CA66 | b24 file $030A76 | LDA #$4b
$CA68 | b24 file $030A78 | STA $0000
$CA6B | b24 file $030A7B | LDA $04aa
$CA6E | b24 file $030A7E | BNE $ca75
$CA70 | b24 file $030A80 | LDA #$4d
$CA72 | b24 file $030A82 | STA $0000
$CA75 | b24 file $030A85 | LDA #$00
$CA77 | b24 file $030A87 | JMP $cdfd
$CA7A | b24 file $030A8A | STA $0010
$CA7D | b24 file $030A8D | LDA $04aa
$CA80 | b24 file $030A90 | BNE $ca8b
$CA82 | b24 file $030A92 | LDA $0010
$CA85 | b24 file $030A95 | CLC
$CA86 | b24 file $030A96 | ADC #$14
$CA88 | b24 file $030A98 | STA $0010
$CA8B | b24 file $030A9B | LDA #$00
$CA8D | b24 file $030A9D | STA $0002
$CA90 | b24 file $030AA0 | LDA $0010
$CA93 | b24 file $030AA3 | CLC
$CA94 | b24 file $030AA4 | ADC #$80
$CA96 | b24 file $030AA6 | JSR $cea5
$CA99 | b24 file $030AA9 | LDY $04aa
$CA9C | b24 file $030AAC | TYA
$CA9D | b24 file $030AAD | CLC
$CA9E | b24 file $030AAE | ADC #$01
$CAA0 | b24 file $030AB0 | STA $0002
$CAA3 | b24 file $030AB3 | LDA $04af,Y
$CAA6 | b24 file $030AB6 | STA $0001
$CAA9 | b24 file $030AB9 | ASL A
$CAAA | b24 file $030ABA | ASL A
$CAAB | b24 file $030ABB | CLC
$CAAC | b24 file $030ABC | ADC $0001
$CAAF | b24 file $030ABF | CLC
$CAB0 | b24 file $030AC0 | ADC $0010
$CAB3 | b24 file $030AC3 | ADC #$85
$CAB5 | b24 file $030AC5 | JMP $cea5
$CAB8 | b24 file $030AC8 | LDA #$00
$CABA | b24 file $030ACA | STA $04b8
$CABD | b24 file $030ACD | INC $04a9
$CAC0 | b24 file $030AD0 | LDA #$eb
$CAC2 | b24 file $030AD2 | STA $0000
$CAC5 | b24 file $030AD5 | LDA $04aa
$CAC8 | b24 file $030AD8 | BNE $cacf
$CACA | b24 file $030ADA | LDA #$ed
$CACC | b24 file $030ADC | STA $0000
$CACF | b24 file $030ADF | LDA #$00
$CAD1 | b24 file $030AE1 | JMP $cdfd
$CAD4 | b24 file $030AE4 | LDA #$90
$CAD6 | b24 file $030AE6 | STA $00cc
$CAD9 | b24 file $030AE9 | STA $00d4
$CADC | b24 file $030AEC | STA $00dc
$CADF | b24 file $030AEF | INC $04a9
$CAE2 | b24 file $030AF2 | LDA $04aa
$CAE5 | b24 file $030AF5 | EOR #$01
$CAE7 | b24 file $030AF7 | TAY
$CAE8 | b24 file $030AF8 | LDA $04af,Y
$CAEB | b24 file $030AFB | STA $0001
$CAEE | b24 file $030AFE | CPY #$01
$CAF0 | b24 file $030B00 | BEQ $cb00
$CAF2 | b24 file $030B02 | LDA #$43
$CAF4 | b24 file $030B04 | STA $0000
$CAF7 | b24 file $030B07 | LDA #$0d
$CAF9 | b24 file $030B09 | CLC
$CAFA | b24 file $030B0A | ADC $0001
$CAFD | b24 file $030B0D | JMP $cdfd
$CB00 | b24 file $030B10 | LDA #$55
$CB02 | b24 file $030B12 | STA $0000
$CB05 | b24 file $030B15 | LDA #$10
$CB07 | b24 file $030B17 | CLC
$CB08 | b24 file $030B18 | ADC $0001
$CB0B | b24 file $030B1B | JMP $cdfd
$CB0E | b24 file $030B1E | LDA $04b8
$CB11 | b24 file $030B21 | LSR A
$CB12 | b24 file $030B22 | LSR A
$CB13 | b24 file $030B23 | LSR A
$CB14 | b24 file $030B24 | LSR A
$CB15 | b24 file $030B25 | AND #$07
$CB17 | b24 file $030B27 | STA $0012
$CB1A | b24 file $030B2A | INC $04b8
$CB1D | b24 file $030B2D | LDA $04b8
$CB20 | b24 file $030B30 | LSR A
$CB21 | b24 file $030B31 | LSR A
$CB22 | b24 file $030B32 | LSR A
$CB23 | b24 file $030B33 | LSR A
$CB24 | b24 file $030B34 | AND #$07
$CB26 | b24 file $030B36 | CMP #$06
$CB28 | b24 file $030B38 | BNE $cb35
$CB2A | b24 file $030B3A | LDA #$13
$CB2C | b24 file $030B3C | STA $04a8
$CB2F | b24 file $030B3F | LDA #$00
$CB31 | b24 file $030B41 | STA $04a9
$CB34 | b24 file $030B44 | RTS
$CB35 | b24 file $030B45 | CMP #$03
$CB37 | b24 file $030B47 | BNE $cb45
$CB39 | b24 file $030B49 | CMP $0012
$CB3C | b24 file $030B4C | BEQ $cb45
$CB3E | b24 file $030B4E | LDA #$68
$CB40 | b24 file $030B50 | JSR $e609
$CB43 | b24 file $030B53 | LDA #$03
$CB45 | b24 file $030B55 | CMP #$04
$CB47 | b24 file $030B57 | BCC $cb4b
$CB49 | b24 file $030B59 | LDA #$03
$CB4B | b24 file $030B5B | STA $0010
$CB4E | b24 file $030B5E | STA $0011
$CB51 | b24 file $030B61 | LDA $04aa
$CB54 | b24 file $030B64 | BNE $cb5f
$CB56 | b24 file $030B66 | LDA $0010
$CB59 | b24 file $030B69 | CLC
$CB5A | b24 file $030B6A | ADC #$14
$CB5C | b24 file $030B6C | STA $0010
$CB5F | b24 file $030B6F | LDA $04aa
$CB62 | b24 file $030B72 | CLC
$CB63 | b24 file $030B73 | ADC #$01
$CB65 | b24 file $030B75 | STA $0002
$CB68 | b24 file $030B78 | LDY $04aa
$CB6B | b24 file $030B7B | LDA $04af,Y
$CB6E | b24 file $030B7E | STA $0001
$CB71 | b24 file $030B81 | ASL A
$CB72 | b24 file $030B82 | ASL A
$CB73 | b24 file $030B83 | CLC
$CB74 | b24 file $030B84 | ADC $0001
$CB77 | b24 file $030B87 | CLC
$CB78 | b24 file $030B88 | ADC $0010
$CB7B | b24 file $030B8B | ADC #$86
$CB7D | b24 file $030B8D | JSR $cea5
$CB80 | b24 file $030B90 | LDA #$00
$CB82 | b24 file $030B92 | STA $0002
$CB85 | b24 file $030B95 | LDA $0010
$CB88 | b24 file $030B98 | CLC
$CB89 | b24 file $030B99 | ADC #$81
$CB8B | b24 file $030B9B | JSR $cea5
$CB8E | b24 file $030B9E | LDA $0011
$CB91 | b24 file $030BA1 | CMP #$03
$CB93 | b24 file $030BA3 | BNE $cb9d
$CB95 | b24 file $030BA5 | LDA #$79
$CB97 | b24 file $030BA7 | STA $0010
$CB9A | b24 file $030BAA | JMP $d235
$CB9D | b24 file $030BAD | RTS
$CB9E | b24 file $030BAE | LDA $04a9
$CBA1 | b24 file $030BB1 | JSR $eade ; inline targets: $CBAA,$CC0A,$CC62
$CBAA | b24 file $030BBA | LDA #$80
$CBAC | b24 file $030BBC | STA $00c6
$CBAF | b24 file $030BBF | STA $00ce
$CBB2 | b24 file $030BC2 | STA $00d6
$CBB5 | b24 file $030BC5 | LDA #$81
$CBB7 | b24 file $030BC7 | STA $00c7
$CBBA | b24 file $030BCA | STA $00cf
$CBBD | b24 file $030BCD | STA $00d7
$CBC0 | b24 file $030BD0 | LDA #$82
$CBC2 | b24 file $030BD2 | STA $00c8
$CBC5 | b24 file $030BD5 | STA $00d0
$CBC8 | b24 file $030BD8 | STA $00d8
$CBCB | b24 file $030BDB | LDA #$85
$CBCD | b24 file $030BDD | STA $00c9
$CBD0 | b24 file $030BE0 | STA $00d1
$CBD3 | b24 file $030BE3 | STA $00d9
$CBD6 | b24 file $030BE6 | LDA #$00
$CBD8 | b24 file $030BE8 | STA $04b8
$CBDB | b24 file $030BEB | INC $04a9
$CBDE | b24 file $030BEE | LDA $04aa
$CBE1 | b24 file $030BF1 | EOR #$01
$CBE3 | b24 file $030BF3 | TAY
$CBE4 | b24 file $030BF4 | LDA $04af,Y
$CBE7 | b24 file $030BF7 | STA $0001
$CBEA | b24 file $030BFA | CPY #$01
$CBEC | b24 file $030BFC | BEQ $cbfc
$CBEE | b24 file $030BFE | LDA #$43
$CBF0 | b24 file $030C00 | STA $0000
$CBF3 | b24 file $030C03 | LDA #$01
$CBF5 | b24 file $030C05 | CLC
$CBF6 | b24 file $030C06 | ADC $0001
$CBF9 | b24 file $030C09 | JMP $cdfd
$CBFC | b24 file $030C0C | LDA #$55
$CBFE | b24 file $030C0E | STA $0000
$CC01 | b24 file $030C11 | LDA #$05
$CC03 | b24 file $030C13 | CLC
$CC04 | b24 file $030C14 | ADC $0001
$CC07 | b24 file $030C17 | JMP $cdfd
$CC0A | b24 file $030C1A | LDA $04aa
$CC0D | b24 file $030C1D | BEQ $cc19
$CC0F | b24 file $030C1F | LDA $04bb
$CC12 | b24 file $030C22 | CMP #$a8
$CC14 | b24 file $030C24 | BNE $cc49
$CC16 | b24 file $030C26 | JMP $cc20
$CC19 | b24 file $030C29 | LDA $04bb
$CC1C | b24 file $030C2C | CMP #$18
$CC1E | b24 file $030C2E | BNE $cc49
$CC20 | b24 file $030C30 | INC $04a9
$CC23 | b24 file $030C33 | LDA #$43
$CC25 | b24 file $030C35 | STA $0000
$CC28 | b24 file $030C38 | LDA #$01
$CC2A | b24 file $030C3A | STA $0001
$CC2D | b24 file $030C3D | LDA $04aa
$CC30 | b24 file $030C40 | BEQ $cc3c
$CC32 | b24 file $030C42 | LDA #$55
$CC34 | b24 file $030C44 | STA $0000
$CC37 | b24 file $030C47 | LDA #$05
$CC39 | b24 file $030C49 | STA $0001
$CC3C | b24 file $030C4C | LDY $04aa
$CC3F | b24 file $030C4F | LDA $04af,Y
$CC42 | b24 file $030C52 | CLC
$CC43 | b24 file $030C53 | ADC $0001
$CC46 | b24 file $030C56 | JMP $cdfd
$CC49 | b24 file $030C59 | LDA $04aa
$CC4C | b24 file $030C5C | EOR #$01
$CC4E | b24 file $030C5E | STA $0011
$CC51 | b24 file $030C61 | LDA $04aa
$CC54 | b24 file $030C64 | BEQ $cc5c
$CC56 | b24 file $030C66 | INC $04bb
$CC59 | b24 file $030C69 | JMP $cee1
$CC5C | b24 file $030C6C | DEC $04bb
$CC5F | b24 file $030C6F | JMP $cee1
$CC62 | b24 file $030C72 | LDA $04bd
$CC65 | b24 file $030C75 | STA $04a8
$CC68 | b24 file $030C78 | LDA $04be
$CC6B | b24 file $030C7B | STA $04a9
$CC6E | b24 file $030C7E | LDA $04aa
$CC71 | b24 file $030C81 | BEQ $cc7d
$CC73 | b24 file $030C83 | LDA #$f5
$CC75 | b24 file $030C85 | STA $0000
$CC78 | b24 file $030C88 | LDA #$08
$CC7A | b24 file $030C8A | JMP $cdfd
$CC7D | b24 file $030C8D | LDA #$e3
$CC7F | b24 file $030C8F | STA $0000
$CC82 | b24 file $030C92 | LDA #$04
$CC84 | b24 file $030C94 | JMP $cdfd
$CC87 | b24 file $030C97 | LDA $04a9
$CC8A | b24 file $030C9A | JSR $eade ; inline targets: $CC93,$CCAA,$CCD0
$CC93 | b24 file $030CA3 | INC $04a9
$CC96 | b24 file $030CA6 | LDA #$55
$CC98 | b24 file $030CA8 | STA $0000
$CC9B | b24 file $030CAB | LDA $04aa
$CC9E | b24 file $030CAE | BNE $cca5
$CCA0 | b24 file $030CB0 | LDA #$43
$CCA2 | b24 file $030CB2 | STA $0000
$CCA5 | b24 file $030CB5 | LDA #$00
$CCA7 | b24 file $030CB7 | JMP $cdfd
$CCAA | b24 file $030CBA | LDA #$00
$CCAC | b24 file $030CBC | STA $04b8
$CCAF | b24 file $030CBF | INC $04a9
$CCB2 | b24 file $030CC2 | LDA #$a8
$CCB4 | b24 file $030CC4 | STA $04bb
$CCB7 | b24 file $030CC7 | LDA #$f5
$CCB9 | b24 file $030CC9 | STA $0000
$CCBC | b24 file $030CCC | LDA $04aa
$CCBF | b24 file $030CCF | BNE $cccb
$CCC1 | b24 file $030CD1 | LDA #$18
$CCC3 | b24 file $030CD3 | STA $04bb
$CCC6 | b24 file $030CD6 | LDA #$e3
$CCC8 | b24 file $030CD8 | STA $0000
$CCCB | b24 file $030CDB | LDA #$00
$CCCD | b24 file $030CDD | JMP $cdfd
$CCD0 | b24 file $030CE0 | LDA $04aa
$CCD3 | b24 file $030CE3 | BEQ $ccdf
$CCD5 | b24 file $030CE5 | LDA $04bb
$CCD8 | b24 file $030CE8 | CMP #$08
$CCDA | b24 file $030CEA | BNE $ccf3
$CCDC | b24 file $030CEC | JMP $cce6
$CCDF | b24 file $030CEF | LDA $04bb
$CCE2 | b24 file $030CF2 | CMP #$b8
$CCE4 | b24 file $030CF4 | BNE $ccf3
$CCE6 | b24 file $030CF6 | LDA $04bd
$CCE9 | b24 file $030CF9 | STA $04a8
$CCEC | b24 file $030CFC | LDA $04be
$CCEF | b24 file $030CFF | STA $04a9
$CCF2 | b24 file $030D02 | RTS
$CCF3 | b24 file $030D03 | LDA $04aa
$CCF6 | b24 file $030D06 | EOR #$01
$CCF8 | b24 file $030D08 | STA $0011
$CCFB | b24 file $030D0B | LDA $04aa
$CCFE | b24 file $030D0E | BEQ $cd06
$CD00 | b24 file $030D10 | INC $04bb
$CD03 | b24 file $030D13 | JMP $cd09
$CD06 | b24 file $030D16 | DEC $04bb
$CD09 | b24 file $030D19 | JSR $cee1
$CD0C | b24 file $030D1C | LDY #$00
$CD0E | b24 file $030D1E | LDX #$00
$CD10 | b24 file $030D20 | CPY $007c
$CD13 | b24 file $030D23 | BEQ $cd3b
$CD15 | b24 file $030D25 | INX
$CD16 | b24 file $030D26 | INX
$CD17 | b24 file $030D27 | INX
$CD18 | b24 file $030D28 | LDA $04aa
$CD1B | b24 file $030D2B | BEQ $cd25
$CD1D | b24 file $030D2D | LDA $0200,X
$CD20 | b24 file $030D30 | BMI $cd33
$CD22 | b24 file $030D32 | JMP $cd2e
$CD25 | b24 file $030D35 | LDA $0200,X
$CD28 | b24 file $030D38 | CMP #$ff
$CD2A | b24 file $030D3A | BCS $cd33
$CD2C | b24 file $030D3C | BPL $cd33
$CD2E | b24 file $030D3E | LDA #$f0
$CD30 | b24 file $030D40 | STA $0200,Y
$CD33 | b24 file $030D43 | INX
$CD34 | b24 file $030D44 | INY
$CD35 | b24 file $030D45 | INY
$CD36 | b24 file $030D46 | INY
$CD37 | b24 file $030D47 | INY
$CD38 | b24 file $030D48 | JMP $cd10
$CD3B | b24 file $030D4B | RTS
$CD3C | b24 file $030D4C | LDA $04a9
$CD3F | b24 file $030D4F | JSR $eade ; inline targets: $CD48,$CD5F,$CD85
$CD48 | b24 file $030D58 | INC $04a9
$CD4B | b24 file $030D5B | LDA #$55
$CD4D | b24 file $030D5D | STA $0000
$CD50 | b24 file $030D60 | LDA $04aa
$CD53 | b24 file $030D63 | BNE $cd5a
$CD55 | b24 file $030D65 | LDA #$43
$CD57 | b24 file $030D67 | STA $0000
$CD5A | b24 file $030D6A | LDA #$00
$CD5C | b24 file $030D6C | JMP $cdfd
$CD5F | b24 file $030D6F | LDA #$00
$CD61 | b24 file $030D71 | STA $04b8
$CD64 | b24 file $030D74 | INC $04a9
$CD67 | b24 file $030D77 | LDA #$a8
$CD69 | b24 file $030D79 | STA $04bb
$CD6C | b24 file $030D7C | LDA #$f5
$CD6E | b24 file $030D7E | STA $0000
$CD71 | b24 file $030D81 | LDA $04aa
$CD74 | b24 file $030D84 | BNE $cd80
$CD76 | b24 file $030D86 | LDA #$18
$CD78 | b24 file $030D88 | STA $04bb
$CD7B | b24 file $030D8B | LDA #$e3
$CD7D | b24 file $030D8D | STA $0000
$CD80 | b24 file $030D90 | LDA #$00
$CD82 | b24 file $030D92 | JMP $cdfd
$CD85 | b24 file $030D95 | LDA $04aa
$CD88 | b24 file $030D98 | BEQ $cd94
$CD8A | b24 file $030D9A | LDA $04bb
$CD8D | b24 file $030D9D | CMP #$b8
$CD8F | b24 file $030D9F | BNE $cda8
$CD91 | b24 file $030DA1 | JMP $cd9b
$CD94 | b24 file $030DA4 | LDA $04bb
$CD97 | b24 file $030DA7 | CMP #$08
$CD99 | b24 file $030DA9 | BNE $cda8
$CD9B | b24 file $030DAB | LDA $04bd
$CD9E | b24 file $030DAE | STA $04a8
$CDA1 | b24 file $030DB1 | LDA $04be
$CDA4 | b24 file $030DB4 | STA $04a9
$CDA7 | b24 file $030DB7 | RTS
$CDA8 | b24 file $030DB8 | LDA $04aa
$CDAB | b24 file $030DBB | STA $0011
$CDAE | b24 file $030DBE | LDA $04aa
$CDB1 | b24 file $030DC1 | BNE $cdb9
$CDB3 | b24 file $030DC3 | INC $04bb
$CDB6 | b24 file $030DC6 | JMP $cdbc
$CDB9 | b24 file $030DC9 | DEC $04bb
$CDBC | b24 file $030DCC | JSR $cee1
$CDBF | b24 file $030DCF | LDY #$00
$CDC1 | b24 file $030DD1 | LDX #$00
$CDC3 | b24 file $030DD3 | CPY $007c
$CDC6 | b24 file $030DD6 | BEQ $cdfc
$CDC8 | b24 file $030DD8 | INX
$CDC9 | b24 file $030DD9 | INX
$CDCA | b24 file $030DDA | INX
$CDCB | b24 file $030DDB | LDA $04aa
$CDCE | b24 file $030DDE | BEQ $cddf
$CDD0 | b24 file $030DE0 | LDA $04bb
$CDD3 | b24 file $030DE3 | CMP #$b8
$CDD5 | b24 file $030DE5 | BCC $cdf4
$CDD7 | b24 file $030DE7 | LDA $0200,X
$CDDA | b24 file $030DEA | BMI $cdef
$CDDC | b24 file $030DEC | JMP $cdf4
$CDDF | b24 file $030DEF | LDA $04bb
$CDE2 | b24 file $030DF2 | CMP #$18
$CDE4 | b24 file $030DF4 | BCC $cdea
$CDE6 | b24 file $030DF6 | CMP #$c8
$CDE8 | b24 file $030DF8 | BCC $cdf4
$CDEA | b24 file $030DFA | LDA $0200,X
$CDED | b24 file $030DFD | BMI $cdf4
$CDEF | b24 file $030DFF | LDA #$f0
$CDF1 | b24 file $030E01 | STA $0200,Y
$CDF4 | b24 file $030E04 | INX
$CDF5 | b24 file $030E05 | INY
$CDF6 | b24 file $030E06 | INY
$CDF7 | b24 file $030E07 | INY
$CDF8 | b24 file $030E08 | INY
$CDF9 | b24 file $030E09 | JMP $cdc3
$CDFC | b24 file $030E0C | RTS
