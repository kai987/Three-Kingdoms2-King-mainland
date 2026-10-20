
; AI_zero_branch_capture_commit, physicalbank10, file$01490C
$A8FC ad 38 00       LDA $0038
$A8FF 20 05 d1       JSR $d105
$A902 a0 00          LDY #$00
$A904 b1 20          LDA ($20),Y
$A906 29 f8          AND #$f8
$A908 0d 03 6f       ORA $6f03
$A90B 91 20          STA ($20),Y

; AI_officer_neighbor_relocation_or_release, physicalbank10, file$014BB3
$ABA3 a0 30          LDY #$30
$ABA5 20 66 f2       JSR $f266
$ABA8 ad 38 00       LDA $0038
$ABAB 0a             ASL A
$ABAC 0a             ASL A
$ABAD 0a             ASL A
$ABAE 85 2a          STA $2a
$ABB0 a9 ff          LDA #$ff
$ABB2 85 2b          STA $2b
$ABB4 85 2c          STA $2c
$ABB6 85 2d          STA $2d
$ABB8 a4 2a          LDY $2a
$ABBA b9 72 9d       LDA $9d72,Y
$ABBD 30 2f          BMI $abee
$ABBF 20 05 d1       JSR $d105
$ABC2 c9 07          CMP #$07
$ABC4 d0 0a          BNE $abd0
$ABC6 a4 2a          LDY $2a
$ABC8 b9 72 9d       LDA $9d72,Y
$ABCB 85 2d          STA $2d
$ABCD 4c e9 ab       JMP $abe9
$ABD0 cd 40 00       CMP $0040
$ABD3 d0 14          BNE $abe9
$ABD5 20 07 d3       JSR $d307
$ABD8 c9 0a          CMP #$0a
$ABDA b0 0d          BCS $abe9
$ABDC c5 2b          CMP $2b
$ABDE b0 09          BCS $abe9
$ABE0 85 2b          STA $2b
$ABE2 a4 2a          LDY $2a
$ABE4 b9 72 9d       LDA $9d72,Y
$ABE7 85 2c          STA $2c
$ABE9 e6 2a          INC $2a
$ABEB 4c b8 ab       JMP $abb8
$ABEE a5 2c          LDA $2c
$ABF0 c9 ff          CMP #$ff
$ABF2 f0 2d          BEQ $ac21
$ABF4 20 05 d1       JSR $d105
$ABF7 a0 11          LDY #$11
$ABF9 b1 20          LDA ($20),Y
$ABFB c9 ff          CMP #$ff
$ABFD f0 04          BEQ $ac03
$ABFF c8             INY
$AC00 4c f9 ab       JMP $abf9
$AC03 ad 41 00       LDA $0041
$AC06 91 20          STA ($20),Y
$AC08 a0 00          LDY #$00
$AC0A b1 20          LDA ($20),Y
$AC0C 29 f8          AND #$f8
$AC0E 0d 40 00       ORA $0040
$AC11 91 20          STA ($20),Y
$AC13 ad 42 00       LDA $0042
$AC16 d0 08          BNE $ac20
$AC18 ad 41 00       LDA $0041
$AC1B 85 20          STA $20
$AC1D 20 0c d0       JSR $d00c
$AC20 60             RTS
$AC21 a5 2d          LDA $2d
$AC23 c9 ff          CMP #$ff
$AC25 d0 cd          BNE $abf4
$AC27 ad 41 00       LDA $0041
$AC2A a0 0b          LDY #$0b
$AC2C 20 ab d2       JSR $d2ab
$AC2F 29 fc          AND #$fc
$AC31 91 22          STA ($22),Y
$AC33 20 9a e8       JSR $e89a
$AC36 29 07          AND #$07
$AC38 d0 0d          BNE $ac47
$AC3A a0 05          LDY #$05
$AC3C ad 38 00       LDA $0038
$AC3F 91 22          STA ($22),Y
$AC41 a9 ff          LDA #$ff
$AC43 8d 2d 00       STA $002d
$AC46 60             RTS
$AC47 8d 2d 00       STA $002d
$AC4A ce 2d 00       DEC $002d
$AC4D ad 38 00       LDA $0038
$AC50 0a             ASL A
$AC51 0a             ASL A
$AC52 0a             ASL A
$AC53 18             CLC
$AC54 6d 2d 00       ADC $002d
$AC57 a8             TAY
$AC58 b9 72 9d       LDA $9d72,Y
$AC5B 30 d6          BMI $ac33
$AC5D a0 05          LDY #$05
$AC5F 91 22          STA ($22),Y
$AC61 a9 ff          LDA #$ff
$AC63 8d 2d 00       STA $002d
$AC66 60             RTS

