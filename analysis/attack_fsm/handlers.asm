; Reachable normal-attack handlers, physical bank14 A000/bank15 C000. Pointer tables excluded.
$A069 | b14 file $01A079 | LDA $0540
$A06C | b14 file $01A07C | JSR $eade ; inline targets: $A085,$A15F,$A4F7,$AA23,$A3BC,$CD43,$CE25,$CF67,$ACC5,$B1EC,$D6BA
$A085 | b14 file $01A095 | LDA $0541
$A088 | b14 file $01A098 | JSR $eade ; inline targets: $A095,$A0D3,$A0F9,$A119,$A137
$A095 | b14 file $01A0A5 | LDA $0087
$A098 | b14 file $01A0A8 | BPL $a0d2
$A09A | b14 file $01A0AA | LDA #$06
$A09C | b14 file $01A0AC | STA $0540
$A09F | b14 file $01A0AF | LDA #$00
$A0A1 | b14 file $01A0B1 | STA $0541
$A0A4 | b14 file $01A0B4 | LDA #$00
$A0A6 | b14 file $01A0B6 | STA $0550
$A0A9 | b14 file $01A0B9 | STA $0551
$A0AC | b14 file $01A0BC | STA $0552
$A0AF | b14 file $01A0BF | STA $0553
$A0B2 | b14 file $01A0C2 | STA $0554
$A0B5 | b14 file $01A0C5 | STA $0555
$A0B8 | b14 file $01A0C8 | STA $0556
$A0BB | b14 file $01A0CB | STA $0557
$A0BE | b14 file $01A0CE | STA $0574
$A0C1 | b14 file $01A0D1 | STA $0575
$A0C4 | b14 file $01A0D4 | STA $0576
$A0C7 | b14 file $01A0D7 | STA $0577
$A0CA | b14 file $01A0DA | LDA #$00
$A0CC | b14 file $01A0DC | STA $0548
$A0CF | b14 file $01A0DF | JSR $c926
$A0D2 | b14 file $01A0E2 | RTS
$A0D3 | b14 file $01A0E3 | JSR $b870
$A0D6 | b14 file $01A0E6 | BCC $a0f8
$A0D8 | b14 file $01A0E8 | LDA #$10
$A0DA | b14 file $01A0EA | STA $12
$A0DC | b14 file $01A0EC | LDY $0548
$A0DF | b14 file $01A0EF | STY $13
$A0E1 | b14 file $01A0F1 | LDA $0580,Y
$A0E4 | b14 file $01A0F4 | CMP #$ff
$A0E6 | b14 file $01A0F6 | BEQ $a0eb
$A0E8 | b14 file $01A0F8 | JSR $b882
$A0EB | b14 file $01A0FB | INC $0548
$A0EE | b14 file $01A0FE | LDA $0548
$A0F1 | b14 file $01A101 | CMP #$16
$A0F3 | b14 file $01A103 | BCC $a0f8
$A0F5 | b14 file $01A105 | INC $0541
$A0F8 | b14 file $01A108 | RTS
$A0F9 | b14 file $01A109 | JSR $b870
$A0FC | b14 file $01A10C | BCC $a118
$A0FE | b14 file $01A10E | LDA #$e8
$A100 | b14 file $01A110 | STA $0310
$A103 | b14 file $01A113 | LDA #$e9
$A105 | b14 file $01A115 | STA $0311
$A108 | b14 file $01A118 | LDA #$00
$A10A | b14 file $01A11A | STA $0300
$A10D | b14 file $01A11D | INC $0541
$A110 | b14 file $01A120 | LDA #$05
$A112 | b14 file $01A122 | STA $00bc
$A115 | b14 file $01A125 | JSR $cbf1
$A118 | b14 file $01A128 | RTS
$A119 | b14 file $01A129 | JSR $b870
$A11C | b14 file $01A12C | BCC $a136
$A11E | b14 file $01A12E | LDA #$09
$A120 | b14 file $01A130 | STA $00bb
$A123 | b14 file $01A133 | LDA $0560
$A126 | b14 file $01A136 | STA $00
$A128 | b14 file $01A138 | LDA #$00
$A12A | b14 file $01A13A | STA $01
$A12C | b14 file $01A13C | LDY #$3d
$A12E | b14 file $01A13E | JSR $ee07 ; inline far target $A03C
$A133 | b14 file $01A143 | INC $0541
$A136 | b14 file $01A146 | RTS
$A137 | b14 file $01A147 | LDA $007e
$A13A | b14 file $01A14A | BNE $a15e
$A13C | b14 file $01A14C | LDA $0561
$A13F | b14 file $01A14F | STA $00
$A141 | b14 file $01A151 | LDA #$01
$A143 | b14 file $01A153 | STA $01
$A145 | b14 file $01A155 | LDY #$3d
$A147 | b14 file $01A157 | JSR $ee07 ; inline far target $A03C
$A14C | b14 file $01A15C | LDA #$01
$A14E | b14 file $01A15E | STA $0540
$A151 | b14 file $01A161 | LDA #$00
$A153 | b14 file $01A163 | STA $0541
$A156 | b14 file $01A166 | LDA #$00
$A158 | b14 file $01A168 | STA $0568
$A15B | b14 file $01A16B | STA $0569
$A15E | b14 file $01A16E | RTS
$A15F | b14 file $01A16F | JSR $bf4c
$A162 | b14 file $01A172 | LDA $0541
$A165 | b14 file $01A175 | JSR $eade ; inline targets: $A16E,$A183,$A235
$A16E | b14 file $01A17E | INC $0541
$A171 | b14 file $01A181 | LDA #$00
$A173 | b14 file $01A183 | STA $0545
$A176 | b14 file $01A186 | STA $0546
$A179 | b14 file $01A189 | STA $0547
$A17C | b14 file $01A18C | STA $057a
$A17F | b14 file $01A18F | JSR $d067
$A182 | b14 file $01A192 | RTS
$A183 | b14 file $01A193 | JSR $a32f
$A186 | b14 file $01A196 | JSR $a2a9
$A189 | b14 file $01A199 | LDA $0568
$A18C | b14 file $01A19C | ORA $0569
$A18F | b14 file $01A19F | BEQ $a1b4
$A191 | b14 file $01A1A1 | LDA $0569
$A194 | b14 file $01A1A4 | STA $0549
$A197 | b14 file $01A1A7 | LDA #$03
$A199 | b14 file $01A1A9 | STA $0540
$A19C | b14 file $01A1AC | LDA #$00
$A19E | b14 file $01A1AE | STA $0541
$A1A1 | b14 file $01A1B1 | LDA #$01
$A1A3 | b14 file $01A1B3 | STA $054b
$A1A6 | b14 file $01A1B6 | LDA #$01
$A1A8 | b14 file $01A1B8 | STA $054c
$A1AB | b14 file $01A1BB | LDA #$00
$A1AD | b14 file $01A1BD | STA $0568
$A1B0 | b14 file $01A1C0 | STA $0569
$A1B3 | b14 file $01A1C3 | RTS
$A1B4 | b14 file $01A1C4 | LDA #$00
$A1B6 | b14 file $01A1C6 | STA $0568
$A1B9 | b14 file $01A1C9 | STA $0569
$A1BC | b14 file $01A1CC | LDY $0546
$A1BF | b14 file $01A1CF | LDA $a231,Y
$A1C2 | b14 file $01A1D2 | STA $00
$A1C4 | b14 file $01A1D4 | LDY $0545
$A1C7 | b14 file $01A1D7 | LDA $05c2,Y
$A1CA | b14 file $01A1DA | CMP #$ff
$A1CC | b14 file $01A1DC | BEQ $a20f
$A1CE | b14 file $01A1DE | AND #$0f
$A1D0 | b14 file $01A1E0 | CMP $00
$A1D2 | b14 file $01A1E2 | BNE $a20f
$A1D4 | b14 file $01A1E4 | LDA #$02
$A1D6 | b14 file $01A1E6 | STA $0540
$A1D9 | b14 file $01A1E9 | LDA #$00
$A1DB | b14 file $01A1EB | STA $0541
$A1DE | b14 file $01A1EE | LDA #$00
$A1E0 | b14 file $01A1F0 | LDY $0545
$A1E3 | b14 file $01A1F3 | CPY #$0b
$A1E5 | b14 file $01A1F5 | BCC $a1e9
$A1E7 | b14 file $01A1F7 | LDA #$04
$A1E9 | b14 file $01A1F9 | STA $00
$A1EB | b14 file $01A1FB | LDA $05c2,Y
$A1EE | b14 file $01A1FE | AND #$0f
$A1F0 | b14 file $01A200 | ORA $00
$A1F2 | b14 file $01A202 | TAY
$A1F3 | b14 file $01A203 | LDA $0550,Y
$A1F6 | b14 file $01A206 | STA $054f
$A1F9 | b14 file $01A209 | CMP #$80
$A1FB | b14 file $01A20B | BNE $a20e
$A1FD | b14 file $01A20D | LDA #$00
$A1FF | b14 file $01A20F | STA $054f
$A202 | b14 file $01A212 | JSR $e87a
$A205 | b14 file $01A215 | AND #$01
$A207 | b14 file $01A217 | BNE $a20e
$A209 | b14 file $01A219 | LDA #$02
$A20B | b14 file $01A21B | STA $054f
$A20E | b14 file $01A21E | RTS
$A20F | b14 file $01A21F | LDA #$00
$A211 | b14 file $01A221 | STA $0547
$A214 | b14 file $01A224 | INC $0545
$A217 | b14 file $01A227 | LDA $0545
$A21A | b14 file $01A22A | CMP #$16
$A21C | b14 file $01A22C | BCC $a1bc
$A21E | b14 file $01A22E | LDA #$00
$A220 | b14 file $01A230 | STA $0545
$A223 | b14 file $01A233 | INC $0546
$A226 | b14 file $01A236 | LDA $0546
$A229 | b14 file $01A239 | CMP #$04
$A22B | b14 file $01A23B | BCC $a1bc
$A22D | b14 file $01A23D | INC $0541
$A230 | b14 file $01A240 | RTS
$A235 | b14 file $01A245 | LDA #$01
$A237 | b14 file $01A247 | STA $0541
$A23A | b14 file $01A24A | JSR $b870
$A23D | b14 file $01A24D | BCC $a24c
$A23F | b14 file $01A24F | LDA #$e9
$A241 | b14 file $01A251 | STA $0310
$A244 | b14 file $01A254 | LDA #$00
$A246 | b14 file $01A256 | STA $0300
$A249 | b14 file $01A259 | JSR $cbf1
$A24C | b14 file $01A25C | LDA $0546
$A24F | b14 file $01A25F | CMP #$04
$A251 | b14 file $01A261 | BCS $a28c
$A253 | b14 file $01A263 | LDY $0546
$A256 | b14 file $01A266 | LDA $a231,Y
$A259 | b14 file $01A269 | CMP #$02
$A25B | b14 file $01A26B | BEQ $a26b
$A25D | b14 file $01A26D | CMP #$03
$A25F | b14 file $01A26F | BEQ $a26b
$A261 | b14 file $01A271 | INC $0547
$A264 | b14 file $01A274 | LDA $0547
$A267 | b14 file $01A277 | CMP #$01
$A269 | b14 file $01A279 | BEQ $a2a8
$A26B | b14 file $01A27B | LDA #$00
$A26D | b14 file $01A27D | STA $0547
$A270 | b14 file $01A280 | INC $0545
$A273 | b14 file $01A283 | LDA $0545
$A276 | b14 file $01A286 | CMP #$16
$A278 | b14 file $01A288 | BCC $a2a8
$A27A | b14 file $01A28A | LDA #$00
$A27C | b14 file $01A28C | STA $0545
$A27F | b14 file $01A28F | STA $0547
$A282 | b14 file $01A292 | INC $0546
$A285 | b14 file $01A295 | LDA $0546
$A288 | b14 file $01A298 | CMP #$04
$A28A | b14 file $01A29A | BCC $a2a8
$A28C | b14 file $01A29C | LDA #$00
$A28E | b14 file $01A29E | STA $0545
$A291 | b14 file $01A2A1 | STA $0546
$A294 | b14 file $01A2A4 | INC $057a
$A297 | b14 file $01A2A7 | JSR $b15b
$A29A | b14 file $01A2AA | JSR $d0ae
$A29D | b14 file $01A2AD | JSR $d067
$A2A0 | b14 file $01A2B0 | LDA #$00
$A2A2 | b14 file $01A2B2 | STA $0545
$A2A5 | b14 file $01A2B5 | STA $0546
$A2A8 | b14 file $01A2B8 | RTS
$A2A9 | b14 file $01A2B9 | LDA $0580
$A2AC | b14 file $01A2BC | CMP #$ff
$A2AE | b14 file $01A2BE | BNE $a2ec
$A2B0 | b14 file $01A2C0 | LDA $05ac
$A2B3 | b14 file $01A2C3 | BEQ $a2b9
$A2B5 | b14 file $01A2C5 | CMP #$ff
$A2B7 | b14 file $01A2C7 | BNE $a2ec
$A2B9 | b14 file $01A2C9 | LDA $0560
$A2BC | b14 file $01A2CC | STA $042c
$A2BF | b14 file $01A2CF | STA $0514
$A2C2 | b14 file $01A2D2 | LDA #$02
$A2C4 | b14 file $01A2D4 | STA $0515
$A2C7 | b14 file $01A2D7 | LDA $0561
$A2CA | b14 file $01A2DA | STA $0516
$A2CD | b14 file $01A2DD | LDA #$00
$A2CF | b14 file $01A2DF | STA $0517
$A2D2 | b14 file $01A2E2 | LDA #$04
$A2D4 | b14 file $01A2E4 | STA $0540
$A2D7 | b14 file $01A2E7 | LDA #$00
$A2D9 | b14 file $01A2E9 | STA $0541
$A2DC | b14 file $01A2EC | LDA #$d3
$A2DE | b14 file $01A2EE | JSR $f28b
$A2E1 | b14 file $01A2F1 | JSR $e57f
$A2E4 | b14 file $01A2F4 | LDA #$71
$A2E6 | b14 file $01A2F6 | JSR $e683
$A2E9 | b14 file $01A2F9 | PLA
$A2EA | b14 file $01A2FA | PLA
$A2EB | b14 file $01A2FB | RTS
$A2EC | b14 file $01A2FC | LDA $058b
$A2EF | b14 file $01A2FF | CMP #$ff
$A2F1 | b14 file $01A301 | BNE $a32e
$A2F3 | b14 file $01A303 | LDA $05b7
$A2F6 | b14 file $01A306 | BEQ $a2fc
$A2F8 | b14 file $01A308 | CMP #$ff
$A2FA | b14 file $01A30A | BNE $a32e
$A2FC | b14 file $01A30C | LDA $0560
$A2FF | b14 file $01A30F | STA $0514
$A302 | b14 file $01A312 | LDA #$00
$A304 | b14 file $01A314 | STA $0515
$A307 | b14 file $01A317 | LDA $0561
$A30A | b14 file $01A31A | STA $042c
$A30D | b14 file $01A31D | STA $0516
$A310 | b14 file $01A320 | LDA #$02
$A312 | b14 file $01A322 | STA $0517
$A315 | b14 file $01A325 | LDA #$04
$A317 | b14 file $01A327 | STA $0540
$A31A | b14 file $01A32A | LDA #$00
$A31C | b14 file $01A32C | STA $0541
$A31F | b14 file $01A32F | LDA #$d3
$A321 | b14 file $01A331 | JSR $f28b
$A324 | b14 file $01A334 | JSR $e57f
$A327 | b14 file $01A337 | LDA #$71
$A329 | b14 file $01A339 | JSR $e683
$A32C | b14 file $01A33C | PLA
$A32D | b14 file $01A33D | PLA
$A32E | b14 file $01A33E | RTS
$A32F | b14 file $01A33F | LDA $0580
$A332 | b14 file $01A342 | CMP #$fe
$A334 | b14 file $01A344 | BNE $a366
$A336 | b14 file $01A346 | LDA $0560
$A339 | b14 file $01A349 | STA $042c
$A33C | b14 file $01A34C | STA $0514
$A33F | b14 file $01A34F | LDA #$01
$A341 | b14 file $01A351 | STA $0515
$A344 | b14 file $01A354 | LDA $0561
$A347 | b14 file $01A357 | STA $0516
$A34A | b14 file $01A35A | LDA #$00
$A34C | b14 file $01A35C | STA $0517
$A34F | b14 file $01A35F | LDA #$00
$A351 | b14 file $01A361 | STA $0545
$A354 | b14 file $01A364 | LDA #$04
$A356 | b14 file $01A366 | STA $0540
$A359 | b14 file $01A369 | LDA #$03
$A35B | b14 file $01A36B | STA $0541
$A35E | b14 file $01A36E | LDA #$fa
$A360 | b14 file $01A370 | JSR $f28b
$A363 | b14 file $01A373 | PLA
$A364 | b14 file $01A374 | PLA
$A365 | b14 file $01A375 | RTS
$A366 | b14 file $01A376 | LDA $058b
$A369 | b14 file $01A379 | CMP #$fe
$A36B | b14 file $01A37B | BNE $a39c
$A36D | b14 file $01A37D | LDA $0560
$A370 | b14 file $01A380 | STA $0514
$A373 | b14 file $01A383 | LDA #$00
$A375 | b14 file $01A385 | STA $0515
$A378 | b14 file $01A388 | LDA $0561
$A37B | b14 file $01A38B | STA $042c
$A37E | b14 file $01A38E | STA $0516
$A381 | b14 file $01A391 | LDA #$01
$A383 | b14 file $01A393 | STA $0517
$A386 | b14 file $01A396 | LDA #$04
$A388 | b14 file $01A398 | STA $0540
$A38B | b14 file $01A39B | LDA #$03
$A38D | b14 file $01A39D | STA $0541
$A390 | b14 file $01A3A0 | LDA #$fa
$A392 | b14 file $01A3A2 | JSR $f28b
$A395 | b14 file $01A3A5 | LDA #$01
$A397 | b14 file $01A3A7 | STA $0545
$A39A | b14 file $01A3AA | PLA
$A39B | b14 file $01A3AB | PLA
$A39C | b14 file $01A3AC | RTS
$A39D | b14 file $01A3AD | LDA #$00
$A39F | b14 file $01A3AF | JSR $ccde
$A3A2 | b14 file $01A3B2 | LDA $01
$A3A4 | b14 file $01A3B4 | LSR A
$A3A5 | b14 file $01A3B5 | BCC $a3ac
$A3A7 | b14 file $01A3B7 | LDA #$01
$A3A9 | b14 file $01A3B9 | STA $0568
$A3AC | b14 file $01A3BC | LDA #$01
$A3AE | b14 file $01A3BE | JSR $ccde
$A3B1 | b14 file $01A3C1 | LDA $01
$A3B3 | b14 file $01A3C3 | LSR A
$A3B4 | b14 file $01A3C4 | BCC $a3bb
$A3B6 | b14 file $01A3C6 | LDA #$01
$A3B8 | b14 file $01A3C8 | STA $0569
$A3BB | b14 file $01A3CB | RTS
$A3BC | b14 file $01A3CC | LDA $0541
$A3BF | b14 file $01A3CF | JSR $eade ; inline targets: $A3D0,$A3D4,$A3F2,$A407,$A488,$A4B5,$A3F2
$A3D0 | b14 file $01A3E0 | INC $0541
$A3D3 | b14 file $01A3E3 | RTS
$A3D4 | b14 file $01A3E4 | JSR $cd22
$A3D7 | b14 file $01A3E7 | JSR $b870
$A3DA | b14 file $01A3EA | BCC $a3f1
$A3DC | b14 file $01A3EC | JSR $cca8
$A3DF | b14 file $01A3EF | JSR $cd22
$A3E2 | b14 file $01A3F2 | LDA $01
$A3E4 | b14 file $01A3F4 | AND #$03
$A3E6 | b14 file $01A3F6 | BEQ $a3f1
$A3E8 | b14 file $01A3F8 | JSR $ecee
$A3EB | b14 file $01A3FB | INC $0541
$A3EE | b14 file $01A3FE | JSR $ca3f
$A3F1 | b14 file $01A401 | RTS
$A3F2 | b14 file $01A402 | LDA $0087
$A3F5 | b14 file $01A405 | BPL $a406
$A3F7 | b14 file $01A407 | LDA #$0b
$A3F9 | b14 file $01A409 | STA $0500
$A3FC | b14 file $01A40C | LDA #$00
$A3FE | b14 file $01A40E | STA $0501
$A401 | b14 file $01A411 | LDA #$03
$A403 | b14 file $01A413 | STA $007a
$A406 | b14 file $01A416 | RTS
$A407 | b14 file $01A417 | JSR $cd22
$A40A | b14 file $01A41A | JSR $b870
$A40D | b14 file $01A41D | BCC $a46c
$A40F | b14 file $01A41F | JSR $cca8
$A412 | b14 file $01A422 | JSR $cd22
$A415 | b14 file $01A425 | LDA $01
$A417 | b14 file $01A427 | AND #$03
$A419 | b14 file $01A429 | BEQ $a46c
$A41B | b14 file $01A42B | LDA #$64
$A41D | b14 file $01A42D | JSR $e862
$A420 | b14 file $01A430 | CMP #$20
$A422 | b14 file $01A432 | BCS $a42f
$A424 | b14 file $01A434 | JSR $ecee
$A427 | b14 file $01A437 | LDA #$02
$A429 | b14 file $01A439 | STA $0541
$A42C | b14 file $01A43C | JMP $ca3f
$A42F | b14 file $01A43F | INC $0541
$A432 | b14 file $01A442 | LDA #$0a
$A434 | b14 file $01A444 | JSR $e862
$A437 | b14 file $01A447 | CLC
$A438 | b14 file $01A448 | ADC #$05
$A43A | b14 file $01A44A | STA $042f
$A43D | b14 file $01A44D | STA $0548
$A440 | b14 file $01A450 | LDA #$00
$A442 | b14 file $01A452 | STA $0430
$A445 | b14 file $01A455 | STA $0431
$A448 | b14 file $01A458 | LDA #$7e
$A44A | b14 file $01A45A | JSR $f28b
$A44D | b14 file $01A45D | LDA $0545
$A450 | b14 file $01A460 | BNE $a46d
$A452 | b14 file $01A462 | LDA $0514
$A455 | b14 file $01A465 | STA $042c
$A458 | b14 file $01A468 | LDA $05ac
$A45B | b14 file $01A46B | SEC
$A45C | b14 file $01A46C | SBC $0548
$A45F | b14 file $01A46F | BCS $a469
$A461 | b14 file $01A471 | LDA $05ac
$A464 | b14 file $01A474 | STA $042f
$A467 | b14 file $01A477 | LDA #$00
$A469 | b14 file $01A479 | STA $05ac
$A46C | b14 file $01A47C | RTS
$A46D | b14 file $01A47D | LDA $0516
$A470 | b14 file $01A480 | STA $042c
$A473 | b14 file $01A483 | LDA $05b7
$A476 | b14 file $01A486 | SEC
$A477 | b14 file $01A487 | SBC $0548
$A47A | b14 file $01A48A | BCS $a484
$A47C | b14 file $01A48C | LDA $05b7
$A47F | b14 file $01A48F | STA $042f
$A482 | b14 file $01A492 | LDA #$00
$A484 | b14 file $01A494 | STA $05b7
$A487 | b14 file $01A497 | RTS
$A488 | b14 file $01A498 | JSR $cd22
$A48B | b14 file $01A49B | JSR $b870
$A48E | b14 file $01A49E | BCC $a4b4
$A490 | b14 file $01A4A0 | JSR $cca8
$A493 | b14 file $01A4A3 | JSR $cd22
$A496 | b14 file $01A4A6 | LDA $01
$A498 | b14 file $01A4A8 | AND #$03
$A49A | b14 file $01A4AA | BEQ $a4b4
$A49C | b14 file $01A4AC | JSR $a4d8
$A49F | b14 file $01A4AF | BEQ $a4ac
$A4A1 | b14 file $01A4B1 | JSR $ecee
$A4A4 | b14 file $01A4B4 | LDA #$02
$A4A6 | b14 file $01A4B6 | STA $0541
$A4A9 | b14 file $01A4B9 | JMP $ca3f
$A4AC | b14 file $01A4BC | INC $0541
$A4AF | b14 file $01A4BF | LDA #$d3
$A4B1 | b14 file $01A4C1 | JSR $f28b
$A4B4 | b14 file $01A4C4 | RTS
$A4B5 | b14 file $01A4C5 | JSR $cd22
$A4B8 | b14 file $01A4C8 | JSR $b870
$A4BB | b14 file $01A4CB | BCC $a4d7
$A4BD | b14 file $01A4CD | JSR $cca8
$A4C0 | b14 file $01A4D0 | JSR $cd22
$A4C3 | b14 file $01A4D3 | LDA $01
$A4C5 | b14 file $01A4D5 | AND #$03
$A4C7 | b14 file $01A4D7 | BEQ $a4d7
$A4C9 | b14 file $01A4D9 | JSR $a4e6
$A4CC | b14 file $01A4DC | JSR $ecee
$A4CF | b14 file $01A4DF | LDA #$02
$A4D1 | b14 file $01A4E1 | STA $0541
$A4D4 | b14 file $01A4E4 | JMP $ca3f
$A4D7 | b14 file $01A4E7 | RTS
$A4D8 | b14 file $01A4E8 | LDA $05ac
$A4DB | b14 file $01A4EB | LDY $0545
$A4DE | b14 file $01A4EE | BEQ $a4e3
$A4E0 | b14 file $01A4F0 | LDA $05b7
$A4E3 | b14 file $01A4F3 | CMP #$00
$A4E5 | b14 file $01A4F5 | RTS
$A4E6 | b14 file $01A4F6 | LDY $0545
$A4E9 | b14 file $01A4F9 | BEQ $a4f1
$A4EB | b14 file $01A4FB | LDA #$02
$A4ED | b14 file $01A4FD | STA $0517
$A4F0 | b14 file $01A500 | RTS
$A4F1 | b14 file $01A501 | LDA #$02
$A4F3 | b14 file $01A503 | STA $0515
$A4F6 | b14 file $01A506 | RTS
$A4F7 | b14 file $01A507 | JSR $bf4c
$A4FA | b14 file $01A50A | JSR $a39d
$A4FD | b14 file $01A50D | LDA $0541
$A500 | b14 file $01A510 | JSR $eade ; inline targets: $A519,$A5C4,$A5F3,$A61D,$A654,$A6E4,$A702,$A72E,$A74A,$A75B,$A7E0
$A519 | b14 file $01A529 | LDA #$00
$A51B | b14 file $01A52B | STA $0548
$A51E | b14 file $01A52E | LDA #$00
$A520 | b14 file $01A530 | STA $054c
$A523 | b14 file $01A533 | LDA $054f
$A526 | b14 file $01A536 | CMP #$01
$A528 | b14 file $01A538 | BEQ $a58c
$A52A | b14 file $01A53A | LDY $0545
$A52D | b14 file $01A53D | LDA $05c2,Y
$A530 | b14 file $01A540 | AND #$0f
$A532 | b14 file $01A542 | CMP #$02
$A534 | b14 file $01A544 | BNE $a561
$A536 | b14 file $01A546 | JSR $c30f
$A539 | b14 file $01A549 | LDA $0549
$A53C | b14 file $01A54C | BMI $a561
$A53E | b14 file $01A54E | LDA $054f
$A541 | b14 file $01A551 | CMP #$03
$A543 | b14 file $01A553 | BNE $a54c
$A545 | b14 file $01A555 | LDA $05c2,X
$A548 | b14 file $01A558 | AND #$03
$A54A | b14 file $01A55A | BEQ $a561
$A54C | b14 file $01A55C | LDY $0545
$A54F | b14 file $01A55F | LDA $05c2,Y
$A552 | b14 file $01A562 | STA $054c
$A555 | b14 file $01A565 | LDA $0549
$A558 | b14 file $01A568 | JSR $aa0f
$A55B | b14 file $01A56B | LDA #$06
$A55D | b14 file $01A56D | STA $0541
$A560 | b14 file $01A570 | RTS
$A561 | b14 file $01A571 | JSR $c20f
$A564 | b14 file $01A574 | LDA $0549
$A567 | b14 file $01A577 | BMI $a58c
$A569 | b14 file $01A579 | LDA $054f
$A56C | b14 file $01A57C | CMP #$03
$A56E | b14 file $01A57E | BNE $a577
$A570 | b14 file $01A580 | LDA $05c2,X
$A573 | b14 file $01A583 | AND #$03
$A575 | b14 file $01A585 | BEQ $a58c
$A577 | b14 file $01A587 | LDY $0545
$A57A | b14 file $01A58A | LDA $05c2,Y
$A57D | b14 file $01A58D | STA $054b
$A580 | b14 file $01A590 | LDA $0549
$A583 | b14 file $01A593 | JSR $aa0f
$A586 | b14 file $01A596 | LDA #$03
$A588 | b14 file $01A598 | STA $0541
$A58B | b14 file $01A59B | RTS
$A58C | b14 file $01A59C | LDA $054f
$A58F | b14 file $01A59F | CMP #$02
$A591 | b14 file $01A5A1 | BEQ $a5c1
$A593 | b14 file $01A5A3 | LDY $0545
$A596 | b14 file $01A5A6 | BEQ $a5a5
$A598 | b14 file $01A5A8 | CPY #$0b
$A59A | b14 file $01A5AA | BNE $a5ac
$A59C | b14 file $01A5AC | LDA $0574
$A59F | b14 file $01A5AF | AND #$0f
$A5A1 | b14 file $01A5B1 | BNE $a5c1
$A5A3 | b14 file $01A5B3 | BEQ $a5ac
$A5A5 | b14 file $01A5B5 | LDA $0574
$A5A8 | b14 file $01A5B8 | AND #$f0
$A5AA | b14 file $01A5BA | BNE $a5c1
$A5AC | b14 file $01A5BC | JSR $a7fe
$A5AF | b14 file $01A5BF | JSR $c064
$A5B2 | b14 file $01A5C2 | LDA $0549
$A5B5 | b14 file $01A5C5 | BMI $a5c1
$A5B7 | b14 file $01A5C7 | INC $0541
$A5BA | b14 file $01A5CA | LDA $0549
$A5BD | b14 file $01A5CD | JSR $aa0f
$A5C0 | b14 file $01A5D0 | RTS
$A5C1 | b14 file $01A5D1 | JMP $a606
$A5C4 | b14 file $01A5D4 | LDA #$00
$A5C6 | b14 file $01A5D6 | STA $12
$A5C8 | b14 file $01A5D8 | LDA $0545
$A5CB | b14 file $01A5DB | STA $13
$A5CD | b14 file $01A5DD | JSR $b882
$A5D0 | b14 file $01A5E0 | INC $0541
$A5D3 | b14 file $01A5E3 | LDA #$00
$A5D5 | b14 file $01A5E5 | STA $0548
$A5D8 | b14 file $01A5E8 | LDY $0545
$A5DB | b14 file $01A5EB | LDA $0580,Y
$A5DE | b14 file $01A5EE | ASL A
$A5DF | b14 file $01A5EF | ASL A
$A5E0 | b14 file $01A5F0 | ASL A
$A5E1 | b14 file $01A5F1 | ASL A
$A5E2 | b14 file $01A5F2 | STA $054a
$A5E5 | b14 file $01A5F5 | LDA $0596,Y
$A5E8 | b14 file $01A5F8 | ASL A
$A5E9 | b14 file $01A5F9 | ASL A
$A5EA | b14 file $01A5FA | ASL A
$A5EB | b14 file $01A5FB | ASL A
$A5EC | b14 file $01A5FC | STA $054b
$A5EF | b14 file $01A5FF | JSR $bb8f
$A5F2 | b14 file $01A602 | RTS
$A5F3 | b14 file $01A603 | JSR $bb8f
$A5F6 | b14 file $01A606 | JSR $a9a0
$A5F9 | b14 file $01A609 | INC $0548
$A5FC | b14 file $01A60C | LDA $0548
$A5FF | b14 file $01A60F | CMP #$10
$A601 | b14 file $01A611 | BCC $a61c
$A603 | b14 file $01A613 | JSR $a9bd
$A606 | b14 file $01A616 | LDA #$10
$A608 | b14 file $01A618 | STA $12
$A60A | b14 file $01A61A | LDA $0545
$A60D | b14 file $01A61D | STA $13
$A60F | b14 file $01A61F | JSR $b882
$A612 | b14 file $01A622 | LDA #$01
$A614 | b14 file $01A624 | STA $0540
$A617 | b14 file $01A627 | LDA #$02
$A619 | b14 file $01A629 | STA $0541
$A61C | b14 file $01A62C | RTS
$A61D | b14 file $01A62D | LDA $0545
$A620 | b14 file $01A630 | BEQ $a626
$A622 | b14 file $01A632 | CMP #$0b
$A624 | b14 file $01A634 | BNE $a63a
$A626 | b14 file $01A636 | LDA $054a
$A629 | b14 file $01A639 | BEQ $a62f
$A62B | b14 file $01A63B | CMP #$0b
$A62D | b14 file $01A63D | BNE $a63a
$A62F | b14 file $01A63F | LDA #$05
$A631 | b14 file $01A641 | STA $0540
$A634 | b14 file $01A644 | LDA #$00
$A636 | b14 file $01A646 | STA $0541
$A639 | b14 file $01A649 | RTS
$A63A | b14 file $01A64A | LDA #$10
$A63C | b14 file $01A64C | STA $12
$A63E | b14 file $01A64E | LDA $0545
$A641 | b14 file $01A651 | STA $13
$A643 | b14 file $01A653 | JSR $b882
$A646 | b14 file $01A656 | INC $0541
$A649 | b14 file $01A659 | LDA #$00
$A64B | b14 file $01A65B | STA $0548
$A64E | b14 file $01A65E | LDA #$5e
$A650 | b14 file $01A660 | JSR $e609
$A653 | b14 file $01A663 | RTS
$A654 | b14 file $01A664 | JSR $be15
$A657 | b14 file $01A667 | LDY $054a
$A65A | b14 file $01A66A | JSR $a6d0
$A65D | b14 file $01A66D | INC $0548
$A660 | b14 file $01A670 | LDA $0548
$A663 | b14 file $01A673 | CMP #$20
$A665 | b14 file $01A675 | BCC $a653
$A667 | b14 file $01A677 | LDY $0545
$A66A | b14 file $01A67A | LDA $054b
$A66D | b14 file $01A67D | STA $05c2,Y
$A670 | b14 file $01A680 | LDY $0545
$A673 | b14 file $01A683 | LDA $05c2,Y
$A676 | b14 file $01A686 | AND #$0f
$A678 | b14 file $01A688 | CMP #$02
$A67A | b14 file $01A68A | BNE $a682
$A67C | b14 file $01A68C | JSR $a84d
$A67F | b14 file $01A68F | JMP $a685
$A682 | b14 file $01A692 | JSR $a8f2
$A685 | b14 file $01A695 | LDY $054a
$A688 | b14 file $01A698 | LDA $05ac,Y
$A68B | b14 file $01A69B | SEC
$A68C | b14 file $01A69C | SBC $00
$A68E | b14 file $01A69E | STA $05ac,Y
$A691 | b14 file $01A6A1 | BEQ $a695
$A693 | b14 file $01A6A3 | BCS $a6bd
$A695 | b14 file $01A6A5 | LDA $01
$A697 | b14 file $01A6A7 | STA $00
$A699 | b14 file $01A6A9 | JSR $a7c5
$A69C | b14 file $01A6AC | LDA #$00
$A69E | b14 file $01A6AE | STA $12
$A6A0 | b14 file $01A6B0 | LDA $054a
$A6A3 | b14 file $01A6B3 | STA $13
$A6A5 | b14 file $01A6B5 | JSR $b882
$A6A8 | b14 file $01A6B8 | LDY $054a
$A6AB | b14 file $01A6BB | LDA #$ff
$A6AD | b14 file $01A6BD | STA $0580,Y
$A6B0 | b14 file $01A6C0 | STA $0596,Y
$A6B3 | b14 file $01A6C3 | STA $05ac,Y
$A6B6 | b14 file $01A6C6 | STA $05c2,Y
$A6B9 | b14 file $01A6C9 | INC $0541
$A6BC | b14 file $01A6CC | RTS
$A6BD | b14 file $01A6CD | JSR $a7c5
$A6C0 | b14 file $01A6D0 | LDA #$10
$A6C2 | b14 file $01A6D2 | STA $12
$A6C4 | b14 file $01A6D4 | LDA $054a
$A6C7 | b14 file $01A6D7 | STA $13
$A6C9 | b14 file $01A6D9 | JSR $b882
$A6CC | b14 file $01A6DC | INC $0541
$A6CF | b14 file $01A6DF | RTS
$A6D0 | b14 file $01A6E0 | LDA $005e
$A6D3 | b14 file $01A6E3 | AND #$03
$A6D5 | b14 file $01A6E5 | BEQ $a6e3
$A6D7 | b14 file $01A6E7 | LDA $005e
$A6DA | b14 file $01A6EA | AND #$08
$A6DC | b14 file $01A6EC | STA $12
$A6DE | b14 file $01A6EE | STY $13
$A6E0 | b14 file $01A6F0 | JSR $b882
$A6E3 | b14 file $01A6F3 | RTS
$A6E4 | b14 file $01A6F4 | LDA $007e
$A6E7 | b14 file $01A6F7 | AND #$04
$A6E9 | b14 file $01A6F9 | BNE $a701
$A6EB | b14 file $01A6FB | LDA #$10
$A6ED | b14 file $01A6FD | STA $12
$A6EF | b14 file $01A6FF | LDA $0545
$A6F2 | b14 file $01A702 | STA $13
$A6F4 | b14 file $01A704 | JSR $b882
$A6F7 | b14 file $01A707 | LDA #$01
$A6F9 | b14 file $01A709 | STA $0540
$A6FC | b14 file $01A70C | LDA #$02
$A6FE | b14 file $01A70E | STA $0541
$A701 | b14 file $01A711 | RTS
$A702 | b14 file $01A712 | LDA #$10
$A704 | b14 file $01A714 | STA $12
$A706 | b14 file $01A716 | LDA $0545
$A709 | b14 file $01A719 | STA $13
$A70B | b14 file $01A71B | JSR $b882
$A70E | b14 file $01A71E | INC $0541
$A711 | b14 file $01A721 | LDY $0545
$A714 | b14 file $01A724 | LDA $0580,Y
$A717 | b14 file $01A727 | ASL A
$A718 | b14 file $01A728 | ASL A
$A719 | b14 file $01A729 | ASL A
$A71A | b14 file $01A72A | ASL A
$A71B | b14 file $01A72B | STA $054a
$A71E | b14 file $01A72E | LDA $0596,Y
$A721 | b14 file $01A731 | ASL A
$A722 | b14 file $01A732 | ASL A
$A723 | b14 file $01A733 | ASL A
$A724 | b14 file $01A734 | ASL A
$A725 | b14 file $01A735 | STA $054b
$A728 | b14 file $01A738 | LDA #$5a
$A72A | b14 file $01A73A | JSR $e69b
$A72D | b14 file $01A73D | RTS
$A72E | b14 file $01A73E | JSR $be76
$A731 | b14 file $01A741 | JSR $a9e6
$A734 | b14 file $01A744 | DEC $0548
$A737 | b14 file $01A747 | DEC $0548
$A73A | b14 file $01A74A | BPL $a7b1
$A73C | b14 file $01A74C | LDA #$08
$A73E | b14 file $01A74E | STA $0548
$A741 | b14 file $01A751 | INC $0541
$A744 | b14 file $01A754 | LDA #$5d
$A746 | b14 file $01A756 | JSR $e609
$A749 | b14 file $01A759 | RTS
$A74A | b14 file $01A75A | JSR $bf15
$A74D | b14 file $01A75D | DEC $0548
$A750 | b14 file $01A760 | BPL $a75a
$A752 | b14 file $01A762 | LDA #$18
$A754 | b14 file $01A764 | STA $0548
$A757 | b14 file $01A767 | INC $0541
$A75A | b14 file $01A76A | RTS
$A75B | b14 file $01A76B | LDY $054d
$A75E | b14 file $01A76E | JSR $a6d0
$A761 | b14 file $01A771 | DEC $0548
$A764 | b14 file $01A774 | BPL $a7b1
$A766 | b14 file $01A776 | LDY $0545
$A769 | b14 file $01A779 | LDA $054c
$A76C | b14 file $01A77C | STA $05c2,Y
$A76F | b14 file $01A77F | LDA $054d
$A772 | b14 file $01A782 | STA $054a
$A775 | b14 file $01A785 | JSR $a871
$A778 | b14 file $01A788 | LDY $054d
$A77B | b14 file $01A78B | LDA $05ac,Y
$A77E | b14 file $01A78E | STA $01
$A780 | b14 file $01A790 | SEC
$A781 | b14 file $01A791 | SBC $00
$A783 | b14 file $01A793 | STA $05ac,Y
$A786 | b14 file $01A796 | BEQ $a78a
$A788 | b14 file $01A798 | BCS $a7b2
$A78A | b14 file $01A79A | LDA $01
$A78C | b14 file $01A79C | STA $00
$A78E | b14 file $01A79E | JSR $a7c5
$A791 | b14 file $01A7A1 | LDA #$00
$A793 | b14 file $01A7A3 | STA $12
$A795 | b14 file $01A7A5 | LDA $054d
$A798 | b14 file $01A7A8 | STA $13
$A79A | b14 file $01A7AA | JSR $b882
$A79D | b14 file $01A7AD | LDY $054d
$A7A0 | b14 file $01A7B0 | LDA #$ff
$A7A2 | b14 file $01A7B2 | STA $0580,Y
$A7A5 | b14 file $01A7B5 | STA $0596,Y
$A7A8 | b14 file $01A7B8 | STA $05ac,Y
$A7AB | b14 file $01A7BB | STA $05c2,Y
$A7AE | b14 file $01A7BE | INC $0541
$A7B1 | b14 file $01A7C1 | RTS
$A7B2 | b14 file $01A7C2 | JSR $a7c5
$A7B5 | b14 file $01A7C5 | LDA #$10
$A7B7 | b14 file $01A7C7 | STA $12
$A7B9 | b14 file $01A7C9 | LDA $054d
$A7BC | b14 file $01A7CC | STA $13
$A7BE | b14 file $01A7CE | JSR $b882
$A7C1 | b14 file $01A7D1 | INC $0541
$A7C4 | b14 file $01A7D4 | RTS
$A7C5 | b14 file $01A7D5 | LDA $00
$A7C7 | b14 file $01A7D7 | STA $0b
$A7C9 | b14 file $01A7D9 | LDA #$00
$A7CB | b14 file $01A7DB | STA $0c
$A7CD | b14 file $01A7DD | LDA $0560
$A7D0 | b14 file $01A7E0 | LDY $0545
$A7D3 | b14 file $01A7E3 | CPY #$0b
$A7D5 | b14 file $01A7E5 | BCC $a7da
$A7D7 | b14 file $01A7E7 | LDA $0561
$A7DA | b14 file $01A7EA | STA $0a
$A7DC | b14 file $01A7EC | JSR $d7fb
$A7DF | b14 file $01A7EF | RTS
$A7E0 | b14 file $01A7F0 | LDA $007e
$A7E3 | b14 file $01A7F3 | AND #$04
$A7E5 | b14 file $01A7F5 | BNE $a7fd
$A7E7 | b14 file $01A7F7 | LDA #$10
$A7E9 | b14 file $01A7F9 | STA $12
$A7EB | b14 file $01A7FB | LDA $0545
$A7EE | b14 file $01A7FE | STA $13
$A7F0 | b14 file $01A800 | JSR $b882
$A7F3 | b14 file $01A803 | LDA #$01
$A7F5 | b14 file $01A805 | STA $0540
$A7F8 | b14 file $01A808 | LDA #$02
$A7FA | b14 file $01A80A | STA $0541
$A7FD | b14 file $01A80D | RTS
$A7FE | b14 file $01A80E | LDY $0545
$A801 | b14 file $01A811 | CPY #$0b
$A803 | b14 file $01A813 | BCS $a814
$A805 | b14 file $01A815 | LDA $054f
$A808 | b14 file $01A818 | CMP #$01
$A80A | b14 file $01A81A | BNE $a84c
$A80C | b14 file $01A81C | LDA $0580,Y
$A80F | b14 file $01A81F | BNE $a84c
$A811 | b14 file $01A821 | JMP $a824
$A814 | b14 file $01A824 | LDA $054f
$A817 | b14 file $01A827 | CMP #$01
$A819 | b14 file $01A829 | BNE $a84c
$A81B | b14 file $01A82B | LDA $0580,Y
$A81E | b14 file $01A82E | AND #$0f
$A820 | b14 file $01A830 | CMP #$0f
$A822 | b14 file $01A832 | BNE $a84c
$A824 | b14 file $01A834 | LDA #$00
$A826 | b14 file $01A836 | STA $12
$A828 | b14 file $01A838 | LDA $0545
$A82B | b14 file $01A83B | STA $13
$A82D | b14 file $01A83D | JSR $b882
$A830 | b14 file $01A840 | LDA #$01
$A832 | b14 file $01A842 | STA $0540
$A835 | b14 file $01A845 | LDA #$02
$A837 | b14 file $01A847 | STA $0541
$A83A | b14 file $01A84A | LDY $0545
$A83D | b14 file $01A84D | LDA #$fe
$A83F | b14 file $01A84F | STA $0580,Y
$A842 | b14 file $01A852 | STA $0596,Y
$A845 | b14 file $01A855 | LDA #$ff
$A847 | b14 file $01A857 | STA $05c2,Y
$A84A | b14 file $01A85A | PLA
$A84B | b14 file $01A85B | PLA
$A84C | b14 file $01A85C | RTS
$A84D | b14 file $01A85D | LDA $056a
$A850 | b14 file $01A860 | PHA
$A851 | b14 file $01A861 | LDY #$3c
$A853 | b14 file $01A863 | JSR $a8cf
$A856 | b14 file $01A866 | STA $056a
$A859 | b14 file $01A869 | LDA $056b
$A85C | b14 file $01A86C | PHA
$A85D | b14 file $01A86D | LDY #$3c
$A85F | b14 file $01A86F | JSR $a8cf
$A862 | b14 file $01A872 | STA $056b
$A865 | b14 file $01A875 | JSR $a8f2
$A868 | b14 file $01A878 | PLA
$A869 | b14 file $01A879 | STA $056b
$A86C | b14 file $01A87C | PLA
$A86D | b14 file $01A87D | STA $056a
$A870 | b14 file $01A880 | RTS
$A871 | b14 file $01A881 | LDA $056a
$A874 | b14 file $01A884 | PHA
$A875 | b14 file $01A885 | LDY #$46
$A877 | b14 file $01A887 | JSR $a8cf
$A87A | b14 file $01A88A | STA $056a
$A87D | b14 file $01A88D | LDA $0577
$A880 | b14 file $01A890 | AND #$0f
$A882 | b14 file $01A892 | BEQ $a89a
$A884 | b14 file $01A894 | JSR $e87a
$A887 | b14 file $01A897 | AND #$0f
$A889 | b14 file $01A899 | CMP #$0a
$A88B | b14 file $01A89B | BCS $a884
$A88D | b14 file $01A89D | CLC
$A88E | b14 file $01A89E | ADC $056a
$A891 | b14 file $01A8A1 | CMP #$64
$A893 | b14 file $01A8A3 | BCC $a897
$A895 | b14 file $01A8A5 | LDA #$64
$A897 | b14 file $01A8A7 | STA $056a
$A89A | b14 file $01A8AA | LDA $056b
$A89D | b14 file $01A8AD | PHA
$A89E | b14 file $01A8AE | LDY #$46
$A8A0 | b14 file $01A8B0 | JSR $a8cf
$A8A3 | b14 file $01A8B3 | STA $056b
$A8A6 | b14 file $01A8B6 | LDA $0577
$A8A9 | b14 file $01A8B9 | AND #$f0
$A8AB | b14 file $01A8BB | BEQ $a8c3
$A8AD | b14 file $01A8BD | JSR $e87a
$A8B0 | b14 file $01A8C0 | AND #$0f
$A8B2 | b14 file $01A8C2 | CMP #$0a
$A8B4 | b14 file $01A8C4 | BCS $a8ad
$A8B6 | b14 file $01A8C6 | CLC
$A8B7 | b14 file $01A8C7 | ADC $056b
$A8BA | b14 file $01A8CA | CMP #$64
$A8BC | b14 file $01A8CC | BCC $a8c0
$A8BE | b14 file $01A8CE | LDA #$64
$A8C0 | b14 file $01A8D0 | STA $056b
$A8C3 | b14 file $01A8D3 | JSR $a8f2
$A8C6 | b14 file $01A8D6 | PLA
$A8C7 | b14 file $01A8D7 | STA $056b
$A8CA | b14 file $01A8DA | PLA
$A8CB | b14 file $01A8DB | STA $056a
$A8CE | b14 file $01A8DE | RTS
$A8CF | b14 file $01A8DF | STY $03
$A8D1 | b14 file $01A8E1 | STA $00
$A8D3 | b14 file $01A8E3 | LDA #$00
$A8D5 | b14 file $01A8E5 | STA $01
$A8D7 | b14 file $01A8E7 | STA $02
$A8D9 | b14 file $01A8E9 | JSR $ebe9
$A8DC | b14 file $01A8EC | LDA $06
$A8DE | b14 file $01A8EE | STA $01
$A8E0 | b14 file $01A8F0 | LDA $07
$A8E2 | b14 file $01A8F2 | STA $02
$A8E4 | b14 file $01A8F4 | LDA #$64
$A8E6 | b14 file $01A8F6 | STA $03
$A8E8 | b14 file $01A8F8 | LDA #$00
$A8EA | b14 file $01A8FA | STA $04
$A8EC | b14 file $01A8FC | JSR $ea7c
$A8EF | b14 file $01A8FF | LDA $01
$A8F1 | b14 file $01A901 | RTS
$A8F2 | b14 file $01A902 | LDY $0545
$A8F5 | b14 file $01A905 | CPY #$0b
$A8F7 | b14 file $01A907 | BCS $a907
$A8F9 | b14 file $01A909 | LDA $056a
$A8FC | b14 file $01A90C | CPY #$00
$A8FE | b14 file $01A90E | BNE $a915
$A900 | b14 file $01A910 | CLC
$A901 | b14 file $01A911 | ADC $0570
$A904 | b14 file $01A914 | JMP $a915
$A907 | b14 file $01A917 | LDA $056b
$A90A | b14 file $01A91A | CPY #$0b
$A90C | b14 file $01A91C | BNE $a915
$A90E | b14 file $01A91E | CLC
$A90F | b14 file $01A91F | ADC $0571
$A912 | b14 file $01A922 | JMP $a915
$A915 | b14 file $01A925 | PHA
$A916 | b14 file $01A926 | LDA $05ac,Y
$A919 | b14 file $01A929 | LDY #$14
$A91B | b14 file $01A92B | CMP #$0f
$A91D | b14 file $01A92D | BCC $a93f
$A91F | b14 file $01A92F | LDY #$28
$A921 | b14 file $01A931 | CMP #$23
$A923 | b14 file $01A933 | BCC $a93f
$A925 | b14 file $01A935 | LDY #$32
$A927 | b14 file $01A937 | CMP #$3c
$A929 | b14 file $01A939 | BCC $a93f
$A92B | b14 file $01A93B | LDY #$46
$A92D | b14 file $01A93D | CMP #$50
$A92F | b14 file $01A93F | BCC $a93f
$A931 | b14 file $01A941 | LDY #$55
$A933 | b14 file $01A943 | CMP #$5a
$A935 | b14 file $01A945 | BCC $a93f
$A937 | b14 file $01A947 | LDY #$5f
$A939 | b14 file $01A949 | CMP #$64
$A93B | b14 file $01A94B | BCC $a93f
$A93D | b14 file $01A94D | LDY #$64
$A93F | b14 file $01A94F | STY $03
$A941 | b14 file $01A951 | PLA
$A942 | b14 file $01A952 | STA $00
$A944 | b14 file $01A954 | LDA #$00
$A946 | b14 file $01A956 | STA $01
$A948 | b14 file $01A958 | STA $02
$A94A | b14 file $01A95A | JSR $ebe9
$A94D | b14 file $01A95D | LDA $06
$A94F | b14 file $01A95F | STA $01
$A951 | b14 file $01A961 | LDA $07
$A953 | b14 file $01A963 | STA $02
$A955 | b14 file $01A965 | LDA #$64
$A957 | b14 file $01A967 | STA $03
$A959 | b14 file $01A969 | LDA #$00
$A95B | b14 file $01A96B | STA $04
$A95D | b14 file $01A96D | JSR $ea7c
$A960 | b14 file $01A970 | LDA $01
$A962 | b14 file $01A972 | STA $00
$A964 | b14 file $01A974 | LDY $054a
$A967 | b14 file $01A977 | BEQ $a979
$A969 | b14 file $01A979 | CPY #$0b
$A96B | b14 file $01A97B | BEQ $a979
$A96D | b14 file $01A97D | LDA $05c2,Y
$A970 | b14 file $01A980 | AND #$0f
$A972 | b14 file $01A982 | CMP #$01
$A974 | b14 file $01A984 | BEQ $a994
$A976 | b14 file $01A986 | JMP $a99f
$A979 | b14 file $01A989 | LDA $00
$A97B | b14 file $01A98B | LSR A
$A97C | b14 file $01A98C | PHA
$A97D | b14 file $01A98D | LDA $056e
$A980 | b14 file $01A990 | CPY #$0b
$A982 | b14 file $01A992 | BCC $a987
$A984 | b14 file $01A994 | LDA $056f
$A987 | b14 file $01A997 | STA $00
$A989 | b14 file $01A999 | PLA
$A98A | b14 file $01A99A | SEC
$A98B | b14 file $01A99B | SBC $00
$A98D | b14 file $01A99D | BCS $a99d
$A98F | b14 file $01A99F | LDA #$00
$A991 | b14 file $01A9A1 | JMP $a99d
$A994 | b14 file $01A9A4 | LDA $00
$A996 | b14 file $01A9A6 | LSR A
$A997 | b14 file $01A9A7 | STA $00
$A999 | b14 file $01A9A9 | LSR A
$A99A | b14 file $01A9AA | CLC
$A99B | b14 file $01A9AB | ADC $00
$A99D | b14 file $01A9AD | STA $00
$A99F | b14 file $01A9AF | RTS
$A9A0 | b14 file $01A9B0 | LDA $0549
$A9A3 | b14 file $01A9B3 | BNE $a9a9
$A9A5 | b14 file $01A9B5 | DEC $054b
$A9A8 | b14 file $01A9B8 | RTS
$A9A9 | b14 file $01A9B9 | CMP #$01
$A9AB | b14 file $01A9BB | BNE $a9b1
$A9AD | b14 file $01A9BD | INC $054b
$A9B0 | b14 file $01A9C0 | RTS
$A9B1 | b14 file $01A9C1 | CMP #$02
$A9B3 | b14 file $01A9C3 | BNE $a9b9
$A9B5 | b14 file $01A9C5 | DEC $054a
$A9B8 | b14 file $01A9C8 | RTS
$A9B9 | b14 file $01A9C9 | INC $054a
$A9BC | b14 file $01A9CC | RTS
$A9BD | b14 file $01A9CD | LDA $0549
$A9C0 | b14 file $01A9D0 | BNE $a9c9
$A9C2 | b14 file $01A9D2 | LDX $0545
$A9C5 | b14 file $01A9D5 | DEC $0596,X
$A9C8 | b14 file $01A9D8 | RTS
$A9C9 | b14 file $01A9D9 | CMP #$01
$A9CB | b14 file $01A9DB | BNE $a9d4
$A9CD | b14 file $01A9DD | LDX $0545
$A9D0 | b14 file $01A9E0 | INC $0596,X
$A9D3 | b14 file $01A9E3 | RTS
$A9D4 | b14 file $01A9E4 | CMP #$02
$A9D6 | b14 file $01A9E6 | BNE $a9df
$A9D8 | b14 file $01A9E8 | LDX $0545
$A9DB | b14 file $01A9EB | DEC $0580,X
$A9DE | b14 file $01A9EE | RTS
$A9DF | b14 file $01A9EF | LDX $0545
$A9E2 | b14 file $01A9F2 | INC $0580,X
$A9E5 | b14 file $01A9F5 | RTS
$A9E6 | b14 file $01A9F6 | LDA $0549
$A9E9 | b14 file $01A9F9 | BNE $a9f2
$A9EB | b14 file $01A9FB | DEC $054b
$A9EE | b14 file $01A9FE | DEC $054b
$A9F1 | b14 file $01AA01 | RTS
$A9F2 | b14 file $01AA02 | CMP #$01
$A9F4 | b14 file $01AA04 | BNE $a9fd
$A9F6 | b14 file $01AA06 | INC $054b
$A9F9 | b14 file $01AA09 | INC $054b
$A9FC | b14 file $01AA0C | RTS
$A9FD | b14 file $01AA0D | CMP #$02
$A9FF | b14 file $01AA0F | BNE $aa08
$AA01 | b14 file $01AA11 | DEC $054a
$AA04 | b14 file $01AA14 | DEC $054a
$AA07 | b14 file $01AA17 | RTS
$AA08 | b14 file $01AA18 | INC $054a
$AA0B | b14 file $01AA1B | INC $054a
$AA0E | b14 file $01AA1E | RTS
$AA0F | b14 file $01AA1F | ASL A
$AA10 | b14 file $01AA20 | ASL A
$AA11 | b14 file $01AA21 | ASL A
$AA12 | b14 file $01AA22 | ASL A
$AA13 | b14 file $01AA23 | STA $00
$AA15 | b14 file $01AA25 | LDY $0545
$AA18 | b14 file $01AA28 | LDA $05c2,Y
$AA1B | b14 file $01AA2B | AND #$0f
$AA1D | b14 file $01AA2D | ORA $00
$AA1F | b14 file $01AA2F | STA $05c2,Y
$AA22 | b14 file $01AA32 | RTS
$AA23 | b14 file $01AA33 | LDY $0549
$AA26 | b14 file $01AA36 | LDA $0560,Y
$AA29 | b14 file $01AA39 | STA $0000
$AA2C | b14 file $01AA3C | LDA #$a5
$AA2E | b14 file $01AA3E | STA $000a
$AA31 | b14 file $01AA41 | LDX #$00
$AA33 | b14 file $01AA43 | LDY #$39
$AA35 | b14 file $01AA45 | JSR $ee07 ; inline far target $A000
$AA3A | b14 file $01AA4A | LDA $0541
$AA3D | b14 file $01AA4D | JSR $eade ; inline targets: $AA4A,$AABD,$AAF0,$AB75,$AB9A
$AA4A | b14 file $01AA5A | INC $0541
$AA4D | b14 file $01AA5D | LDA #$00
$AA4F | b14 file $01AA5F | STA $0548
$AA52 | b14 file $01AA62 | STA $054a
$AA55 | b14 file $01AA65 | LDA #$d1
$AA57 | b14 file $01AA67 | JSR $f26d
$AA5A | b14 file $01AA6A | LDY $0549
$AA5D | b14 file $01AA6D | LDA $0560,Y
$AA60 | b14 file $01AA70 | JSR $f2d7
$AA63 | b14 file $01AA73 | LDA $05ac
$AA66 | b14 file $01AA76 | LDY $0549
$AA69 | b14 file $01AA79 | BEQ $aa6e
$AA6B | b14 file $01AA7B | LDA $05b7
$AA6E | b14 file $01AA7E | STA $044c
$AA71 | b14 file $01AA81 | LDX $054b
$AA74 | b14 file $01AA84 | CPX #$01
$AA76 | b14 file $01AA86 | BEQ $aa7f
$AA78 | b14 file $01AA88 | LDY #$00
$AA7A | b14 file $01AA8A | LDA ($00),Y
$AA7C | b14 file $01AA8C | STA $044c
$AA7F | b14 file $01AA8F | LDY #$02
$AA81 | b14 file $01AA91 | LDA ($00),Y
$AA83 | b14 file $01AA93 | STA $044f
$AA86 | b14 file $01AA96 | LDY #$01
$AA88 | b14 file $01AA98 | LDA ($00),Y
$AA8A | b14 file $01AA9A | STA $0452
$AA8D | b14 file $01AA9D | LDA #$00
$AA8F | b14 file $01AA9F | STA $044d
$AA92 | b14 file $01AAA2 | STA $044e
$AA95 | b14 file $01AAA5 | STA $0450
$AA98 | b14 file $01AAA8 | STA $0451
$AA9B | b14 file $01AAAB | STA $0453
$AA9E | b14 file $01AAAE | STA $0454
$AAA1 | b14 file $01AAB1 | STA $0456
$AAA4 | b14 file $01AAB4 | STA $0457
$AAA7 | b14 file $01AAB7 | LDY #$03
$AAA9 | b14 file $01AAB9 | LDA ($00),Y
$AAAB | b14 file $01AABB | STA $0455
$AAAE | b14 file $01AABE | CMP #$64
$AAB0 | b14 file $01AAC0 | BNE $aab7
$AAB2 | b14 file $01AAC2 | LDA #$fe
$AAB4 | b14 file $01AAC4 | STA $0457
$AAB7 | b14 file $01AAC7 | LDA #$06
$AAB9 | b14 file $01AAC9 | STA $00bd
$AABC | b14 file $01AACC | RTS
$AABD | b14 file $01AACD | JSR $b870
$AAC0 | b14 file $01AAD0 | BCC $aaef
$AAC2 | b14 file $01AAD2 | LDA $007e
$AAC5 | b14 file $01AAD5 | AND #$04
$AAC7 | b14 file $01AAD7 | BNE $aaef
$AAC9 | b14 file $01AAD9 | LDA $0548
$AACC | b14 file $01AADC | CMP #$04
$AACE | b14 file $01AADE | BCS $aad7
$AAD0 | b14 file $01AAE0 | JSR $aca8
$AAD3 | b14 file $01AAE3 | INC $0548
$AAD6 | b14 file $01AAE6 | RTS
$AAD7 | b14 file $01AAE7 | INC $0541
$AADA | b14 file $01AAEA | LDA #$00
$AADC | b14 file $01AAEC | STA $0548
$AADF | b14 file $01AAEF | LDY $0549
$AAE2 | b14 file $01AAF2 | LDA $0560,Y
$AAE5 | b14 file $01AAF5 | STA $0000
$AAE8 | b14 file $01AAF8 | LDY #$3d
$AAEA | b14 file $01AAFA | JSR $ee07 ; inline far target $A030
$AAEF | b14 file $01AAFF | RTS
$AAF0 | b14 file $01AB00 | LDA $0549
$AAF3 | b14 file $01AB03 | JSR $ccde
$AAF6 | b14 file $01AB06 | LDA $0001
$AAF9 | b14 file $01AB09 | AND #$02
$AAFB | b14 file $01AB0B | BEQ $ab05
$AAFD | b14 file $01AB0D | LDA $008f
$AB00 | b14 file $01AB10 | EOR #$01
$AB02 | b14 file $01AB12 | STA $008f
$AB05 | b14 file $01AB15 | LDA $0549
$AB08 | b14 file $01AB18 | JSR $ccde
$AB0B | b14 file $01AB1B | LDA $0001
$AB0E | b14 file $01AB1E | AND #$01
$AB10 | b14 file $01AB20 | BEQ $ab6e
$AB12 | b14 file $01AB22 | LDA $0549
$AB15 | b14 file $01AB25 | ASL A
$AB16 | b14 file $01AB26 | ASL A
$AB17 | b14 file $01AB27 | TAY
$AB18 | b14 file $01AB28 | LDA $0550,Y
$AB1B | b14 file $01AB2B | CMP #$04
$AB1D | b14 file $01AB2D | BNE $ab51
$AB1F | b14 file $01AB2F | LDA $0574
$AB22 | b14 file $01AB32 | ORA $0575
$AB25 | b14 file $01AB35 | ORA $0576
$AB28 | b14 file $01AB38 | ORA $0577
$AB2B | b14 file $01AB3B | LDY $0549
$AB2E | b14 file $01AB3E | BEQ $ab37
$AB30 | b14 file $01AB40 | AND #$f0
$AB32 | b14 file $01AB42 | BNE $ab6e
$AB34 | b14 file $01AB44 | JMP $ab3b
$AB37 | b14 file $01AB47 | AND #$0f
$AB39 | b14 file $01AB49 | BNE $ab6e
$AB3B | b14 file $01AB4B | LDA #$08
$AB3D | b14 file $01AB4D | STA $0540
$AB40 | b14 file $01AB50 | LDA #$00
$AB42 | b14 file $01AB52 | STA $0541
$AB45 | b14 file $01AB55 | LDA $0549
$AB48 | b14 file $01AB58 | ASL A
$AB49 | b14 file $01AB59 | ASL A
$AB4A | b14 file $01AB5A | TAY
$AB4B | b14 file $01AB5B | LDA #$02
$AB4D | b14 file $01AB5D | STA $0550,Y
$AB50 | b14 file $01AB60 | RTS
$AB51 | b14 file $01AB61 | INC $0541
$AB54 | b14 file $01AB64 | LDA $054b
$AB57 | b14 file $01AB67 | CMP #$01
$AB59 | b14 file $01AB69 | BNE $abb1
$AB5B | b14 file $01AB6B | LDA #$e8
$AB5D | b14 file $01AB6D | STA $0310
$AB60 | b14 file $01AB70 | LDA #$e9
$AB62 | b14 file $01AB72 | STA $0311
$AB65 | b14 file $01AB75 | LDA #$00
$AB67 | b14 file $01AB77 | STA $0300
$AB6A | b14 file $01AB7A | JSR $cbf1
$AB6D | b14 file $01AB7D | RTS
$AB6E | b14 file $01AB7E | JSR $abc3
$AB71 | b14 file $01AB81 | JSR $ac73
$AB74 | b14 file $01AB84 | RTS
$AB75 | b14 file $01AB85 | LDA #$06
$AB77 | b14 file $01AB87 | STA $00bd
$AB7A | b14 file $01AB8A | JSR $b870
$AB7D | b14 file $01AB8D | BCC $ab99
$AB7F | b14 file $01AB8F | LDA #$09
$AB81 | b14 file $01AB91 | STA $00bb
$AB84 | b14 file $01AB94 | LDA $0560
$AB87 | b14 file $01AB97 | STA $0000
$AB8A | b14 file $01AB9A | LDA #$00
$AB8C | b14 file $01AB9C | STA $0001
$AB8F | b14 file $01AB9F | LDY #$3d
$AB91 | b14 file $01ABA1 | JSR $ee07 ; inline far target $A03C
$AB96 | b14 file $01ABA6 | INC $0541
$AB99 | b14 file $01ABA9 | RTS
$AB9A | b14 file $01ABAA | LDA $007e
$AB9D | b14 file $01ABAD | BNE $abc2
$AB9F | b14 file $01ABAF | LDA $0561
$ABA2 | b14 file $01ABB2 | STA $0000
$ABA5 | b14 file $01ABB5 | LDA #$01
$ABA7 | b14 file $01ABB7 | STA $0001
$ABAA | b14 file $01ABBA | LDY #$3d
$ABAC | b14 file $01ABBC | JSR $ee07 ; inline far target $A03C
$ABB1 | b14 file $01ABC1 | LDA #$00
$ABB3 | b14 file $01ABC3 | STA $008f
$ABB6 | b14 file $01ABC6 | LDA $054b
$ABB9 | b14 file $01ABC9 | STA $0540
$ABBC | b14 file $01ABCC | LDA $054c
$ABBF | b14 file $01ABCF | STA $0541
$ABC2 | b14 file $01ABD2 | RTS
$ABC3 | b14 file $01ABD3 | LDA $0549
$ABC6 | b14 file $01ABD6 | JSR $ccde
$ABC9 | b14 file $01ABD9 | LDA $0001
$ABCC | b14 file $01ABDC | AND #$80
$ABCE | b14 file $01ABDE | BEQ $abfa
$ABD0 | b14 file $01ABE0 | LDA $0549
$ABD3 | b14 file $01ABE3 | ASL A
$ABD4 | b14 file $01ABE4 | ASL A
$ABD5 | b14 file $01ABE5 | ORA $0548
$ABD8 | b14 file $01ABE8 | TAY
$ABD9 | b14 file $01ABE9 | LDA $0550,Y
$ABDC | b14 file $01ABEC | SEC
$ABDD | b14 file $01ABED | SBC #$01
$ABDF | b14 file $01ABEF | BCS $abf4
$ABE1 | b14 file $01ABF1 | LDA #$03
$ABE3 | b14 file $01ABF3 | CPY #$00
$ABE5 | b14 file $01ABF5 | BEQ $abeb
$ABE7 | b14 file $01ABF7 | CPY #$04
$ABE9 | b14 file $01ABF9 | BNE $abf4
$ABEB | b14 file $01ABFB | LDX $054b
$ABEE | b14 file $01ABFE | CPX #$01
$ABF0 | b14 file $01AC00 | BNE $abf4
$ABF2 | b14 file $01AC02 | LDA #$04
$ABF4 | b14 file $01AC04 | STA $0550,Y
$ABF7 | b14 file $01AC07 | JMP $ac6f
$ABFA | b14 file $01AC0A | LDA $0549
$ABFD | b14 file $01AC0D | JSR $ccde
$AC00 | b14 file $01AC10 | LDA $0001
$AC03 | b14 file $01AC13 | AND #$40
$AC05 | b14 file $01AC15 | BEQ $ac39
$AC07 | b14 file $01AC17 | LDA $0549
$AC0A | b14 file $01AC1A | ASL A
$AC0B | b14 file $01AC1B | ASL A
$AC0C | b14 file $01AC1C | ORA $0548
$AC0F | b14 file $01AC1F | TAY
$AC10 | b14 file $01AC20 | LDA #$04
$AC12 | b14 file $01AC22 | CPY #$00
$AC14 | b14 file $01AC24 | BEQ $ac1a
$AC16 | b14 file $01AC26 | CPY #$04
$AC18 | b14 file $01AC28 | BNE $ac23
$AC1A | b14 file $01AC2A | LDX $054b
$AC1D | b14 file $01AC2D | CPX #$01
$AC1F | b14 file $01AC2F | BNE $ac23
$AC21 | b14 file $01AC31 | LDA #$05
$AC23 | b14 file $01AC33 | STA $0000
$AC26 | b14 file $01AC36 | LDA $0550,Y
$AC29 | b14 file $01AC39 | CLC
$AC2A | b14 file $01AC3A | ADC #$01
$AC2C | b14 file $01AC3C | CMP $0000
$AC2F | b14 file $01AC3F | BCC $ac33
$AC31 | b14 file $01AC41 | LDA #$00
$AC33 | b14 file $01AC43 | STA $0550,Y
$AC36 | b14 file $01AC46 | JMP $ac6f
$AC39 | b14 file $01AC49 | LDA $0549
$AC3C | b14 file $01AC4C | JSR $ccde
$AC3F | b14 file $01AC4F | LDA $0001
$AC42 | b14 file $01AC52 | AND #$20
$AC44 | b14 file $01AC54 | BEQ $ac58
$AC46 | b14 file $01AC56 | INC $0548
$AC49 | b14 file $01AC59 | LDA $0548
$AC4C | b14 file $01AC5C | CMP #$04
$AC4E | b14 file $01AC5E | BCC $ac55
$AC50 | b14 file $01AC60 | LDA #$00
$AC52 | b14 file $01AC62 | STA $0548
$AC55 | b14 file $01AC65 | JMP $ac6f
$AC58 | b14 file $01AC68 | LDA $0549
$AC5B | b14 file $01AC6B | JSR $ccde
$AC5E | b14 file $01AC6E | LDA $0001
$AC61 | b14 file $01AC71 | AND #$10
$AC63 | b14 file $01AC73 | BEQ $ac72
$AC65 | b14 file $01AC75 | DEC $0548
$AC68 | b14 file $01AC78 | BPL $ac6f
$AC6A | b14 file $01AC7A | LDA #$03
$AC6C | b14 file $01AC7C | STA $0548
$AC6F | b14 file $01AC7F | JSR $aca8
$AC72 | b14 file $01AC82 | RTS
$AC73 | b14 file $01AC83 | LDA #$a3
$AC75 | b14 file $01AC85 | STA $0000
$AC78 | b14 file $01AC88 | LDA #$ac
$AC7A | b14 file $01AC8A | STA $0001
$AC7D | b14 file $01AC8D | LDY $0548
$AC80 | b14 file $01AC90 | LDA $ac9b,Y
$AC83 | b14 file $01AC93 | STA $000a
$AC86 | b14 file $01AC96 | LDA #$80
$AC88 | b14 file $01AC98 | STA $000c
$AC8B | b14 file $01AC9B | LDA #$00
$AC8D | b14 file $01AC9D | STA $000b
$AC90 | b14 file $01ACA0 | STA $000d
$AC93 | b14 file $01ACA3 | LDA #$00
$AC95 | b14 file $01ACA5 | STA $0002
$AC98 | b14 file $01ACA8 | JMP $f1ad
$ACA8 | b14 file $01ACB8 | LDA $0548
$ACAB | b14 file $01ACBB | STA $0000
$ACAE | b14 file $01ACBE | LDA $0549
$ACB1 | b14 file $01ACC1 | ASL A
$ACB2 | b14 file $01ACC2 | ASL A
$ACB3 | b14 file $01ACC3 | CLC
$ACB4 | b14 file $01ACC4 | ADC $0548
$ACB7 | b14 file $01ACC7 | TAY
$ACB8 | b14 file $01ACC8 | LDA $0550,Y
$ACBB | b14 file $01ACCB | STA $0001
$ACBE | b14 file $01ACCE | STA $0002
$ACC1 | b14 file $01ACD1 | JSR $c839
$ACC4 | b14 file $01ACD4 | RTS
$ACC5 | b14 file $01ACD5 | LDY $0549
$ACC8 | b14 file $01ACD8 | LDA $0560,Y
$ACCB | b14 file $01ACDB | STA $0000
$ACCE | b14 file $01ACDE | LDA #$a5
$ACD0 | b14 file $01ACE0 | STA $000a
$ACD3 | b14 file $01ACE3 | LDX #$00
$ACD5 | b14 file $01ACE5 | LDY #$39
$ACD7 | b14 file $01ACE7 | JSR $ee07 ; inline far target $A000
$ACDC | b14 file $01ACEC | LDA $0541
$ACDF | b14 file $01ACEF | JSR $eade ; inline targets: $ACEC,$AD3C,$AD5D,$AE11,$AE8E
$ACEC | b14 file $01ACFC | INC $0541
$ACEF | b14 file $01ACFF | LDA #$00
$ACF1 | b14 file $01AD01 | STA $0548
$ACF4 | b14 file $01AD04 | LDY $0549
$ACF7 | b14 file $01AD07 | LDA $0572,Y
$ACFA | b14 file $01AD0A | LDY #$00
$ACFC | b14 file $01AD0C | CMP #$05
$ACFE | b14 file $01AD0E | BCC $ad15
$AD00 | b14 file $01AD10 | INY
$AD01 | b14 file $01AD11 | CMP #$07
$AD03 | b14 file $01AD13 | BCC $ad15
$AD05 | b14 file $01AD15 | INY
$AD06 | b14 file $01AD16 | CMP #$08
$AD08 | b14 file $01AD18 | BCC $ad15
$AD0A | b14 file $01AD1A | INY
$AD0B | b14 file $01AD1B | CMP #$0a
$AD0D | b14 file $01AD1D | BCC $ad15
$AD0F | b14 file $01AD1F | INY
$AD10 | b14 file $01AD20 | CMP #$0c
$AD12 | b14 file $01AD22 | BCC $ad15
$AD14 | b14 file $01AD24 | INY
$AD15 | b14 file $01AD25 | STY $054a
$AD18 | b14 file $01AD28 | LDA #$e7
$AD1A | b14 file $01AD2A | JSR $f26d
$AD1D | b14 file $01AD2D | LDY $0549
$AD20 | b14 file $01AD30 | LDA $0572,Y
$AD23 | b14 file $01AD33 | STA $044c
$AD26 | b14 file $01AD36 | LDA #$00
$AD28 | b14 file $01AD38 | STA $044d
$AD2B | b14 file $01AD3B | STA $044e
$AD2E | b14 file $01AD3E | LDA #$57
$AD30 | b14 file $01AD40 | STA $00bd
$AD33 | b14 file $01AD43 | LDA #$00
$AD35 | b14 file $01AD45 | STA $0424
$AD38 | b14 file $01AD48 | STA $0425
$AD3B | b14 file $01AD4B | RTS
$AD3C | b14 file $01AD4C | JSR $b870
$AD3F | b14 file $01AD4F | BCC $ad5c
$AD41 | b14 file $01AD51 | LDA $007e
$AD44 | b14 file $01AD54 | BNE $ad5c
$AD46 | b14 file $01AD56 | LDA #$09
$AD48 | b14 file $01AD58 | STA $00bb
$AD4B | b14 file $01AD5B | JSR $b0ac
$AD4E | b14 file $01AD5E | LDA $0548
$AD51 | b14 file $01AD61 | INC $0548
$AD54 | b14 file $01AD64 | CMP $054a
$AD57 | b14 file $01AD67 | BCC $ad5c
$AD59 | b14 file $01AD69 | INC $0541
$AD5C | b14 file $01AD6C | RTS
$AD5D | b14 file $01AD6D | LDA $0083
$AD60 | b14 file $01AD70 | PHA
$AD61 | b14 file $01AD71 | LDA $0081
$AD64 | b14 file $01AD74 | PHA
$AD65 | b14 file $01AD75 | LDA $0549
$AD68 | b14 file $01AD78 | JSR $ccde
$AD6B | b14 file $01AD7B | LDA $0000
$AD6E | b14 file $01AD7E | STA $0083
$AD71 | b14 file $01AD81 | LDA $0001
$AD74 | b14 file $01AD84 | STA $0081
$AD77 | b14 file $01AD87 | LDA $054a
$AD7A | b14 file $01AD8A | ASL A
$AD7B | b14 file $01AD8B | TAY
$AD7C | b14 file $01AD8C | LDA $aed0,Y
$AD7F | b14 file $01AD8F | STA $0010
$AD82 | b14 file $01AD92 | LDA $aed1,Y
$AD85 | b14 file $01AD95 | STA $0011
$AD88 | b14 file $01AD98 | LDA #$00
$AD8A | b14 file $01AD9A | STA $0012
$AD8D | b14 file $01AD9D | JSR $ed1e
$AD90 | b14 file $01ADA0 | LDA #$00
$AD92 | b14 file $01ADA2 | STA $0010
$AD95 | b14 file $01ADA5 | LDA #$af
$AD97 | b14 file $01ADA7 | STA $0011
$AD9A | b14 file $01ADAA | LDA #$0c
$AD9C | b14 file $01ADAC | STA $0000
$AD9F | b14 file $01ADAF | LDA #$af
$ADA1 | b14 file $01ADB1 | STA $0001
$ADA4 | b14 file $01ADB4 | LDA $0012
$ADA7 | b14 file $01ADB7 | JSR $edf5
$ADAA | b14 file $01ADBA | PLA
$ADAB | b14 file $01ADBB | STA $0081
$ADAE | b14 file $01ADBE | PLA
$ADAF | b14 file $01ADBF | STA $0083
$ADB2 | b14 file $01ADC2 | JSR $b870
$ADB5 | b14 file $01ADC5 | BCC $ae10
$ADB7 | b14 file $01ADC7 | LDA $0549
$ADBA | b14 file $01ADCA | JSR $ccde
$ADBD | b14 file $01ADCD | LDA $0001
$ADC0 | b14 file $01ADD0 | AND #$01
$ADC2 | b14 file $01ADD2 | BEQ $ade7
$ADC4 | b14 file $01ADD4 | LDY $0549
$ADC7 | b14 file $01ADD7 | LDA $0572,Y
$ADCA | b14 file $01ADDA | LDY $0012
$ADCD | b14 file $01ADDD | CMP $addf,Y
$ADD0 | b14 file $01ADE0 | BCC $ade7
$ADD2 | b14 file $01ADE2 | SEC
$ADD3 | b14 file $01ADE3 | SBC $addf,Y
$ADD6 | b14 file $01ADE6 | LDY $0549
$ADD9 | b14 file $01ADE9 | STA $0572,Y
$ADDC | b14 file $01ADEC | JMP $af11
$ADE7 | b14 file $01ADF7 | LDA $0549
$ADEA | b14 file $01ADFA | JSR $ccde
$ADED | b14 file $01ADFD | LDA $0001
$ADF0 | b14 file $01AE00 | AND #$02
$ADF2 | b14 file $01AE02 | BEQ $ae10
$ADF4 | b14 file $01AE04 | LDA #$03
$ADF6 | b14 file $01AE06 | STA $0540
$ADF9 | b14 file $01AE09 | LDA #$03
$ADFB | b14 file $01AE0B | STA $0541
$ADFE | b14 file $01AE0E | LDA #$e8
$AE00 | b14 file $01AE10 | STA $0310
$AE03 | b14 file $01AE13 | LDA #$e9
$AE05 | b14 file $01AE15 | STA $0311
$AE08 | b14 file $01AE18 | LDA #$00
$AE0A | b14 file $01AE1A | STA $0300
$AE0D | b14 file $01AE1D | JSR $cbf1
$AE10 | b14 file $01AE20 | RTS
$AE11 | b14 file $01AE21 | JSR $cca8
$AE14 | b14 file $01AE24 | LDY $0549
$AE17 | b14 file $01AE27 | LDA $0562,Y
$AE1A | b14 file $01AE2A | CMP #$03
$AE1C | b14 file $01AE2C | BNE $ae24
$AE1E | b14 file $01AE2E | JSR $cd22
$AE21 | b14 file $01AE31 | JMP $ae2a
$AE24 | b14 file $01AE34 | LDA $0549
$AE27 | b14 file $01AE37 | JSR $ccde
$AE2A | b14 file $01AE3A | JSR $b870
$AE2D | b14 file $01AE3D | BCC $ae6b
$AE2F | b14 file $01AE3F | LDA $0001
$AE32 | b14 file $01AE42 | AND #$01
$AE34 | b14 file $01AE44 | BEQ $ae6b
$AE36 | b14 file $01AE46 | LDY $0549
$AE39 | b14 file $01AE49 | LDA $0562,Y
$AE3C | b14 file $01AE4C | CMP #$03
$AE3E | b14 file $01AE4E | BNE $ae6c
$AE40 | b14 file $01AE50 | LDA #$03
$AE42 | b14 file $01AE52 | STA $0540
$AE45 | b14 file $01AE55 | LDA #$03
$AE47 | b14 file $01AE57 | STA $0541
$AE4A | b14 file $01AE5A | LDA #$e8
$AE4C | b14 file $01AE5C | STA $0310
$AE4F | b14 file $01AE5F | LDA #$e9
$AE51 | b14 file $01AE61 | STA $0311
$AE54 | b14 file $01AE64 | LDA #$00
$AE56 | b14 file $01AE66 | STA $0300
$AE59 | b14 file $01AE69 | LDA #$00
$AE5B | b14 file $01AE6B | STA $0310
$AE5E | b14 file $01AE6E | LDA #$01
$AE60 | b14 file $01AE70 | STA $054b
$AE63 | b14 file $01AE73 | LDA #$01
$AE65 | b14 file $01AE75 | STA $054c
$AE68 | b14 file $01AE78 | JSR $cbf1
$AE6B | b14 file $01AE7B | RTS
$AE6C | b14 file $01AE7C | LDA #$03
$AE6E | b14 file $01AE7E | STA $0540
$AE71 | b14 file $01AE81 | LDA #$03
$AE73 | b14 file $01AE83 | STA $0541
$AE76 | b14 file $01AE86 | LDA #$e8
$AE78 | b14 file $01AE88 | STA $0310
$AE7B | b14 file $01AE8B | LDA #$e9
$AE7D | b14 file $01AE8D | STA $0311
$AE80 | b14 file $01AE90 | LDA #$00
$AE82 | b14 file $01AE92 | STA $0300
$AE85 | b14 file $01AE95 | LDA #$00
$AE87 | b14 file $01AE97 | STA $0310
$AE8A | b14 file $01AE9A | JSR $cbf1
$AE8D | b14 file $01AE9D | RTS
$AE8E | b14 file $01AE9E | JSR $cca8
$AE91 | b14 file $01AEA1 | LDA $0549
$AE94 | b14 file $01AEA4 | JSR $ccde
$AE97 | b14 file $01AEA7 | JSR $b870
$AE9A | b14 file $01AEAA | BCC $aead
$AE9C | b14 file $01AEAC | LDA $0001
$AE9F | b14 file $01AEAF | AND #$01
$AEA1 | b14 file $01AEB1 | BEQ $aead
$AEA3 | b14 file $01AEB3 | LDA #$05
$AEA5 | b14 file $01AEB5 | STA $0540
$AEA8 | b14 file $01AEB8 | LDA #$00
$AEAA | b14 file $01AEBA | STA $0541
$AEAD | b14 file $01AEBD | RTS
$AF11 | b14 file $01AF21 | LDA $0012
$AF14 | b14 file $01AF24 | STA $0548
$AF17 | b14 file $01AF27 | JSR $eade ; inline targets: $AFD2,$AF26,$B00E,$B02E,$B07C,$B09C
$AF26 | b14 file $01AF36 | LDA $0544
$AF29 | b14 file $01AF39 | CMP #$05
$AF2B | b14 file $01AF3B | BNE $af35
$AF2D | b14 file $01AF3D | LDA $0549
$AF30 | b14 file $01AF40 | BNE $af35
$AF32 | b14 file $01AF42 | JMP $afc9
$AF35 | b14 file $01AF45 | LDA $0560
$AF38 | b14 file $01AF48 | JSR $f2d7
$AF3B | b14 file $01AF4B | LDY #$0b
$AF3D | b14 file $01AF4D | LDA ($00),Y
$AF3F | b14 file $01AF4F | LSR A
$AF40 | b14 file $01AF50 | LSR A
$AF41 | b14 file $01AF51 | LSR A
$AF42 | b14 file $01AF52 | LSR A
$AF43 | b14 file $01AF53 | STA $000a
$AF46 | b14 file $01AF56 | LDY #$02
$AF48 | b14 file $01AF58 | LDA ($00),Y
$AF4A | b14 file $01AF5A | STA $000c
$AF4D | b14 file $01AF5D | LDA $0561
$AF50 | b14 file $01AF60 | JSR $f2d7
$AF53 | b14 file $01AF63 | LDY #$0b
$AF55 | b14 file $01AF65 | LDA ($00),Y
$AF57 | b14 file $01AF67 | LSR A
$AF58 | b14 file $01AF68 | LSR A
$AF59 | b14 file $01AF69 | LSR A
$AF5A | b14 file $01AF6A | LSR A
$AF5B | b14 file $01AF6B | STA $000b
$AF5E | b14 file $01AF6E | LDY #$02
$AF60 | b14 file $01AF70 | LDA ($00),Y
$AF62 | b14 file $01AF72 | STA $000d
$AF65 | b14 file $01AF75 | LDA $0549
$AF68 | b14 file $01AF78 | BEQ $af82
$AF6A | b14 file $01AF7A | LDY $000a
$AF6D | b14 file $01AF7D | LDA $000b
$AF70 | b14 file $01AF80 | STA $000a
$AF73 | b14 file $01AF83 | STY $000b
$AF76 | b14 file $01AF86 | LDY $000c
$AF79 | b14 file $01AF89 | LDA $000d
$AF7C | b14 file $01AF8C | STA $000c
$AF7F | b14 file $01AF8F | STY $000d
$AF82 | b14 file $01AF92 | LDA $000a
$AF85 | b14 file $01AF95 | SEC
$AF86 | b14 file $01AF96 | SBC $000b
$AF89 | b14 file $01AF99 | BCS $af8d
$AF8B | b14 file $01AF9B | LDA #$00
$AF8D | b14 file $01AF9D | ASL A
$AF8E | b14 file $01AF9E | STA $000a
$AF91 | b14 file $01AFA1 | LDA $000d
$AF94 | b14 file $01AFA4 | STA $0001
$AF97 | b14 file $01AFA7 | LDA #$0a
$AF99 | b14 file $01AFA9 | STA $0003
$AF9C | b14 file $01AFAC | LDA #$00
$AF9E | b14 file $01AFAE | STA $0002
$AFA1 | b14 file $01AFB1 | STA $0004
$AFA4 | b14 file $01AFB4 | JSR $ea7c
$AFA7 | b14 file $01AFB7 | LDA $000a
$AFAA | b14 file $01AFBA | CLC
$AFAB | b14 file $01AFBB | ADC #$20
$AFAD | b14 file $01AFBD | SEC
$AFAE | b14 file $01AFBE | SBC $0001
$AFB1 | b14 file $01AFC1 | STA $000a
$AFB4 | b14 file $01AFC4 | LDA #$64
$AFB6 | b14 file $01AFC6 | JSR $e862
$AFB9 | b14 file $01AFC9 | CMP $000a
$AFBC | b14 file $01AFCC | BCS $afc9
$AFBE | b14 file $01AFCE | LDA #$ea
$AFC0 | b14 file $01AFD0 | JSR $f26d
$AFC3 | b14 file $01AFD3 | LDA #$04
$AFC5 | b14 file $01AFD5 | STA $0541
$AFC8 | b14 file $01AFD8 | RTS
$AFC9 | b14 file $01AFD9 | LDA #$eb
$AFCB | b14 file $01AFDB | JSR $f26d
$AFCE | b14 file $01AFDE | INC $0541
$AFD1 | b14 file $01AFE1 | RTS
$AFD2 | b14 file $01AFE2 | JSR $e87a
$AFD5 | b14 file $01AFE5 | AND #$01
$AFD7 | b14 file $01AFE7 | BNE $afe2
$AFD9 | b14 file $01AFE9 | INC $0541
$AFDC | b14 file $01AFEC | LDA #$ed
$AFDE | b14 file $01AFEE | JSR $f26d
$AFE1 | b14 file $01AFF1 | RTS
$AFE2 | b14 file $01AFF2 | LDA #$ec
$AFE4 | b14 file $01AFF4 | JSR $f26d
$AFE7 | b14 file $01AFF7 | LDA $0549
$AFEA | b14 file $01AFFA | EOR #$01
$AFEC | b14 file $01AFFC | TAY
$AFED | b14 file $01AFFD | LDA $0560,Y
$AFF0 | b14 file $01B000 | STA $042c
$AFF3 | b14 file $01B003 | INC $0541
$AFF6 | b14 file $01B006 | LDA $0574
$AFF9 | b14 file $01B009 | LDY $0549
$AFFC | b14 file $01B00C | BNE $b006
$AFFE | b14 file $01B00E | AND #$f0
$B000 | b14 file $01B010 | ORA #$04
$B002 | b14 file $01B012 | STA $0574
$B005 | b14 file $01B015 | RTS
$B006 | b14 file $01B016 | AND #$0f
$B008 | b14 file $01B018 | ORA #$40
$B00A | b14 file $01B01A | STA $0574
$B00D | b14 file $01B01D | RTS
$B00E | b14 file $01B01E | LDA #$ee
$B010 | b14 file $01B020 | JSR $f26d
$B013 | b14 file $01B023 | INC $0541
$B016 | b14 file $01B026 | LDA $0575
$B019 | b14 file $01B029 | LDY $0549
$B01C | b14 file $01B02C | BNE $b026
$B01E | b14 file $01B02E | AND #$f0
$B020 | b14 file $01B030 | ORA #$03
$B022 | b14 file $01B032 | STA $0575
$B025 | b14 file $01B035 | RTS
$B026 | b14 file $01B036 | AND #$0f
$B028 | b14 file $01B038 | ORA #$30
$B02A | b14 file $01B03A | STA $0575
$B02D | b14 file $01B03D | RTS
$B02E | b14 file $01B03E | LDA #$ef
$B030 | b14 file $01B040 | JSR $f26d
$B033 | b14 file $01B043 | INC $0541
$B036 | b14 file $01B046 | LDA $0576
$B039 | b14 file $01B049 | LDY $0549
$B03C | b14 file $01B04C | BEQ $b052
$B03E | b14 file $01B04E | AND #$0f
$B040 | b14 file $01B050 | ORA #$40
$B042 | b14 file $01B052 | STA $0576
$B045 | b14 file $01B055 | LDA $056b
$B048 | b14 file $01B058 | STA $0579
$B04B | b14 file $01B05B | JSR $b066
$B04E | b14 file $01B05E | STA $056b
$B051 | b14 file $01B061 | RTS
$B052 | b14 file $01B062 | AND #$f0
$B054 | b14 file $01B064 | ORA #$04
$B056 | b14 file $01B066 | STA $0576
$B059 | b14 file $01B069 | LDA $056a
$B05C | b14 file $01B06C | STA $0578
$B05F | b14 file $01B06F | JSR $b066
$B062 | b14 file $01B072 | STA $056a
$B065 | b14 file $01B075 | RTS
$B066 | b14 file $01B076 | PHA
$B067 | b14 file $01B077 | JSR $e87a
$B06A | b14 file $01B07A | AND #$07
$B06C | b14 file $01B07C | CMP #$05
$B06E | b14 file $01B07E | BCS $b067
$B070 | b14 file $01B080 | STA $0000
$B073 | b14 file $01B083 | PLA
$B074 | b14 file $01B084 | CLC
$B075 | b14 file $01B085 | ADC #$05
$B077 | b14 file $01B087 | CLC
$B078 | b14 file $01B088 | ADC $0000
$B07B | b14 file $01B08B | RTS
$B07C | b14 file $01B08C | LDA #$f0
$B07E | b14 file $01B08E | JSR $f26d
$B081 | b14 file $01B091 | INC $0541
$B084 | b14 file $01B094 | LDA $0577
$B087 | b14 file $01B097 | LDY $0549
$B08A | b14 file $01B09A | BNE $b094
$B08C | b14 file $01B09C | AND #$f0
$B08E | b14 file $01B09E | ORA #$03
$B090 | b14 file $01B0A0 | STA $0577
$B093 | b14 file $01B0A3 | RTS
$B094 | b14 file $01B0A4 | AND #$0f
$B096 | b14 file $01B0A6 | ORA #$30
$B098 | b14 file $01B0A8 | STA $0577
$B09B | b14 file $01B0AB | RTS
$B09C | b14 file $01B0AC | LDA #$09
$B09E | b14 file $01B0AE | STA $0540
$B0A1 | b14 file $01B0B1 | LDA #$00
$B0A3 | b14 file $01B0B3 | STA $0541
$B0A6 | b14 file $01B0B6 | LDA #$f1
$B0A8 | b14 file $01B0B8 | JSR $f26d
$B0AB | b14 file $01B0BB | RTS
$B0AC | b14 file $01B0BC | LDA $0548
$B0AF | b14 file $01B0BF | ASL A
$B0B0 | b14 file $01B0C0 | TAY
$B0B1 | b14 file $01B0C1 | LDA $b0d5,Y
$B0B4 | b14 file $01B0C4 | STA $0000
$B0B7 | b14 file $01B0C7 | LDA $b0d6,Y
$B0BA | b14 file $01B0CA | STA $0001
$B0BD | b14 file $01B0CD | LDY #$00
$B0BF | b14 file $01B0CF | LDA ($00),Y
$B0C1 | b14 file $01B0D1 | CMP #$ff
$B0C3 | b14 file $01B0D3 | STA $0380,Y
$B0C6 | b14 file $01B0D6 | BEQ $b0cc
$B0C8 | b14 file $01B0D8 | INY
$B0C9 | b14 file $01B0D9 | JMP $b0bf
$B0CC | b14 file $01B0DC | LDA $007e
$B0CF | b14 file $01B0DF | ORA #$04
$B0D1 | b14 file $01B0E1 | STA $007e
$B0D4 | b14 file $01B0E4 | RTS
$B15B | b14 file $01B16B | LDA $0574
$B15E | b14 file $01B16E | STA $0000
$B161 | b14 file $01B171 | JSR $b198
$B164 | b14 file $01B174 | LDA $0000
$B167 | b14 file $01B177 | STA $0574
$B16A | b14 file $01B17A | LDA $0575
$B16D | b14 file $01B17D | STA $0000
$B170 | b14 file $01B180 | JSR $b198
$B173 | b14 file $01B183 | LDA $0000
$B176 | b14 file $01B186 | STA $0575
$B179 | b14 file $01B189 | LDA $0576
$B17C | b14 file $01B18C | STA $0000
$B17F | b14 file $01B18F | JSR $b1b7
$B182 | b14 file $01B192 | LDA $0000
$B185 | b14 file $01B195 | STA $0576
$B188 | b14 file $01B198 | LDA $0577
$B18B | b14 file $01B19B | STA $0000
$B18E | b14 file $01B19E | JSR $b198
$B191 | b14 file $01B1A1 | LDA $0000
$B194 | b14 file $01B1A4 | STA $0577
$B197 | b14 file $01B1A7 | RTS
$B198 | b14 file $01B1A8 | LDA $0000
$B19B | b14 file $01B1AB | AND #$0f
$B19D | b14 file $01B1AD | BEQ $b1a6
$B19F | b14 file $01B1AF | LDY $0000
$B1A2 | b14 file $01B1B2 | DEY
$B1A3 | b14 file $01B1B3 | STY $0000
$B1A6 | b14 file $01B1B6 | LDA $0000
$B1A9 | b14 file $01B1B9 | AND #$f0
$B1AB | b14 file $01B1BB | BEQ $b1b6
$B1AD | b14 file $01B1BD | LDA $0000
$B1B0 | b14 file $01B1C0 | SEC
$B1B1 | b14 file $01B1C1 | SBC #$10
$B1B3 | b14 file $01B1C3 | STA $0000
$B1B6 | b14 file $01B1C6 | RTS
$B1B7 | b14 file $01B1C7 | LDA $0000
$B1BA | b14 file $01B1CA | AND #$0f
$B1BC | b14 file $01B1CC | BEQ $b1d1
$B1BE | b14 file $01B1CE | LDA $0000
$B1C1 | b14 file $01B1D1 | SEC
$B1C2 | b14 file $01B1D2 | SBC #$01
$B1C4 | b14 file $01B1D4 | STA $0000
$B1C7 | b14 file $01B1D7 | AND #$0f
$B1C9 | b14 file $01B1D9 | BNE $b1d1
$B1CB | b14 file $01B1DB | LDA $0578
$B1CE | b14 file $01B1DE | STA $056a
$B1D1 | b14 file $01B1E1 | LDA $0000
$B1D4 | b14 file $01B1E4 | AND #$f0
$B1D6 | b14 file $01B1E6 | BEQ $b1eb
$B1D8 | b14 file $01B1E8 | LDA $0000
$B1DB | b14 file $01B1EB | SEC
$B1DC | b14 file $01B1EC | SBC #$10
$B1DE | b14 file $01B1EE | STA $0000
$B1E1 | b14 file $01B1F1 | AND #$f0
$B1E3 | b14 file $01B1F3 | BNE $b1eb
$B1E5 | b14 file $01B1F5 | LDA $0579
$B1E8 | b14 file $01B1F8 | STA $056b
$B1EB | b14 file $01B1FB | RTS
$B1EC | b14 file $01B1FC | LDY $0549
$B1EF | b14 file $01B1FF | LDA $0560,Y
$B1F2 | b14 file $01B202 | STA $0000
$B1F5 | b14 file $01B205 | LDA #$a5
$B1F7 | b14 file $01B207 | STA $000a
$B1FA | b14 file $01B20A | LDX #$00
$B1FC | b14 file $01B20C | LDY #$39
$B1FE | b14 file $01B20E | JSR $ee07 ; inline far target $A000
$B203 | b14 file $01B213 | LDA $0541
$B206 | b14 file $01B216 | JSR $eade ; inline targets: $B211,$B25B,$B2F5,$B3EF
$B211 | b14 file $01B221 | LDA #$7f
$B213 | b14 file $01B223 | STA $00b1
$B216 | b14 file $01B226 | STA $00c1
$B219 | b14 file $01B229 | STA $00d1
$B21C | b14 file $01B22C | STA $00c9
$B21F | b14 file $01B22F | STA $00d9
$B222 | b14 file $01B232 | LDA #$00
$B224 | b14 file $01B234 | STA $0548
$B227 | b14 file $01B237 | INC $0541
$B22A | b14 file $01B23A | LDA #$00
$B22C | b14 file $01B23C | LDY $0549
$B22F | b14 file $01B23F | BEQ $b233
$B231 | b14 file $01B241 | LDA #$0b
$B233 | b14 file $01B243 | STA $0558
$B236 | b14 file $01B246 | TAY
$B237 | b14 file $01B247 | LDA $05c2,Y
$B23A | b14 file $01B24A | LSR A
$B23B | b14 file $01B24B | LSR A
$B23C | b14 file $01B24C | LSR A
$B23D | b14 file $01B24D | LSR A
$B23E | b14 file $01B24E | STA $0559
$B241 | b14 file $01B251 | LDA $0596,Y
$B244 | b14 file $01B254 | ASL A
$B245 | b14 file $01B255 | ASL A
$B246 | b14 file $01B256 | ASL A
$B247 | b14 file $01B257 | ASL A
$B248 | b14 file $01B258 | STA $055a
$B24B | b14 file $01B25B | LDA $0580,Y
$B24E | b14 file $01B25E | ASL A
$B24F | b14 file $01B25F | ASL A
$B250 | b14 file $01B260 | ASL A
$B251 | b14 file $01B261 | ASL A
$B252 | b14 file $01B262 | STA $055b
$B255 | b14 file $01B265 | LDA #$00
$B257 | b14 file $01B267 | STA $008f
$B25A | b14 file $01B26A | RTS
$B25B | b14 file $01B26B | INC $0548
$B25E | b14 file $01B26E | LDA $0548
$B261 | b14 file $01B271 | CMP #$20
$B263 | b14 file $01B273 | BCC $b26d
$B265 | b14 file $01B275 | LDA #$00
$B267 | b14 file $01B277 | STA $0548
$B26A | b14 file $01B27A | INC $0541
$B26D | b14 file $01B27D | LDA $0559
$B270 | b14 file $01B280 | BNE $b27f
$B272 | b14 file $01B282 | DEC $055a
$B275 | b14 file $01B285 | LDA $055a
$B278 | b14 file $01B288 | CMP #$a0
$B27A | b14 file $01B28A | BCS $b2a9
$B27C | b14 file $01B28C | JMP $b2ac
$B27F | b14 file $01B28F | CMP #$01
$B281 | b14 file $01B291 | BNE $b290
$B283 | b14 file $01B293 | INC $055a
$B286 | b14 file $01B296 | LDA $055a
$B289 | b14 file $01B299 | CMP #$a0
$B28B | b14 file $01B29B | BCS $b2a9
$B28D | b14 file $01B29D | JMP $b2ac
$B290 | b14 file $01B2A0 | CMP #$02
$B292 | b14 file $01B2A2 | BNE $b2a1
$B294 | b14 file $01B2A4 | DEC $055b
$B297 | b14 file $01B2A7 | LDA $055b
$B29A | b14 file $01B2AA | CMP #$ff
$B29C | b14 file $01B2AC | BEQ $b2a9
$B29E | b14 file $01B2AE | JMP $b2ac
$B2A1 | b14 file $01B2B1 | INC $055b
$B2A4 | b14 file $01B2B4 | LDA $055b
$B2A7 | b14 file $01B2B7 | BNE $b2ac
$B2A9 | b14 file $01B2B9 | JMP $b440
$B2AC | b14 file $01B2BC | LDA #$e8
$B2AE | b14 file $01B2BE | STA $0000
$B2B1 | b14 file $01B2C1 | LDA #$b2
$B2B3 | b14 file $01B2C3 | STA $0001
$B2B6 | b14 file $01B2C6 | LDA #$00
$B2B8 | b14 file $01B2C8 | STA $0002
$B2BB | b14 file $01B2CB | LDA $0548
$B2BE | b14 file $01B2CE | LSR A
$B2BF | b14 file $01B2CF | LSR A
$B2C0 | b14 file $01B2D0 | AND #$07
$B2C2 | b14 file $01B2D2 | TAY
$B2C3 | b14 file $01B2D3 | LDA $055a
$B2C6 | b14 file $01B2D6 | SEC
$B2C7 | b14 file $01B2D7 | SBC $b2ed,Y
$B2CA | b14 file $01B2DA | STA $000a
$B2CD | b14 file $01B2DD | LDA $055b
$B2D0 | b14 file $01B2E0 | STA $000c
$B2D3 | b14 file $01B2E3 | LDA #$00
$B2D5 | b14 file $01B2E5 | STA $000b
$B2D8 | b14 file $01B2E8 | STA $000d
$B2DB | b14 file $01B2EB | LDA #$00
$B2DD | b14 file $01B2ED | STA $0003
$B2E0 | b14 file $01B2F0 | LDA #$a0
$B2E2 | b14 file $01B2F2 | STA $0004
$B2E5 | b14 file $01B2F5 | JMP $f09c
$B2F5 | b14 file $01B305 | LDA $005e
$B2F8 | b14 file $01B308 | AND #$0f
$B2FA | b14 file $01B30A | BNE $b312
$B2FC | b14 file $01B30C | INC $0548
$B2FF | b14 file $01B30F | LDA $0548
$B302 | b14 file $01B312 | CMP #$04
$B304 | b14 file $01B314 | BCC $b312
$B306 | b14 file $01B316 | JSR $b44b
$B309 | b14 file $01B319 | INC $0541
$B30C | b14 file $01B31C | LDA #$00
$B30E | b14 file $01B31E | STA $0548
$B311 | b14 file $01B321 | RTS
$B312 | b14 file $01B322 | LDA $0548
$B315 | b14 file $01B325 | ASL A
$B316 | b14 file $01B326 | TAY
$B317 | b14 file $01B327 | LDA $b349,Y
$B31A | b14 file $01B32A | STA $0000
$B31D | b14 file $01B32D | LDA $b34a,Y
$B320 | b14 file $01B330 | STA $0001
$B323 | b14 file $01B333 | LDA #$00
$B325 | b14 file $01B335 | STA $0002
$B328 | b14 file $01B338 | LDA $055a
$B32B | b14 file $01B33B | STA $000a
$B32E | b14 file $01B33E | LDA $055b
$B331 | b14 file $01B341 | STA $000c
$B334 | b14 file $01B344 | LDA #$00
$B336 | b14 file $01B346 | STA $000b
$B339 | b14 file $01B349 | STA $000d
$B33C | b14 file $01B34C | LDA #$00
$B33E | b14 file $01B34E | STA $0003
$B341 | b14 file $01B351 | LDA #$a0
$B343 | b14 file $01B353 | STA $0004
$B346 | b14 file $01B356 | JMP $f09c
$B3EF | b14 file $01B3FF | LDA #$00
$B3F1 | b14 file $01B401 | LDY $0549
$B3F4 | b14 file $01B404 | BNE $b3f8
$B3F6 | b14 file $01B406 | LDA #$0b
$B3F8 | b14 file $01B408 | CLC
$B3F9 | b14 file $01B409 | ADC $0548
$B3FC | b14 file $01B40C | TAY
$B3FD | b14 file $01B40D | LDA $05c2,Y
$B400 | b14 file $01B410 | CMP #$ff
$B402 | b14 file $01B412 | BEQ $b436
$B404 | b14 file $01B414 | LDA $05ac,Y
$B407 | b14 file $01B417 | BNE $b42b
$B409 | b14 file $01B419 | LDA #$00
$B40B | b14 file $01B41B | STA $0012
$B40E | b14 file $01B41E | STY $0013
$B411 | b14 file $01B421 | TYA
$B412 | b14 file $01B422 | PHA
$B413 | b14 file $01B423 | JSR $b882
$B416 | b14 file $01B426 | PLA
$B417 | b14 file $01B427 | TAY
$B418 | b14 file $01B428 | LDA #$ff
$B41A | b14 file $01B42A | STA $0580,Y
$B41D | b14 file $01B42D | STA $0596,Y
$B420 | b14 file $01B430 | STA $05c2,Y
$B423 | b14 file $01B433 | LDA #$00
$B425 | b14 file $01B435 | STA $05ac,Y
$B428 | b14 file $01B438 | JMP $b436
$B42B | b14 file $01B43B | LDA #$01
$B42D | b14 file $01B43D | STA $0012
$B430 | b14 file $01B440 | STY $0013
$B433 | b14 file $01B443 | JSR $b882
$B436 | b14 file $01B446 | INC $0548
$B439 | b14 file $01B449 | LDA $0548
$B43C | b14 file $01B44C | CMP #$0b
$B43E | b14 file $01B44E | BCC $b44a
$B440 | b14 file $01B450 | LDA #$08
$B442 | b14 file $01B452 | STA $0540
$B445 | b14 file $01B455 | LDA #$03
$B447 | b14 file $01B457 | STA $0541
$B44A | b14 file $01B45A | RTS
$B44B | b14 file $01B45B | LDA $055a
$B44E | b14 file $01B45E | LSR A
$B44F | b14 file $01B45F | LSR A
$B450 | b14 file $01B460 | LSR A
$B451 | b14 file $01B461 | LSR A
$B452 | b14 file $01B462 | STA $001a
$B455 | b14 file $01B465 | LDA $055b
$B458 | b14 file $01B468 | LSR A
$B459 | b14 file $01B469 | LSR A
$B45A | b14 file $01B46A | LSR A
$B45B | b14 file $01B46B | LSR A
$B45C | b14 file $01B46C | STA $001b
$B45F | b14 file $01B46F | LDY $0549
$B462 | b14 file $01B472 | BNE $b477
$B464 | b14 file $01B474 | LDA #$0b
$B466 | b14 file $01B476 | STA $001c
$B469 | b14 file $01B479 | JSR $b48a
$B46C | b14 file $01B47C | INC $001c
$B46F | b14 file $01B47F | LDA $001c
$B472 | b14 file $01B482 | CMP #$16
$B474 | b14 file $01B484 | BCC $b469
$B476 | b14 file $01B486 | RTS
$B477 | b14 file $01B487 | LDA #$00
$B479 | b14 file $01B489 | STA $001c
$B47C | b14 file $01B48C | JSR $b48a
$B47F | b14 file $01B48F | INC $001c
$B482 | b14 file $01B492 | LDA $001c
$B485 | b14 file $01B495 | CMP #$0b
$B487 | b14 file $01B497 | BCC $b47c
$B489 | b14 file $01B499 | RTS
$B48A | b14 file $01B49A | LDY $001c
$B48D | b14 file $01B49D | LDA $0596,Y
$B490 | b14 file $01B4A0 | SEC
$B491 | b14 file $01B4A1 | SBC $001a
$B494 | b14 file $01B4A4 | CLC
$B495 | b14 file $01B4A5 | ADC #$01
$B497 | b14 file $01B4A7 | CMP #$03
$B499 | b14 file $01B4A9 | BCS $b4a9
$B49B | b14 file $01B4AB | LDA $0580,Y
$B49E | b14 file $01B4AE | SEC
$B49F | b14 file $01B4AF | SBC $001b
$B4A2 | b14 file $01B4B2 | CLC
$B4A3 | b14 file $01B4B3 | ADC #$01
$B4A5 | b14 file $01B4B5 | CMP #$03
$B4A7 | b14 file $01B4B7 | BCC $b4aa
$B4A9 | b14 file $01B4B9 | RTS
$B4AA | b14 file $01B4BA | JSR $b4e3
$B4AD | b14 file $01B4BD | LDY $001c
$B4B0 | b14 file $01B4C0 | LDA $05ac,Y
$B4B3 | b14 file $01B4C3 | STA $0001
$B4B6 | b14 file $01B4C6 | SEC
$B4B7 | b14 file $01B4C7 | SBC $0000
$B4BA | b14 file $01B4CA | STA $05ac,Y
$B4BD | b14 file $01B4CD | BEQ $b4cc
$B4BF | b14 file $01B4CF | BCS $b4cc
$B4C1 | b14 file $01B4D1 | LDA #$00
$B4C3 | b14 file $01B4D3 | STA $05ac,Y
$B4C6 | b14 file $01B4D6 | LDA $0001
$B4C9 | b14 file $01B4D9 | STA $0000
$B4CC | b14 file $01B4DC | LDA $0000
$B4CF | b14 file $01B4DF | STA $000b
$B4D2 | b14 file $01B4E2 | LDA #$00
$B4D4 | b14 file $01B4E4 | STA $000c
$B4D7 | b14 file $01B4E7 | LDY $0549
$B4DA | b14 file $01B4EA | LDA $0560,Y
$B4DD | b14 file $01B4ED | STA $000a
$B4E0 | b14 file $01B4F0 | JMP $d7fb
$B4E3 | b14 file $01B4F3 | LDY $0549
$B4E6 | b14 file $01B4F6 | LDA $0560,Y
$B4E9 | b14 file $01B4F9 | JSR $f2d7
$B4EC | b14 file $01B4FC | LDY #$02
$B4EE | b14 file $01B4FE | LDA ($00),Y
$B4F0 | b14 file $01B500 | PHA
$B4F1 | b14 file $01B501 | LDA #$0a
$B4F3 | b14 file $01B503 | JSR $e862
$B4F6 | b14 file $01B506 | CLC
$B4F7 | b14 file $01B507 | ADC #$02
$B4F9 | b14 file $01B509 | STA $0000
$B4FC | b14 file $01B50C | PLA
$B4FD | b14 file $01B50D | SEC
$B4FE | b14 file $01B50E | SBC $0000
$B501 | b14 file $01B511 | BCS $b505
$B503 | b14 file $01B513 | LDA #$00
$B505 | b14 file $01B515 | CLC
$B506 | b14 file $01B516 | ADC #$01
$B508 | b14 file $01B518 | STA $0000
$B50B | b14 file $01B51B | LDY $001c
$B50E | b14 file $01B51E | BEQ $b520
$B510 | b14 file $01B520 | CPY #$0b
$B512 | b14 file $01B522 | BEQ $b520
$B514 | b14 file $01B524 | LDA $05c2,Y
$B517 | b14 file $01B527 | AND #$0f
$B519 | b14 file $01B529 | CMP #$01
$B51B | b14 file $01B52B | BEQ $b52a
$B51D | b14 file $01B52D | JMP $b547
$B520 | b14 file $01B530 | LDA $0000
$B523 | b14 file $01B533 | LSR A
$B524 | b14 file $01B534 | STA $0000
$B527 | b14 file $01B537 | JMP $b547
$B52A | b14 file $01B53A | LDA $0000
$B52D | b14 file $01B53D | STA $0001
$B530 | b14 file $01B540 | LDA #$03
$B532 | b14 file $01B542 | STA $0003
$B535 | b14 file $01B545 | LDA #$00
$B537 | b14 file $01B547 | STA $0002
$B53A | b14 file $01B54A | STA $0004
$B53D | b14 file $01B54D | JSR $ea7c
$B540 | b14 file $01B550 | LDA $0001
$B543 | b14 file $01B553 | ASL A
$B544 | b14 file $01B554 | STA $0000
$B547 | b14 file $01B557 | RTS
$B548 | b14 file $01B558 | LDY #$57
$B54A | b14 file $01B55A | LDA #$ff
$B54C | b14 file $01B55C | STA $0580,Y
$B54F | b14 file $01B55F | DEY
$B550 | b14 file $01B560 | BPL $b54c
$B552 | b14 file $01B562 | LDA $0560
$B555 | b14 file $01B565 | JSR $f2d7
$B558 | b14 file $01B568 | LDY #$00
$B55A | b14 file $01B56A | LDA ($00),Y
$B55C | b14 file $01B56C | STA $05ac
$B55F | b14 file $01B56F | LDY #$0b
$B561 | b14 file $01B571 | LDA ($00),Y
$B563 | b14 file $01B573 | PHA
$B564 | b14 file $01B574 | LDY #$01
$B566 | b14 file $01B576 | LDA ($00),Y
$B568 | b14 file $01B578 | PHA
$B569 | b14 file $01B579 | LDY #$09
$B56B | b14 file $01B57B | LDA ($00),Y
$B56D | b14 file $01B57D | PHA
$B56E | b14 file $01B57E | STA $0002
$B571 | b14 file $01B581 | DEY
$B572 | b14 file $01B582 | LDA ($00),Y
$B574 | b14 file $01B584 | PHA
$B575 | b14 file $01B585 | STA $0001
$B578 | b14 file $01B588 | LDA #$64
$B57A | b14 file $01B58A | STA $0003
$B57D | b14 file $01B58D | LDA #$00
$B57F | b14 file $01B58F | STA $0004
$B582 | b14 file $01B592 | JSR $ea7c
$B585 | b14 file $01B595 | LDA $0005
$B588 | b14 file $01B598 | BEQ $b58d
$B58A | b14 file $01B59A | INC $0001
$B58D | b14 file $01B59D | LDA $0001
$B590 | b14 file $01B5A0 | STA $0566
$B593 | b14 file $01B5A3 | STA $0003
$B596 | b14 file $01B5A6 | PLA
$B597 | b14 file $01B5A7 | STA $0001
$B59A | b14 file $01B5AA | PLA
$B59B | b14 file $01B5AB | STA $0002
$B59E | b14 file $01B5AE | LDA #$00
$B5A0 | b14 file $01B5B0 | STA $0004
$B5A3 | b14 file $01B5B3 | JSR $ea7c
$B5A6 | b14 file $01B5B6 | LDY #$00
$B5A8 | b14 file $01B5B8 | INC $0001
$B5AB | b14 file $01B5BB | LDA $0001
$B5AE | b14 file $01B5BE | CPY $0005
$B5B1 | b14 file $01B5C1 | BCS $b5be
$B5B3 | b14 file $01B5C3 | STA $05ad,Y
$B5B6 | b14 file $01B5C6 | INY
$B5B7 | b14 file $01B5C7 | CPY $0566
$B5BA | b14 file $01B5CA | BCC $b5ae
$B5BC | b14 file $01B5CC | BCS $b5ca
$B5BE | b14 file $01B5CE | SEC
$B5BF | b14 file $01B5CF | SBC #$01
$B5C1 | b14 file $01B5D1 | STA $05ad,Y
$B5C4 | b14 file $01B5D4 | INY
$B5C5 | b14 file $01B5D5 | CPY $0566
$B5C8 | b14 file $01B5D8 | BCC $b5c1
$B5CA | b14 file $01B5DA | LDA $056c
$B5CD | b14 file $01B5DD | AND #$03
$B5CF | b14 file $01B5DF | ASL A
$B5D0 | b14 file $01B5E0 | TAY
$B5D1 | b14 file $01B5E1 | LDA $b794,Y
$B5D4 | b14 file $01B5E4 | STA $000a
$B5D7 | b14 file $01B5E7 | LDA $b795,Y
$B5DA | b14 file $01B5EA | STA $000b
$B5DD | b14 file $01B5ED | LDA $b7a0,Y
$B5E0 | b14 file $01B5F0 | STA $000c
$B5E3 | b14 file $01B5F3 | LDA $b7a1,Y
$B5E6 | b14 file $01B5F6 | STA $000d
$B5E9 | b14 file $01B5F9 | LDY #$00
$B5EB | b14 file $01B5FB | PLA
$B5EC | b14 file $01B5FC | CMP #$50
$B5EE | b14 file $01B5FE | BCS $b5f6
$B5F0 | b14 file $01B600 | INY
$B5F1 | b14 file $01B601 | CMP #$32
$B5F3 | b14 file $01B603 | BCS $b5f6
$B5F5 | b14 file $01B605 | INY
$B5F6 | b14 file $01B606 | STY $0000
$B5F9 | b14 file $01B609 | PLA
$B5FA | b14 file $01B60A | LSR A
$B5FB | b14 file $01B60B | LSR A
$B5FC | b14 file $01B60C | LSR A
$B5FD | b14 file $01B60D | LSR A
$B5FE | b14 file $01B60E | ASL A
$B5FF | b14 file $01B60F | ASL A
$B600 | b14 file $01B610 | ORA $0000
$B603 | b14 file $01B613 | ASL A
$B604 | b14 file $01B614 | TAY
$B605 | b14 file $01B615 | LDA $b7ac,Y
$B608 | b14 file $01B618 | STA $0001
$B60B | b14 file $01B61B | LDA $b7ad,Y
$B60E | b14 file $01B61E | STA $0002
$B611 | b14 file $01B621 | LDA $0566
$B614 | b14 file $01B624 | STA $0000
$B617 | b14 file $01B627 | INC $0000
$B61A | b14 file $01B62A | LDY #$00
$B61C | b14 file $01B62C | LDA #$30
$B61E | b14 file $01B62E | CPY #$00
$B620 | b14 file $01B630 | BEQ $b632
$B622 | b14 file $01B632 | LDA #$33
$B624 | b14 file $01B634 | CPY $0001
$B627 | b14 file $01B637 | BCC $b632
$B629 | b14 file $01B639 | LDA #$32
$B62B | b14 file $01B63B | CPY $0002
$B62E | b14 file $01B63E | BCC $b632
$B630 | b14 file $01B640 | LDA #$31
$B632 | b14 file $01B642 | STA $05c2,Y
$B635 | b14 file $01B645 | LDA ($0a),Y
$B637 | b14 file $01B647 | STA $0580,Y
$B63A | b14 file $01B64A | LDA ($0c),Y
$B63C | b14 file $01B64C | STA $0596,Y
$B63F | b14 file $01B64F | INY
$B640 | b14 file $01B650 | CPY $0000
$B643 | b14 file $01B653 | BCC $b61c
$B645 | b14 file $01B655 | LDA $0561
$B648 | b14 file $01B658 | JSR $f2d7
$B64B | b14 file $01B65B | LDY #$00
$B64D | b14 file $01B65D | LDA ($00),Y
$B64F | b14 file $01B65F | STA $05b7
$B652 | b14 file $01B662 | LDY #$0b
$B654 | b14 file $01B664 | LDA ($00),Y
$B656 | b14 file $01B666 | PHA
$B657 | b14 file $01B667 | LDY #$01
$B659 | b14 file $01B669 | LDA ($00),Y
$B65B | b14 file $01B66B | PHA
$B65C | b14 file $01B66C | LDY #$09
$B65E | b14 file $01B66E | LDA ($00),Y
$B660 | b14 file $01B670 | PHA
$B661 | b14 file $01B671 | STA $0002
$B664 | b14 file $01B674 | DEY
$B665 | b14 file $01B675 | LDA ($00),Y
$B667 | b14 file $01B677 | PHA
$B668 | b14 file $01B678 | STA $0001
$B66B | b14 file $01B67B | LDA #$64
$B66D | b14 file $01B67D | STA $0003
$B670 | b14 file $01B680 | LDA #$00
$B672 | b14 file $01B682 | STA $0004
$B675 | b14 file $01B685 | JSR $ea7c
$B678 | b14 file $01B688 | LDA $0005
$B67B | b14 file $01B68B | BEQ $b680
$B67D | b14 file $01B68D | INC $0001
$B680 | b14 file $01B690 | LDA $0001
$B683 | b14 file $01B693 | STA $0567
$B686 | b14 file $01B696 | STA $0003
$B689 | b14 file $01B699 | PLA
$B68A | b14 file $01B69A | STA $0001
$B68D | b14 file $01B69D | PLA
$B68E | b14 file $01B69E | STA $0002
$B691 | b14 file $01B6A1 | LDA #$00
$B693 | b14 file $01B6A3 | STA $0004
$B696 | b14 file $01B6A6 | JSR $ea7c
$B699 | b14 file $01B6A9 | LDY #$00
$B69B | b14 file $01B6AB | INC $0001
$B69E | b14 file $01B6AE | LDA $0001
$B6A1 | b14 file $01B6B1 | CPY $0005
$B6A4 | b14 file $01B6B4 | BCS $b6b1
$B6A6 | b14 file $01B6B6 | STA $05b8,Y
$B6A9 | b14 file $01B6B9 | INY
$B6AA | b14 file $01B6BA | CPY $0567
$B6AD | b14 file $01B6BD | BCC $b6a1
$B6AF | b14 file $01B6BF | BCS $b6bd
$B6B1 | b14 file $01B6C1 | SEC
$B6B2 | b14 file $01B6C2 | SBC #$01
$B6B4 | b14 file $01B6C4 | STA $05b8,Y
$B6B7 | b14 file $01B6C7 | INY
$B6B8 | b14 file $01B6C8 | CPY $0567
$B6BB | b14 file $01B6CB | BCC $b6b4
$B6BD | b14 file $01B6CD | LDA #$04
$B6BF | b14 file $01B6CF | LDY $0544
$B6C2 | b14 file $01B6D2 | CPY #$05
$B6C4 | b14 file $01B6D4 | BEQ $b6cb
$B6C6 | b14 file $01B6D6 | LDA $056d
$B6C9 | b14 file $01B6D9 | AND #$03
$B6CB | b14 file $01B6DB | ASL A
$B6CC | b14 file $01B6DC | TAY
$B6CD | b14 file $01B6DD | LDA $b794,Y
$B6D0 | b14 file $01B6E0 | STA $000a
$B6D3 | b14 file $01B6E3 | LDA $b795,Y
$B6D6 | b14 file $01B6E6 | STA $000b
$B6D9 | b14 file $01B6E9 | LDA $b7a0,Y
$B6DC | b14 file $01B6EC | STA $000c
$B6DF | b14 file $01B6EF | LDA $b7a1,Y
$B6E2 | b14 file $01B6F2 | STA $000d
$B6E5 | b14 file $01B6F5 | LDA $b796,Y
$B6E8 | b14 file $01B6F8 | STA $001a
$B6EB | b14 file $01B6FB | LDA $b797,Y
$B6EE | b14 file $01B6FE | STA $001b
$B6F1 | b14 file $01B701 | LDA $b7a2,Y
$B6F4 | b14 file $01B704 | STA $001c
$B6F7 | b14 file $01B707 | LDA $b7a3,Y
$B6FA | b14 file $01B70A | STA $001d
$B6FD | b14 file $01B70D | LDY #$00
$B6FF | b14 file $01B70F | PLA
$B700 | b14 file $01B710 | CMP #$50
$B702 | b14 file $01B712 | BCS $b70a
$B704 | b14 file $01B714 | INY
$B705 | b14 file $01B715 | CMP #$32
$B707 | b14 file $01B717 | BCS $b70a
$B709 | b14 file $01B719 | INY
$B70A | b14 file $01B71A | STY $0000
$B70D | b14 file $01B71D | PLA
$B70E | b14 file $01B71E | LSR A
$B70F | b14 file $01B71F | LSR A
$B710 | b14 file $01B720 | LSR A
$B711 | b14 file $01B721 | LSR A
$B712 | b14 file $01B722 | ASL A
$B713 | b14 file $01B723 | ASL A
$B714 | b14 file $01B724 | ORA $0000
$B717 | b14 file $01B727 | ASL A
$B718 | b14 file $01B728 | TAY
$B719 | b14 file $01B729 | LDA $b7ac,Y
$B71C | b14 file $01B72C | STA $0001
$B71F | b14 file $01B72F | LDA $b7ad,Y
$B722 | b14 file $01B732 | STA $0002
$B725 | b14 file $01B735 | LDA $0544
$B728 | b14 file $01B738 | CMP #$05
$B72A | b14 file $01B73A | BNE $b731
$B72C | b14 file $01B73C | LDA #$00
$B72E | b14 file $01B73E | STA $0001
$B731 | b14 file $01B741 | LDA $0567
$B734 | b14 file $01B744 | STA $0000
$B737 | b14 file $01B747 | INC $0000
$B73A | b14 file $01B74A | LDY #$00
$B73C | b14 file $01B74C | LDA #$20
$B73E | b14 file $01B74E | CPY #$00
$B740 | b14 file $01B750 | BEQ $b752
$B742 | b14 file $01B752 | LDA #$23
$B744 | b14 file $01B754 | CPY $0001
$B747 | b14 file $01B757 | BCC $b752
$B749 | b14 file $01B759 | LDA #$22
$B74B | b14 file $01B75B | CPY $0002
$B74E | b14 file $01B75E | BCC $b752
$B750 | b14 file $01B760 | LDA #$21
$B752 | b14 file $01B762 | STA $05cd,Y
$B755 | b14 file $01B765 | CMP #$22
$B757 | b14 file $01B767 | BEQ $b77a
$B759 | b14 file $01B769 | LDA $0544
$B75C | b14 file $01B76C | CMP #$05
$B75E | b14 file $01B76E | BNE $b77a
$B760 | b14 file $01B770 | LDA ($1a),Y
$B762 | b14 file $01B772 | STA $0003
$B765 | b14 file $01B775 | LDA #$0f
$B767 | b14 file $01B777 | SEC
$B768 | b14 file $01B778 | SBC $0003
$B76B | b14 file $01B77B | STA $058b,Y
$B76E | b14 file $01B77E | LDA ($1c),Y
$B770 | b14 file $01B780 | STA $05a1,Y
$B773 | b14 file $01B783 | INY
$B774 | b14 file $01B784 | CPY $0000
$B777 | b14 file $01B787 | BCC $b73c
$B779 | b14 file $01B789 | RTS
$B77A | b14 file $01B78A | LDA ($0a),Y
$B77C | b14 file $01B78C | STA $0003
$B77F | b14 file $01B78F | LDA #$0f
$B781 | b14 file $01B791 | SEC
$B782 | b14 file $01B792 | SBC $0003
$B785 | b14 file $01B795 | STA $058b,Y
$B788 | b14 file $01B798 | LDA ($0c),Y
$B78A | b14 file $01B79A | STA $05a1,Y
$B78D | b14 file $01B79D | INY
$B78E | b14 file $01B79E | CPY $0000
$B791 | b14 file $01B7A1 | BCC $b73c
$B793 | b14 file $01B7A3 | RTS
$B870 | b14 file $01B880 | LDA $0304
$B873 | b14 file $01B883 | CMP #$ff
$B875 | b14 file $01B885 | BNE $b880
$B877 | b14 file $01B887 | LDA $0300
$B87A | b14 file $01B88A | CMP #$ff
$B87C | b14 file $01B88C | BNE $b880
$B87E | b14 file $01B88E | SEC
$B87F | b14 file $01B88F | RTS
$B880 | b14 file $01B890 | CLC
$B881 | b14 file $01B891 | RTS
$B882 | b14 file $01B892 | LDY $0013
$B885 | b14 file $01B895 | LDA $0580,Y
$B888 | b14 file $01B898 | STA $0010
$B88B | b14 file $01B89B | LDA $0596,Y
$B88E | b14 file $01B89E | STA $0011
$B891 | b14 file $01B8A1 | LDA $0544
$B894 | b14 file $01B8A4 | PHA
$B895 | b14 file $01B8A5 | PHA
$B896 | b14 file $01B8A6 | TAY
$B897 | b14 file $01B8A7 | LDA $bb48,Y
$B89A | b14 file $01B8AA | TAY
$B89B | b14 file $01B8AB | JSR $f25f
$B89E | b14 file $01B8AE | PLA
$B89F | b14 file $01B8AF | ASL A
$B8A0 | b14 file $01B8B0 | TAY
$B8A1 | b14 file $01B8B1 | LDA $bb1e,Y
$B8A4 | b14 file $01B8B4 | STA $0000
$B8A7 | b14 file $01B8B7 | LDA $bb1f,Y
$B8AA | b14 file $01B8BA | STA $0001
$B8AD | b14 file $01B8BD | LDA $bb2c,Y
$B8B0 | b14 file $01B8C0 | STA $0002
$B8B3 | b14 file $01B8C3 | LDA $bb2d,Y
$B8B6 | b14 file $01B8C6 | STA $0003
$B8B9 | b14 file $01B8C9 | LDA $0010
$B8BC | b14 file $01B8CC | STA $0008
$B8BF | b14 file $01B8CF | LDX #$00
$B8C1 | b14 file $01B8D1 | LDA $0011
$B8C4 | b14 file $01B8D4 | ASL A
$B8C5 | b14 file $01B8D5 | ASL A
$B8C6 | b14 file $01B8D6 | ASL A
$B8C7 | b14 file $01B8D7 | ASL A
$B8C8 | b14 file $01B8D8 | PHA
$B8C9 | b14 file $01B8D9 | ORA $0010
$B8CC | b14 file $01B8DC | TAY
$B8CD | b14 file $01B8DD | LDA #$00
$B8CF | b14 file $01B8DF | STA $0004
$B8D2 | b14 file $01B8E2 | LDA ($00),Y
$B8D4 | b14 file $01B8E4 | ASL A
$B8D5 | b14 file $01B8E5 | ROL $0004
$B8D8 | b14 file $01B8E8 | ASL A
$B8D9 | b14 file $01B8E9 | ROL $0004
$B8DC | b14 file $01B8EC | CLC
$B8DD | b14 file $01B8ED | ADC $0002
$B8E0 | b14 file $01B8F0 | STA $0002
$B8E3 | b14 file $01B8F3 | LDA $0003
$B8E6 | b14 file $01B8F6 | ADC $0004
$B8E9 | b14 file $01B8F9 | STA $0003
$B8EC | b14 file $01B8FC | LDY #$00
$B8EE | b14 file $01B8FE | LDA ($02),Y
$B8F0 | b14 file $01B900 | STA $0383
$B8F3 | b14 file $01B903 | STA $0391
$B8F6 | b14 file $01B906 | INY
$B8F7 | b14 file $01B907 | LDA ($02),Y
$B8F9 | b14 file $01B909 | STA $0384
$B8FC | b14 file $01B90C | STA $0392
$B8FF | b14 file $01B90F | INY
$B900 | b14 file $01B910 | LDA ($02),Y
$B902 | b14 file $01B912 | STA $0388
$B905 | b14 file $01B915 | STA $0396
$B908 | b14 file $01B918 | INY
$B909 | b14 file $01B919 | LDA ($02),Y
$B90B | b14 file $01B91B | STA $0389
$B90E | b14 file $01B91E | STA $0397
$B911 | b14 file $01B921 | ASL $0008
$B914 | b14 file $01B924 | LDA #$00
$B916 | b14 file $01B926 | STA $000b
$B919 | b14 file $01B929 | PLA
$B91A | b14 file $01B92A | ASL A
$B91B | b14 file $01B92B | ROL $000b
$B91E | b14 file $01B92E | ASL A
$B91F | b14 file $01B92F | ROL $000b
$B922 | b14 file $01B932 | CLC
$B923 | b14 file $01B933 | ADC $0008
$B926 | b14 file $01B936 | STA $0382
$B929 | b14 file $01B939 | STA $0390
$B92C | b14 file $01B93C | LDA $000b
$B92F | b14 file $01B93F | ORA #$20
$B931 | b14 file $01B941 | STA $0381
$B934 | b14 file $01B944 | ORA #$04
$B936 | b14 file $01B946 | STA $038f
$B939 | b14 file $01B949 | LDA $0382
$B93C | b14 file $01B94C | CLC
$B93D | b14 file $01B94D | ADC #$20
$B93F | b14 file $01B94F | STA $0387
$B942 | b14 file $01B952 | STA $0395
$B945 | b14 file $01B955 | LDA $0381
$B948 | b14 file $01B958 | ADC #$00
$B94A | b14 file $01B95A | STA $0386
$B94D | b14 file $01B95D | ORA #$04
$B94F | b14 file $01B95F | STA $0394
$B952 | b14 file $01B962 | LDA #$02
$B954 | b14 file $01B964 | STA $0380
$B957 | b14 file $01B967 | STA $0385
$B95A | b14 file $01B96A | STA $038e
$B95D | b14 file $01B96D | STA $0393
$B960 | b14 file $01B970 | LDA $0012
$B963 | b14 file $01B973 | BEQ $b9a9
$B965 | b14 file $01B975 | LDY $0013
$B968 | b14 file $01B978 | LDA $05c2,Y
$B96B | b14 file $01B97B | AND #$03
$B96D | b14 file $01B97D | STA $0000
$B970 | b14 file $01B980 | LDA $05c2,Y
$B973 | b14 file $01B983 | AND #$f0
$B975 | b14 file $01B985 | LSR A
$B976 | b14 file $01B986 | LSR A
$B977 | b14 file $01B987 | ORA $0000
$B97A | b14 file $01B98A | CMP #$10
$B97C | b14 file $01B98C | BCC $b97f
$B97E | b14 file $01B98E | NOP
$B97F | b14 file $01B98F | ASL A
$B980 | b14 file $01B990 | ASL A
$B981 | b14 file $01B991 | TAY
$B982 | b14 file $01B992 | LDA $bb4f,Y
$B985 | b14 file $01B995 | STA $0383
$B988 | b14 file $01B998 | STA $0391
$B98B | b14 file $01B99B | LDA $bb50,Y
$B98E | b14 file $01B99E | STA $0384
$B991 | b14 file $01B9A1 | STA $0392
$B994 | b14 file $01B9A4 | LDA $bb51,Y
$B997 | b14 file $01B9A7 | STA $0388
$B99A | b14 file $01B9AA | STA $0396
$B99D | b14 file $01B9AD | LDA $bb52,Y
$B9A0 | b14 file $01B9B0 | STA $0389
$B9A3 | b14 file $01B9B3 | STA $0397
$B9A6 | b14 file $01B9B6 | JSR $ba18
$B9A9 | b14 file $01B9B9 | PLA
$B9AA | b14 file $01B9BA | ASL A
$B9AB | b14 file $01B9BB | TAY
$B9AC | b14 file $01B9BC | LDA $bb3a,Y
$B9AF | b14 file $01B9BF | STA $0000
$B9B2 | b14 file $01B9C2 | LDA $bb3b,Y
$B9B5 | b14 file $01B9C5 | STA $0001
$B9B8 | b14 file $01B9C8 | LDA $0010
$B9BB | b14 file $01B9CB | AND #$0e
$B9BD | b14 file $01B9CD | LSR A
$B9BE | b14 file $01B9CE | STA $0008
$B9C1 | b14 file $01B9D1 | LDA $0011
$B9C4 | b14 file $01B9D4 | AND #$0e
$B9C6 | b14 file $01B9D6 | ASL A
$B9C7 | b14 file $01B9D7 | ASL A
$B9C8 | b14 file $01B9D8 | ORA $0008
$B9CB | b14 file $01B9DB | TAY
$B9CC | b14 file $01B9DC | LDA ($00),Y
$B9CE | b14 file $01B9DE | STA $0000
$B9D1 | b14 file $01B9E1 | JSR $ba56
$B9D4 | b14 file $01B9E4 | LDA $0000
$B9D7 | b14 file $01B9E7 | STA $038d
$B9DA | b14 file $01B9EA | STA $039b
$B9DD | b14 file $01B9ED | LDA $0010
$B9E0 | b14 file $01B9F0 | AND #$0e
$B9E2 | b14 file $01B9F2 | LSR A
$B9E3 | b14 file $01B9F3 | STA $0000
$B9E6 | b14 file $01B9F6 | LDA $0011
$B9E9 | b14 file $01B9F9 | AND #$0e
$B9EB | b14 file $01B9FB | ASL A
$B9EC | b14 file $01B9FC | ASL A
$B9ED | b14 file $01B9FD | ORA $0000
$B9F0 | b14 file $01BA00 | ORA #$c0
$B9F2 | b14 file $01BA02 | STA $038c
$B9F5 | b14 file $01BA05 | STA $039a
$B9F8 | b14 file $01BA08 | LDA #$23
$B9FA | b14 file $01BA0A | STA $038b
$B9FD | b14 file $01BA0D | LDA #$27
$B9FF | b14 file $01BA0F | STA $0399
$BA02 | b14 file $01BA12 | LDA #$01
$BA04 | b14 file $01BA14 | STA $038a
$BA07 | b14 file $01BA17 | STA $0398
$BA0A | b14 file $01BA1A | LDA #$ff
$BA0C | b14 file $01BA1C | STA $039c
$BA0F | b14 file $01BA1F | LDA $007e
$BA12 | b14 file $01BA22 | ORA #$04
$BA14 | b14 file $01BA24 | STA $007e
$BA17 | b14 file $01BA27 | RTS
$BA18 | b14 file $01BA28 | LDY $0013
$BA1B | b14 file $01BA2B | LDA $05ac,Y
$BA1E | b14 file $01BA2E | STA $0001
$BA21 | b14 file $01BA31 | LDA #$00
$BA23 | b14 file $01BA33 | STA $0002
$BA26 | b14 file $01BA36 | STA $0003
$BA29 | b14 file $01BA39 | JSR $e9ba
$BA2C | b14 file $01BA3C | LDA $0007
$BA2F | b14 file $01BA3F | LSR A
$BA30 | b14 file $01BA40 | LSR A
$BA31 | b14 file $01BA41 | LSR A
$BA32 | b14 file $01BA42 | LSR A
$BA33 | b14 file $01BA43 | CLC
$BA34 | b14 file $01BA44 | ADC #$b4
$BA36 | b14 file $01BA46 | STA $0396
$BA39 | b14 file $01BA49 | LDA $0007
$BA3C | b14 file $01BA4C | AND #$0f
$BA3E | b14 file $01BA4E | CLC
$BA3F | b14 file $01BA4F | ADC #$b4
$BA41 | b14 file $01BA51 | STA $0397
$BA44 | b14 file $01BA54 | LDA $0008
$BA47 | b14 file $01BA57 | AND #$0f
$BA49 | b14 file $01BA59 | BEQ $ba55
$BA4B | b14 file $01BA5B | LDA #$be
$BA4D | b14 file $01BA5D | STA $0396
$BA50 | b14 file $01BA60 | LDA #$bf
$BA52 | b14 file $01BA62 | STA $0397
$BA55 | b14 file $01BA65 | RTS
$BA56 | b14 file $01BA66 | LDA $0010
$BA59 | b14 file $01BA69 | AND #$0e
$BA5B | b14 file $01BA6B | STA $0002
$BA5E | b14 file $01BA6E | LDA $0011
$BA61 | b14 file $01BA71 | AND #$0e
$BA63 | b14 file $01BA73 | STA $0003
$BA66 | b14 file $01BA76 | LDY #$15
$BA68 | b14 file $01BA78 | LDA $0012
$BA6B | b14 file $01BA7B | BNE $ba72
$BA6D | b14 file $01BA7D | CPY $0013
$BA70 | b14 file $01BA80 | BEQ $ba75
$BA72 | b14 file $01BA82 | JSR $ba79
$BA75 | b14 file $01BA85 | DEY
$BA76 | b14 file $01BA86 | BPL $ba68
$BA78 | b14 file $01BA88 | RTS
$BA79 | b14 file $01BA89 | LDA #$01
$BA7B | b14 file $01BA8B | STA $000a
$BA7E | b14 file $01BA8E | LDA #$04
$BA80 | b14 file $01BA90 | STA $000b
$BA83 | b14 file $01BA93 | LDA #$10
$BA85 | b14 file $01BA95 | STA $000c
$BA88 | b14 file $01BA98 | LDA #$40
$BA8A | b14 file $01BA9A | STA $000d
$BA8D | b14 file $01BA9D | CPY #$0b
$BA8F | b14 file $01BA9F | BCS $baa5
$BA91 | b14 file $01BAA1 | LDA #$03
$BA93 | b14 file $01BAA3 | STA $000a
$BA96 | b14 file $01BAA6 | LDA #$0c
$BA98 | b14 file $01BAA8 | STA $000b
$BA9B | b14 file $01BAAB | LDA #$30
$BA9D | b14 file $01BAAD | STA $000c
$BAA0 | b14 file $01BAB0 | LDA #$c0
$BAA2 | b14 file $01BAB2 | STA $000d
$BAA5 | b14 file $01BAB5 | LDA $0002
$BAA8 | b14 file $01BAB8 | CMP $0580,Y
$BAAB | b14 file $01BABB | BNE $bac0
$BAAD | b14 file $01BABD | LDA $0003
$BAB0 | b14 file $01BAC0 | CMP $0596,Y
$BAB3 | b14 file $01BAC3 | BNE $bac0
$BAB5 | b14 file $01BAC5 | LDA $0000
$BAB8 | b14 file $01BAC8 | AND #$fc
$BABA | b14 file $01BACA | ORA $000a
$BABD | b14 file $01BACD | STA $0000
$BAC0 | b14 file $01BAD0 | INC $0002
$BAC3 | b14 file $01BAD3 | LDA $0002
$BAC6 | b14 file $01BAD6 | CMP $0580,Y
$BAC9 | b14 file $01BAD9 | BNE $bade
$BACB | b14 file $01BADB | LDA $0003
$BACE | b14 file $01BADE | CMP $0596,Y
$BAD1 | b14 file $01BAE1 | BNE $bade
$BAD3 | b14 file $01BAE3 | LDA $0000
$BAD6 | b14 file $01BAE6 | AND #$f3
$BAD8 | b14 file $01BAE8 | ORA $000b
$BADB | b14 file $01BAEB | STA $0000
$BADE | b14 file $01BAEE | INC $0003
$BAE1 | b14 file $01BAF1 | LDA $0002
$BAE4 | b14 file $01BAF4 | CMP $0580,Y
$BAE7 | b14 file $01BAF7 | BNE $bafc
$BAE9 | b14 file $01BAF9 | LDA $0003
$BAEC | b14 file $01BAFC | CMP $0596,Y
$BAEF | b14 file $01BAFF | BNE $bafc
$BAF1 | b14 file $01BB01 | LDA $0000
$BAF4 | b14 file $01BB04 | AND #$3f
$BAF6 | b14 file $01BB06 | ORA $000d
$BAF9 | b14 file $01BB09 | STA $0000
$BAFC | b14 file $01BB0C | DEC $0002
$BAFF | b14 file $01BB0F | LDA $0002
$BB02 | b14 file $01BB12 | CMP $0580,Y
$BB05 | b14 file $01BB15 | BNE $bb1a
$BB07 | b14 file $01BB17 | LDA $0003
$BB0A | b14 file $01BB1A | CMP $0596,Y
$BB0D | b14 file $01BB1D | BNE $bb1a
$BB0F | b14 file $01BB1F | LDA $0000
$BB12 | b14 file $01BB22 | AND #$cf
$BB14 | b14 file $01BB24 | ORA $000c
$BB17 | b14 file $01BB27 | STA $0000
$BB1A | b14 file $01BB2A | DEC $0003
$BB1D | b14 file $01BB2D | RTS
$BB8F | b14 file $01BB9F | LDA $005e
$BB92 | b14 file $01BBA2 | LSR A
$BB93 | b14 file $01BBA3 | LSR A
$BB94 | b14 file $01BBA4 | AND #$03
$BB96 | b14 file $01BBA6 | STA $0001
$BB99 | b14 file $01BBA9 | LDY $0545
$BB9C | b14 file $01BBAC | LDA $05c2,Y
$BB9F | b14 file $01BBAF | AND #$03
$BBA1 | b14 file $01BBB1 | STA $0000
$BBA4 | b14 file $01BBB4 | LDA $05c2,Y
$BBA7 | b14 file $01BBB7 | AND #$f0
$BBA9 | b14 file $01BBB9 | LSR A
$BBAA | b14 file $01BBBA | LSR A
$BBAB | b14 file $01BBBB | ORA $0000
$BBAE | b14 file $01BBBE | ASL A
$BBAF | b14 file $01BBBF | ASL A
$BBB0 | b14 file $01BBC0 | ORA $0001
$BBB3 | b14 file $01BBC3 | ASL A
$BBB4 | b14 file $01BBC4 | TAY
$BBB5 | b14 file $01BBC5 | LDA $bbfd,Y
$BBB8 | b14 file $01BBC8 | STA $0000
$BBBB | b14 file $01BBCB | LDA $bbfe,Y
$BBBE | b14 file $01BBCE | STA $0001
$BBC1 | b14 file $01BBD1 | LDA $054a
$BBC4 | b14 file $01BBD4 | CLC
$BBC5 | b14 file $01BBD5 | ADC #$08
$BBC7 | b14 file $01BBD7 | STA $000c
$BBCA | b14 file $01BBDA | LDA $054b
$BBCD | b14 file $01BBDD | STA $000a
$BBD0 | b14 file $01BBE0 | LDA #$00
$BBD2 | b14 file $01BBE2 | STA $000b
$BBD5 | b14 file $01BBE5 | STA $000d
$BBD8 | b14 file $01BBE8 | LDA #$00
$BBDA | b14 file $01BBEA | STA $0002
$BBDD | b14 file $01BBED | LDY $0545
$BBE0 | b14 file $01BBF0 | LDA $05c2,Y
$BBE3 | b14 file $01BBF3 | LSR A
$BBE4 | b14 file $01BBF4 | LSR A
$BBE5 | b14 file $01BBF5 | LSR A
$BBE6 | b14 file $01BBF6 | LSR A
$BBE7 | b14 file $01BBF7 | CMP #$03
$BBE9 | b14 file $01BBF9 | BNE $bbf0
$BBEB | b14 file $01BBFB | LDA #$40
$BBED | b14 file $01BBFD | STA $0002
$BBF0 | b14 file $01BC00 | LDY $0545
$BBF3 | b14 file $01BC03 | CPY #$0b
$BBF5 | b14 file $01BC05 | BCS $bbfa
$BBF7 | b14 file $01BC07 | INC $0002
$BBFA | b14 file $01BC0A | JMP $f092
$BE15 | b14 file $01BE25 | LDY $0545
$BE18 | b14 file $01BE28 | LDA $0580,Y
$BE1B | b14 file $01BE2B | ASL A
$BE1C | b14 file $01BE2C | ASL A
$BE1D | b14 file $01BE2D | ASL A
$BE1E | b14 file $01BE2E | ASL A
$BE1F | b14 file $01BE2F | STA $000c
$BE22 | b14 file $01BE32 | LDA $0596,Y
$BE25 | b14 file $01BE35 | ASL A
$BE26 | b14 file $01BE36 | ASL A
$BE27 | b14 file $01BE37 | ASL A
$BE28 | b14 file $01BE38 | ASL A
$BE29 | b14 file $01BE39 | STA $000a
$BE2C | b14 file $01BE3C | LDA #$65
$BE2E | b14 file $01BE3E | STA $0000
$BE31 | b14 file $01BE41 | LDA #$be
$BE33 | b14 file $01BE43 | STA $0001
$BE36 | b14 file $01BE46 | LDY $0549
$BE39 | b14 file $01BE49 | LDA $000c
$BE3C | b14 file $01BE4C | CLC
$BE3D | b14 file $01BE4D | ADC $be5d,Y
$BE40 | b14 file $01BE50 | STA $000c
$BE43 | b14 file $01BE53 | LDA $000a
$BE46 | b14 file $01BE56 | CLC
$BE47 | b14 file $01BE57 | ADC $be61,Y
$BE4A | b14 file $01BE5A | STA $000a
$BE4D | b14 file $01BE5D | LDA #$00
$BE4F | b14 file $01BE5F | STA $000b
$BE52 | b14 file $01BE62 | STA $000d
$BE55 | b14 file $01BE65 | LDA #$00
$BE57 | b14 file $01BE67 | STA $0002
$BE5A | b14 file $01BE6A | JMP $f092
$BE76 | b14 file $01BE86 | LDA $0545
$BE79 | b14 file $01BE89 | CMP #$0b
$BE7B | b14 file $01BE8B | BCC $be8d
$BE7D | b14 file $01BE8D | LDA $0577
$BE80 | b14 file $01BE90 | AND #$f0
$BE82 | b14 file $01BE92 | BEQ $be9d
$BE84 | b14 file $01BE94 | LDA $0549
$BE87 | b14 file $01BE97 | CLC
$BE88 | b14 file $01BE98 | ADC #$04
$BE8A | b14 file $01BE9A | JMP $bea0
$BE8D | b14 file $01BE9D | LDA $0577
$BE90 | b14 file $01BEA0 | AND #$0f
$BE92 | b14 file $01BEA2 | BEQ $be9d
$BE94 | b14 file $01BEA4 | LDA $0549
$BE97 | b14 file $01BEA7 | CLC
$BE98 | b14 file $01BEA8 | ADC #$04
$BE9A | b14 file $01BEAA | JMP $bea0
$BE9D | b14 file $01BEAD | LDA $0549
$BEA0 | b14 file $01BEB0 | ASL A
$BEA1 | b14 file $01BEB1 | TAY
$BEA2 | b14 file $01BEB2 | LDA $bedd,Y
$BEA5 | b14 file $01BEB5 | STA $0000
$BEA8 | b14 file $01BEB8 | LDA $bede,Y
$BEAB | b14 file $01BEBB | STA $0001
$BEAE | b14 file $01BEBE | LDY $0549
$BEB1 | b14 file $01BEC1 | LDA $054a
$BEB4 | b14 file $01BEC4 | CLC
$BEB5 | b14 file $01BEC5 | ADC $bed5,Y
$BEB8 | b14 file $01BEC8 | STA $000c
$BEBB | b14 file $01BECB | LDA $054b
$BEBE | b14 file $01BECE | CLC
$BEBF | b14 file $01BECF | ADC $bed9,Y
$BEC2 | b14 file $01BED2 | STA $000a
$BEC5 | b14 file $01BED5 | LDA #$00
$BEC7 | b14 file $01BED7 | STA $000b
$BECA | b14 file $01BEDA | STA $000d
$BECD | b14 file $01BEDD | LDA #$00
$BECF | b14 file $01BEDF | STA $0002
$BED2 | b14 file $01BEE2 | JMP $f092
$BF15 | b14 file $01BF25 | LDA #$3b
$BF17 | b14 file $01BF27 | STA $0000
$BF1A | b14 file $01BF2A | LDA #$bf
$BF1C | b14 file $01BF2C | STA $0001
$BF1F | b14 file $01BF2F | LDA $054a
$BF22 | b14 file $01BF32 | STA $000c
$BF25 | b14 file $01BF35 | LDA $054b
$BF28 | b14 file $01BF38 | STA $000a
$BF2B | b14 file $01BF3B | LDA #$00
$BF2D | b14 file $01BF3D | STA $000b
$BF30 | b14 file $01BF40 | STA $000d
$BF33 | b14 file $01BF43 | LDA #$00
$BF35 | b14 file $01BF45 | STA $0002
$BF38 | b14 file $01BF48 | JMP $f092
$BF4C | b14 file $01BF5C | LDY #$00
$BF4E | b14 file $01BF5E | LDA $0574
$BF51 | b14 file $01BF61 | LDX #$80
$BF53 | b14 file $01BF63 | JSR $bf9d
$BF56 | b14 file $01BF66 | LDY #$00
$BF58 | b14 file $01BF68 | LDA $0574
$BF5B | b14 file $01BF6B | LDX #$70
$BF5D | b14 file $01BF6D | JSR $bfa1
$BF60 | b14 file $01BF70 | LDY #$02
$BF62 | b14 file $01BF72 | LDA $0575
$BF65 | b14 file $01BF75 | LDX #$80
$BF67 | b14 file $01BF77 | JSR $bf9d
$BF6A | b14 file $01BF7A | LDY #$02
$BF6C | b14 file $01BF7C | LDA $0575
$BF6F | b14 file $01BF7F | LDX #$70
$BF71 | b14 file $01BF81 | JSR $bfa1
$BF74 | b14 file $01BF84 | LDY #$04
$BF76 | b14 file $01BF86 | LDA $0576
$BF79 | b14 file $01BF89 | LDX #$80
$BF7B | b14 file $01BF8B | JSR $bf9d
$BF7E | b14 file $01BF8E | LDY #$04
$BF80 | b14 file $01BF90 | LDA $0576
$BF83 | b14 file $01BF93 | LDX #$70
$BF85 | b14 file $01BF95 | JSR $bfa1
$BF88 | b14 file $01BF98 | LDY #$06
$BF8A | b14 file $01BF9A | LDA $0577
$BF8D | b14 file $01BF9D | LDX #$80
$BF8F | b14 file $01BF9F | JSR $bf9d
$BF92 | b14 file $01BFA2 | LDY #$06
$BF94 | b14 file $01BFA4 | LDA $0577
$BF97 | b14 file $01BFA7 | LDX #$70
$BF99 | b14 file $01BFA9 | JSR $bfa1
$BF9C | b14 file $01BFAC | RTS
$BF9D | b14 file $01BFAD | LSR A
$BF9E | b14 file $01BFAE | LSR A
$BF9F | b14 file $01BFAF | LSR A
$BFA0 | b14 file $01BFB0 | LSR A
$BFA1 | b14 file $01BFB1 | AND #$0f
$BFA3 | b14 file $01BFB3 | BEQ $bfce
$BFA5 | b14 file $01BFB5 | STX $000c
$BFA8 | b14 file $01BFB8 | LDA $bfcf,Y
$BFAB | b14 file $01BFBB | STA $0000
$BFAE | b14 file $01BFBE | LDA $bfd0,Y
$BFB1 | b14 file $01BFC1 | STA $0001
$BFB4 | b14 file $01BFC4 | LDA #$d0
$BFB6 | b14 file $01BFC6 | STA $000a
$BFB9 | b14 file $01BFC9 | LDA #$00
$BFBB | b14 file $01BFCB | STA $000b
$BFBE | b14 file $01BFCE | STA $000d
$BFC1 | b14 file $01BFD1 | LDA #$00
$BFC3 | b14 file $01BFD3 | STA $0002
$BFC6 | b14 file $01BFD6 | JSR $f092
$BFC9 | b14 file $01BFD9 | LDA #$91
$BFCB | b14 file $01BFDB | STA $00b7
$BFCE | b14 file $01BFDE | RTS
$C064 | b15 file $01E074 | LDA #$00
$C066 | b15 file $01E076 | STA $0012
$C069 | b15 file $01E079 | LDA $054f
$C06C | b15 file $01E07C | CMP #$01
$C06E | b15 file $01E07E | BEQ $c095
$C070 | b15 file $01E080 | LDA $0545
$C073 | b15 file $01E083 | CMP #$0b
$C075 | b15 file $01E085 | BCS $c086
$C077 | b15 file $01E087 | LDA $058b
$C07A | b15 file $01E08A | STA $0010
$C07D | b15 file $01E08D | LDA $05a1
$C080 | b15 file $01E090 | STA $0011
$C083 | b15 file $01E093 | JMP $c0b8
$C086 | b15 file $01E096 | LDA $0580
$C089 | b15 file $01E099 | STA $0010
$C08C | b15 file $01E09C | LDA $0596
$C08F | b15 file $01E09F | STA $0011
$C092 | b15 file $01E0A2 | JMP $c0b8
$C095 | b15 file $01E0A5 | LDA $0545
$C098 | b15 file $01E0A8 | CMP #$0b
$C09A | b15 file $01E0AA | BCS $c0aa
$C09C | b15 file $01E0AC | LDA #$ff
$C09E | b15 file $01E0AE | STA $0010
$C0A1 | b15 file $01E0B1 | LDA $05a1
$C0A4 | b15 file $01E0B4 | STA $0011
$C0A7 | b15 file $01E0B7 | JMP $c0b8
$C0AA | b15 file $01E0BA | LDA #$20
$C0AC | b15 file $01E0BC | STA $0010
$C0AF | b15 file $01E0BF | LDA $0596
$C0B2 | b15 file $01E0C2 | STA $0011
$C0B5 | b15 file $01E0C5 | JMP $c0b8
$C0B8 | b15 file $01E0C8 | LDA $0580,Y
$C0BB | b15 file $01E0CB | SEC
$C0BC | b15 file $01E0CC | SBC $0010
$C0BF | b15 file $01E0CF | STA $0010
$C0C2 | b15 file $01E0D2 | BCS $c0c9
$C0C4 | b15 file $01E0D4 | EOR #$ff
$C0C6 | b15 file $01E0D6 | CLC
$C0C7 | b15 file $01E0D7 | ADC #$01
$C0C9 | b15 file $01E0D9 | STA $0000
$C0CC | b15 file $01E0DC | LDA $0596,Y
$C0CF | b15 file $01E0DF | SEC
$C0D0 | b15 file $01E0E0 | SBC $0011
$C0D3 | b15 file $01E0E3 | STA $0011
$C0D6 | b15 file $01E0E6 | BCS $c0dd
$C0D8 | b15 file $01E0E8 | EOR #$ff
$C0DA | b15 file $01E0EA | CLC
$C0DB | b15 file $01E0EB | ADC #$01
$C0DD | b15 file $01E0ED | STA $0001
$C0E0 | b15 file $01E0F0 | LDA $05c2,Y
$C0E3 | b15 file $01E0F3 | AND #$0f
$C0E5 | b15 file $01E0F5 | BEQ $c109
$C0E7 | b15 file $01E0F7 | CMP #$03
$C0E9 | b15 file $01E0F9 | BEQ $c109
$C0EB | b15 file $01E0FB | CMP #$02
$C0ED | b15 file $01E0FD | BEQ $c0fc
$C0EF | b15 file $01E0FF | LDA $0000
$C0F2 | b15 file $01E102 | CMP #$02
$C0F4 | b15 file $01E104 | BCC $c0f9
$C0F6 | b15 file $01E106 | JMP $c123
$C0F9 | b15 file $01E109 | JMP $c178
$C0FC | b15 file $01E10C | LDA $0001
$C0FF | b15 file $01E10F | CMP #$02
$C101 | b15 file $01E111 | BCC $c106
$C103 | b15 file $01E113 | JMP $c178
$C106 | b15 file $01E116 | JMP $c123
$C109 | b15 file $01E119 | LDA $0001
$C10C | b15 file $01E11C | CMP $0000
$C10F | b15 file $01E11F | BEQ $c116
$C111 | b15 file $01E121 | BCC $c120
$C113 | b15 file $01E123 | JMP $c178
$C116 | b15 file $01E126 | JSR $e87a
$C119 | b15 file $01E129 | AND #$01
$C11B | b15 file $01E12B | BEQ $c120
$C11D | b15 file $01E12D | JMP $c178
$C120 | b15 file $01E130 | JMP $c123
$C123 | b15 file $01E133 | LDA $0010
$C126 | b15 file $01E136 | BEQ $c12c
$C128 | b15 file $01E138 | BMI $c14d
$C12A | b15 file $01E13A | BPL $c133
$C12C | b15 file $01E13C | JSR $e87a
$C12F | b15 file $01E13F | AND #$80
$C131 | b15 file $01E141 | BNE $c14d
$C133 | b15 file $01E143 | LDA #$ff
$C135 | b15 file $01E145 | STA $0000
$C138 | b15 file $01E148 | LDA #$00
$C13A | b15 file $01E14A | STA $0001
$C13D | b15 file $01E14D | JSR $c1cd
$C140 | b15 file $01E150 | BCC $c167
$C142 | b15 file $01E152 | JSR $caf9
$C145 | b15 file $01E155 | BNE $c167
$C147 | b15 file $01E157 | LDA #$02
$C149 | b15 file $01E159 | STA $0549
$C14C | b15 file $01E15C | RTS
$C14D | b15 file $01E15D | LDA #$01
$C14F | b15 file $01E15F | STA $0000
$C152 | b15 file $01E162 | LDA #$00
$C154 | b15 file $01E164 | STA $0001
$C157 | b15 file $01E167 | JSR $c1cd
$C15A | b15 file $01E16A | BCC $c167
$C15C | b15 file $01E16C | JSR $caf9
$C15F | b15 file $01E16F | BNE $c167
$C161 | b15 file $01E171 | LDA #$03
$C163 | b15 file $01E173 | STA $0549
$C166 | b15 file $01E176 | RTS
$C167 | b15 file $01E177 | LDA $0012
$C16A | b15 file $01E17A | BNE $c172
$C16C | b15 file $01E17C | INC $0012
$C16F | b15 file $01E17F | JMP $c178
$C172 | b15 file $01E182 | LDA #$ff
$C174 | b15 file $01E184 | STA $0549
$C177 | b15 file $01E187 | RTS
$C178 | b15 file $01E188 | LDA $0011
$C17B | b15 file $01E18B | BEQ $c181
$C17D | b15 file $01E18D | BMI $c1a2
$C17F | b15 file $01E18F | BPL $c188
$C181 | b15 file $01E191 | JSR $e87a
$C184 | b15 file $01E194 | AND #$80
$C186 | b15 file $01E196 | BNE $c1a2
$C188 | b15 file $01E198 | LDA #$00
$C18A | b15 file $01E19A | STA $0000
$C18D | b15 file $01E19D | LDA #$ff
$C18F | b15 file $01E19F | STA $0001
$C192 | b15 file $01E1A2 | JSR $c1cd
$C195 | b15 file $01E1A5 | BCC $c1bc
$C197 | b15 file $01E1A7 | JSR $caf9
$C19A | b15 file $01E1AA | BNE $c1bc
$C19C | b15 file $01E1AC | LDA #$00
$C19E | b15 file $01E1AE | STA $0549
$C1A1 | b15 file $01E1B1 | RTS
$C1A2 | b15 file $01E1B2 | LDA #$00
$C1A4 | b15 file $01E1B4 | STA $0000
$C1A7 | b15 file $01E1B7 | LDA #$01
$C1A9 | b15 file $01E1B9 | STA $0001
$C1AC | b15 file $01E1BC | JSR $c1cd
$C1AF | b15 file $01E1BF | BCC $c1bc
$C1B1 | b15 file $01E1C1 | JSR $caf9
$C1B4 | b15 file $01E1C4 | BNE $c1bc
$C1B6 | b15 file $01E1C6 | LDA #$01
$C1B8 | b15 file $01E1C8 | STA $0549
$C1BB | b15 file $01E1CB | RTS
$C1BC | b15 file $01E1CC | LDA $0012
$C1BF | b15 file $01E1CF | BNE $c1c7
$C1C1 | b15 file $01E1D1 | INC $0012
$C1C4 | b15 file $01E1D4 | JMP $c123
$C1C7 | b15 file $01E1D7 | LDA #$ff
$C1C9 | b15 file $01E1D9 | STA $0549
$C1CC | b15 file $01E1DC | RTS
$C1CD | b15 file $01E1DD | LDY $0545
$C1D0 | b15 file $01E1E0 | LDA $0580,Y
$C1D3 | b15 file $01E1E3 | CLC
$C1D4 | b15 file $01E1E4 | ADC $0000
$C1D7 | b15 file $01E1E7 | STA $0000
$C1DA | b15 file $01E1EA | CMP #$10
$C1DC | b15 file $01E1EC | BCS $c206
$C1DE | b15 file $01E1EE | LDA $0596,Y
$C1E1 | b15 file $01E1F1 | CLC
$C1E2 | b15 file $01E1F2 | ADC $0001
$C1E5 | b15 file $01E1F5 | STA $0001
$C1E8 | b15 file $01E1F8 | CMP #$0a
$C1EA | b15 file $01E1FA | BCS $c206
$C1EC | b15 file $01E1FC | LDX #$15
$C1EE | b15 file $01E1FE | LDA $0580,X
$C1F1 | b15 file $01E201 | CMP $0000
$C1F4 | b15 file $01E204 | BNE $c20a
$C1F6 | b15 file $01E206 | LDA $0596,X
$C1F9 | b15 file $01E209 | CMP $0001
$C1FC | b15 file $01E20C | BNE $c20a
$C1FE | b15 file $01E20E | LDA $0545
$C201 | b15 file $01E211 | JSR $c827
$C204 | b15 file $01E214 | CLC
$C205 | b15 file $01E215 | RTS
$C206 | b15 file $01E216 | LDA #$00
$C208 | b15 file $01E218 | CLC
$C209 | b15 file $01E219 | RTS
$C20A | b15 file $01E21A | DEX
$C20B | b15 file $01E21B | BPL $c1ee
$C20D | b15 file $01E21D | SEC
$C20E | b15 file $01E21E | RTS
$C20F | b15 file $01E21F | LDA #$00
$C211 | b15 file $01E221 | STA $0010
$C214 | b15 file $01E224 | STA $0011
$C217 | b15 file $01E227 | JSR $e87a
$C21A | b15 file $01E22A | AND #$01
$C21C | b15 file $01E22C | BEQ $c221
$C21E | b15 file $01E22E | JMP $c298
$C221 | b15 file $01E231 | JSR $e87a
$C224 | b15 file $01E234 | AND #$80
$C226 | b15 file $01E236 | BNE $c260
$C228 | b15 file $01E238 | LDA #$ff
$C22A | b15 file $01E23A | STA $0000
$C22D | b15 file $01E23D | LDA #$00
$C22F | b15 file $01E23F | STA $0001
$C232 | b15 file $01E242 | JSR $c1cd
$C235 | b15 file $01E245 | BCS $c243
$C237 | b15 file $01E247 | TAY
$C238 | b15 file $01E248 | BEQ $c243
$C23A | b15 file $01E24A | STX $054a
$C23D | b15 file $01E24D | LDA #$02
$C23F | b15 file $01E24F | STA $0549
$C242 | b15 file $01E252 | RTS
$C243 | b15 file $01E253 | LDA $0010
$C246 | b15 file $01E256 | CMP #$03
$C248 | b15 file $01E258 | BNE $c250
$C24A | b15 file $01E25A | LDA #$ff
$C24C | b15 file $01E25C | STA $0549
$C24F | b15 file $01E25F | RTS
$C250 | b15 file $01E260 | CMP #$01
$C252 | b15 file $01E262 | BNE $c25a
$C254 | b15 file $01E264 | INC $0010
$C257 | b15 file $01E267 | JMP $c298
$C25A | b15 file $01E26A | INC $0010
$C25D | b15 file $01E26D | JMP $c260
$C260 | b15 file $01E270 | LDA #$01
$C262 | b15 file $01E272 | STA $0000
$C265 | b15 file $01E275 | LDA #$00
$C267 | b15 file $01E277 | STA $0001
$C26A | b15 file $01E27A | JSR $c1cd
$C26D | b15 file $01E27D | BCS $c27b
$C26F | b15 file $01E27F | TAY
$C270 | b15 file $01E280 | BEQ $c27b
$C272 | b15 file $01E282 | STX $054a
$C275 | b15 file $01E285 | LDA #$03
$C277 | b15 file $01E287 | STA $0549
$C27A | b15 file $01E28A | RTS
$C27B | b15 file $01E28B | LDA $0010
$C27E | b15 file $01E28E | CMP #$03
$C280 | b15 file $01E290 | BNE $c288
$C282 | b15 file $01E292 | LDA #$ff
$C284 | b15 file $01E294 | STA $0549
$C287 | b15 file $01E297 | RTS
$C288 | b15 file $01E298 | CMP #$01
$C28A | b15 file $01E29A | BNE $c292
$C28C | b15 file $01E29C | INC $0010
$C28F | b15 file $01E29F | JMP $c298
$C292 | b15 file $01E2A2 | INC $0010
$C295 | b15 file $01E2A5 | JMP $c228
$C298 | b15 file $01E2A8 | JSR $e87a
$C29B | b15 file $01E2AB | AND #$80
$C29D | b15 file $01E2AD | BNE $c2d7
$C29F | b15 file $01E2AF | LDA #$00
$C2A1 | b15 file $01E2B1 | STA $0000
$C2A4 | b15 file $01E2B4 | LDA #$ff
$C2A6 | b15 file $01E2B6 | STA $0001
$C2A9 | b15 file $01E2B9 | JSR $c1cd
$C2AC | b15 file $01E2BC | BCS $c2ba
$C2AE | b15 file $01E2BE | TAY
$C2AF | b15 file $01E2BF | BEQ $c2ba
$C2B1 | b15 file $01E2C1 | STX $054a
$C2B4 | b15 file $01E2C4 | LDA #$00
$C2B6 | b15 file $01E2C6 | STA $0549
$C2B9 | b15 file $01E2C9 | RTS
$C2BA | b15 file $01E2CA | LDA $0010
$C2BD | b15 file $01E2CD | CMP #$03
$C2BF | b15 file $01E2CF | BNE $c2c7
$C2C1 | b15 file $01E2D1 | LDA #$ff
$C2C3 | b15 file $01E2D3 | STA $0549
$C2C6 | b15 file $01E2D6 | RTS
$C2C7 | b15 file $01E2D7 | CMP #$01
$C2C9 | b15 file $01E2D9 | BNE $c2d1
$C2CB | b15 file $01E2DB | INC $0010
$C2CE | b15 file $01E2DE | JMP $c221
$C2D1 | b15 file $01E2E1 | INC $0010
$C2D4 | b15 file $01E2E4 | JMP $c2d7
$C2D7 | b15 file $01E2E7 | LDA #$00
$C2D9 | b15 file $01E2E9 | STA $0000
$C2DC | b15 file $01E2EC | LDA #$01
$C2DE | b15 file $01E2EE | STA $0001
$C2E1 | b15 file $01E2F1 | JSR $c1cd
$C2E4 | b15 file $01E2F4 | BCS $c2f2
$C2E6 | b15 file $01E2F6 | TAY
$C2E7 | b15 file $01E2F7 | BEQ $c2f2
$C2E9 | b15 file $01E2F9 | STX $054a
$C2EC | b15 file $01E2FC | LDA #$01
$C2EE | b15 file $01E2FE | STA $0549
$C2F1 | b15 file $01E301 | RTS
$C2F2 | b15 file $01E302 | LDA $0010
$C2F5 | b15 file $01E305 | CMP #$03
$C2F7 | b15 file $01E307 | BNE $c2ff
$C2F9 | b15 file $01E309 | LDA #$ff
$C2FB | b15 file $01E30B | STA $0549
$C2FE | b15 file $01E30E | RTS
$C2FF | b15 file $01E30F | CMP #$01
$C301 | b15 file $01E311 | BNE $c309
$C303 | b15 file $01E313 | INC $0010
$C306 | b15 file $01E316 | JMP $c221
$C309 | b15 file $01E319 | INC $0010
$C30C | b15 file $01E31C | JMP $c29f
$C30F | b15 file $01E31F | LDA #$00
$C311 | b15 file $01E321 | STA $0010
$C314 | b15 file $01E324 | STA $0011
$C317 | b15 file $01E327 | JSR $e87a
$C31A | b15 file $01E32A | AND #$01
$C31C | b15 file $01E32C | BEQ $c321
$C31E | b15 file $01E32E | JMP $c5a4
$C321 | b15 file $01E331 | JSR $e87a
$C324 | b15 file $01E334 | AND #$80
$C326 | b15 file $01E336 | BNE $c32b
$C328 | b15 file $01E338 | JMP $c469
$C32B | b15 file $01E33B | LDA #$ff
$C32D | b15 file $01E33D | STA $0000
$C330 | b15 file $01E340 | LDA #$00
$C332 | b15 file $01E342 | STA $0001
$C335 | b15 file $01E345 | JSR $cac8
$C338 | b15 file $01E348 | TAY
$C339 | b15 file $01E349 | BEQ $c33e
$C33B | b15 file $01E34B | JMP $c44c
$C33E | b15 file $01E34E | LDA #$ff
$C340 | b15 file $01E350 | STA $0000
$C343 | b15 file $01E353 | LDA #$00
$C345 | b15 file $01E355 | STA $0001
$C348 | b15 file $01E358 | JSR $c1cd
$C34B | b15 file $01E35B | BCS $c353
$C34D | b15 file $01E35D | TAY
$C34E | b15 file $01E35E | BEQ $c353
$C350 | b15 file $01E360 | JMP $c44c
$C353 | b15 file $01E363 | LDA #$fe
$C355 | b15 file $01E365 | STA $0000
$C358 | b15 file $01E368 | LDA #$00
$C35A | b15 file $01E36A | STA $0001
$C35D | b15 file $01E36D | JSR $cac8
$C360 | b15 file $01E370 | TAY
$C361 | b15 file $01E371 | BEQ $c366
$C363 | b15 file $01E373 | JMP $c44c
$C366 | b15 file $01E376 | LDA #$fe
$C368 | b15 file $01E378 | STA $0000
$C36B | b15 file $01E37B | LDA #$00
$C36D | b15 file $01E37D | STA $0001
$C370 | b15 file $01E380 | JSR $c1cd
$C373 | b15 file $01E383 | BCS $c37d
$C375 | b15 file $01E385 | TAY
$C376 | b15 file $01E386 | BEQ $c37d
$C378 | b15 file $01E388 | LDA #$1c
$C37A | b15 file $01E38A | JMP $c440
$C37D | b15 file $01E38D | LDA #$fd
$C37F | b15 file $01E38F | STA $0000
$C382 | b15 file $01E392 | LDA #$00
$C384 | b15 file $01E394 | STA $0001
$C387 | b15 file $01E397 | JSR $cac8
$C38A | b15 file $01E39A | TAY
$C38B | b15 file $01E39B | BEQ $c390
$C38D | b15 file $01E39D | JMP $c44c
$C390 | b15 file $01E3A0 | LDA #$fd
$C392 | b15 file $01E3A2 | STA $0000
$C395 | b15 file $01E3A5 | LDA #$00
$C397 | b15 file $01E3A7 | STA $0001
$C39A | b15 file $01E3AA | JSR $c1cd
$C39D | b15 file $01E3AD | BCS $c3a7
$C39F | b15 file $01E3AF | TAY
$C3A0 | b15 file $01E3B0 | BEQ $c3a7
$C3A2 | b15 file $01E3B2 | LDA #$2c
$C3A4 | b15 file $01E3B4 | JMP $c440
$C3A7 | b15 file $01E3B7 | LDA #$fc
$C3A9 | b15 file $01E3B9 | STA $0000
$C3AC | b15 file $01E3BC | LDA #$00
$C3AE | b15 file $01E3BE | STA $0001
$C3B1 | b15 file $01E3C1 | JSR $cac8
$C3B4 | b15 file $01E3C4 | TAY
$C3B5 | b15 file $01E3C5 | BEQ $c3ba
$C3B7 | b15 file $01E3C7 | JMP $c44c
$C3BA | b15 file $01E3CA | LDA #$fc
$C3BC | b15 file $01E3CC | STA $0000
$C3BF | b15 file $01E3CF | LDA #$00
$C3C1 | b15 file $01E3D1 | STA $0001
$C3C4 | b15 file $01E3D4 | JSR $c1cd
$C3C7 | b15 file $01E3D7 | BCS $c3d1
$C3C9 | b15 file $01E3D9 | TAY
$C3CA | b15 file $01E3DA | BEQ $c3d1
$C3CC | b15 file $01E3DC | LDA #$3c
$C3CE | b15 file $01E3DE | JMP $c440
$C3D1 | b15 file $01E3E1 | LDA $0545
$C3D4 | b15 file $01E3E4 | CMP #$0b
$C3D6 | b15 file $01E3E6 | BCC $c3e2
$C3D8 | b15 file $01E3E8 | LDA $0575
$C3DB | b15 file $01E3EB | AND #$f0
$C3DD | b15 file $01E3ED | BNE $c3ec
$C3DF | b15 file $01E3EF | JMP $c44c
$C3E2 | b15 file $01E3F2 | LDA $0575
$C3E5 | b15 file $01E3F5 | AND #$0f
$C3E7 | b15 file $01E3F7 | BNE $c3ec
$C3E9 | b15 file $01E3F9 | JMP $c44c
$C3EC | b15 file $01E3FC | LDA #$fb
$C3EE | b15 file $01E3FE | STA $0000
$C3F1 | b15 file $01E401 | LDA #$00
$C3F3 | b15 file $01E403 | STA $0001
$C3F6 | b15 file $01E406 | JSR $cac8
$C3F9 | b15 file $01E409 | TAY
$C3FA | b15 file $01E40A | BEQ $c3ff
$C3FC | b15 file $01E40C | JMP $c44c
$C3FF | b15 file $01E40F | LDA #$fb
$C401 | b15 file $01E411 | STA $0000
$C404 | b15 file $01E414 | LDA #$00
$C406 | b15 file $01E416 | STA $0001
$C409 | b15 file $01E419 | JSR $c1cd
$C40C | b15 file $01E41C | BCS $c416
$C40E | b15 file $01E41E | TAY
$C40F | b15 file $01E41F | BEQ $c416
$C411 | b15 file $01E421 | LDA #$4c
$C413 | b15 file $01E423 | JMP $c440
$C416 | b15 file $01E426 | LDA #$fa
$C418 | b15 file $01E428 | STA $0000
$C41B | b15 file $01E42B | LDA #$00
$C41D | b15 file $01E42D | STA $0001
$C420 | b15 file $01E430 | JSR $cac8
$C423 | b15 file $01E433 | TAY
$C424 | b15 file $01E434 | BEQ $c429
$C426 | b15 file $01E436 | JMP $c44c
$C429 | b15 file $01E439 | LDA #$fa
$C42B | b15 file $01E43B | STA $0000
$C42E | b15 file $01E43E | LDA #$00
$C430 | b15 file $01E440 | STA $0001
$C433 | b15 file $01E443 | JSR $c1cd
$C436 | b15 file $01E446 | BCS $c44c
$C438 | b15 file $01E448 | TAY
$C439 | b15 file $01E449 | BEQ $c44c
$C43B | b15 file $01E44B | LDA #$5c
$C43D | b15 file $01E44D | JMP $c440
$C440 | b15 file $01E450 | STX $054d
$C443 | b15 file $01E453 | STA $0548
$C446 | b15 file $01E456 | LDA #$02
$C448 | b15 file $01E458 | STA $0549
$C44B | b15 file $01E45B | RTS
$C44C | b15 file $01E45C | LDA $0010
$C44F | b15 file $01E45F | CMP #$03
$C451 | b15 file $01E461 | BNE $c459
$C453 | b15 file $01E463 | LDA #$ff
$C455 | b15 file $01E465 | STA $0549
$C458 | b15 file $01E468 | RTS
$C459 | b15 file $01E469 | CMP #$01
$C45B | b15 file $01E46B | BNE $c463
$C45D | b15 file $01E46D | INC $0010
$C460 | b15 file $01E470 | JMP $c5a4
$C463 | b15 file $01E473 | INC $0010
$C466 | b15 file $01E476 | JMP $c44c
$C469 | b15 file $01E479 | LDA #$01
$C46B | b15 file $01E47B | STA $0000
$C46E | b15 file $01E47E | LDA #$00
$C470 | b15 file $01E480 | STA $0001
$C473 | b15 file $01E483 | JSR $cac8
$C476 | b15 file $01E486 | TAY
$C477 | b15 file $01E487 | BEQ $c47c
$C479 | b15 file $01E489 | JMP $c587
$C47C | b15 file $01E48C | LDA #$01
$C47E | b15 file $01E48E | STA $0000
$C481 | b15 file $01E491 | LDA #$00
$C483 | b15 file $01E493 | STA $0001
$C486 | b15 file $01E496 | JSR $c1cd
$C489 | b15 file $01E499 | BCS $c491
$C48B | b15 file $01E49B | TAY
$C48C | b15 file $01E49C | BEQ $c491
$C48E | b15 file $01E49E | JMP $c587
$C491 | b15 file $01E4A1 | LDA #$02
$C493 | b15 file $01E4A3 | STA $0000
$C496 | b15 file $01E4A6 | LDA #$00
$C498 | b15 file $01E4A8 | STA $0001
$C49B | b15 file $01E4AB | JSR $cac8
$C49E | b15 file $01E4AE | TAY
$C49F | b15 file $01E4AF | BEQ $c4a4
$C4A1 | b15 file $01E4B1 | JMP $c587
$C4A4 | b15 file $01E4B4 | LDA #$02
$C4A6 | b15 file $01E4B6 | STA $0000
$C4A9 | b15 file $01E4B9 | LDA #$00
$C4AB | b15 file $01E4BB | STA $0001
$C4AE | b15 file $01E4BE | JSR $c1cd
$C4B1 | b15 file $01E4C1 | BCS $c4bb
$C4B3 | b15 file $01E4C3 | TAY
$C4B4 | b15 file $01E4C4 | BEQ $c4bb
$C4B6 | b15 file $01E4C6 | LDA #$1c
$C4B8 | b15 file $01E4C8 | JMP $c57b
$C4BB | b15 file $01E4CB | LDA #$03
$C4BD | b15 file $01E4CD | STA $0000
$C4C0 | b15 file $01E4D0 | LDA #$00
$C4C2 | b15 file $01E4D2 | STA $0001
$C4C5 | b15 file $01E4D5 | JSR $cac8
$C4C8 | b15 file $01E4D8 | TAY
$C4C9 | b15 file $01E4D9 | BEQ $c4ce
$C4CB | b15 file $01E4DB | JMP $c587
$C4CE | b15 file $01E4DE | LDA #$03
$C4D0 | b15 file $01E4E0 | STA $0000
$C4D3 | b15 file $01E4E3 | LDA #$00
$C4D5 | b15 file $01E4E5 | STA $0001
$C4D8 | b15 file $01E4E8 | JSR $c1cd
$C4DB | b15 file $01E4EB | BCS $c4e5
$C4DD | b15 file $01E4ED | TAY
$C4DE | b15 file $01E4EE | BEQ $c4e5
$C4E0 | b15 file $01E4F0 | LDA #$2c
$C4E2 | b15 file $01E4F2 | JMP $c57b
$C4E5 | b15 file $01E4F5 | LDA #$04
$C4E7 | b15 file $01E4F7 | STA $0000
$C4EA | b15 file $01E4FA | LDA #$00
$C4EC | b15 file $01E4FC | STA $0001
$C4EF | b15 file $01E4FF | JSR $cac8
$C4F2 | b15 file $01E502 | TAY
$C4F3 | b15 file $01E503 | BEQ $c4f8
$C4F5 | b15 file $01E505 | JMP $c587
$C4F8 | b15 file $01E508 | LDA #$04
$C4FA | b15 file $01E50A | STA $0000
$C4FD | b15 file $01E50D | LDA #$00
$C4FF | b15 file $01E50F | STA $0001
$C502 | b15 file $01E512 | JSR $c1cd
$C505 | b15 file $01E515 | BCS $c50f
$C507 | b15 file $01E517 | TAY
$C508 | b15 file $01E518 | BEQ $c50f
$C50A | b15 file $01E51A | LDA #$3c
$C50C | b15 file $01E51C | JMP $c57b
$C50F | b15 file $01E51F | LDA $0545
$C512 | b15 file $01E522 | CMP #$0b
$C514 | b15 file $01E524 | BCC $c520
$C516 | b15 file $01E526 | LDA $0575
$C519 | b15 file $01E529 | AND #$f0
$C51B | b15 file $01E52B | BNE $c52a
$C51D | b15 file $01E52D | JMP $c587
$C520 | b15 file $01E530 | LDA $0575
$C523 | b15 file $01E533 | AND #$0f
$C525 | b15 file $01E535 | BNE $c52a
$C527 | b15 file $01E537 | JMP $c587
$C52A | b15 file $01E53A | LDA #$05
$C52C | b15 file $01E53C | STA $0000
$C52F | b15 file $01E53F | LDA #$00
$C531 | b15 file $01E541 | STA $0001
$C534 | b15 file $01E544 | JSR $cac8
$C537 | b15 file $01E547 | TAY
$C538 | b15 file $01E548 | BEQ $c53d
$C53A | b15 file $01E54A | JMP $c587
$C53D | b15 file $01E54D | LDA #$05
$C53F | b15 file $01E54F | STA $0000
$C542 | b15 file $01E552 | LDA #$00
$C544 | b15 file $01E554 | STA $0001
$C547 | b15 file $01E557 | JSR $c1cd
$C54A | b15 file $01E55A | BCS $c554
$C54C | b15 file $01E55C | TAY
$C54D | b15 file $01E55D | BEQ $c554
$C54F | b15 file $01E55F | LDA #$4c
$C551 | b15 file $01E561 | JMP $c57b
$C554 | b15 file $01E564 | LDA #$06
$C556 | b15 file $01E566 | STA $0000
$C559 | b15 file $01E569 | LDA #$00
$C55B | b15 file $01E56B | STA $0001
$C55E | b15 file $01E56E | JSR $cac8
$C561 | b15 file $01E571 | TAY
$C562 | b15 file $01E572 | BEQ $c567
$C564 | b15 file $01E574 | JMP $c587
$C567 | b15 file $01E577 | LDA #$06
$C569 | b15 file $01E579 | STA $0000
$C56C | b15 file $01E57C | LDA #$00
$C56E | b15 file $01E57E | STA $0001
$C571 | b15 file $01E581 | JSR $c1cd
$C574 | b15 file $01E584 | BCS $c587
$C576 | b15 file $01E586 | TAY
$C577 | b15 file $01E587 | BEQ $c587
$C579 | b15 file $01E589 | LDA #$5c
$C57B | b15 file $01E58B | STX $054d
$C57E | b15 file $01E58E | STA $0548
$C581 | b15 file $01E591 | LDA #$03
$C583 | b15 file $01E593 | STA $0549
$C586 | b15 file $01E596 | RTS
$C587 | b15 file $01E597 | LDA $0010
$C58A | b15 file $01E59A | CMP #$03
$C58C | b15 file $01E59C | BNE $c594
$C58E | b15 file $01E59E | LDA #$ff
$C590 | b15 file $01E5A0 | STA $0549
$C593 | b15 file $01E5A3 | RTS
$C594 | b15 file $01E5A4 | CMP #$01
$C596 | b15 file $01E5A6 | BNE $c59e
$C598 | b15 file $01E5A8 | INC $0010
$C59B | b15 file $01E5AB | JMP $c5a4
$C59E | b15 file $01E5AE | INC $0010
$C5A1 | b15 file $01E5B1 | JMP $c32b
$C5A4 | b15 file $01E5B4 | JSR $e87a
$C5A7 | b15 file $01E5B7 | AND #$80
$C5A9 | b15 file $01E5B9 | BNE $c5ae
$C5AB | b15 file $01E5BB | JMP $c6ec
$C5AE | b15 file $01E5BE | LDA #$00
$C5B0 | b15 file $01E5C0 | STA $0000
$C5B3 | b15 file $01E5C3 | LDA #$ff
$C5B5 | b15 file $01E5C5 | STA $0001
$C5B8 | b15 file $01E5C8 | JSR $cac8
$C5BB | b15 file $01E5CB | TAY
$C5BC | b15 file $01E5CC | BEQ $c5c1
$C5BE | b15 file $01E5CE | JMP $c6cf
$C5C1 | b15 file $01E5D1 | LDA #$00
$C5C3 | b15 file $01E5D3 | STA $0000
$C5C6 | b15 file $01E5D6 | LDA #$ff
$C5C8 | b15 file $01E5D8 | STA $0001
$C5CB | b15 file $01E5DB | JSR $c1cd
$C5CE | b15 file $01E5DE | BCS $c5d6
$C5D0 | b15 file $01E5E0 | TAY
$C5D1 | b15 file $01E5E1 | BEQ $c5d6
$C5D3 | b15 file $01E5E3 | JMP $c6cf
$C5D6 | b15 file $01E5E6 | LDA #$00
$C5D8 | b15 file $01E5E8 | STA $0000
$C5DB | b15 file $01E5EB | LDA #$fe
$C5DD | b15 file $01E5ED | STA $0001
$C5E0 | b15 file $01E5F0 | JSR $cac8
$C5E3 | b15 file $01E5F3 | TAY
$C5E4 | b15 file $01E5F4 | BEQ $c5e9
$C5E6 | b15 file $01E5F6 | JMP $c6cf
$C5E9 | b15 file $01E5F9 | LDA #$00
$C5EB | b15 file $01E5FB | STA $0000
$C5EE | b15 file $01E5FE | LDA #$fe
$C5F0 | b15 file $01E600 | STA $0001
$C5F3 | b15 file $01E603 | JSR $c1cd
$C5F6 | b15 file $01E606 | BCS $c600
$C5F8 | b15 file $01E608 | TAY
$C5F9 | b15 file $01E609 | BEQ $c600
$C5FB | b15 file $01E60B | LDA #$1c
$C5FD | b15 file $01E60D | JMP $c6c3
$C600 | b15 file $01E610 | LDA #$00
$C602 | b15 file $01E612 | STA $0000
$C605 | b15 file $01E615 | LDA #$fd
$C607 | b15 file $01E617 | STA $0001
$C60A | b15 file $01E61A | JSR $cac8
$C60D | b15 file $01E61D | TAY
$C60E | b15 file $01E61E | BEQ $c613
$C610 | b15 file $01E620 | JMP $c6cf
$C613 | b15 file $01E623 | LDA #$00
$C615 | b15 file $01E625 | STA $0000
$C618 | b15 file $01E628 | LDA #$fd
$C61A | b15 file $01E62A | STA $0001
$C61D | b15 file $01E62D | JSR $c1cd
$C620 | b15 file $01E630 | BCS $c62a
$C622 | b15 file $01E632 | TAY
$C623 | b15 file $01E633 | BEQ $c62a
$C625 | b15 file $01E635 | LDA #$2c
$C627 | b15 file $01E637 | JMP $c6c3
$C62A | b15 file $01E63A | LDA #$00
$C62C | b15 file $01E63C | STA $0000
$C62F | b15 file $01E63F | LDA #$fc
$C631 | b15 file $01E641 | STA $0001
$C634 | b15 file $01E644 | JSR $cac8
$C637 | b15 file $01E647 | TAY
$C638 | b15 file $01E648 | BEQ $c63d
$C63A | b15 file $01E64A | JMP $c6cf
$C63D | b15 file $01E64D | LDA #$00
$C63F | b15 file $01E64F | STA $0000
$C642 | b15 file $01E652 | LDA #$fc
$C644 | b15 file $01E654 | STA $0001
$C647 | b15 file $01E657 | JSR $c1cd
$C64A | b15 file $01E65A | BCS $c654
$C64C | b15 file $01E65C | TAY
$C64D | b15 file $01E65D | BEQ $c654
$C64F | b15 file $01E65F | LDA #$3c
$C651 | b15 file $01E661 | JMP $c6c3
$C654 | b15 file $01E664 | LDA $0545
$C657 | b15 file $01E667 | CMP #$0b
$C659 | b15 file $01E669 | BCC $c665
$C65B | b15 file $01E66B | LDA $0575
$C65E | b15 file $01E66E | AND #$f0
$C660 | b15 file $01E670 | BNE $c66f
$C662 | b15 file $01E672 | JMP $c6cf
$C665 | b15 file $01E675 | LDA $0575
$C668 | b15 file $01E678 | AND #$0f
$C66A | b15 file $01E67A | BNE $c66f
$C66C | b15 file $01E67C | JMP $c6cf
$C66F | b15 file $01E67F | LDA #$00
$C671 | b15 file $01E681 | STA $0000
$C674 | b15 file $01E684 | LDA #$fb
$C676 | b15 file $01E686 | STA $0001
$C679 | b15 file $01E689 | JSR $cac8
$C67C | b15 file $01E68C | TAY
$C67D | b15 file $01E68D | BEQ $c682
$C67F | b15 file $01E68F | JMP $c6cf
$C682 | b15 file $01E692 | LDA #$00
$C684 | b15 file $01E694 | STA $0000
$C687 | b15 file $01E697 | LDA #$fb
$C689 | b15 file $01E699 | STA $0001
$C68C | b15 file $01E69C | JSR $c1cd
$C68F | b15 file $01E69F | BCS $c699
$C691 | b15 file $01E6A1 | TAY
$C692 | b15 file $01E6A2 | BEQ $c699
$C694 | b15 file $01E6A4 | LDA #$4c
$C696 | b15 file $01E6A6 | JMP $c6c3
$C699 | b15 file $01E6A9 | LDA #$00
$C69B | b15 file $01E6AB | STA $0000
$C69E | b15 file $01E6AE | LDA #$fa
$C6A0 | b15 file $01E6B0 | STA $0001
$C6A3 | b15 file $01E6B3 | JSR $cac8
$C6A6 | b15 file $01E6B6 | TAY
$C6A7 | b15 file $01E6B7 | BEQ $c6ac
$C6A9 | b15 file $01E6B9 | JMP $c6cf
$C6AC | b15 file $01E6BC | LDA #$00
$C6AE | b15 file $01E6BE | STA $0000
$C6B1 | b15 file $01E6C1 | LDA #$fa
$C6B3 | b15 file $01E6C3 | STA $0001
$C6B6 | b15 file $01E6C6 | JSR $c1cd
$C6B9 | b15 file $01E6C9 | BCS $c6cf
$C6BB | b15 file $01E6CB | TAY
$C6BC | b15 file $01E6CC | BEQ $c6cf
$C6BE | b15 file $01E6CE | LDA #$5c
$C6C0 | b15 file $01E6D0 | JMP $c6c3
$C6C3 | b15 file $01E6D3 | STX $054d
$C6C6 | b15 file $01E6D6 | STA $0548
$C6C9 | b15 file $01E6D9 | LDA #$00
$C6CB | b15 file $01E6DB | STA $0549
$C6CE | b15 file $01E6DE | RTS
$C6CF | b15 file $01E6DF | LDA $0010
$C6D2 | b15 file $01E6E2 | CMP #$03
$C6D4 | b15 file $01E6E4 | BNE $c6dc
$C6D6 | b15 file $01E6E6 | LDA #$ff
$C6D8 | b15 file $01E6E8 | STA $0549
$C6DB | b15 file $01E6EB | RTS
$C6DC | b15 file $01E6EC | CMP #$01
$C6DE | b15 file $01E6EE | BNE $c6e6
$C6E0 | b15 file $01E6F0 | INC $0010
$C6E3 | b15 file $01E6F3 | JMP $c321
$C6E6 | b15 file $01E6F6 | INC $0010
$C6E9 | b15 file $01E6F9 | JMP $c6ec
$C6EC | b15 file $01E6FC | LDA #$00
$C6EE | b15 file $01E6FE | STA $0000
$C6F1 | b15 file $01E701 | LDA #$01
$C6F3 | b15 file $01E703 | STA $0001
$C6F6 | b15 file $01E706 | JSR $cac8
$C6F9 | b15 file $01E709 | TAY
$C6FA | b15 file $01E70A | BEQ $c6ff
$C6FC | b15 file $01E70C | JMP $c80a
$C6FF | b15 file $01E70F | LDA #$00
$C701 | b15 file $01E711 | STA $0000
$C704 | b15 file $01E714 | LDA #$01
$C706 | b15 file $01E716 | STA $0001
$C709 | b15 file $01E719 | JSR $c1cd
$C70C | b15 file $01E71C | BCS $c714
$C70E | b15 file $01E71E | TAY
$C70F | b15 file $01E71F | BEQ $c714
$C711 | b15 file $01E721 | JMP $c80a
$C714 | b15 file $01E724 | LDA #$00
$C716 | b15 file $01E726 | STA $0000
$C719 | b15 file $01E729 | LDA #$02
$C71B | b15 file $01E72B | STA $0001
$C71E | b15 file $01E72E | JSR $cac8
$C721 | b15 file $01E731 | TAY
$C722 | b15 file $01E732 | BEQ $c727
$C724 | b15 file $01E734 | JMP $c80a
$C727 | b15 file $01E737 | LDA #$00
$C729 | b15 file $01E739 | STA $0000
$C72C | b15 file $01E73C | LDA #$02
$C72E | b15 file $01E73E | STA $0001
$C731 | b15 file $01E741 | JSR $c1cd
$C734 | b15 file $01E744 | BCS $c73e
$C736 | b15 file $01E746 | TAY
$C737 | b15 file $01E747 | BEQ $c73e
$C739 | b15 file $01E749 | LDA #$1c
$C73B | b15 file $01E74B | JMP $c7fe
$C73E | b15 file $01E74E | LDA #$00
$C740 | b15 file $01E750 | STA $0000
$C743 | b15 file $01E753 | LDA #$03
$C745 | b15 file $01E755 | STA $0001
$C748 | b15 file $01E758 | JSR $cac8
$C74B | b15 file $01E75B | TAY
$C74C | b15 file $01E75C | BEQ $c751
$C74E | b15 file $01E75E | JMP $c80a
$C751 | b15 file $01E761 | LDA #$00
$C753 | b15 file $01E763 | STA $0000
$C756 | b15 file $01E766 | LDA #$03
$C758 | b15 file $01E768 | STA $0001
$C75B | b15 file $01E76B | JSR $c1cd
$C75E | b15 file $01E76E | BCS $c768
$C760 | b15 file $01E770 | TAY
$C761 | b15 file $01E771 | BEQ $c768
$C763 | b15 file $01E773 | LDA #$2c
$C765 | b15 file $01E775 | JMP $c7fe
$C768 | b15 file $01E778 | LDA #$00
$C76A | b15 file $01E77A | STA $0000
$C76D | b15 file $01E77D | LDA #$04
$C76F | b15 file $01E77F | STA $0001
$C772 | b15 file $01E782 | JSR $cac8
$C775 | b15 file $01E785 | TAY
$C776 | b15 file $01E786 | BEQ $c77b
$C778 | b15 file $01E788 | JMP $c80a
$C77B | b15 file $01E78B | LDA #$00
$C77D | b15 file $01E78D | STA $0000
$C780 | b15 file $01E790 | LDA #$04
$C782 | b15 file $01E792 | STA $0001
$C785 | b15 file $01E795 | JSR $c1cd
$C788 | b15 file $01E798 | BCS $c792
$C78A | b15 file $01E79A | TAY
$C78B | b15 file $01E79B | BEQ $c792
$C78D | b15 file $01E79D | LDA #$3c
$C78F | b15 file $01E79F | JMP $c7fe
$C792 | b15 file $01E7A2 | LDA $0545
$C795 | b15 file $01E7A5 | CMP #$0b
$C797 | b15 file $01E7A7 | BCC $c7a3
$C799 | b15 file $01E7A9 | LDA $0575
$C79C | b15 file $01E7AC | AND #$f0
$C79E | b15 file $01E7AE | BNE $c7ad
$C7A0 | b15 file $01E7B0 | JMP $c80a
$C7A3 | b15 file $01E7B3 | LDA $0575
$C7A6 | b15 file $01E7B6 | AND #$0f
$C7A8 | b15 file $01E7B8 | BNE $c7ad
$C7AA | b15 file $01E7BA | JMP $c80a
$C7AD | b15 file $01E7BD | LDA #$00
$C7AF | b15 file $01E7BF | STA $0000
$C7B2 | b15 file $01E7C2 | LDA #$05
$C7B4 | b15 file $01E7C4 | STA $0001
$C7B7 | b15 file $01E7C7 | JSR $cac8
$C7BA | b15 file $01E7CA | TAY
$C7BB | b15 file $01E7CB | BEQ $c7c0
$C7BD | b15 file $01E7CD | JMP $c80a
$C7C0 | b15 file $01E7D0 | LDA #$00
$C7C2 | b15 file $01E7D2 | STA $0000
$C7C5 | b15 file $01E7D5 | LDA #$05
$C7C7 | b15 file $01E7D7 | STA $0001
$C7CA | b15 file $01E7DA | JSR $c1cd
$C7CD | b15 file $01E7DD | BCS $c7d7
$C7CF | b15 file $01E7DF | TAY
$C7D0 | b15 file $01E7E0 | BEQ $c7d7
$C7D2 | b15 file $01E7E2 | LDA #$4c
$C7D4 | b15 file $01E7E4 | JMP $c7fe
$C7D7 | b15 file $01E7E7 | LDA #$00
$C7D9 | b15 file $01E7E9 | STA $0000
$C7DC | b15 file $01E7EC | LDA #$06
$C7DE | b15 file $01E7EE | STA $0001
$C7E1 | b15 file $01E7F1 | JSR $cac8
$C7E4 | b15 file $01E7F4 | TAY
$C7E5 | b15 file $01E7F5 | BEQ $c7ea
$C7E7 | b15 file $01E7F7 | JMP $c80a
$C7EA | b15 file $01E7FA | LDA #$00
$C7EC | b15 file $01E7FC | STA $0000
$C7EF | b15 file $01E7FF | LDA #$06
$C7F1 | b15 file $01E801 | STA $0001
$C7F4 | b15 file $01E804 | JSR $c1cd
$C7F7 | b15 file $01E807 | BCS $c80a
$C7F9 | b15 file $01E809 | TAY
$C7FA | b15 file $01E80A | BEQ $c80a
$C7FC | b15 file $01E80C | LDA #$5c
$C7FE | b15 file $01E80E | STX $054d
$C801 | b15 file $01E811 | STA $0548
$C804 | b15 file $01E814 | LDA #$01
$C806 | b15 file $01E816 | STA $0549
$C809 | b15 file $01E819 | RTS
$C80A | b15 file $01E81A | LDA $0010
$C80D | b15 file $01E81D | CMP #$03
$C80F | b15 file $01E81F | BNE $c817
$C811 | b15 file $01E821 | LDA #$ff
$C813 | b15 file $01E823 | STA $0549
$C816 | b15 file $01E826 | RTS
$C817 | b15 file $01E827 | CMP #$01
$C819 | b15 file $01E829 | BNE $c821
$C81B | b15 file $01E82B | INC $0010
$C81E | b15 file $01E82E | JMP $c321
$C821 | b15 file $01E831 | INC $0010
$C824 | b15 file $01E834 | JMP $c5ae
$C827 | b15 file $01E837 | CPX #$0b
$C829 | b15 file $01E839 | BCS $c832
$C82B | b15 file $01E83B | CMP #$0b
$C82D | b15 file $01E83D | BCS $c836
$C82F | b15 file $01E83F | LDA #$00
$C831 | b15 file $01E841 | RTS
$C832 | b15 file $01E842 | CMP #$0b
$C834 | b15 file $01E844 | BCS $c82f
$C836 | b15 file $01E846 | LDA #$01
$C838 | b15 file $01E848 | RTS
$C839 | b15 file $01E849 | LDA $0000
$C83C | b15 file $01E84C | ASL A
$C83D | b15 file $01E84D | ASL A
$C83E | b15 file $01E84E | TAY
$C83F | b15 file $01E84F | LDA $c8bc,Y
$C842 | b15 file $01E852 | STA $0381
$C845 | b15 file $01E855 | LDA $c8bb,Y
$C848 | b15 file $01E858 | STA $0382
$C84B | b15 file $01E85B | LDA $c8be,Y
$C84E | b15 file $01E85E | STA $0389
$C851 | b15 file $01E861 | LDA $c8bd,Y
$C854 | b15 file $01E864 | STA $038a
$C857 | b15 file $01E867 | LDA $0001
$C85A | b15 file $01E86A | ASL A
$C85B | b15 file $01E86B | ASL A
$C85C | b15 file $01E86C | CLC
$C85D | b15 file $01E86D | ADC $0001
$C860 | b15 file $01E870 | ASL A
$C861 | b15 file $01E871 | TAY
$C862 | b15 file $01E872 | LDA $c8cb,Y
$C865 | b15 file $01E875 | STA $0383
$C868 | b15 file $01E878 | LDA $c8cc,Y
$C86B | b15 file $01E87B | STA $0384
$C86E | b15 file $01E87E | LDA $c8cd,Y
$C871 | b15 file $01E881 | STA $0385
$C874 | b15 file $01E884 | LDA $c8ce,Y
$C877 | b15 file $01E887 | STA $0386
$C87A | b15 file $01E88A | LDA $c8cf,Y
$C87D | b15 file $01E88D | STA $0387
$C880 | b15 file $01E890 | LDA $c8d0,Y
$C883 | b15 file $01E893 | STA $038b
$C886 | b15 file $01E896 | LDA $c8d1,Y
$C889 | b15 file $01E899 | STA $038c
$C88C | b15 file $01E89C | LDA $c8d2,Y
$C88F | b15 file $01E89F | STA $038d
$C892 | b15 file $01E8A2 | LDA $c8d3,Y
$C895 | b15 file $01E8A5 | STA $038e
$C898 | b15 file $01E8A8 | LDA $c8d4,Y
$C89B | b15 file $01E8AB | STA $038f
$C89E | b15 file $01E8AE | LDA #$05
$C8A0 | b15 file $01E8B0 | STA $0380
$C8A3 | b15 file $01E8B3 | LDA #$05
$C8A5 | b15 file $01E8B5 | STA $0388
$C8A8 | b15 file $01E8B8 | LDA #$ff
$C8AA | b15 file $01E8BA | STA $0390
$C8AD | b15 file $01E8BD | LDA $007e
$C8B0 | b15 file $01E8C0 | ORA #$04
$C8B2 | b15 file $01E8C2 | STA $007e
$C8B5 | b15 file $01E8C5 | LDA #$77
$C8B7 | b15 file $01E8C7 | STA $00bb
$C8BA | b15 file $01E8CA | RTS
$C8FD | b15 file $01E90D | LDA $005e
$C900 | b15 file $01E910 | AND #$10
$C902 | b15 file $01E912 | BNE $c920
$C904 | b15 file $01E914 | LDA #$d8
$C906 | b15 file $01E916 | STA $000a
$C909 | b15 file $01E919 | LDA #$a0
$C90B | b15 file $01E91B | STA $000c
$C90E | b15 file $01E91E | LDA #$21
$C910 | b15 file $01E920 | STA $0000
$C913 | b15 file $01E923 | LDA #$c9
$C915 | b15 file $01E925 | STA $0001
$C918 | b15 file $01E928 | LDA #$00
$C91A | b15 file $01E92A | STA $0002
$C91D | b15 file $01E92D | JMP $f1ad
$C920 | b15 file $01E930 | RTS
$C926 | b15 file $01E936 | LDA $0560
$C929 | b15 file $01E939 | JSR $f2d7
$C92C | b15 file $01E93C | JSR $c991
$C92F | b15 file $01E93F | STA $056a
$C932 | b15 file $01E942 | STA $04c1
$C935 | b15 file $01E945 | STY $0570
$C938 | b15 file $01E948 | STX $056e
$C93B | b15 file $01E94B | LDA $0560
$C93E | b15 file $01E94E | JSR $f2d7
$C941 | b15 file $01E951 | LDY #$02
$C943 | b15 file $01E953 | LDA ($00),Y
$C945 | b15 file $01E955 | STA $0000
$C948 | b15 file $01E958 | LDA #$00
$C94A | b15 file $01E95A | STA $0001
$C94D | b15 file $01E95D | LDA #$0d
$C94F | b15 file $01E95F | STA $0003
$C952 | b15 file $01E962 | JSR $ebca
$C955 | b15 file $01E965 | LDA $0000
$C958 | b15 file $01E968 | STA $0572
$C95B | b15 file $01E96B | LDA $0561
$C95E | b15 file $01E96E | JSR $f2d7
$C961 | b15 file $01E971 | JSR $c991
$C964 | b15 file $01E974 | STA $056b
$C967 | b15 file $01E977 | STA $04c2
$C96A | b15 file $01E97A | STY $0571
$C96D | b15 file $01E97D | STX $056f
$C970 | b15 file $01E980 | LDA $0561
$C973 | b15 file $01E983 | JSR $f2d7
$C976 | b15 file $01E986 | LDY #$02
$C978 | b15 file $01E988 | LDA ($00),Y
$C97A | b15 file $01E98A | STA $0000
$C97D | b15 file $01E98D | LDA #$00
$C97F | b15 file $01E98F | STA $0001
$C982 | b15 file $01E992 | LDA #$0d
$C984 | b15 file $01E994 | STA $0003
$C987 | b15 file $01E997 | JSR $ebca
$C98A | b15 file $01E99A | LDA $0000
$C98D | b15 file $01E99D | STA $0573
$C990 | b15 file $01E9A0 | RTS
$C991 | b15 file $01E9A1 | LDY #$0a
$C993 | b15 file $01E9A3 | LDA ($00),Y
$C995 | b15 file $01E9A5 | PHA
$C996 | b15 file $01E9A6 | LDY #$01
$C998 | b15 file $01E9A8 | LDA ($00),Y
$C99A | b15 file $01E9AA | LDY #$2d
$C99C | b15 file $01E9AC | CMP #$32
$C99E | b15 file $01E9AE | BCC $c9c0
$C9A0 | b15 file $01E9B0 | LDY #$2d
$C9A2 | b15 file $01E9B2 | CMP #$41
$C9A4 | b15 file $01E9B4 | BCC $c9c0
$C9A6 | b15 file $01E9B6 | LDY #$32
$C9A8 | b15 file $01E9B8 | CMP #$50
$C9AA | b15 file $01E9BA | BCC $c9c0
$C9AC | b15 file $01E9BC | LDY #$37
$C9AE | b15 file $01E9BE | CMP #$57
$C9B0 | b15 file $01E9C0 | BCC $c9c0
$C9B2 | b15 file $01E9C2 | LDY #$3c
$C9B4 | b15 file $01E9C4 | CMP #$5c
$C9B6 | b15 file $01E9C6 | BCC $c9c0
$C9B8 | b15 file $01E9C8 | LDY #$41
$C9BA | b15 file $01E9CA | CMP #$61
$C9BC | b15 file $01E9CC | BCC $c9c0
$C9BE | b15 file $01E9CE | LDY #$46
$C9C0 | b15 file $01E9D0 | STY $0003
$C9C3 | b15 file $01E9D3 | STA $0000
$C9C6 | b15 file $01E9D6 | LDA #$00
$C9C8 | b15 file $01E9D8 | STA $0001
$C9CB | b15 file $01E9DB | STA $0002
$C9CE | b15 file $01E9DE | JSR $ebe9
$C9D1 | b15 file $01E9E1 | LDA $0006
$C9D4 | b15 file $01E9E4 | STA $0001
$C9D7 | b15 file $01E9E7 | LDA $0007
$C9DA | b15 file $01E9EA | STA $0002
$C9DD | b15 file $01E9ED | LDA #$64
$C9DF | b15 file $01E9EF | STA $0003
$C9E2 | b15 file $01E9F2 | LDA #$00
$C9E4 | b15 file $01E9F4 | STA $0004
$C9E7 | b15 file $01E9F7 | JSR $ea7c
$C9EA | b15 file $01E9FA | JSR $e87a
$C9ED | b15 file $01E9FD | AND #$0f
$C9EF | b15 file $01E9FF | CMP #$09
$C9F1 | b15 file $01EA01 | BCS $c9ea
$C9F3 | b15 file $01EA03 | STA $0002
$C9F6 | b15 file $01EA06 | LDA $0001
$C9F9 | b15 file $01EA09 | CLC
$C9FA | b15 file $01EA0A | ADC #$09
$C9FC | b15 file $01EA0C | SEC
$C9FD | b15 file $01EA0D | SBC $0002
$CA00 | b15 file $01EA10 | BCS $ca04
$CA02 | b15 file $01EA12 | LDA #$01
$CA04 | b15 file $01EA14 | STA $0001
$CA07 | b15 file $01EA17 | PLA
$CA08 | b15 file $01EA18 | PHA
$CA09 | b15 file $01EA19 | AND #$1f
$CA0B | b15 file $01EA1B | TAY
$CA0C | b15 file $01EA1C | LDA $ca1f,Y
$CA0F | b15 file $01EA1F | TAY
$CA10 | b15 file $01EA20 | PLA
$CA11 | b15 file $01EA21 | LSR A
$CA12 | b15 file $01EA22 | LSR A
$CA13 | b15 file $01EA23 | LSR A
$CA14 | b15 file $01EA24 | LSR A
$CA15 | b15 file $01EA25 | LSR A
$CA16 | b15 file $01EA26 | TAX
$CA17 | b15 file $01EA27 | LDA $ca37,X
$CA1A | b15 file $01EA2A | TAX
$CA1B | b15 file $01EA2B | LDA $0001
$CA1E | b15 file $01EA2E | RTS
$CA3F | b15 file $01EA4F | LDA $0560
$CA42 | b15 file $01EA52 | JSR $f2d7
$CA45 | b15 file $01EA55 | LDA $05ac
$CA48 | b15 file $01EA58 | LDY #$00
$CA4A | b15 file $01EA5A | STA ($00),Y
$CA4C | b15 file $01EA5C | LDY #$00
$CA4E | b15 file $01EA5E | STY $0002
$CA51 | b15 file $01EA61 | STY $0003
$CA54 | b15 file $01EA64 | LDA $05ad,Y
$CA57 | b15 file $01EA67 | CMP #$ff
$CA59 | b15 file $01EA69 | BEQ $ca6d
$CA5B | b15 file $01EA6B | LDA $05ad,Y
$CA5E | b15 file $01EA6E | CLC
$CA5F | b15 file $01EA6F | ADC $0002
$CA62 | b15 file $01EA72 | STA $0002
$CA65 | b15 file $01EA75 | LDA $0003
$CA68 | b15 file $01EA78 | ADC #$00
$CA6A | b15 file $01EA7A | STA $0003
$CA6D | b15 file $01EA7D | INY
$CA6E | b15 file $01EA7E | CPY #$0a
$CA70 | b15 file $01EA80 | BCC $ca54
$CA72 | b15 file $01EA82 | LDY #$08
$CA74 | b15 file $01EA84 | LDA $0002
$CA77 | b15 file $01EA87 | STA ($00),Y
$CA79 | b15 file $01EA89 | INY
$CA7A | b15 file $01EA8A | LDA ($00),Y
$CA7C | b15 file $01EA8C | AND #$fc
$CA7E | b15 file $01EA8E | ORA $0003
$CA81 | b15 file $01EA91 | STA ($00),Y
$CA83 | b15 file $01EA93 | LDA $0561
$CA86 | b15 file $01EA96 | JSR $f2d7
$CA89 | b15 file $01EA99 | LDA $05b7
$CA8C | b15 file $01EA9C | LDY #$00
$CA8E | b15 file $01EA9E | STA ($00),Y
$CA90 | b15 file $01EAA0 | LDY #$00
$CA92 | b15 file $01EAA2 | STY $0002
$CA95 | b15 file $01EAA5 | STY $0003
$CA98 | b15 file $01EAA8 | LDA $05b8,Y
$CA9B | b15 file $01EAAB | CMP #$ff
$CA9D | b15 file $01EAAD | BEQ $cab1
$CA9F | b15 file $01EAAF | LDA $05b8,Y
$CAA2 | b15 file $01EAB2 | CLC
$CAA3 | b15 file $01EAB3 | ADC $0002
$CAA6 | b15 file $01EAB6 | STA $0002
$CAA9 | b15 file $01EAB9 | LDA $0003
$CAAC | b15 file $01EABC | ADC #$00
$CAAE | b15 file $01EABE | STA $0003
$CAB1 | b15 file $01EAC1 | INY
$CAB2 | b15 file $01EAC2 | CPY #$0a
$CAB4 | b15 file $01EAC4 | BCC $ca98
$CAB6 | b15 file $01EAC6 | LDY #$08
$CAB8 | b15 file $01EAC8 | LDA $0002
$CABB | b15 file $01EACB | STA ($00),Y
$CABD | b15 file $01EACD | INY
$CABE | b15 file $01EACE | LDA ($00),Y
$CAC0 | b15 file $01EAD0 | AND #$fc
$CAC2 | b15 file $01EAD2 | ORA $0003
$CAC5 | b15 file $01EAD5 | STA ($00),Y
$CAC7 | b15 file $01EAD7 | RTS
$CAC8 | b15 file $01EAD8 | LDY $0545
$CACB | b15 file $01EADB | LDA $0580,Y
$CACE | b15 file $01EADE | CLC
$CACF | b15 file $01EADF | ADC $0000
$CAD2 | b15 file $01EAE2 | STA $0000
$CAD5 | b15 file $01EAE5 | CMP #$10
$CAD7 | b15 file $01EAE7 | BCS $cae7
$CAD9 | b15 file $01EAE9 | LDA $0596,Y
$CADC | b15 file $01EAEC | CLC
$CADD | b15 file $01EAED | ADC $0001
$CAE0 | b15 file $01EAF0 | STA $0001
$CAE3 | b15 file $01EAF3 | CMP #$0a
$CAE5 | b15 file $01EAF5 | BCC $caea
$CAE7 | b15 file $01EAF7 | LDA #$01
$CAE9 | b15 file $01EAF9 | RTS
$CAEA | b15 file $01EAFA | JSR $caf9
$CAED | b15 file $01EAFD | CMP #$04
$CAEF | b15 file $01EAFF | BEQ $caf5
$CAF1 | b15 file $01EB01 | CMP #$05
$CAF3 | b15 file $01EB03 | BNE $caf7
$CAF5 | b15 file $01EB05 | LDA #$00
$CAF7 | b15 file $01EB07 | TAY
$CAF8 | b15 file $01EB08 | RTS
$CAF9 | b15 file $01EB09 | LDA $0544
$CAFC | b15 file $01EB0C | PHA
$CAFD | b15 file $01EB0D | TAY
$CAFE | b15 file $01EB0E | LDA $bb48,Y
$CB01 | b15 file $01EB11 | TAY
$CB02 | b15 file $01EB12 | JSR $f25f
$CB05 | b15 file $01EB15 | PLA
$CB06 | b15 file $01EB16 | ASL A
$CB07 | b15 file $01EB17 | TAY
$CB08 | b15 file $01EB18 | LDA $bb1e,Y
$CB0B | b15 file $01EB1B | STA $0002
$CB0E | b15 file $01EB1E | LDA $bb1f,Y
$CB11 | b15 file $01EB21 | STA $0003
$CB14 | b15 file $01EB24 | LDA $0001
$CB17 | b15 file $01EB27 | ASL A
$CB18 | b15 file $01EB28 | ASL A
$CB19 | b15 file $01EB29 | ASL A
$CB1A | b15 file $01EB2A | ASL A
$CB1B | b15 file $01EB2B | ORA $0000
$CB1E | b15 file $01EB2E | TAY
$CB1F | b15 file $01EB2F | LDA ($02),Y
$CB21 | b15 file $01EB31 | TAY
$CB22 | b15 file $01EB32 | LDA $cb59,Y
$CB25 | b15 file $01EB35 | BEQ $cb57
$CB27 | b15 file $01EB37 | CMP #$01
$CB29 | b15 file $01EB39 | BEQ $cb57
$CB2B | b15 file $01EB3B | CMP #$05
$CB2D | b15 file $01EB3D | BEQ $cb57
$CB2F | b15 file $01EB3F | PHA
$CB30 | b15 file $01EB40 | LDY #$00
$CB32 | b15 file $01EB42 | LDA $0545
$CB35 | b15 file $01EB45 | CMP #$0b
$CB37 | b15 file $01EB47 | BCC $cb3a
$CB39 | b15 file $01EB49 | INY
$CB3A | b15 file $01EB4A | LDA $0560,Y
$CB3D | b15 file $01EB4D | JSR $f2d7
$CB40 | b15 file $01EB50 | LDY #$0b
$CB42 | b15 file $01EB52 | LDA ($00),Y
$CB44 | b15 file $01EB54 | LSR A
$CB45 | b15 file $01EB55 | LSR A
$CB46 | b15 file $01EB56 | AND #$03
$CB48 | b15 file $01EB58 | TAY
$CB49 | b15 file $01EB59 | PLA
$CB4A | b15 file $01EB5A | TAX
$CB4B | b15 file $01EB5B | CMP $cbe9,Y
$CB4E | b15 file $01EB5E | BEQ $cb55
$CB50 | b15 file $01EB60 | CMP $cbed,Y
$CB53 | b15 file $01EB63 | BNE $cb57
$CB55 | b15 file $01EB65 | LDA #$00
$CB57 | b15 file $01EB67 | TAY
$CB58 | b15 file $01EB68 | RTS
$CBF1 | b15 file $01EC01 | LDY #$20
$CBF3 | b15 file $01EC03 | LDA #$00
$CBF5 | b15 file $01EC05 | STA $044c,Y
$CBF8 | b15 file $01EC08 | DEY
$CBF9 | b15 file $01EC09 | BPL $cbf5
$CBFB | b15 file $01EC0B | LDA $05ac
$CBFE | b15 file $01EC0E | STA $044c
$CC01 | b15 file $01EC11 | LDA $05b7
$CC04 | b15 file $01EC14 | STA $044f
$CC07 | b15 file $01EC17 | LDA #$01
$CC09 | b15 file $01EC19 | LDY #$00
$CC0B | b15 file $01EC1B | JSR $cc7a
$CC0E | b15 file $01EC1E | LDA $0001
$CC11 | b15 file $01EC21 | STA $0452
$CC14 | b15 file $01EC24 | LDA $0002
$CC17 | b15 file $01EC27 | STA $0453
$CC1A | b15 file $01EC2A | LDA #$01
$CC1C | b15 file $01EC2C | LDY #$0b
$CC1E | b15 file $01EC2E | JSR $cc7a
$CC21 | b15 file $01EC31 | LDA $0001
$CC24 | b15 file $01EC34 | STA $0455
$CC27 | b15 file $01EC37 | LDA $0002
$CC2A | b15 file $01EC3A | STA $0456
$CC2D | b15 file $01EC3D | LDA #$02
$CC2F | b15 file $01EC3F | LDY #$00
$CC31 | b15 file $01EC41 | JSR $cc7a
$CC34 | b15 file $01EC44 | LDA $0001
$CC37 | b15 file $01EC47 | STA $0458
$CC3A | b15 file $01EC4A | LDA $0002
$CC3D | b15 file $01EC4D | STA $0459
$CC40 | b15 file $01EC50 | LDA #$02
$CC42 | b15 file $01EC52 | LDY #$0b
$CC44 | b15 file $01EC54 | JSR $cc7a
$CC47 | b15 file $01EC57 | LDA $0001
$CC4A | b15 file $01EC5A | STA $045b
$CC4D | b15 file $01EC5D | LDA $0002
$CC50 | b15 file $01EC60 | STA $045c
$CC53 | b15 file $01EC63 | LDA #$03
$CC55 | b15 file $01EC65 | LDY #$00
$CC57 | b15 file $01EC67 | JSR $cc7a
$CC5A | b15 file $01EC6A | LDA $0001
$CC5D | b15 file $01EC6D | STA $045e
$CC60 | b15 file $01EC70 | LDA $0002
$CC63 | b15 file $01EC73 | STA $045f
$CC66 | b15 file $01EC76 | LDA #$03
$CC68 | b15 file $01EC78 | LDY #$0b
$CC6A | b15 file $01EC7A | JSR $cc7a
$CC6D | b15 file $01EC7D | LDA $0001
$CC70 | b15 file $01EC80 | STA $0461
$CC73 | b15 file $01EC83 | LDA $0002
$CC76 | b15 file $01EC86 | STA $0462
$CC79 | b15 file $01EC89 | RTS
$CC7A | b15 file $01EC8A | STA $0000
$CC7D | b15 file $01EC8D | LDA #$00
$CC7F | b15 file $01EC8F | STA $0001
$CC82 | b15 file $01EC92 | STA $0002
$CC85 | b15 file $01EC95 | LDX #$0a
$CC87 | b15 file $01EC97 | LDA $05c2,Y
$CC8A | b15 file $01EC9A | AND #$0f
$CC8C | b15 file $01EC9C | CMP $0000
$CC8F | b15 file $01EC9F | BNE $cca3
$CC91 | b15 file $01ECA1 | LDA $05ac,Y
$CC94 | b15 file $01ECA4 | CLC
$CC95 | b15 file $01ECA5 | ADC $0001
$CC98 | b15 file $01ECA8 | STA $0001
$CC9B | b15 file $01ECAB | LDA $0002
$CC9E | b15 file $01ECAE | ADC #$00
$CCA0 | b15 file $01ECB0 | STA $0002
$CCA3 | b15 file $01ECB3 | INY
$CCA4 | b15 file $01ECB4 | DEX
$CCA5 | b15 file $01ECB5 | BPL $cc87
$CCA7 | b15 file $01ECB7 | RTS
$CCA8 | b15 file $01ECB8 | LDA #$d8
$CCAA | b15 file $01ECBA | STA $000a
$CCAD | b15 file $01ECBD | LDA #$a0
$CCAF | b15 file $01ECBF | STA $000c
$CCB2 | b15 file $01ECC2 | JMP $ccbf
$CCBF | b15 file $01ECCF | LDA $005e
$CCC2 | b15 file $01ECD2 | AND #$10
$CCC4 | b15 file $01ECD4 | BNE $ccd8
$CCC6 | b15 file $01ECD6 | LDA #$d9
$CCC8 | b15 file $01ECD8 | STA $0000
$CCCB | b15 file $01ECDB | LDA #$cc
$CCCD | b15 file $01ECDD | STA $0001
$CCD0 | b15 file $01ECE0 | LDA #$00
$CCD2 | b15 file $01ECE2 | STA $0002
$CCD5 | b15 file $01ECE5 | JMP $f1ad
$CCD8 | b15 file $01ECE8 | RTS
$CCDE | b15 file $01ECEE | CMP #$00
$CCE0 | b15 file $01ECF0 | BNE $cce8
$CCE2 | b15 file $01ECF2 | LDA $0562
$CCE5 | b15 file $01ECF5 | JMP $cceb
$CCE8 | b15 file $01ECF8 | LDA $0563
$CCEB | b15 file $01ECFB | CMP #$01
$CCED | b15 file $01ECFD | BEQ $cd06
$CCEF | b15 file $01ECFF | CMP #$03
$CCF1 | b15 file $01ED01 | BEQ $cd19
$CCF3 | b15 file $01ED03 | LDA $0083
$CCF6 | b15 file $01ED06 | STA $0000
$CCF9 | b15 file $01ED09 | LDA $0081
$CCFC | b15 file $01ED0C | STA $0001
$CCFF | b15 file $01ED0F | ORA $057b
$CD02 | b15 file $01ED12 | STA $057b
$CD05 | b15 file $01ED15 | RTS
$CD06 | b15 file $01ED16 | LDA $0085
$CD09 | b15 file $01ED19 | STA $0000
$CD0C | b15 file $01ED1C | LDA $0082
$CD0F | b15 file $01ED1F | STA $0001
$CD12 | b15 file $01ED22 | ORA $057b
$CD15 | b15 file $01ED25 | STA $057b
$CD18 | b15 file $01ED28 | RTS
$CD19 | b15 file $01ED29 | LDA #$00
$CD1B | b15 file $01ED2B | STA $0000
$CD1E | b15 file $01ED2E | STA $0001
$CD21 | b15 file $01ED31 | RTS
$CD22 | b15 file $01ED32 | LDA #$00
$CD24 | b15 file $01ED34 | JSR $ccde
$CD27 | b15 file $01ED37 | LDA $0000
$CD2A | b15 file $01ED3A | PHA
$CD2B | b15 file $01ED3B | LDA $0001
$CD2E | b15 file $01ED3E | PHA
$CD2F | b15 file $01ED3F | LDA #$01
$CD31 | b15 file $01ED41 | JSR $ccde
$CD34 | b15 file $01ED44 | PLA
$CD35 | b15 file $01ED45 | ORA $0001
$CD38 | b15 file $01ED48 | STA $0001
$CD3B | b15 file $01ED4B | PLA
$CD3C | b15 file $01ED4C | ORA $0000
$CD3F | b15 file $01ED4F | STA $0000
$CD42 | b15 file $01ED52 | RTS
$CD43 | b15 file $01ED53 | LDA $0541
$CD46 | b15 file $01ED56 | JSR $eade ; inline targets: $CD4F,$CD59,$CDCF
$CD4F | b15 file $01ED5F | JSR $ecee
$CD52 | b15 file $01ED62 | INC $0541
$CD55 | b15 file $01ED65 | JSR $ca3f
$CD58 | b15 file $01ED68 | RTS
$CD59 | b15 file $01ED69 | LDA $0087
$CD5C | b15 file $01ED6C | BPL $cd58
$CD5E | b15 file $01ED6E | JSR $e768
$CD61 | b15 file $01ED71 | INC $0541
$CD64 | b15 file $01ED74 | LDA #$07
$CD66 | b15 file $01ED76 | STA $007a
$CD69 | b15 file $01ED79 | LDA #$00
$CD6B | b15 file $01ED7B | STA $04a8
$CD6E | b15 file $01ED7E | STA $04a9
$CD71 | b15 file $01ED81 | STA $04aa
$CD74 | b15 file $01ED84 | LDA $0562
$CD77 | b15 file $01ED87 | BEQ $cd85
$CD79 | b15 file $01ED89 | LDA $0563
$CD7C | b15 file $01ED8C | BEQ $cdaa
$CD7E | b15 file $01ED8E | LDA $0563
$CD81 | b15 file $01ED91 | CMP #$01
$CD83 | b15 file $01ED93 | BEQ $cdaa
$CD85 | b15 file $01ED95 | LDA $0560
$CD88 | b15 file $01ED98 | STA $04ad
$CD8B | b15 file $01ED9B | LDA $0561
$CD8E | b15 file $01ED9E | STA $04ae
$CD91 | b15 file $01EDA1 | LDA $0562
$CD94 | b15 file $01EDA4 | CMP #$03
$CD96 | b15 file $01EDA6 | BNE $cd9a
$CD98 | b15 file $01EDA8 | LDA #$80
$CD9A | b15 file $01EDAA | STA $04ab
$CD9D | b15 file $01EDAD | LDA $0563
$CDA0 | b15 file $01EDB0 | CMP #$03
$CDA2 | b15 file $01EDB2 | BNE $cda6
$CDA4 | b15 file $01EDB4 | LDA #$80
$CDA6 | b15 file $01EDB6 | STA $04ac
$CDA9 | b15 file $01EDB9 | RTS
$CDAA | b15 file $01EDBA | LDA $0560
$CDAD | b15 file $01EDBD | STA $04ae
$CDB0 | b15 file $01EDC0 | LDA $0561
$CDB3 | b15 file $01EDC3 | STA $04ad
$CDB6 | b15 file $01EDC6 | LDA $0562
$CDB9 | b15 file $01EDC9 | CMP #$03
$CDBB | b15 file $01EDCB | BNE $cdbf
$CDBD | b15 file $01EDCD | LDA #$80
$CDBF | b15 file $01EDCF | STA $04ac
$CDC2 | b15 file $01EDD2 | LDA $0563
$CDC5 | b15 file $01EDD5 | CMP #$03
$CDC7 | b15 file $01EDD7 | BNE $cdcb
$CDC9 | b15 file $01EDD9 | LDA #$80
$CDCB | b15 file $01EDDB | STA $04ab
$CDCE | b15 file $01EDDE | RTS
$CDCF | b15 file $01EDDF | LDA $0087
$CDD2 | b15 file $01EDE2 | BPL $ce0f
$CDD4 | b15 file $01EDE4 | LDA $0560
$CDD7 | b15 file $01EDE7 | JSR $f2d7
$CDDA | b15 file $01EDEA | LDY #$00
$CDDC | b15 file $01EDEC | LDA ($00),Y
$CDDE | b15 file $01EDEE | STA $05ac
$CDE1 | b15 file $01EDF1 | LDA $0561
$CDE4 | b15 file $01EDF4 | JSR $f2d7
$CDE7 | b15 file $01EDF7 | LDY #$00
$CDE9 | b15 file $01EDF9 | LDA ($00),Y
$CDEB | b15 file $01EDFB | STA $05b7
$CDEE | b15 file $01EDFE | LDA #$00
$CDF0 | b15 file $01EE00 | STA $0540
$CDF3 | b15 file $01EE03 | LDA #$01
$CDF5 | b15 file $01EE05 | STA $0541
$CDF8 | b15 file $01EE08 | LDA #$00
$CDFA | b15 file $01EE0A | STA $0548
$CDFD | b15 file $01EE0D | LDA $0514
$CE00 | b15 file $01EE10 | LDY $0515
$CE03 | b15 file $01EE13 | JSR $ce10
$CE06 | b15 file $01EE16 | LDA $0516
$CE09 | b15 file $01EE19 | LDY $0517
$CE0C | b15 file $01EE1C | JSR $ce10
$CE0F | b15 file $01EE1F | RTS
$CE10 | b15 file $01EE20 | CPY #$01
$CE12 | b15 file $01EE22 | BNE $ce24
$CE14 | b15 file $01EE24 | CMP $0560
$CE17 | b15 file $01EE27 | BNE $ce1f
$CE19 | b15 file $01EE29 | LDA #$01
$CE1B | b15 file $01EE2B | STA $0550
$CE1E | b15 file $01EE2E | RTS
$CE1F | b15 file $01EE2F | LDA #$01
$CE21 | b15 file $01EE31 | STA $0554
$CE24 | b15 file $01EE34 | RTS
$CE25 | b15 file $01EE35 | LDA $0541
$CE28 | b15 file $01EE38 | JSR $eade ; inline targets: $CE33,$CE68,$CEAE,$CEFA
$CE33 | b15 file $01EE43 | JSR $e87a
$CE36 | b15 file $01EE46 | AND #$03
$CE38 | b15 file $01EE48 | STA $056c
$CE3B | b15 file $01EE4B | LDA $0562
$CE3E | b15 file $01EE4E | CMP #$03
$CE40 | b15 file $01EE50 | BNE $ce45
$CE42 | b15 file $01EE52 | JMP $cefa
$CE45 | b15 file $01EE55 | LDA #$d4
$CE47 | b15 file $01EE57 | JSR $f26d
$CE4A | b15 file $01EE5A | INC $0541
$CE4D | b15 file $01EE5D | LDA $0560
$CE50 | b15 file $01EE60 | STA $0000
$CE53 | b15 file $01EE63 | LDY #$3d
$CE55 | b15 file $01EE65 | JSR $ee07 ; inline far target $A030
$CE5A | b15 file $01EE6A | LDA #$00
$CE5C | b15 file $01EE6C | STA $0424
$CE5F | b15 file $01EE6F | STA $0425
$CE62 | b15 file $01EE72 | LDA #$7d
$CE64 | b15 file $01EE74 | STA $00bc
$CE67 | b15 file $01EE77 | RTS
$CE68 | b15 file $01EE78 | LDA $0560
$CE6B | b15 file $01EE7B | STA $0000
$CE6E | b15 file $01EE7E | LDA #$a5
$CE70 | b15 file $01EE80 | STA $000a
$CE73 | b15 file $01EE83 | LDX #$00
$CE75 | b15 file $01EE85 | LDY #$39
$CE77 | b15 file $01EE87 | JSR $ee07 ; inline far target $A000
$CE7C | b15 file $01EE8C | LDY #$00
$CE7E | b15 file $01EE8E | JSR $cf05
$CE81 | b15 file $01EE91 | LDA $0012
$CE84 | b15 file $01EE94 | STA $056c
$CE87 | b15 file $01EE97 | LDA #$00
$CE89 | b15 file $01EE99 | JSR $ccde
$CE8C | b15 file $01EE9C | JSR $b870
$CE8F | b15 file $01EE9F | BCC $cead
$CE91 | b15 file $01EEA1 | LDA $0001
$CE94 | b15 file $01EEA4 | AND #$01
$CE96 | b15 file $01EEA6 | BEQ $cead
$CE98 | b15 file $01EEA8 | INC $0541
$CE9B | b15 file $01EEAB | LDA #$d2
$CE9D | b15 file $01EEAD | JSR $f26d
$CEA0 | b15 file $01EEB0 | LDA $0564
$CEA3 | b15 file $01EEB3 | JSR $f368
$CEA6 | b15 file $01EEB6 | LDY #$00
$CEA8 | b15 file $01EEB8 | LDA ($00),Y
$CEAA | b15 file $01EEBA | STA $042c
$CEAD | b15 file $01EEBD | RTS
$CEAE | b15 file $01EEBE | LDA $0560
$CEB1 | b15 file $01EEC1 | STA $0000
$CEB4 | b15 file $01EEC4 | LDA #$a5
$CEB6 | b15 file $01EEC6 | STA $000a
$CEB9 | b15 file $01EEC9 | LDX #$00
$CEBB | b15 file $01EECB | LDY #$39
$CEBD | b15 file $01EECD | JSR $ee07 ; inline far target $A000
$CEC2 | b15 file $01EED2 | LDA #$00
$CEC4 | b15 file $01EED4 | JSR $ccde
$CEC7 | b15 file $01EED7 | JSR $b870
$CECA | b15 file $01EEDA | BCC $cef9
$CECC | b15 file $01EEDC | JSR $c8fd
$CECF | b15 file $01EEDF | LDA #$00
$CED1 | b15 file $01EEE1 | JSR $ccde
$CED4 | b15 file $01EEE4 | LDA $0001
$CED7 | b15 file $01EEE7 | AND #$01
$CED9 | b15 file $01EEE9 | BEQ $cef9
$CEDB | b15 file $01EEEB | LDA #$03
$CEDD | b15 file $01EEED | STA $0540
$CEE0 | b15 file $01EEF0 | LDA #$00
$CEE2 | b15 file $01EEF2 | STA $0541
$CEE5 | b15 file $01EEF5 | LDA #$06
$CEE7 | b15 file $01EEF7 | STA $054b
$CEEA | b15 file $01EEFA | LDA #$03
$CEEC | b15 file $01EEFC | STA $054c
$CEEF | b15 file $01EEFF | LDA #$00
$CEF1 | b15 file $01EF01 | STA $0549
$CEF4 | b15 file $01EF04 | LDA #$05
$CEF6 | b15 file $01EF06 | STA $00bc
$CEF9 | b15 file $01EF09 | RTS
$CEFA | b15 file $01EF0A | LDA #$07
$CEFC | b15 file $01EF0C | STA $0540
$CEFF | b15 file $01EF0F | LDA #$00
$CF01 | b15 file $01EF11 | STA $0541
$CF04 | b15 file $01EF14 | RTS
$CF05 | b15 file $01EF15 | LDA $0083
$CF08 | b15 file $01EF18 | PHA
$CF09 | b15 file $01EF19 | LDA $0081
$CF0C | b15 file $01EF1C | PHA
$CF0D | b15 file $01EF1D | TYA
$CF0E | b15 file $01EF1E | JSR $ccde
$CF11 | b15 file $01EF21 | LDA $0000
$CF14 | b15 file $01EF24 | STA $0083
$CF17 | b15 file $01EF27 | LDA $0001
$CF1A | b15 file $01EF2A | STA $0081
$CF1D | b15 file $01EF2D | LDA #$52
$CF1F | b15 file $01EF2F | STA $0010
$CF22 | b15 file $01EF32 | LDA #$cf
$CF24 | b15 file $01EF34 | STA $0011
$CF27 | b15 file $01EF37 | LDA #$00
$CF29 | b15 file $01EF39 | STA $0012
$CF2C | b15 file $01EF3C | JSR $ed28
$CF2F | b15 file $01EF3F | LDA #$5a
$CF31 | b15 file $01EF41 | STA $0010
$CF34 | b15 file $01EF44 | LDA #$cf
$CF36 | b15 file $01EF46 | STA $0011
$CF39 | b15 file $01EF49 | LDA #$62
$CF3B | b15 file $01EF4B | STA $0000
$CF3E | b15 file $01EF4E | LDA #$cf
$CF40 | b15 file $01EF50 | STA $0001
$CF43 | b15 file $01EF53 | LDA $0012
$CF46 | b15 file $01EF56 | JSR $edf5
$CF49 | b15 file $01EF59 | PLA
$CF4A | b15 file $01EF5A | STA $0081
$CF4D | b15 file $01EF5D | PLA
$CF4E | b15 file $01EF5E | STA $0083
$CF51 | b15 file $01EF61 | RTS
$CF67 | b15 file $01EF77 | LDA $0541
$CF6A | b15 file $01EF7A | JSR $eade ; inline targets: $CF77,$CF9D,$CFC2,$D008,$D054
$CF77 | b15 file $01EF87 | JSR $e87a
$CF7A | b15 file $01EF8A | AND #$03
$CF7C | b15 file $01EF8C | STA $056d
$CF7F | b15 file $01EF8F | LDA $0563
$CF82 | b15 file $01EF92 | CMP #$03
$CF84 | b15 file $01EF94 | BNE $cf89
$CF86 | b15 file $01EF96 | JMP $d054
$CF89 | b15 file $01EF99 | LDA #$00
$CF8B | b15 file $01EF9B | STA $0310
$CF8E | b15 file $01EF9E | STA $0300
$CF91 | b15 file $01EFA1 | INC $0541
$CF94 | b15 file $01EFA4 | LDA #$00
$CF96 | b15 file $01EFA6 | STA $0424
$CF99 | b15 file $01EFA9 | STA $0425
$CF9C | b15 file $01EFAC | RTS
$CF9D | b15 file $01EFAD | JSR $b870
$CFA0 | b15 file $01EFB0 | BCC $cfc1
$CFA2 | b15 file $01EFB2 | LDA #$d4
$CFA4 | b15 file $01EFB4 | JSR $f26d
$CFA7 | b15 file $01EFB7 | INC $0541
$CFAA | b15 file $01EFBA | LDA $0561
$CFAD | b15 file $01EFBD | STA $0000
$CFB0 | b15 file $01EFC0 | LDY #$3d
$CFB2 | b15 file $01EFC2 | JSR $ee07 ; inline far target $A030
$CFB7 | b15 file $01EFC7 | LDA #$09
$CFB9 | b15 file $01EFC9 | STA $00bb
$CFBC | b15 file $01EFCC | LDA #$7d
$CFBE | b15 file $01EFCE | STA $00bc
$CFC1 | b15 file $01EFD1 | RTS
$CFC2 | b15 file $01EFD2 | LDA $0561
$CFC5 | b15 file $01EFD5 | STA $0000
$CFC8 | b15 file $01EFD8 | LDA #$a5
$CFCA | b15 file $01EFDA | STA $000a
$CFCD | b15 file $01EFDD | LDX #$00
$CFCF | b15 file $01EFDF | LDY #$39
$CFD1 | b15 file $01EFE1 | JSR $ee07 ; inline far target $A000
$CFD6 | b15 file $01EFE6 | LDY #$01
$CFD8 | b15 file $01EFE8 | JSR $cf05
$CFDB | b15 file $01EFEB | LDA $0012
$CFDE | b15 file $01EFEE | STA $056d
$CFE1 | b15 file $01EFF1 | LDA #$01
$CFE3 | b15 file $01EFF3 | JSR $ccde
$CFE6 | b15 file $01EFF6 | JSR $b870
$CFE9 | b15 file $01EFF9 | BCC $d007
$CFEB | b15 file $01EFFB | LDA $0001
$CFEE | b15 file $01EFFE | AND #$01
$CFF0 | b15 file $01F000 | BEQ $d007
$CFF2 | b15 file $01F002 | INC $0541
$CFF5 | b15 file $01F005 | LDA #$d2
$CFF7 | b15 file $01F007 | JSR $f26d
$CFFA | b15 file $01F00A | LDA $0565
$CFFD | b15 file $01F00D | JSR $f368
$D000 | b15 file $01F010 | LDY #$00
$D002 | b15 file $01F012 | LDA ($00),Y
$D004 | b15 file $01F014 | STA $042c
$D007 | b15 file $01F017 | RTS
$D008 | b15 file $01F018 | LDA $0561
$D00B | b15 file $01F01B | STA $0000
$D00E | b15 file $01F01E | LDA #$a5
$D010 | b15 file $01F020 | STA $000a
$D013 | b15 file $01F023 | LDX #$00
$D015 | b15 file $01F025 | LDY #$39
$D017 | b15 file $01F027 | JSR $ee07 ; inline far target $A000
$D01C | b15 file $01F02C | LDA #$01
$D01E | b15 file $01F02E | JSR $ccde
$D021 | b15 file $01F031 | JSR $b870
$D024 | b15 file $01F034 | BCC $d053
$D026 | b15 file $01F036 | JSR $c8fd
$D029 | b15 file $01F039 | LDA #$01
$D02B | b15 file $01F03B | JSR $ccde
$D02E | b15 file $01F03E | LDA $0001
$D031 | b15 file $01F041 | AND #$01
$D033 | b15 file $01F043 | BEQ $d053
$D035 | b15 file $01F045 | LDA #$03
$D037 | b15 file $01F047 | STA $0540
$D03A | b15 file $01F04A | LDA #$00
$D03C | b15 file $01F04C | STA $0541
$D03F | b15 file $01F04F | LDA #$07
$D041 | b15 file $01F051 | STA $054b
$D044 | b15 file $01F054 | LDA #$04
$D046 | b15 file $01F056 | STA $054c
$D049 | b15 file $01F059 | LDA #$01
$D04B | b15 file $01F05B | STA $0549
$D04E | b15 file $01F05E | LDA #$05
$D050 | b15 file $01F060 | STA $00bc
$D053 | b15 file $01F063 | RTS
$D054 | b15 file $01F064 | LDA #$00
$D056 | b15 file $01F066 | STA $0540
$D059 | b15 file $01F069 | LDA #$01
$D05B | b15 file $01F06B | STA $0541
$D05E | b15 file $01F06E | LDA #$00
$D060 | b15 file $01F070 | STA $0548
$D063 | b15 file $01F073 | JSR $b548
$D066 | b15 file $01F076 | RTS
$D067 | b15 file $01F077 | JSR $d0cb
$D06A | b15 file $01F07A | LDA $057a
$D06D | b15 file $01F07D | CMP #$04
$D06F | b15 file $01F07F | BCC $d089
$D071 | b15 file $01F081 | LDA $0562
$D074 | b15 file $01F084 | CMP #$03
$D076 | b15 file $01F086 | BNE $d07d
$D078 | b15 file $01F088 | LDY #$00
$D07A | b15 file $01F08A | JSR $d1d8
$D07D | b15 file $01F08D | LDA $0563
$D080 | b15 file $01F090 | CMP #$03
$D082 | b15 file $01F092 | BNE $d089
$D084 | b15 file $01F094 | LDY #$0b
$D086 | b15 file $01F096 | JSR $d1d8
$D089 | b15 file $01F099 | LDA #$00
$D08B | b15 file $01F09B | STA $0545
$D08E | b15 file $01F09E | LDA $057a
$D091 | b15 file $01F0A1 | CMP #$04
$D093 | b15 file $01F0A3 | BCC $d0ad
$D095 | b15 file $01F0A5 | LDA $0562
$D098 | b15 file $01F0A8 | CMP #$03
$D09A | b15 file $01F0AA | BNE $d0a1
$D09C | b15 file $01F0AC | LDY #$00
$D09E | b15 file $01F0AE | JSR $d2d4
$D0A1 | b15 file $01F0B1 | LDA $0563
$D0A4 | b15 file $01F0B4 | CMP #$03
$D0A6 | b15 file $01F0B6 | BNE $d0ad
$D0A8 | b15 file $01F0B8 | LDY #$0b
$D0AA | b15 file $01F0BA | JSR $d2d4
$D0AD | b15 file $01F0BD | RTS
$D0AE | b15 file $01F0BE | LDA $0562
$D0B1 | b15 file $01F0C1 | CMP #$03
$D0B3 | b15 file $01F0C3 | BNE $d0bc
$D0B5 | b15 file $01F0C5 | LDX #$00
$D0B7 | b15 file $01F0C7 | LDY #$00
$D0B9 | b15 file $01F0C9 | JSR $d3c7
$D0BC | b15 file $01F0CC | LDA $0563
$D0BF | b15 file $01F0CF | CMP #$03
$D0C1 | b15 file $01F0D1 | BNE $d0ca
$D0C3 | b15 file $01F0D3 | LDX #$01
$D0C5 | b15 file $01F0D5 | LDY #$0b
$D0C7 | b15 file $01F0D7 | JSR $d3c7
$D0CA | b15 file $01F0DA | RTS
$D0CB | b15 file $01F0DB | LDA $0562
$D0CE | b15 file $01F0DE | CMP #$03
$D0D0 | b15 file $01F0E0 | BNE $d0e6
$D0D2 | b15 file $01F0E2 | LDA $0550
$D0D5 | b15 file $01F0E5 | CMP #$01
$D0D7 | b15 file $01F0E7 | BEQ $d0e6
$D0D9 | b15 file $01F0E9 | LDA $0560
$D0DC | b15 file $01F0EC | STA $000c
$D0DF | b15 file $01F0EF | LDA #$00
$D0E1 | b15 file $01F0F1 | LDX #$00
$D0E3 | b15 file $01F0F3 | JSR $d102
$D0E6 | b15 file $01F0F6 | LDA $0563
$D0E9 | b15 file $01F0F9 | CMP #$03
$D0EB | b15 file $01F0FB | BNE $d101
$D0ED | b15 file $01F0FD | LDA $0554
$D0F0 | b15 file $01F100 | CMP #$01
$D0F2 | b15 file $01F102 | BEQ $d101
$D0F4 | b15 file $01F104 | LDA $0561
$D0F7 | b15 file $01F107 | STA $000c
$D0FA | b15 file $01F10A | LDA #$04
$D0FC | b15 file $01F10C | LDX #$01
$D0FE | b15 file $01F10E | JSR $d102
$D101 | b15 file $01F111 | RTS
$D102 | b15 file $01F112 | STA $000a
$D105 | b15 file $01F115 | STX $000b
$D108 | b15 file $01F118 | LDA $000c
$D10B | b15 file $01F11B | JSR $f2d7
$D10E | b15 file $01F11E | LDY #$0b
$D110 | b15 file $01F120 | LDA ($00),Y
$D112 | b15 file $01F122 | LSR A
$D113 | b15 file $01F123 | LSR A
$D114 | b15 file $01F124 | AND #$03
$D116 | b15 file $01F126 | ASL A
$D117 | b15 file $01F127 | ASL A
$D118 | b15 file $01F128 | ASL A
$D119 | b15 file $01F129 | CLC
$D11A | b15 file $01F12A | ADC $0544
$D11D | b15 file $01F12D | TAY
$D11E | b15 file $01F12E | LDA $d1b0,Y
$D121 | b15 file $01F131 | STA $000d
$D124 | b15 file $01F134 | LDA $057a
$D127 | b15 file $01F137 | CMP #$04
$D129 | b15 file $01F139 | BCC $d134
$D12B | b15 file $01F13B | LDA $000d
$D12E | b15 file $01F13E | CLC
$D12F | b15 file $01F13F | ADC #$04
$D131 | b15 file $01F141 | STA $000d
$D134 | b15 file $01F144 | LDX $000d
$D137 | b15 file $01F147 | LDY $000a
$D13A | b15 file $01F14A | LDA $0544
$D13D | b15 file $01F14D | CMP #$05
$D13F | b15 file $01F14F | BEQ $d15a
$D141 | b15 file $01F151 | LDA $d1c8,X
$D144 | b15 file $01F154 | STA $0550,Y
$D147 | b15 file $01F157 | LDA $d1c9,X
$D14A | b15 file $01F15A | STA $0551,Y
$D14D | b15 file $01F15D | LDA $d1ca,X
$D150 | b15 file $01F160 | STA $0552,Y
$D153 | b15 file $01F163 | LDA $d1cb,X
$D156 | b15 file $01F166 | STA $0553,Y
$D159 | b15 file $01F169 | RTS
$D15A | b15 file $01F16A | CPY #$04
$D15C | b15 file $01F16C | BCS $d17b
$D15E | b15 file $01F16E | LDA #$02
$D160 | b15 file $01F170 | STA $0550,Y
$D163 | b15 file $01F173 | LDA #$00
$D165 | b15 file $01F175 | STA $0551,Y
$D168 | b15 file $01F178 | STA $0552,Y
$D16B | b15 file $01F17B | STA $0553,Y
$D16E | b15 file $01F17E | LDA $057a
$D171 | b15 file $01F181 | CMP #$04
$D173 | b15 file $01F183 | BCC $d17a
$D175 | b15 file $01F185 | LDA #$00
$D177 | b15 file $01F187 | STA $0550,Y
$D17A | b15 file $01F18A | RTS
$D17B | b15 file $01F18B | LDA #$02
$D17D | b15 file $01F18D | STA $0550,Y
$D180 | b15 file $01F190 | STA $0551,Y
$D183 | b15 file $01F193 | STA $0552,Y
$D186 | b15 file $01F196 | STA $0553,Y
$D189 | b15 file $01F199 | LDA $057a
$D18C | b15 file $01F19C | CMP #$06
$D18E | b15 file $01F19E | BCC $d195
$D190 | b15 file $01F1A0 | LDA #$00
$D192 | b15 file $01F1A2 | STA $0551,Y
$D195 | b15 file $01F1A5 | LDY #$01
$D197 | b15 file $01F1A7 | LDX #$00
$D199 | b15 file $01F1A9 | LDA $0580,Y
$D19C | b15 file $01F1AC | CMP #$08
$D19E | b15 file $01F1AE | BCS $d1a1
$D1A0 | b15 file $01F1B0 | INX
$D1A1 | b15 file $01F1B1 | INY
$D1A2 | b15 file $01F1B2 | CPY #$0b
$D1A4 | b15 file $01F1B4 | BCC $d199
$D1A6 | b15 file $01F1B6 | CPX #$00
$D1A8 | b15 file $01F1B8 | BNE $d1af
$D1AA | b15 file $01F1BA | LDA #$00
$D1AC | b15 file $01F1BC | STA $0556
$D1AF | b15 file $01F1BF | RTS
$D1D8 | b15 file $01F1E8 | STY $0545
$D1DB | b15 file $01F1EB | LDA $05ac,Y
$D1DE | b15 file $01F1EE | LDY $6f02
$D1E1 | b15 file $01F1F1 | CMP $d1e7,Y
$D1E4 | b15 file $01F1F4 | BCC $d1ed
$D1E6 | b15 file $01F1F6 | RTS
$D1ED | b15 file $01F1FD | LDA #$00
$D1EF | b15 file $01F1FF | STA $0548
$D1F2 | b15 file $01F202 | LDA #$01
$D1F4 | b15 file $01F204 | STA $0000
$D1F7 | b15 file $01F207 | LDA #$00
$D1F9 | b15 file $01F209 | STA $0001
$D1FC | b15 file $01F20C | JSR $c1cd
$D1FF | b15 file $01F20F | BCS $d207
$D201 | b15 file $01F211 | TAY
$D202 | b15 file $01F212 | BEQ $d207
$D204 | b15 file $01F214 | INC $0548
$D207 | b15 file $01F217 | LDA #$ff
$D209 | b15 file $01F219 | STA $0000
$D20C | b15 file $01F21C | LDA #$00
$D20E | b15 file $01F21E | STA $0001
$D211 | b15 file $01F221 | JSR $c1cd
$D214 | b15 file $01F224 | BCS $d21c
$D216 | b15 file $01F226 | TAY
$D217 | b15 file $01F227 | BEQ $d21c
$D219 | b15 file $01F229 | INC $0548
$D21C | b15 file $01F22C | LDA #$00
$D21E | b15 file $01F22E | STA $0000
$D221 | b15 file $01F231 | LDA #$ff
$D223 | b15 file $01F233 | STA $0001
$D226 | b15 file $01F236 | JSR $c1cd
$D229 | b15 file $01F239 | BCS $d231
$D22B | b15 file $01F23B | TAY
$D22C | b15 file $01F23C | BEQ $d231
$D22E | b15 file $01F23E | INC $0548
$D231 | b15 file $01F241 | LDA #$00
$D233 | b15 file $01F243 | STA $0000
$D236 | b15 file $01F246 | LDA #$01
$D238 | b15 file $01F248 | STA $0001
$D23B | b15 file $01F24B | JSR $c1cd
$D23E | b15 file $01F24E | BCS $d246
$D240 | b15 file $01F250 | TAY
$D241 | b15 file $01F251 | BEQ $d246
$D243 | b15 file $01F253 | INC $0548
$D246 | b15 file $01F256 | LDA $0548
$D249 | b15 file $01F259 | CMP #$02
$D24B | b15 file $01F25B | BCS $d24e
$D24D | b15 file $01F25D | RTS
$D24E | b15 file $01F25E | LDA $0560
$D251 | b15 file $01F261 | LDY $0545
$D254 | b15 file $01F264 | CPY #$0b
$D256 | b15 file $01F266 | BCC $d25b
$D258 | b15 file $01F268 | LDA $0561
$D25B | b15 file $01F26B | JSR $f2d7
$D25E | b15 file $01F26E | LDY #$03
$D260 | b15 file $01F270 | LDA ($00),Y
$D262 | b15 file $01F272 | CMP #$64
$D264 | b15 file $01F274 | BEQ $d24d
$D266 | b15 file $01F276 | LDA #$64
$D268 | b15 file $01F278 | JSR $e862
$D26B | b15 file $01F27B | LDY $6f02
$D26E | b15 file $01F27E | CMP $d1ea,Y
$D271 | b15 file $01F281 | BCS $d24d
$D273 | b15 file $01F283 | PLA
$D274 | b15 file $01F284 | PLA
$D275 | b15 file $01F285 | JSR $e57f
$D278 | b15 file $01F288 | LDA #$6c
$D27A | b15 file $01F28A | JSR $e683
$D27D | b15 file $01F28D | LDA $0545
$D280 | b15 file $01F290 | BNE $d2ab
$D282 | b15 file $01F292 | LDA $0560
$D285 | b15 file $01F295 | STA $042c
$D288 | b15 file $01F298 | STA $0514
$D28B | b15 file $01F29B | LDA #$03
$D28D | b15 file $01F29D | STA $0515
$D290 | b15 file $01F2A0 | LDA $0561
$D293 | b15 file $01F2A3 | STA $0516
$D296 | b15 file $01F2A6 | LDA #$00
$D298 | b15 file $01F2A8 | STA $0517
$D29B | b15 file $01F2AB | LDA #$04
$D29D | b15 file $01F2AD | STA $0540
$D2A0 | b15 file $01F2B0 | LDA #$00
$D2A2 | b15 file $01F2B2 | STA $0541
$D2A5 | b15 file $01F2B5 | LDA #$7d
$D2A7 | b15 file $01F2B7 | JSR $f28b
$D2AA | b15 file $01F2BA | RTS
$D2AB | b15 file $01F2BB | LDA $0561
$D2AE | b15 file $01F2BE | STA $042c
$D2B1 | b15 file $01F2C1 | STA $0514
$D2B4 | b15 file $01F2C4 | LDA #$03
$D2B6 | b15 file $01F2C6 | STA $0515
$D2B9 | b15 file $01F2C9 | LDA $0561
$D2BC | b15 file $01F2CC | STA $0516
$D2BF | b15 file $01F2CF | LDA #$00
$D2C1 | b15 file $01F2D1 | STA $0517
$D2C4 | b15 file $01F2D4 | LDA #$04
$D2C6 | b15 file $01F2D6 | STA $0540
$D2C9 | b15 file $01F2D9 | LDA #$00
$D2CB | b15 file $01F2DB | STA $0541
$D2CE | b15 file $01F2DE | LDA #$7d
$D2D0 | b15 file $01F2E0 | JSR $f28b
$D2D3 | b15 file $01F2E3 | RTS
$D2D4 | b15 file $01F2E4 | STY $0545
$D2D7 | b15 file $01F2E7 | LDA $0545
$D2DA | b15 file $01F2EA | BNE $d2e5
$D2DC | b15 file $01F2EC | LDA $0550
$D2DF | b15 file $01F2EF | CMP #$01
$D2E1 | b15 file $01F2F1 | BNE $d2ed
$D2E3 | b15 file $01F2F3 | BEQ $d2ec
$D2E5 | b15 file $01F2F5 | LDA $0554
$D2E8 | b15 file $01F2F8 | CMP #$01
$D2EA | b15 file $01F2FA | BNE $d2ed
$D2EC | b15 file $01F2FC | RTS
$D2ED | b15 file $01F2FD | JSR $d32a
$D2F0 | b15 file $01F300 | TYA
$D2F1 | b15 file $01F301 | BNE $d317
$D2F3 | b15 file $01F303 | LDA #$64
$D2F5 | b15 file $01F305 | JSR $e862
$D2F8 | b15 file $01F308 | LDY $6f02
$D2FB | b15 file $01F30B | CMP $d327,Y
$D2FE | b15 file $01F30E | BCS $d317
$D300 | b15 file $01F310 | PLA
$D301 | b15 file $01F311 | PLA
$D302 | b15 file $01F312 | PLA
$D303 | b15 file $01F313 | PLA
$D304 | b15 file $01F314 | LDA $0545
$D307 | b15 file $01F317 | BNE $d318
$D309 | b15 file $01F319 | LDA #$01
$D30B | b15 file $01F31B | STA $0550
$D30E | b15 file $01F31E | STA $0551
$D311 | b15 file $01F321 | STA $0552
$D314 | b15 file $01F324 | STA $0553
$D317 | b15 file $01F327 | RTS
$D318 | b15 file $01F328 | LDA #$01
$D31A | b15 file $01F32A | STA $0554
$D31D | b15 file $01F32D | STA $0555
$D320 | b15 file $01F330 | STA $0556
$D323 | b15 file $01F333 | STA $0557
$D326 | b15 file $01F336 | RTS
$D32A | b15 file $01F33A | LDY #$00
$D32C | b15 file $01F33C | LDX #$00
$D32E | b15 file $01F33E | STX $0000
$D331 | b15 file $01F341 | STX $0001
$D334 | b15 file $01F344 | LDA $0581,Y
$D337 | b15 file $01F347 | BMI $d34b
$D339 | b15 file $01F349 | LDA $05ad,Y
$D33C | b15 file $01F34C | CLC
$D33D | b15 file $01F34D | ADC $0000
$D340 | b15 file $01F350 | STA $0000
$D343 | b15 file $01F353 | LDA $0001
$D346 | b15 file $01F356 | ADC #$00
$D348 | b15 file $01F358 | STA $0001
$D34B | b15 file $01F35B | INY
$D34C | b15 file $01F35C | INX
$D34D | b15 file $01F35D | CPX #$0a
$D34F | b15 file $01F35F | BCC $d334
$D351 | b15 file $01F361 | LDY #$00
$D353 | b15 file $01F363 | LDX #$00
$D355 | b15 file $01F365 | STX $0002
$D358 | b15 file $01F368 | STX $0003
$D35B | b15 file $01F36B | LDA $058c,Y
$D35E | b15 file $01F36E | BMI $d372
$D360 | b15 file $01F370 | LDA $05b8,Y
$D363 | b15 file $01F373 | CLC
$D364 | b15 file $01F374 | ADC $0002
$D367 | b15 file $01F377 | STA $0002
$D36A | b15 file $01F37A | LDA $0003
$D36D | b15 file $01F37D | ADC #$00
$D36F | b15 file $01F37F | STA $0003
$D372 | b15 file $01F382 | INY
$D373 | b15 file $01F383 | INX
$D374 | b15 file $01F384 | CPX #$0a
$D376 | b15 file $01F386 | BCC $d35b
$D378 | b15 file $01F388 | LDA $0545
$D37B | b15 file $01F38B | BEQ $d395
$D37D | b15 file $01F38D | LDX $0000
$D380 | b15 file $01F390 | LDY $0001
$D383 | b15 file $01F393 | LDA $0002
$D386 | b15 file $01F396 | STA $0000
$D389 | b15 file $01F399 | LDA $0003
$D38C | b15 file $01F39C | STA $0001
$D38F | b15 file $01F39F | STX $0002
$D392 | b15 file $01F3A2 | STY $0003
$D395 | b15 file $01F3A5 | LDA $0001
$D398 | b15 file $01F3A8 | BNE $d3c4
$D39A | b15 file $01F3AA | LDA $0000
$D39D | b15 file $01F3AD | CMP #$c8
$D39F | b15 file $01F3AF | BCS $d3c4
$D3A1 | b15 file $01F3B1 | LDA $0000
$D3A4 | b15 file $01F3B4 | CLC
$D3A5 | b15 file $01F3B5 | ADC #$90
$D3A7 | b15 file $01F3B7 | STA $0000
$D3AA | b15 file $01F3BA | LDA $0001
$D3AD | b15 file $01F3BD | ADC #$01
$D3AF | b15 file $01F3BF | STA $0001
$D3B2 | b15 file $01F3C2 | LDA $0000
$D3B5 | b15 file $01F3C5 | SEC
$D3B6 | b15 file $01F3C6 | SBC $0002
$D3B9 | b15 file $01F3C9 | LDA $0001
$D3BC | b15 file $01F3CC | SBC $0003
$D3BF | b15 file $01F3CF | BCS $d3c4
$D3C1 | b15 file $01F3D1 | LDY #$00
$D3C3 | b15 file $01F3D3 | RTS
$D3C4 | b15 file $01F3D4 | LDY #$ff
$D3C6 | b15 file $01F3D6 | RTS
$D3C7 | b15 file $01F3D7 | STX $057c
$D3CA | b15 file $01F3DA | STX $0549
$D3CD | b15 file $01F3DD | STY $0545
$D3D0 | b15 file $01F3E0 | LDA $0574
$D3D3 | b15 file $01F3E3 | ORA $0575
$D3D6 | b15 file $01F3E6 | ORA $0576
$D3D9 | b15 file $01F3E9 | ORA $0577
$D3DC | b15 file $01F3EC | LDX $0572
$D3DF | b15 file $01F3EF | CPY #$00
$D3E1 | b15 file $01F3F1 | BEQ $d3ea
$D3E3 | b15 file $01F3F3 | LSR A
$D3E4 | b15 file $01F3F4 | LSR A
$D3E5 | b15 file $01F3F5 | LSR A
$D3E6 | b15 file $01F3F6 | LSR A
$D3E7 | b15 file $01F3F7 | LDX $0573
$D3EA | b15 file $01F3FA | STX $0548
$D3ED | b15 file $01F3FD | AND #$0f
$D3EF | b15 file $01F3FF | BEQ $d3f2
$D3F1 | b15 file $01F401 | RTS
$D3F2 | b15 file $01F402 | LDX $0548
$D3F5 | b15 file $01F405 | CPX #$0c
$D3F7 | b15 file $01F407 | BCC $d3fc
$D3F9 | b15 file $01F409 | JSR $d42f
$D3FC | b15 file $01F40C | LDX $0548
$D3FF | b15 file $01F40F | CPX #$0a
$D401 | b15 file $01F411 | BCC $d406
$D403 | b15 file $01F413 | JSR $d506
$D406 | b15 file $01F416 | LDX $0548
$D409 | b15 file $01F419 | CPX #$08
$D40B | b15 file $01F41B | BCC $d410
$D40D | b15 file $01F41D | JSR $d5a0
$D410 | b15 file $01F420 | LDX $0548
$D413 | b15 file $01F423 | CPX #$07
$D415 | b15 file $01F425 | BCC $d41a
$D417 | b15 file $01F427 | JSR $d5bc
$D41A | b15 file $01F42A | LDX $0548
$D41D | b15 file $01F42D | CPX #$05
$D41F | b15 file $01F42F | BCC $d424
$D421 | b15 file $01F431 | JSR $d652
$D424 | b15 file $01F434 | LDX $0548
$D427 | b15 file $01F437 | CPX #$03
$D429 | b15 file $01F439 | BCC $d42e
$D42B | b15 file $01F43B | JSR $d612
$D42E | b15 file $01F43E | RTS
$D42F | b15 file $01F43F | LDY $0545
$D432 | b15 file $01F442 | LDA $05c2,Y
$D435 | b15 file $01F445 | LSR A
$D436 | b15 file $01F446 | LSR A
$D437 | b15 file $01F447 | LSR A
$D438 | b15 file $01F448 | LSR A
$D439 | b15 file $01F449 | STA $057d
$D43C | b15 file $01F44C | LDA #$00
$D43E | b15 file $01F44E | STA $057e
$D441 | b15 file $01F451 | PHA
$D442 | b15 file $01F452 | TAY
$D443 | b15 file $01F453 | LDA $057d
$D446 | b15 file $01F456 | ASL A
$D447 | b15 file $01F457 | TAX
$D448 | b15 file $01F458 | LDA $d4aa,X
$D44B | b15 file $01F45B | STA $000a
$D44E | b15 file $01F45E | LDA $d4ab,X
$D451 | b15 file $01F461 | STA $000b
$D454 | b15 file $01F464 | LDA ($0a),Y
$D456 | b15 file $01F466 | STA $0000
$D459 | b15 file $01F469 | TYA
$D45A | b15 file $01F46A | CLC
$D45B | b15 file $01F46B | ADC #$09
$D45D | b15 file $01F46D | TAY
$D45E | b15 file $01F46E | LDA ($0a),Y
$D460 | b15 file $01F470 | STA $0001
$D463 | b15 file $01F473 | JSR $c1cd
$D466 | b15 file $01F476 | BCS $d46e
$D468 | b15 file $01F478 | TAY
$D469 | b15 file $01F479 | BEQ $d46e
$D46B | b15 file $01F47B | INC $057e
$D46E | b15 file $01F47E | PLA
$D46F | b15 file $01F47F | CLC
$D470 | b15 file $01F480 | ADC #$01
$D472 | b15 file $01F482 | CMP #$09
$D474 | b15 file $01F484 | BCC $d441
$D476 | b15 file $01F486 | LDY $057e
$D479 | b15 file $01F489 | LDA $d4fa,Y
$D47C | b15 file $01F48C | BEQ $d48b
$D47E | b15 file $01F48E | STA $000a
$D481 | b15 file $01F491 | LDA #$64
$D483 | b15 file $01F493 | JSR $e862
$D486 | b15 file $01F496 | CMP $000a
$D489 | b15 file $01F499 | BCC $d48c
$D48B | b15 file $01F49B | RTS
$D48C | b15 file $01F49C | PLA
$D48D | b15 file $01F49D | PLA
$D48E | b15 file $01F49E | LDA #$09
$D490 | b15 file $01F4A0 | STA $0540
$D493 | b15 file $01F4A3 | LDA #$00
$D495 | b15 file $01F4A5 | STA $0541
$D498 | b15 file $01F4A8 | LDA #$f1
$D49A | b15 file $01F4AA | JSR $f26d
$D49D | b15 file $01F4AD | LDY $057c
$D4A0 | b15 file $01F4B0 | LDA $0572,Y
$D4A3 | b15 file $01F4B3 | SEC
$D4A4 | b15 file $01F4B4 | SBC #$0c
$D4A6 | b15 file $01F4B6 | STA $0572,Y
$D4A9 | b15 file $01F4B9 | RTS
$D506 | b15 file $01F516 | LDA #$00
$D508 | b15 file $01F518 | STA $057e
$D50B | b15 file $01F51B | LDA $0545
$D50E | b15 file $01F51E | PHA
$D50F | b15 file $01F51F | LDY $0545
$D512 | b15 file $01F522 | LDA $05c2,Y
$D515 | b15 file $01F525 | AND #$0f
$D517 | b15 file $01F527 | CMP #$02
$D519 | b15 file $01F529 | BNE $d51e
$D51B | b15 file $01F52B | JSR $d558
$D51E | b15 file $01F52E | INC $0545
$D521 | b15 file $01F531 | LDA $0545
$D524 | b15 file $01F534 | CMP #$0b
$D526 | b15 file $01F536 | BEQ $d52c
$D528 | b15 file $01F538 | CMP #$16
$D52A | b15 file $01F53A | BNE $d50f
$D52C | b15 file $01F53C | PLA
$D52D | b15 file $01F53D | STA $0545
$D530 | b15 file $01F540 | LDY $057e
$D533 | b15 file $01F543 | LDA $d594,Y
$D536 | b15 file $01F546 | BEQ $d545
$D538 | b15 file $01F548 | STA $000a
$D53B | b15 file $01F54B | LDA #$64
$D53D | b15 file $01F54D | JSR $e862
$D540 | b15 file $01F550 | CMP $000a
$D543 | b15 file $01F553 | BCC $d546
$D545 | b15 file $01F555 | RTS
$D546 | b15 file $01F556 | JSR $b084
$D549 | b15 file $01F559 | LDY $057c
$D54C | b15 file $01F55C | LDA $0572,Y
$D54F | b15 file $01F55F | SEC
$D550 | b15 file $01F560 | SBC #$0a
$D552 | b15 file $01F562 | STA $0572,Y
$D555 | b15 file $01F565 | PLA
$D556 | b15 file $01F566 | PLA
$D557 | b15 file $01F567 | RTS
$D558 | b15 file $01F568 | LDA #$00
$D55A | b15 file $01F56A | PHA
$D55B | b15 file $01F56B | TAY
$D55C | b15 file $01F56C | LDA $d57c,Y
$D55F | b15 file $01F56F | STA $0000
$D562 | b15 file $01F572 | LDA $d588,Y
$D565 | b15 file $01F575 | STA $0001
$D568 | b15 file $01F578 | JSR $c1cd
$D56B | b15 file $01F57B | BCS $d573
$D56D | b15 file $01F57D | TAY
$D56E | b15 file $01F57E | BEQ $d573
$D570 | b15 file $01F580 | INC $057e
$D573 | b15 file $01F583 | PLA
$D574 | b15 file $01F584 | CLC
$D575 | b15 file $01F585 | ADC #$01
$D577 | b15 file $01F587 | CMP #$09
$D579 | b15 file $01F589 | BCC $d55a
$D57B | b15 file $01F58B | RTS
$D5A0 | b15 file $01F5B0 | LDA #$64
$D5A2 | b15 file $01F5B2 | JSR $e862
$D5A5 | b15 file $01F5B5 | CMP #$14
$D5A7 | b15 file $01F5B7 | BCC $d5aa
$D5A9 | b15 file $01F5B9 | RTS
$D5AA | b15 file $01F5BA | JSR $b036
$D5AD | b15 file $01F5BD | LDY $057c
$D5B0 | b15 file $01F5C0 | LDA $0572,Y
$D5B3 | b15 file $01F5C3 | SEC
$D5B4 | b15 file $01F5C4 | SBC #$08
$D5B6 | b15 file $01F5C6 | STA $0572,Y
$D5B9 | b15 file $01F5C9 | PLA
$D5BA | b15 file $01F5CA | PLA
$D5BB | b15 file $01F5CB | RTS
$D5BC | b15 file $01F5CC | JSR $d5f3
$D5BF | b15 file $01F5CF | LDY $0000
$D5C2 | b15 file $01F5D2 | BEQ $d5d4
$D5C4 | b15 file $01F5D4 | LDA $d5e7,Y
$D5C7 | b15 file $01F5D7 | STA $000a
$D5CA | b15 file $01F5DA | LDA #$64
$D5CC | b15 file $01F5DC | JSR $e862
$D5CF | b15 file $01F5DF | CMP $000a
$D5D2 | b15 file $01F5E2 | BCC $d5d5
$D5D4 | b15 file $01F5E4 | RTS
$D5D5 | b15 file $01F5E5 | JSR $b016
$D5D8 | b15 file $01F5E8 | LDY $057c
$D5DB | b15 file $01F5EB | LDA $0572,Y
$D5DE | b15 file $01F5EE | SEC
$D5DF | b15 file $01F5EF | SBC #$07
$D5E1 | b15 file $01F5F1 | STA $0572,Y
$D5E4 | b15 file $01F5F4 | PLA
$D5E5 | b15 file $01F5F5 | PLA
$D5E6 | b15 file $01F5F6 | RTS
$D5F3 | b15 file $01F603 | LDY $0545
$D5F6 | b15 file $01F606 | LDX #$00
$D5F8 | b15 file $01F608 | STX $0000
$D5FB | b15 file $01F60B | LDA $05c2,Y
$D5FE | b15 file $01F60E | CMP #$ff
$D600 | b15 file $01F610 | BEQ $d60b
$D602 | b15 file $01F612 | AND #$0f
$D604 | b15 file $01F614 | CMP #$02
$D606 | b15 file $01F616 | BNE $d60b
$D608 | b15 file $01F618 | INC $0000
$D60B | b15 file $01F61B | INY
$D60C | b15 file $01F61C | INX
$D60D | b15 file $01F61D | CPX #$0b
$D60F | b15 file $01F61F | BCC $d5fb
$D611 | b15 file $01F621 | RTS
$D612 | b15 file $01F622 | LDA $0545
$D615 | b15 file $01F625 | PHA
$D616 | b15 file $01F626 | LDA $057c
$D619 | b15 file $01F629 | EOR #$01
$D61B | b15 file $01F62B | STA $0545
$D61E | b15 file $01F62E | JSR $d32a
$D621 | b15 file $01F631 | PLA
$D622 | b15 file $01F632 | STA $0545
$D625 | b15 file $01F635 | TYA
$D626 | b15 file $01F636 | BNE $d631
$D628 | b15 file $01F638 | LDA #$64
$D62A | b15 file $01F63A | JSR $e862
$D62D | b15 file $01F63D | CMP #$32
$D62F | b15 file $01F63F | BCC $d632
$D631 | b15 file $01F641 | RTS
$D632 | b15 file $01F642 | LDY $057c
$D635 | b15 file $01F645 | LDA $0572,Y
$D638 | b15 file $01F648 | SEC
$D639 | b15 file $01F649 | SBC #$03
$D63B | b15 file $01F64B | STA $0572,Y
$D63E | b15 file $01F64E | JSR $e87a
$D641 | b15 file $01F651 | AND #$01
$D643 | b15 file $01F653 | BNE $d631
$D645 | b15 file $01F655 | PLA
$D646 | b15 file $01F656 | PLA
$D647 | b15 file $01F657 | LDA #$0a
$D649 | b15 file $01F659 | STA $0540
$D64C | b15 file $01F65C | LDA #$00
$D64E | b15 file $01F65E | STA $0541
$D651 | b15 file $01F661 | RTS
$D652 | b15 file $01F662 | LDA $0570
$D655 | b15 file $01F665 | STA $000a
$D658 | b15 file $01F668 | LDA $0571
$D65B | b15 file $01F66B | STA $000b
$D65E | b15 file $01F66E | LDA $05ac
$D661 | b15 file $01F671 | STA $000c
$D664 | b15 file $01F674 | LDA $05b7
$D667 | b15 file $01F677 | STA $000d
$D66A | b15 file $01F67A | LDA $0545
$D66D | b15 file $01F67D | BEQ $d687
$D66F | b15 file $01F67F | LDX $000a
$D672 | b15 file $01F682 | LDA $000b
$D675 | b15 file $01F685 | STA $000a
$D678 | b15 file $01F688 | STX $000b
$D67B | b15 file $01F68B | LDX $000c
$D67E | b15 file $01F68E | LDA $000d
$D681 | b15 file $01F691 | STA $000c
$D684 | b15 file $01F694 | STX $000d
$D687 | b15 file $01F697 | LDA $000a
$D68A | b15 file $01F69A | CMP $000b
$D68D | b15 file $01F69D | BCC $d697
$D68F | b15 file $01F69F | LDA $000c
$D692 | b15 file $01F6A2 | CMP $000d
$D695 | b15 file $01F6A5 | BCS $d698
$D697 | b15 file $01F6A7 | RTS
$D698 | b15 file $01F6A8 | LDA #$64
$D69A | b15 file $01F6AA | JSR $e862
$D69D | b15 file $01F6AD | CMP #$28
$D69F | b15 file $01F6AF | BCS $d697
$D6A1 | b15 file $01F6B1 | PLA
$D6A2 | b15 file $01F6B2 | PLA
$D6A3 | b15 file $01F6B3 | LDA #$0a
$D6A5 | b15 file $01F6B5 | STA $0540
$D6A8 | b15 file $01F6B8 | LDA #$04
$D6AA | b15 file $01F6BA | STA $0541
$D6AD | b15 file $01F6BD | LDY $057c
$D6B0 | b15 file $01F6C0 | LDA $0572,Y
$D6B3 | b15 file $01F6C3 | SEC
$D6B4 | b15 file $01F6C4 | SBC #$05
$D6B6 | b15 file $01F6C6 | STA $0572,Y
$D6B9 | b15 file $01F6C9 | RTS
$D6BA | b15 file $01F6CA | LDA $0541
$D6BD | b15 file $01F6CD | JSR $eade ; inline targets: $D6CC,$D6DD,$D72A,$D72A,$D743,$D77F
$D6CC | b15 file $01F6DC | INC $0541
$D6CF | b15 file $01F6DF | LDA #$00
$D6D1 | b15 file $01F6E1 | STA $0548
$D6D4 | b15 file $01F6E4 | LDA #$7b
$D6D6 | b15 file $01F6E6 | JSR $f26d
$D6D9 | b15 file $01F6E9 | JSR $aff6
$D6DC | b15 file $01F6EC | RTS
$D6DD | b15 file $01F6ED | LDA $057c
$D6E0 | b15 file $01F6F0 | PHA
$D6E1 | b15 file $01F6F1 | EOR #$01
$D6E3 | b15 file $01F6F3 | STA $057c
$D6E6 | b15 file $01F6F6 | JSR $d72b
$D6E9 | b15 file $01F6F9 | PLA
$D6EA | b15 file $01F6FA | STA $057c
$D6ED | b15 file $01F6FD | JSR $cd22
$D6F0 | b15 file $01F700 | JSR $b870
$D6F3 | b15 file $01F703 | BCC $d72a
$D6F5 | b15 file $01F705 | LDA $0001
$D6F8 | b15 file $01F708 | AND #$01
$D6FA | b15 file $01F70A | BEQ $d72a
$D6FC | b15 file $01F70C | LDA #$03
$D6FE | b15 file $01F70E | STA $0540
$D701 | b15 file $01F711 | LDA #$03
$D703 | b15 file $01F713 | STA $0541
$D706 | b15 file $01F716 | LDA #$00
$D708 | b15 file $01F718 | STA $0545
$D70B | b15 file $01F71B | STA $0546
$D70E | b15 file $01F71E | LDA #$01
$D710 | b15 file $01F720 | STA $054b
$D713 | b15 file $01F723 | LDA #$01
$D715 | b15 file $01F725 | STA $054c
$D718 | b15 file $01F728 | LDA #$e8
$D71A | b15 file $01F72A | STA $0310
$D71D | b15 file $01F72D | LDA #$e9
$D71F | b15 file $01F72F | STA $0311
$D722 | b15 file $01F732 | LDA #$00
$D724 | b15 file $01F734 | STA $0300
$D727 | b15 file $01F737 | JSR $cbf1
$D72A | b15 file $01F73A | RTS
$D72B | b15 file $01F73B | LDY $057c
$D72E | b15 file $01F73E | LDA $0560,Y
$D731 | b15 file $01F741 | STA $0000
$D734 | b15 file $01F744 | LDA #$a5
$D736 | b15 file $01F746 | STA $000a
$D739 | b15 file $01F749 | LDX #$00
$D73B | b15 file $01F74B | LDY #$39
$D73D | b15 file $01F74D | JSR $ee07 ; inline far target $A000
$D742 | b15 file $01F752 | RTS
$D743 | b15 file $01F753 | INC $0541
$D746 | b15 file $01F756 | LDA #$00
$D748 | b15 file $01F758 | STA $0548
$D74B | b15 file $01F75B | LDA #$7c
$D74D | b15 file $01F75D | JSR $f26d
$D750 | b15 file $01F760 | LDY $057c
$D753 | b15 file $01F763 | LDA $0560,Y
$D756 | b15 file $01F766 | STA $042c
$D759 | b15 file $01F769 | LDA #$09
$D75B | b15 file $01F76B | STA $00bb
$D75E | b15 file $01F76E | LDA $057c
$D761 | b15 file $01F771 | EOR #$01
$D763 | b15 file $01F773 | TAY
$D764 | b15 file $01F774 | LDA $0560,Y
$D767 | b15 file $01F777 | STA $0000
$D76A | b15 file $01F77A | LDA #$00
$D76C | b15 file $01F77C | STA $0001
$D76F | b15 file $01F77F | LDY #$3d
$D771 | b15 file $01F781 | JSR $ee07 ; inline far target $A03C
$D776 | b15 file $01F786 | LDA #$00
$D778 | b15 file $01F788 | STA $0424
$D77B | b15 file $01F78B | STA $0425
$D77E | b15 file $01F78E | RTS
$D77F | b15 file $01F78F | LDA $057c
$D782 | b15 file $01F792 | PHA
$D783 | b15 file $01F793 | EOR #$01
$D785 | b15 file $01F795 | STA $057c
$D788 | b15 file $01F798 | JSR $d72b
$D78B | b15 file $01F79B | PLA
$D78C | b15 file $01F79C | STA $057c
$D78F | b15 file $01F79F | LDA $0081
$D792 | b15 file $01F7A2 | PHA
$D793 | b15 file $01F7A3 | JSR $cd22
$D796 | b15 file $01F7A6 | LDA $0001
$D799 | b15 file $01F7A9 | STA $0081
$D79C | b15 file $01F7AC | LDA #$ee
$D79E | b15 file $01F7AE | STA $0010
$D7A1 | b15 file $01F7B1 | LDA #$d7
$D7A3 | b15 file $01F7B3 | STA $0011
$D7A6 | b15 file $01F7B6 | LDA #$00
$D7A8 | b15 file $01F7B8 | STA $0012
$D7AB | b15 file $01F7BB | JSR $ed1e
$D7AE | b15 file $01F7BE | PLA
$D7AF | b15 file $01F7BF | STA $0081
$D7B2 | b15 file $01F7C2 | LDA #$f2
$D7B4 | b15 file $01F7C4 | STA $0010
$D7B7 | b15 file $01F7C7 | LDA #$d7
$D7B9 | b15 file $01F7C9 | STA $0011
$D7BC | b15 file $01F7CC | LDA #$f6
$D7BE | b15 file $01F7CE | STA $0000
$D7C1 | b15 file $01F7D1 | LDA #$d7
$D7C3 | b15 file $01F7D3 | STA $0001
$D7C6 | b15 file $01F7D6 | LDA $0012
$D7C9 | b15 file $01F7D9 | JSR $edf5
$D7CC | b15 file $01F7DC | JSR $b870
$D7CF | b15 file $01F7DF | BCC $d7ed
$D7D1 | b15 file $01F7E1 | JSR $cd22
$D7D4 | b15 file $01F7E4 | LDA $0001
$D7D7 | b15 file $01F7E7 | AND #$01
$D7D9 | b15 file $01F7E9 | BEQ $d7ed
$D7DB | b15 file $01F7EB | LDA $0012
$D7DE | b15 file $01F7EE | BEQ $d7e3
$D7E0 | b15 file $01F7F0 | JMP $d6fc
$D7E3 | b15 file $01F7F3 | LDA #$05
$D7E5 | b15 file $01F7F5 | STA $0540
$D7E8 | b15 file $01F7F8 | LDA #$00
$D7EA | b15 file $01F7FA | STA $0541
$D7ED | b15 file $01F7FD | RTS
$D7FB | b15 file $01F80B | LDA $000a
$D7FE | b15 file $01F80E | JSR $f2d7
$D801 | b15 file $01F811 | LSR $000c
$D804 | b15 file $01F814 | ROR $000b
$D807 | b15 file $01F817 | LDY #$06
$D809 | b15 file $01F819 | LDA ($00),Y
$D80B | b15 file $01F81B | CLC
$D80C | b15 file $01F81C | ADC $000b
$D80F | b15 file $01F81F | STA $000d
$D812 | b15 file $01F822 | STA ($00),Y
$D814 | b15 file $01F824 | INY
$D815 | b15 file $01F825 | LDA ($00),Y
$D817 | b15 file $01F827 | ADC $000c
$D81A | b15 file $01F82A | STA $000e
$D81D | b15 file $01F82D | STA ($00),Y
$D81F | b15 file $01F82F | LDY #$06
$D821 | b15 file $01F831 | LDA ($00),Y
$D823 | b15 file $01F833 | SEC
$D824 | b15 file $01F834 | SBC #$4f
$D826 | b15 file $01F836 | INY
$D827 | b15 file $01F837 | LDA ($00),Y
$D829 | b15 file $01F839 | SBC #$c3
$D82B | b15 file $01F83B | BCC $d838
$D82D | b15 file $01F83D | LDY #$06
$D82F | b15 file $01F83F | LDA #$4f
$D831 | b15 file $01F841 | STA ($00),Y
$D833 | b15 file $01F843 | INY
$D834 | b15 file $01F844 | LDA #$c3
$D836 | b15 file $01F846 | STA ($00),Y
$D838 | b15 file $01F848 | LDY #$0b
$D83A | b15 file $01F84A | LDA ($00),Y
$D83C | b15 file $01F84C | AND #$f0
$D83E | b15 file $01F84E | LSR A
$D83F | b15 file $01F84F | LSR A
$D840 | b15 file $01F850 | LSR A
$D841 | b15 file $01F851 | CMP #$0e
$D843 | b15 file $01F853 | BCS $d855
$D845 | b15 file $01F855 | TAY
$D846 | b15 file $01F856 | LDA $000d
$D849 | b15 file $01F859 | SEC
$D84A | b15 file $01F85A | SBC $d85b,Y
$D84D | b15 file $01F85D | LDA $000e
$D850 | b15 file $01F860 | SBC $d85c,Y
$D853 | b15 file $01F863 | BCS $d869
$D855 | b15 file $01F865 | LDA #$00
$D857 | b15 file $01F867 | STA $000f
$D85A | b15 file $01F86A | RTS
$D869 | b15 file $01F879 | TYA
$D86A | b15 file $01F87A | LSR A
$D86B | b15 file $01F87B | CLC
$D86C | b15 file $01F87C | ADC #$01
$D86E | b15 file $01F87E | ASL A
$D86F | b15 file $01F87F | ASL A
$D870 | b15 file $01F880 | ASL A
$D871 | b15 file $01F881 | ASL A
$D872 | b15 file $01F882 | STA $000f
$D875 | b15 file $01F885 | LDY #$0b
$D877 | b15 file $01F887 | LDA ($00),Y
$D879 | b15 file $01F889 | AND #$f0
$D87B | b15 file $01F88B | CMP $000f
$D87E | b15 file $01F88E | BCS $d855
$D880 | b15 file $01F890 | LDY #$0b
$D882 | b15 file $01F892 | LDA ($00),Y
$D884 | b15 file $01F894 | AND #$0f
$D886 | b15 file $01F896 | ORA $000f
$D889 | b15 file $01F899 | STA ($00),Y
$D88B | b15 file $01F89B | LDY #$01
$D88D | b15 file $01F89D | LDA ($00),Y
$D88F | b15 file $01F89F | LDY #$06
$D891 | b15 file $01F8A1 | CMP #$33
$D893 | b15 file $01F8A3 | BCC $d8a7
$D895 | b15 file $01F8A5 | LDY #$05
$D897 | b15 file $01F8A7 | CMP #$47
$D899 | b15 file $01F8A9 | BCC $d8a7
$D89B | b15 file $01F8AB | LDY #$04
$D89D | b15 file $01F8AD | CMP #$51
$D89F | b15 file $01F8AF | BCC $d8a7
$D8A1 | b15 file $01F8B1 | LDY #$02
$D8A3 | b15 file $01F8B3 | CMP #$5a
$D8A5 | b15 file $01F8B5 | BCS $d8af
$D8A7 | b15 file $01F8B7 | TYA
$D8A8 | b15 file $01F8B8 | LDY #$01
$D8AA | b15 file $01F8BA | CLC
$D8AB | b15 file $01F8BB | ADC ($00),Y
$D8AD | b15 file $01F8BD | STA ($00),Y
$D8AF | b15 file $01F8BF | RTS