; AI_colonization_transaction, physicalbank10, file$015297
$B287 ad 3a 00       LDA $003a
$B28A 20 05 d1       JSR $d105
$B28D a0 02          LDY #$02
$B28F b1 20          LDA ($20),Y
$B291 38             SEC
$B292 ed 3d 00       SBC $003d
$B295 91 20          STA ($20),Y
$B297 c8             INY
$B298 b1 20          LDA ($20),Y
$B29A ed 3e 00       SBC $003e
$B29D 91 20          STA ($20),Y
$B29F 20 9d d6       JSR $d69d
$B2A2 a0 04          LDY #$04
$B2A4 b1 20          LDA ($20),Y
$B2A6 38             SEC
$B2A7 ed 3b 00       SBC $003b
$B2AA 91 20          STA ($20),Y
$B2AC c8             INY
$B2AD b1 20          LDA ($20),Y
$B2AF ed 3c 00       SBC $003c
$B2B2 91 20          STA ($20),Y
$B2B4 20 9d d6       JSR $d69d
$B2B7 ad 38 00       LDA $0038
$B2BA 20 05 d1       JSR $d105
$B2BD a0 02          LDY #$02
$B2BF b1 20          LDA ($20),Y
$B2C1 18             CLC
$B2C2 6d 3d 00       ADC $003d
$B2C5 91 20          STA ($20),Y
$B2C7 c8             INY
$B2C8 b1 20          LDA ($20),Y
$B2CA 6d 3e 00       ADC $003e
$B2CD 91 20          STA ($20),Y
$B2CF a0 04          LDY #$04
$B2D1 b1 20          LDA ($20),Y
$B2D3 18             CLC
$B2D4 6d 3b 00       ADC $003b
$B2D7 91 20          STA ($20),Y
$B2D9 c8             INY
$B2DA b1 20          LDA ($20),Y
$B2DC 6d 3c 00       ADC $003c
$B2DF 91 20          STA ($20),Y
$B2E1 ad 38 00       LDA $0038
$B2E4 20 05 d1       JSR $d105
$B2E7 a5 20          LDA $20
$B2E9 85 28          STA $28
$B2EB a5 21          LDA $21
$B2ED 85 29          STA $29
$B2EF ad 3a 00       LDA $003a
$B2F2 20 05 d1       JSR $d105
$B2F5 ce 37 00       DEC $0037
$B2F8 ce 37 00       DEC $0037
$B2FB a9 00          LDA #$00
$B2FD 85 2a          STA $2a
$B2FF a9 12          LDA #$12
$B301 85 2b          STA $2b
$B303 a9 00          LDA #$00
$B305 85 2c          STA $2c
$B307 a9 ff          LDA #$ff
$B309 85 2d          STA $2d
$B30B a4 2b          LDY $2b
$B30D b1 20          LDA ($20),Y
$B30F c9 ff          CMP #$ff
$B311 f0 0f          BEQ $b322
$B313 a0 03          LDY #$03
$B315 20 ab d2       JSR $d2ab
$B318 c5 2c          CMP $2c
$B31A 90 06          BCC $b322
$B31C 85 2c          STA $2c
$B31E a5 2b          LDA $2b
$B320 85 2d          STA $2d
$B322 e6 2b          INC $2b
$B324 a5 2b          LDA $2b
$B326 c9 1b          CMP #$1b
$B328 90 e1          BCC $b30b
$B32A a4 2d          LDY $2d
$B32C b1 20          LDA ($20),Y
$B32E 48             PHA
$B32F a9 ff          LDA #$ff
$B331 91 20          STA ($20),Y
$B333 a5 2a          LDA $2a
$B335 18             CLC
$B336 69 11          ADC #$11
$B338 a8             TAY
$B339 68             PLA
$B33A 91 28          STA ($28),Y
$B33C e6 2a          INC $2a
$B33E a4 2a          LDY $2a
$B340 cc 37 00       CPY $0037
$B343 90 ba          BCC $b2ff
$B345 ad 3a 00       LDA $003a
$B348 20 dd d3       JSR $d3dd
$B34B a0 00          LDY #$00
$B34D b1 28          LDA ($28),Y
$B34F 29 f8          AND #$f8
$B351 0d 03 6f       ORA $6f03
$B354 91 28          STA ($28),Y
$B356 60             RTS

; AI_withdrawal_transaction, physicalbank10, file$0153C1
$B3B1 20 05 d1       JSR $d105
$B3B4 a5 20          LDA $20
$B3B6 85 22          STA $22
$B3B8 a5 21          LDA $21
$B3BA 85 23          STA $23
$B3BC ad 37 00       LDA $0037
$B3BF 20 05 d1       JSR $d105
$B3C2 a0 02          LDY #$02
$B3C4 b1 20          LDA ($20),Y
$B3C6 18             CLC
$B3C7 71 22          ADC ($22),Y
$B3C9 91 22          STA ($22),Y
$B3CB c8             INY
$B3CC b1 20          LDA ($20),Y
$B3CE 71 22          ADC ($22),Y
$B3D0 91 22          STA ($22),Y
$B3D2 a0 04          LDY #$04
$B3D4 b1 20          LDA ($20),Y
$B3D6 18             CLC
$B3D7 71 22          ADC ($22),Y
$B3D9 91 22          STA ($22),Y
$B3DB c8             INY
$B3DC b1 20          LDA ($20),Y
$B3DE 71 22          ADC ($22),Y
$B3E0 91 22          STA ($22),Y
$B3E2 a0 02          LDY #$02
$B3E4 a9 00          LDA #$00
$B3E6 91 20          STA ($20),Y
$B3E8 c8             INY
$B3E9 91 20          STA ($20),Y
$B3EB c8             INY
$B3EC 91 20          STA ($20),Y
$B3EE c8             INY
$B3EF 91 20          STA ($20),Y
$B3F1 a0 11          LDY #$11
$B3F3 84 24          STY $24
$B3F5 84 25          STY $25
$B3F7 a0 04          LDY #$04
$B3F9 84 26          STY $26
$B3FB a4 24          LDY $24
$B3FD b1 20          LDA ($20),Y
$B3FF c9 ff          CMP #$ff
$B401 f0 1e          BEQ $b421
$B403 48             PHA
$B404 a9 ff          LDA #$ff
$B406 91 20          STA ($20),Y
$B408 a4 25          LDY $25
$B40A e6 25          INC $25
$B40C b1 22          LDA ($22),Y
$B40E c9 ff          CMP #$ff
$B410 d0 f6          BNE $b408
$B412 68             PLA
$B413 91 22          STA ($22),Y
$B415 e6 26          INC $26
$B417 e6 26          INC $26
$B419 e6 24          INC $24
$B41B a4 24          LDY $24
$B41D c0 1b          CPY #$1b
$B41F 90 da          BCC $b3fb
$B421 a0 00          LDY #$00
$B423 b1 20          LDA ($20),Y
$B425 29 f8          AND #$f8
$B427 09 07          ORA #$07
$B429 91 20          STA ($20),Y

; AI_persuasion_membership_transaction, physicalbank10, file$015A9D
$BA8D ad 38 00       LDA $0038
$BA90 20 05 d1       JSR $d105
$BA93 a0 10          LDY #$10
$BA95 c8             INY
$BA96 b1 20          LDA ($20),Y
$BA98 c9 ff          CMP #$ff
$BA9A d0 f9          BNE $ba95
$BA9C ad 3d 00       LDA $003d
$BA9F 91 20          STA ($20),Y
$BAA1 ad 03 6f       LDA $6f03
$BAA4 20 19 d3       JSR $d319
$BAA7 a0 00          LDY #$00
$BAA9 b1 24          LDA ($24),Y
$BAAB 85 30          STA $30
$BAAD ad 3d 00       LDA $003d
$BAB0 85 31          STA $31
$BAB2 20 3f cf       JSR $cf3f
$BAB5 ad 3f 00       LDA $003f
$BAB8 20 05 d1       JSR $d105
$BABB 8d 42 00       STA $0042
$BABE a0 10          LDY #$10
$BAC0 c8             INY
$BAC1 b1 20          LDA ($20),Y
$BAC3 cd 3d 00       CMP $003d
$BAC6 d0 f8          BNE $bac0
$BAC8 a9 ff          LDA #$ff
$BACA 91 20          STA ($20),Y
$BACC ad 3f 00       LDA $003f
$BACF 20 dd d3       JSR $d3dd
$BAD2 ad 3f 00       LDA $003f
$BAD5 20 04 d3       JSR $d304
$BAD8 c9 00          CMP #$00
$BADA d0 06          BNE $bae2
$BADC a0 00          LDY #$00
$BADE a9 07          LDA #$07
$BAE0 91 20          STA ($20),Y

; city_action_mode2_empty_firstslot_check, physicalbank28, file$03917B
$D16B c9 02          CMP #$02
$D16D d0 14          BNE $d183
$D16F ad 71 04       LDA $0471
$D172 20 af f2       JSR $f2af
$D175 a0 11          LDY #$11
$D177 b1 00          LDA ($00),Y
$D179 c9 ff          CMP #$ff
$D17B d0 06          BNE $d183
$D17D a0 00          LDY #$00
$D17F a9 07          LDA #$07
$D181 91 00          STA ($00),Y

; unit_retreat_roster_cache_owner_body, physicalbank12, file$019C3D
$BC2D 20 11 bc       JSR $bc11
$BC30 ae 09 05       LDX $0509
$BC33 f0 04          BEQ $bc39
$BC35 e0 0a          CPX #$0a
$BC37 d0 0c          BNE $bc45
$BC39 bd 64 06       LDA $0664,X
$BC3C 8d 2b 05       STA $052b
$BC3F ad 0b 05       LDA $050b
$BC42 8d 2c 05       STA $052c
$BC45 bd 64 06       LDA $0664,X
$BC48 91 00          STA ($00),Y
$BC4A a9 ff          LDA #$ff
$BC4C 9d 00 06       STA $0600,X
$BC4F 9d 14 06       STA $0614,X
$BC52 9d 28 06       STA $0628,X
$BC55 9d 3c 06       STA $063c,X
$BC58 9d 50 06       STA $0650,X
$BC5B 9d 64 06       STA $0664,X
$BC5E ec d8 04       CPX $04d8
$BC61 d0 03          BNE $bc66
$BC63 8d d8 04       STA $04d8
$BC66 ec dc 04       CPX $04dc
$BC69 d0 03          BNE $bc6e
$BC6B 8d dc 04       STA $04dc
$BC6E a0 00          LDY #$00
$BC70 b1 00          LDA ($00),Y
$BC72 29 07          AND #$07
$BC74 c9 07          CMP #$07
$BC76 d0 1a          BNE $bc92
$BC78 ad 07 05       LDA $0507
$BC7B ac 04 05       LDY $0504
$BC7E 10 04          BPL $bc84
$BC80 4a             LSR A
$BC81 4a             LSR A
$BC82 4a             LSR A
$BC83 4a             LSR A
$BC84 29 0f          AND #$0f
$BC86 85 02          STA $02
$BC88 a0 00          LDY #$00
$BC8A b1 00          LDA ($00),Y
$BC8C 29 f0          AND #$f0
$BC8E 05 02          ORA $02
$BC90 91 00          STA ($00),Y
$BC92 60             RTS

; existing_finalizer_owner_and_chiefs, physicalbank8, file$011BC8
$BBB8 a0 30          LDY #$30
$BBBA 20 5f f2       JSR $f25f
$BBBD ad 0e 05       LDA $050e
$BBC0 20 af f2       JSR $f2af
$BBC3 ad 14 05       LDA $0514
$BBC6 d0 17          BNE $bbdf
$BBC8 ad 07 05       LDA $0507
$BBCB 4a             LSR A
$BBCC 4a             LSR A
$BBCD 4a             LSR A
$BBCE 4a             LSR A
$BBCF 29 0f          AND #$0f
$BBD1 8d 02 00       STA $0002
$BBD4 a0 00          LDY #$00
$BBD6 b1 00          LDA ($00),Y
$BBD8 29 f0          AND #$f0
$BBDA 0d 02 00       ORA $0002
$BBDD 91 00          STA ($00),Y
$BBDF 20 00 bc       JSR $bc00
$BBE2 ad 0e 05       LDA $050e
$BBE5 0a             ASL A
$BBE6 0a             ASL A
$BBE7 0a             ASL A
$BBE8 a8             TAY
$BBE9 98             TYA
$BBEA 48             PHA
$BBEB b9 72 9d       LDA $9d72,Y
$BBEE c9 ff          CMP #$ff
$BBF0 d0 02          BNE $bbf4
$BBF2 68             PLA
$BBF3 60             RTS
$BBF4 20 af f2       JSR $f2af
$BBF7 20 00 bc       JSR $bc00
$BBFA 68             PLA
$BBFB a8             TAY
$BBFC c8             INY
$BBFD 4c e9 bb       JMP $bbe9
$BC00 ad 00 00       LDA $0000
$BC03 8d 0a 00       STA $000a
$BC06 ad 01 00       LDA $0001
$BC09 8d 0b 00       STA $000b
$BC0C a0 00          LDY #$00
$BC0E b1 0a          LDA ($0a),Y
$BC10 29 0f          AND #$0f
$BC12 c9 07          CMP #$07
$BC14 d0 01          BNE $bc17
$BC16 60             RTS
$BC17 20 68 f3       JSR $f368
$BC1A a0 00          LDY #$00
$BC1C b1 00          LDA ($00),Y
$BC1E 8d 02 00       STA $0002
$BC21 a0 11          LDY #$11
$BC23 b1 0a          LDA ($0a),Y
$BC25 cd 02 00       CMP $0002
$BC28 f0 06          BEQ $bc30
$BC2A c8             INY
$BC2B c0 1b          CPY #$1b
$BC2D 90 f4          BCC $bc23
$BC2F 60             RTS
$BC30 98             TYA
$BC31 48             PHA
$BC32 a0 11          LDY #$11
$BC34 b1 0a          LDA ($0a),Y
$BC36 8d 03 00       STA $0003
$BC39 ad 02 00       LDA $0002
$BC3C 91 0a          STA ($0a),Y
$BC3E 68             PLA
$BC3F a8             TAY
$BC40 ad 03 00       LDA $0003
$BC43 91 0a          STA ($0a),Y
$BC45 60             RTS
