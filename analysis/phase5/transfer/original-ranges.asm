
; pair10_entry_trampolines; bank10, ROM$014010, byteSHA256745e72093840a08c3316a18c6feb895183ff3c3ee11dcef132ae66a5669125f0
$A000 4c 0f a0          JMP $a00f
$A003 4c 17 d7          JMP $d717
$A006 4c 3f cf          JMP $cf3f
$A009 4c 7c cf          JMP $cf7c
$A00C 4c 0c d0          JMP $d00c

; all_city_chiefs; bank11, ROM$01699F, byteSHA2568e32c1514b1c17eb923141141abe76b461c0e1c3e339c8993afa44e0735fe1b5
$C98F 8d 37 00          STA $0037
$C992 a9 00             LDA #$00
$C994 8d 36 00          STA $0036
$C997 20 a5 c9          JSR $c9a5
$C99A ee 36 00          INC $0036
$C99D ad 36 00          LDA $0036
$C9A0 c9 1e             CMP #$1e
$C9A2 90 f3             BCC $c997
$C9A4 60                RTS
$C9A5 ad 36 00          LDA $0036
$C9A8 20 05 d1          JSR $d105
$C9AB 29 07             AND #$07
$C9AD cd 37 00          CMP $0037
$C9B0 d0 f2             BNE $c9a4
$C9B2 a9 11             LDA #$11
$C9B4 8d 3a 00          STA $003a
$C9B7 a9 00             LDA #$00
$C9B9 8d 3b 00          STA $003b
$C9BC a9 ff             LDA #$ff
$C9BE 8d 3c 00          STA $003c
$C9C1 ac 3a 00          LDY $003a
$C9C4 b1 20             LDA ($20),Y
$C9C6 c9 ff             CMP #$ff
$C9C8 f0 25             BEQ $c9ef
$C9CA a0 03             LDY #$03
$C9CC 20 ab d2          JSR $d2ab
$C9CF c9 64             CMP #$64
$C9D1 d0 09             BNE $c9dc
$C9D3 ad 3a 00          LDA $003a
$C9D6 8d 3c 00          STA $003c
$C9D9 4c f9 c9          JMP $c9f9
$C9DC a0 04             LDY #$04
$C9DE 18                CLC
$C9DF 71 22             ADC ($22),Y
$C9E1 cd 3b 00          CMP $003b
$C9E4 90 09             BCC $c9ef
$C9E6 8d 3b 00          STA $003b
$C9E9 ad 3a 00          LDA $003a
$C9EC 8d 3c 00          STA $003c
$C9EF ee 3a 00          INC $003a
$C9F2 ad 3a 00          LDA $003a
$C9F5 c9 1b             CMP #$1b
$C9F7 90 c8             BCC $c9c1
$C9F9 ad 3c 00          LDA $003c
$C9FC c9 ff             CMP #$ff
$C9FE f0 18             BEQ $ca18
$CA00 c9 11             CMP #$11
$CA02 f0 14             BEQ $ca18
$CA04 a0 11             LDY #$11
$CA06 b1 20             LDA ($20),Y
$CA08 48                PHA
$CA09 ac 3c 00          LDY $003c
$CA0C b1 20             LDA ($20),Y
$CA0E a0 11             LDY #$11
$CA10 91 20             STA ($20),Y
$CA12 68                PLA
$CA13 ac 3c 00          LDY $003c
$CA16 91 20             STA ($20),Y
$CA18 60                RTS

; AI_leader_death_and_family_selection; bank11, ROM$016A29, byteSHA25660aa091adf63b5741e533ba028a9b3236f86bdb678ffebd18928938d8200f443
$CA19 a9 00             LDA #$00
$CA1B 8d 40 00          STA $0040
$CA1E ad 40 00          LDA $0040
$CA21 20 19 d3          JSR $d319
$CA24 a0 00             LDY #$00
$CA26 b1 24             LDA ($24),Y
$CA28 c9 ff             CMP #$ff
$CA2A f0 2c             BEQ $ca58
$CA2C 8d 38 00          STA $0038
$CA2F a0 03             LDY #$03
$CA31 b1 24             LDA ($24),Y
$CA33 c9 03             CMP #$03
$CA35 d0 21             BNE $ca58
$CA37 ad 38 00          LDA $0038
$CA3A a0 0b             LDY #$0b
$CA3C 20 ab d2          JSR $d2ab
$CA3F 29 03             AND #$03
$CA41 c9 02             CMP #$02
$CA43 f0 0d             BEQ $ca52
$CA45 a0 0b             LDY #$0b
$CA47 b1 22             LDA ($22),Y
$CA49 29 fc             AND #$fc
$CA4B 09 03             ORA #$03
$CA4D 91 22             STA ($22),Y
$CA4F 20 68 ca          JSR $ca68
$CA52 ad 40 00          LDA $0040
$CA55 20 8f c9          JSR $c98f
$CA58 ee 40 00          INC $0040
$CA5B ad 40 00          LDA $0040
$CA5E c9 07             CMP #$07
$CA60 90 bc             BCC $ca1e
$CA62 20 49 d2          JSR $d249
$CA65 4c c7 be          JMP $bec7
$CA68 20 87 ca          JSR $ca87
$CA6B 20 05 cb          JSR $cb05
$CA6E ad 40 00          LDA $0040
$CA71 20 19 d3          JSR $d319
$CA74 a0 00             LDY #$00
$CA76 a9 ff             LDA #$ff
$CA78 91 24             STA ($24),Y
$CA7A a9 fb             LDA #$fb
$CA7C 8d 8b 6f          STA $6f8b
$CA7F ad 8b 6f          LDA $6f8b
$CA82 c9 01             CMP #$01
$CA84 d0 f9             BNE $ca7f
$CA86 60                RTS
$CA87 ad 40 00          LDA $0040
$CA8A 0a                ASL A
$CA8B a8                TAY
$CA8C b9 d8 ca          LDA $cad8,Y
$CA8F 85 24             STA $24
$CA91 b9 d9 ca          LDA $cad9,Y
$CA94 85 25             STA $25
$CA96 a9 00             LDA #$00
$CA98 85 26             STA $26
$CA9A a4 26             LDY $26
$CA9C b1 24             LDA ($24),Y
$CA9E c9 ff             CMP #$ff
$CAA0 f0 0a             BEQ $caac
$CAA2 85 27             STA $27
$CAA4 20 ad ca          JSR $caad
$CAA7 e6 26             INC $26
$CAA9 4c 9a ca          JMP $ca9a
$CAAC 60                RTS
$CAAD a9 00             LDA #$00
$CAAF 85 2a             STA $2a
$CAB1 a5 2a             LDA $2a
$CAB3 20 05 d1          JSR $d105
$CAB6 cd 40 00          CMP $0040
$CAB9 d0 0d             BNE $cac8
$CABB a0 11             LDY #$11
$CABD b1 20             LDA ($20),Y
$CABF c5 27             CMP $27
$CAC1 f0 0e             BEQ $cad1
$CAC3 c8                INY
$CAC4 c0 1b             CPY #$1b
$CAC6 90 f5             BCC $cabd
$CAC8 e6 2a             INC $2a
$CACA a5 2a             LDA $2a
$CACC c9 1e             CMP #$1e
$CACE 90 e1             BCC $cab1
$CAD0 60                RTS
$CAD1 68                PLA
$CAD2 68                PLA
$CAD3 68                PLA
$CAD4 68                PLA
$CAD5 4c 52 cb          JMP $cb52

; AI_virtue_selection_and_commit_and_followers; bank11, ROM$016B15, byteSHA2563f3513a74e809a0dda0cb1a92bdfa49e393c22ed9dbc56fdf0f110feccaae40a
$CB05 a9 00             LDA #$00
$CB07 85 2a             STA $2a
$CB09 85 2b             STA $2b
$CB0B a9 ff             LDA #$ff
$CB0D 85 27             STA $27
$CB0F a5 2a             LDA $2a
$CB11 20 05 d1          JSR $d105
$CB14 cd 40 00          CMP $0040
$CB17 d0 25             BNE $cb3e
$CB19 a0 11             LDY #$11
$CB1B 84 24             STY $24
$CB1D a4 24             LDY $24
$CB1F b1 20             LDA ($20),Y
$CB21 c9 ff             CMP #$ff
$CB23 f0 11             BEQ $cb36
$CB25 a0 04             LDY #$04
$CB27 20 ab d2          JSR $d2ab
$CB2A c5 2b             CMP $2b
$CB2C 90 08             BCC $cb36
$CB2E 85 2b             STA $2b
$CB30 a4 24             LDY $24
$CB32 b1 20             LDA ($20),Y
$CB34 85 27             STA $27
$CB36 e6 24             INC $24
$CB38 a5 24             LDA $24
$CB3A c9 1b             CMP #$1b
$CB3C 90 df             BCC $cb1d
$CB3E e6 2a             INC $2a
$CB40 a5 2a             LDA $2a
$CB42 c9 1e             CMP #$1e
$CB44 90 c9             BCC $cb0f
$CB46 a5 27             LDA $27
$CB48 c9 ff             CMP #$ff
$CB4A f0 05             BEQ $cb51
$CB4C 68                PLA
$CB4D 68                PLA
$CB4E 4c 52 cb          JMP $cb52
$CB51 60                RTS
$CB52 ad 40 00          LDA $0040
$CB55 20 19 d3          JSR $d319
$CB58 a0 00             LDY #$00
$CB5A b1 24             LDA ($24),Y
$CB5C 85 33             STA $33
$CB5E a5 27             LDA $27
$CB60 91 24             STA ($24),Y
$CB62 a0 03             LDY #$03
$CB64 20 ab d2          JSR $d2ab
$CB67 a9 64             LDA #$64
$CB69 91 22             STA ($22),Y
$CB6B a5 27             LDA $27
$CB6D 48                PHA
$CB6E 20 81 cb          JSR $cb81
$CB71 68                PLA
$CB72 85 27             STA $27
$CB74 a9 fc             LDA #$fc
$CB76 8d 8b 6f          STA $6f8b
$CB79 ad 8b 6f          LDA $6f8b
$CB7C c9 01             CMP #$01
$CB7E d0 f9             BNE $cb79
$CB80 60                RTS
$CB81 a5 27             LDA $27
$CB83 85 30             STA $30
$CB85 a9 00             LDA #$00
$CB87 8d 45 00          STA $0045
$CB8A ad 45 00          LDA $0045
$CB8D 20 05 d1          JSR $d105
$CB90 cd 40 00          CMP $0040
$CB93 d0 03             BNE $cb98
$CB95 20 a3 cb          JSR $cba3
$CB98 ee 45 00          INC $0045
$CB9B ad 45 00          LDA $0045
$CB9E c9 1e             CMP #$1e
$CBA0 90 e8             BCC $cb8a
$CBA2 60                RTS
$CBA3 a9 11             LDA #$11
$CBA5 8d 44 00          STA $0044
$CBA8 ad 45 00          LDA $0045
$CBAB 20 05 d1          JSR $d105
$CBAE ac 44 00          LDY $0044
$CBB1 b1 20             LDA ($20),Y
$CBB3 c9 ff             CMP #$ff
$CBB5 f0 e1             BEQ $cb98
$CBB7 c5 30             CMP $30
$CBB9 f0 dd             BEQ $cb98
$CBBB 85 31             STA $31
$CBBD ad 40 00          LDA $0040
$CBC0 85 32             STA $32
$CBC2 20 7c cf          JSR $cf7c
$CBC5 a5 31             LDA $31
$CBC7 a0 03             LDY #$03
$CBC9 20 ab d2          JSR $d2ab
$CBCC c9 1f             CMP #$1f
$CBCE b0 1b             BCS $cbeb
$CBD0 a9 64             LDA #$64
$CBD2 20 bb d4          JSR $d4bb
$CBD5 c9 14             CMP #$14
$CBD7 b0 12             BCS $cbeb
$CBD9 a5 31             LDA $31
$CBDB a0 0b             LDY #$0b
$CBDD 20 ab d2          JSR $d2ab
$CBE0 29 fc             AND #$fc
$CBE2 91 22             STA ($22),Y
$CBE4 a0 05             LDY #$05
$CBE6 ad 45 00          LDA $0045
$CBE9 91 22             STA ($22),Y
$CBEB ee 44 00          INC $0044
$CBEE ad 44 00          LDA $0044
$CBF1 c9 1b             CMP #$1b
$CBF3 90 b3             BCC $cba8
$CBF5 ad 45 00          LDA $0045
$CBF8 20 dd d3          JSR $d3dd
$CBFB ad 45 00          LDA $0045
$CBFE 20 04 d3          JSR $d304
$CC01 c9 00             CMP #$00
$CC03 d0 0c             BNE $cc11
$CC05 ad 45 00          LDA $0045
$CC08 20 05 d1          JSR $d105
$CC0B a0 00             LDY #$00
$CC0D a9 07             LDA #$07
$CC0F 91 20             STA ($20),Y
$CC11 60                RTS

; recruitment_loyalty_only; bank11, ROM$016F4F, byteSHA2565a74e24c8a2d928aac4ba645997d00ce32cee9f845e683c0068781f63bb17b49
$CF3F a5 30             LDA $30
$CF41 a0 04             LDY #$04
$CF43 20 ab d2          JSR $d2ab
$CF46 85 21             STA $21
$CF48 a9 0a             LDA #$0a
$CF4A 85 23             STA $23
$CF4C a9 00             LDA #$00
$CF4E 85 22             STA $22
$CF50 85 24             STA $24
$CF52 20 0f d4          JSR $d40f
$CF55 a5 21             LDA $21
$CF57 18                CLC
$CF58 69 46             ADC #$46
$CF5A 48                PHA
$CF5B a5 31             LDA $31
$CF5D a0 03             LDY #$03
$CF5F 20 ab d2          JSR $d2ab
$CF62 85 20             STA $20
$CF64 68                PLA
$CF65 38                SEC
$CF66 e5 20             SBC $20
$CF68 c9 5a             CMP #$5a
$CF6A 90 02             BCC $cf6e
$CF6C a9 5a             LDA #$5a
$CF6E c9 0a             CMP #$0a
$CF70 b0 02             BCS $cf74
$CF72 a9 0a             LDA #$0a
$CF74 a0 03             LDY #$03
$CF76 91 22             STA ($22),Y
$CF78 20 1e d6          JSR $d61e
$CF7B 60                RTS

; leader_change_loyalty_only; bank11, ROM$016F8C, byteSHA256b401e5b7e1d1f22b0d1111643f9826ab48ca427c2e5d96ba87ceeef57677e5cb
$CF7C a5 32             LDA $32
$CF7E 0a                ASL A
$CF7F a8                TAY
$CF80 b9 d8 ca          LDA $cad8,Y
$CF83 85 24             STA $24
$CF85 b9 d9 ca          LDA $cad9,Y
$CF88 85 25             STA $25
$CF8A a0 ff             LDY #$ff
$CF8C c8                INY
$CF8D b1 24             LDA ($24),Y
$CF8F c9 ff             CMP #$ff
$CF91 f0 05             BEQ $cf98
$CF93 c5 30             CMP $30
$CF95 d0 f5             BNE $cf8c
$CF97 60                RTS
$CF98 a5 30             LDA $30
$CF9A a0 04             LDY #$04
$CF9C 20 ab d2          JSR $d2ab
$CF9F 85 21             STA $21
$CFA1 a9 05             LDA #$05
$CFA3 85 23             STA $23
$CFA5 a9 00             LDA #$00
$CFA7 85 22             STA $22
$CFA9 85 24             STA $24
$CFAB 20 0f d4          JSR $d40f
$CFAE a5 21             LDA $21
$CFB0 48                PHA
$CFB1 a5 33             LDA $33
$CFB3 a0 04             LDY #$04
$CFB5 20 ab d2          JSR $d2ab
$CFB8 85 21             STA $21
$CFBA a9 05             LDA #$05
$CFBC 85 23             STA $23
$CFBE a9 00             LDA #$00
$CFC0 85 22             STA $22
$CFC2 85 24             STA $24
$CFC4 20 0f d4          JSR $d40f
$CFC7 68                PLA
$CFC8 38                SEC
$CFC9 e5 21             SBC $21
$CFCB 90 0f             BCC $cfdc
$CFCD 85 20             STA $20
$CFCF a5 31             LDA $31
$CFD1 a0 03             LDY #$03
$CFD3 20 ab d2          JSR $d2ab
$CFD6 18                CLC
$CFD7 65 20             ADC $20
$CFD9 4c f1 cf          JMP $cff1
$CFDC 49 ff             EOR #$ff
$CFDE 18                CLC
$CFDF 69 01             ADC #$01
$CFE1 85 20             STA $20
$CFE3 a5 31             LDA $31
$CFE5 a0 03             LDY #$03
$CFE7 20 ab d2          JSR $d2ab
$CFEA 38                SEC
$CFEB e5 20             SBC $20
$CFED b0 02             BCS $cff1
$CFEF a9 00             LDA #$00
$CFF1 38                SEC
$CFF2 e9 0a             SBC #$0a
$CFF4 b0 02             BCS $cff8
$CFF6 a9 00             LDA #$00
$CFF8 c9 63             CMP #$63
$CFFA 90 02             BCC $cffe
$CFFC a9 63             LDA #$63
$CFFE c9 0a             CMP #$0a
$D000 b0 02             BCS $d004
$D002 a9 0a             LDA #$0a
$D004 a0 03             LDY #$03
$D006 91 22             STA ($22),Y
$D008 20 1e d6          JSR $d61e
$D00B 60                RTS

; capture_loyalty_only; bank11, ROM$01701C, byteSHA2560ff4332bc5821cefdc93548bbf458efa4950c5eacb50f71baaa894ab29030694
$D00C a5 20             LDA $20
$D00E a0 03             LDY #$03
$D010 20 ab d2          JSR $d2ab
$D013 85 20             STA $20
$D015 a9 32             LDA #$32
$D017 38                SEC
$D018 e5 20             SBC $20
$D01A b0 05             BCS $d021
$D01C 49 ff             EOR #$ff
$D01E 18                CLC
$D01F 69 01             ADC #$01
$D021 85 20             STA $20
$D023 a9 33             LDA #$33
$D025 38                SEC
$D026 e5 20             SBC $20
$D028 b0 02             BCS $d02c
$D02A a9 00             LDA #$00
$D02C c9 0a             CMP #$0a
$D02E b0 02             BCS $d032
$D030 a9 0a             LDA #$0a
$D032 a0 03             LDY #$03
$D034 91 22             STA ($22),Y
$D036 20 1e d6          JSR $d61e
$D039 60                RTS

; city_pointer_caps_resources; bank11, ROM$017115, byteSHA2563f7dcb93afde2dda7ebf10ce0af762e939fe99e77dcbe511ee857285908fea6b
$D105 a0 00             LDY #$00
$D107 84 21             STY $21
$D109 0a                ASL A
$D10A 26 21             ROL $21
$D10C 0a                ASL A
$D10D 26 21             ROL $21
$D10F 0a                ASL A
$D110 26 21             ROL $21
$D112 0a                ASL A
$D113 26 21             ROL $21
$D115 0a                ASL A
$D116 26 21             ROL $21
$D118 18                CLC
$D119 69 00             ADC #$00
$D11B 85 20             STA $20
$D11D a5 21             LDA $21
$D11F 69 60             ADC #$60
$D121 85 21             STA $21
$D123 20 9d d6          JSR $d69d
$D126 a0 00             LDY #$00
$D128 b1 20             LDA ($20),Y
$D12A 29 07             AND #$07
$D12C 60                RTS

; ruler_pointer_protocol; bank11, ROM$017329, byteSHA25634e53f6046e35e66c84d5a2df27d97a0a198f1008ef3e45b0ed60092a0fb0d31
$D319 29 0f             AND #$0f
$D31B 0a                ASL A
$D31C a8                TAY
$D31D b9 28 d3          LDA $d328,Y
$D320 85 24             STA $24
$D322 b9 29 d3          LDA $d329,Y
$D325 85 25             STA $25
$D327 60                RTS

; AI_roster_compaction; bank11, ROM$0173ED, byteSHA256a7c091cc1ecaf49b03e9b784bb1e76704fe7ee142a3f0f6d9f442e084296b60d
$D3DD 20 05 d1          JSR $d105
$D3E0 a2 00             LDX #$00
$D3E2 a9 ff             LDA #$ff
$D3E4 9d 73 6f          STA $6f73,X
$D3E7 e8                INX
$D3E8 e0 10             CPX #$10
$D3EA 90 f8             BCC $d3e4
$D3EC a0 11             LDY #$11
$D3EE a2 00             LDX #$00
$D3F0 b1 20             LDA ($20),Y
$D3F2 c9 ff             CMP #$ff
$D3F4 f0 04             BEQ $d3fa
$D3F6 9d 73 6f          STA $6f73,X
$D3F9 e8                INX
$D3FA c8                INY
$D3FB c0 1b             CPY #$1b
$D3FD 90 f1             BCC $d3f0
$D3FF a0 11             LDY #$11
$D401 a2 00             LDX #$00
$D403 bd 73 6f          LDA $6f73,X
$D406 91 20             STA ($20),Y
$D408 c8                INY
$D409 e8                INX
$D40A c0 1b             CPY #$1b
$D40C 90 f5             BCC $d403
$D40E 60                RTS

; city_resources_cap; bank11, ROM$0176AD, byteSHA25652348b0c6629da386e0d07f9212d93d1ee53d9a60557027d4cbeeaab990e4001
$D69D a0 02             LDY #$02
$D69F b1 20             LDA ($20),Y
$D6A1 38                SEC
$D6A2 e9 10             SBC #$10
$D6A4 c8                INY
$D6A5 b1 20             LDA ($20),Y
$D6A7 e9 27             SBC #$27
$D6A9 90 0b             BCC $d6b6
$D6AB a0 02             LDY #$02
$D6AD a9 0f             LDA #$0f
$D6AF 91 20             STA ($20),Y
$D6B1 c8                INY
$D6B2 a9 27             LDA #$27
$D6B4 91 20             STA ($20),Y
$D6B6 a0 04             LDY #$04
$D6B8 b1 20             LDA ($20),Y
$D6BA 38                SEC
$D6BB e9 10             SBC #$10
$D6BD c8                INY
$D6BE b1 20             LDA ($20),Y
$D6C0 e9 27             SBC #$27
$D6C2 90 0b             BCC $d6cf
$D6C4 a0 04             LDY #$04
$D6C6 a9 0f             LDA #$0f
$D6C8 91 20             STA ($20),Y
$D6CA c8                INY
$D6CB a9 27             LDA #$27
$D6CD 91 20             STA ($20),Y
$D6CF 60                RTS

; loyalty_post_write_helper_is_RTS; bank11, ROM$01762E, byteSHA2568d33f520a3c4cef80d2453aef81b612bfe1cb44c8b2025630ad38662763f13d3
$D61E 60                RTS

; player_roster_compaction_and_removal; bank25, ROM$033D96, byteSHA2561795cc2314da321e48957cd9cd918419ebdf0e7faee88c9242f87cd23530003e
$BD86 a2 00             LDX #$00
$BD88 a9 ff             LDA #$ff
$BD8A 9d 80 05          STA $0580,X
$BD8D e8                INX
$BD8E e0 10             CPX #$10
$BD90 90 f8             BCC $bd8a
$BD92 ad 08 04          LDA $0408
$BD95 20 af f2          JSR $f2af
$BD98 a0 11             LDY #$11
$BD9A a2 00             LDX #$00
$BD9C b1 00             LDA ($00),Y
$BD9E c9 ff             CMP #$ff
$BDA0 f0 04             BEQ $bda6
$BDA2 9d 80 05          STA $0580,X
$BDA5 e8                INX
$BDA6 c8                INY
$BDA7 c0 1b             CPY #$1b
$BDA9 90 f1             BCC $bd9c
$BDAB a0 11             LDY #$11
$BDAD a2 00             LDX #$00
$BDAF bd 80 05          LDA $0580,X
$BDB2 91 00             STA ($00),Y
$BDB4 c8                INY
$BDB5 e8                INX
$BDB6 c0 1b             CPY #$1b
$BDB8 90 f5             BCC $bdaf
$BDBA 60                RTS
$BDBB a0 31             LDY #$31
$BDBD 20 5f f2          JSR $f25f
$BDC0 ad 0a 04          LDA $040a
$BDC3 20 d7 f2          JSR $f2d7
$BDC6 a0 0b             LDY #$0b
$BDC8 b1 00             LDA ($00),Y
$BDCA 09 03             ORA #$03
$BDCC 91 00             STA ($00),Y
$BDCE a0 30             LDY #$30
$BDD0 20 5f f2          JSR $f25f
$BDD3 ad 08 04          LDA $0408
$BDD6 20 af f2          JSR $f2af
$BDD9 ac 09 04          LDY $0409
$BDDC a9 ff             LDA #$ff
$BDDE 91 00             STA ($00),Y
$BDE0 20 86 bd          JSR $bd86
$BDE3 a0 11             LDY #$11
$BDE5 a2 00             LDX #$00
$BDE7 b1 00             LDA ($00),Y
$BDE9 c9 ff             CMP #$ff
$BDEB f0 01             BEQ $bdee
$BDED e8                INX
$BDEE c8                INY
$BDEF c0 1b             CPY #$1b
$BDF1 90 f4             BCC $bde7
$BDF3 8a                TXA
$BDF4 d0 0a             BNE $be00
$BDF6 a0 00             LDY #$00
$BDF8 b1 00             LDA ($00),Y
$BDFA 29 f8             AND #$f8
$BDFC 09 07             ORA #$07
$BDFE 91 00             STA ($00),Y
$BE00 60                RTS

; manual_successor_commit; bank25, ROM$033F95, byteSHA2562d4827d07cb71d3da65653be3ab28ea470fdcec5b41084c7a3b9f32a01288e0c
$BF85 ad 12 00          LDA $0012
$BF88 d0 e8             BNE $bf72
$BF8A ad 0a 04          LDA $040a
$BF8D 20 68 f3          JSR $f368
$BF90 ad 0d 04          LDA $040d
$BF93 8d 2c 04          STA $042c
$BF96 a0 00             LDY #$00
$BF98 91 00             STA ($00),Y
$BF9A ad 0c 04          LDA $040c
$BF9D a0 01             LDY #$01
$BF9F 91 ee             STA ($ee),Y
$BFA1 20 01 c1          JSR $c101
$BFA4 ee 02 04          INC $0402
$BFA7 a9 d3             LDA #$d3
$BFA9 4c 8b f2          JMP $f28b

; release_selected_officer; bank26, ROM$0340A9, byteSHA256467c489105d0a5ba81a082989d5eddaf7c7194f70ba4fb5a5b1f4c61b580ca6b
$C099 a0 0b             LDY #$0b
$C09B b1 00             LDA ($00),Y
$C09D 29 fc             AND #$fc
$C09F 91 00             STA ($00),Y
$C0A1 a0 05             LDY #$05
$C0A3 ad 0e 04          LDA $040e
$C0A6 91 00             STA ($00),Y
$C0A8 ac 0f 04          LDY $040f
$C0AB c0 1a             CPY #$1a
$C0AD f0 0a             BEQ $c0b9
$C0AF c8                INY
$C0B0 b1 10             LDA ($10),Y
$C0B2 88                DEY
$C0B3 91 10             STA ($10),Y
$C0B5 c8                INY
$C0B6 4c ab c0          JMP $c0ab
$C0B9 a9 ff             LDA #$ff
$C0BB 91 10             STA ($10),Y
$C0BD a2 00             LDX #$00
$C0BF a0 11             LDY #$11
$C0C1 b1 10             LDA ($10),Y
$C0C3 c9 ff             CMP #$ff
$C0C5 f0 01             BEQ $c0c8
$C0C7 e8                INX
$C0C8 c8                INY
$C0C9 c0 1b             CPY #$1b
$C0CB 90 f4             BCC $c0c1
$C0CD e0 00             CPX #$00
$C0CF d0 06             BNE $c0d7
$C0D1 a0 00             LDY #$00
$C0D3 a9 07             LDA #$07
$C0D5 91 10             STA ($10),Y
$C0D7 ee 02 04          INC $0402
$C0DA ad 31 00          LDA $0031
$C0DD 8d 2c 04          STA $042c
$C0E0 a9 d4             LDA #$d4
$C0E2 4c 8b f2          JMP $f28b

; swap_city_chief; bank26, ROM$034111, byteSHA2569b4122838bcea24a63dbd9b9bf4bdfab90877770d1b4de9f5fa39846102a1163
$C101 ad 0c 04          LDA $040c
$C104 20 af f2          JSR $f2af
$C107 ad 0d 04          LDA $040d
$C10A 8d 02 00          STA $0002
$C10D a0 11             LDY #$11
$C10F b1 00             LDA ($00),Y
$C111 cd 02 00          CMP $0002
$C114 f0 06             BEQ $c11c
$C116 c8                INY
$C117 c0 1b             CPY #$1b
$C119 90 f4             BCC $c10f
$C11B 60                RTS
$C11C 98                TYA
$C11D 48                PHA
$C11E a0 11             LDY #$11
$C120 b1 00             LDA ($00),Y
$C122 8d 03 00          STA $0003
$C125 ad 02 00          LDA $0002
$C128 91 00             STA ($00),Y
$C12A 68                PLA
$C12B a8                TAY
$C12C ad 03 00          LDA $0003
$C12F 91 00             STA ($00),Y
$C131 60                RTS

; automatic_successor_commit; bank26, ROM$03426D, byteSHA2561d046a539d2a39ee8c37e7b2ee487236a652bfefa8d6a2655f4f6806774507d0
$C25D ad 0a 04          LDA $040a
$C260 20 68 f3          JSR $f368
$C263 a0 00             LDY #$00
$C265 ad 0d 04          LDA $040d
$C268 91 00             STA ($00),Y
$C26A 20 01 c1          JSR $c101
$C26D ee 02 04          INC $0402
$C270 ad 0d 04          LDA $040d
$C273 8d 2c 04          STA $042c
$C276 a9 00             LDA #$00
$C278 8d d0 04          STA $04d0
$C27B a9 c2             LDA #$c2
$C27D 4c 8b f2          JMP $f28b

; player_follower_recalculation_and_removal; bank26, ROM$034299, byteSHA2563fe77ed3ab69916e2c97d77d1b41c1fa4a6c12ea4c15c2fa213f81a3136bef54
$C289 ad 09 04          LDA $0409
$C28C 30 18             BMI $c2a6
$C28E ad 0d 04          LDA $040d
$C291 20 d7 f2          JSR $f2d7
$C294 a0 03             LDY #$03
$C296 a9 64             LDA #$64
$C298 91 00             STA ($00),Y
$C29A ad 70 04          LDA $0470
$C29D 8d 01 04          STA $0401
$C2A0 a9 00             LDA #$00
$C2A2 8d 02 04          STA $0402
$C2A5 60                RTS
$C2A6 a9 00             LDA #$00
$C2A8 8d 12 00          STA $0012
$C2AB ad 12 00          LDA $0012
$C2AE 20 af f2          JSR $f2af
$C2B1 a0 00             LDY #$00
$C2B3 b1 00             LDA ($00),Y
$C2B5 29 07             AND #$07
$C2B7 cd 0a 04          CMP $040a
$C2BA d0 4f             BNE $c30b
$C2BC ad 00 00          LDA $0000
$C2BF 8d 10 00          STA $0010
$C2C2 ad 01 00          LDA $0001
$C2C5 8d 11 00          STA $0011
$C2C8 a0 11             LDY #$11
$C2CA 8c 13 00          STY $0013
$C2CD b1 10             LDA ($10),Y
$C2CF c9 ff             CMP #$ff
$C2D1 f0 38             BEQ $c30b
$C2D3 8d 31 00          STA $0031
$C2D6 ad 0d 04          LDA $040d
$C2D9 8d 30 00          STA $0030
$C2DC ad 0a 04          LDA $040a
$C2DF 8d 32 00          STA $0032
$C2E2 ad 0b 04          LDA $040b
$C2E5 8d 33 00          STA $0033
$C2E8 a0 2a             LDY #$2a
$C2EA 20 07 ee 09 a0    JSR $ee07 ; inline far target$A009; selector supplied inY
$C2EF a0 03             LDY #$03
$C2F1 b1 22             LDA ($22),Y
$C2F3 c9 1f             CMP #$1f
$C2F5 b0 0a             BCS $c301
$C2F7 20 43 e8          JSR $e843
$C2FA c9 14             CMP #$14
$C2FC b0 03             BCS $c301
$C2FE 20 18 c3          JSR $c318
$C301 ee 13 00          INC $0013
$C304 ac 13 00          LDY $0013
$C307 c0 1b             CPY #$1b
$C309 90 c2             BCC $c2cd
$C30B ee 12 00          INC $0012
$C30E ad 12 00          LDA $0012
$C311 c9 1e             CMP #$1e
$C313 90 96             BCC $c2ab
$C315 4c 8e c2          JMP $c28e
$C318 ad 31 00          LDA $0031
$C31B cd 0d 04          CMP $040d
$C31E d0 01             BNE $c321
$C320 60                RTS
$C321 a0 0b             LDY #$0b
$C323 b1 22             LDA ($22),Y
$C325 29 fc             AND #$fc
$C327 91 22             STA ($22),Y
$C329 ac 13 00          LDY $0013
$C32C c0 1a             CPY #$1a
$C32E f0 0a             BEQ $c33a
$C330 c8                INY
$C331 b1 10             LDA ($10),Y
$C333 88                DEY
$C334 91 10             STA ($10),Y
$C336 c8                INY
$C337 4c 2c c3          JMP $c32c
$C33A a9 ff             LDA #$ff
$C33C 91 10             STA ($10),Y
$C33E ce 13 00          DEC $0013
$C341 60                RTS

; recruit_and_move_roster; bank27, ROM$036D00, byteSHA2560c6cf405c78383e8bd8fd0d531984a9e1126bc14cf58775251af8771402cbb37
$ACF0 ad 02 04          LDA $0402
$ACF3 20 af f2          JSR $f2af
$ACF6 20 6b dc          JSR $dc6b
$ACF9 8a                TXA
$ACFA 18                CLC
$ACFB 69 11             ADC #$11
$ACFD a8                TAY
$ACFE ad 72 04          LDA $0472
$AD01 91 00             STA ($00),Y
$AD03 a0 00             LDY #$00
$AD05 b1 00             LDA ($00),Y
$AD07 20 68 f3          JSR $f368
$AD0A a0 00             LDY #$00
$AD0C b1 00             LDA ($00),Y
$AD0E 8d 30 00          STA $0030
$AD11 ad 72 04          LDA $0472
$AD14 8d 31 00          STA $0031
$AD17 20 d7 f2          JSR $f2d7
$AD1A a0 0b             LDY #$0b
$AD1C b1 00             LDA ($00),Y
$AD1E 8d 02 00          STA $0002
$AD21 29 fc             AND #$fc
$AD23 09 02             ORA #$02
$AD25 91 00             STA ($00),Y
$AD27 ad 02 00          LDA $0002
$AD2A 29 03             AND #$03
$AD2C c9 01             CMP #$01
$AD2E f0 07             BEQ $ad37
$AD30 a0 2a             LDY #$2a
$AD32 20 07 ee 06 a0    JSR $ee07 ; inline far target$A006; selector supplied inY
$AD37 a9 16             LDA #$16
$AD39 8d 01 04          STA $0401
$AD3C a9 39             LDA #$39
$AD3E 4c 6d f2          JMP $f26d
$AD41 ad 71 04          LDA $0471
$AD44 20 af f2          JSR $f2af
$AD47 a2 00             LDX #$00
$AD49 a0 11             LDY #$11
$AD4B b1 00             LDA ($00),Y
$AD4D c9 ff             CMP #$ff
$AD4F f0 04             BEQ $ad55
$AD51 c8                INY
$AD52 4c 4b ad          JMP $ad4b
$AD55 bd 81 04          LDA $0481,X
$AD58 c9 ff             CMP #$ff
$AD5A f0 08             BEQ $ad64
$AD5C 91 00             STA ($00),Y
$AD5E e8                INX
$AD5F c8                INY
$AD60 e0 0a             CPX #$0a
$AD62 90 f1             BCC $ad55
$AD64 a0 00             LDY #$00
$AD66 b1 ee             LDA ($ee),Y
$AD68 8d 02 00          STA $0002
$AD6B a0 11             LDY #$11
$AD6D b1 00             LDA ($00),Y
$AD6F cd 02 00          CMP $0002
$AD72 f0 08             BEQ $ad7c
$AD74 c8                INY
$AD75 c0 1b             CPY #$1b
$AD77 90 f4             BCC $ad6d
$AD79 4c 98 ad          JMP $ad98
$AD7C 98                TYA
$AD7D 48                PHA
$AD7E a0 11             LDY #$11
$AD80 b1 00             LDA ($00),Y
$AD82 8d 03 00          STA $0003
$AD85 ad 02 00          LDA $0002
$AD88 91 00             STA ($00),Y
$AD8A 68                PLA
$AD8B a8                TAY
$AD8C ad 03 00          LDA $0003
$AD8F 91 00             STA ($00),Y
$AD91 a0 01             LDY #$01
$AD93 ad 71 04          LDA $0471
$AD96 91 ee             STA ($ee),Y
$AD98 ad 70 04          LDA $0470
$AD9B 20 af f2          JSR $f2af
$AD9E a2 00             LDX #$00
$ADA0 bd 81 04          LDA $0481,X
$ADA3 c9 ff             CMP #$ff
$ADA5 f0 1c             BEQ $adc3
$ADA7 8d 10 00          STA $0010
$ADAA a0 11             LDY #$11
$ADAC b1 00             LDA ($00),Y
$ADAE cd 10 00          CMP $0010
$ADB1 d0 07             BNE $adba
$ADB3 a9 ff             LDA #$ff
$ADB5 91 00             STA ($00),Y
$ADB7 4c be ad          JMP $adbe
$ADBA c8                INY
$ADBB 4c ac ad          JMP $adac
$ADBE e8                INX
$ADBF e0 0a             CPX #$0a
$ADC1 90 dd             BCC $ada0
$ADC3 a2 00             LDX #$00
$ADC5 a9 ff             LDA #$ff
$ADC7 9d 81 04          STA $0481,X
$ADCA e8                INX
$ADCB e0 0a             CPX #$0a
$ADCD 90 f8             BCC $adc7
$ADCF a0 11             LDY #$11
$ADD1 a2 00             LDX #$00
$ADD3 b1 00             LDA ($00),Y
$ADD5 c9 ff             CMP #$ff
$ADD7 f0 04             BEQ $addd
$ADD9 9d 81 04          STA $0481,X
$ADDC e8                INX
$ADDD c8                INY
$ADDE c0 1b             CPY #$1b
$ADE0 90 f1             BCC $add3
$ADE2 a0 11             LDY #$11
$ADE4 a2 00             LDX #$00
$ADE6 bd 81 04          LDA $0481,X
$ADE9 91 00             STA ($00),Y
$ADEB e8                INX
$ADEC c8                INY
$ADED e0 0a             CPX #$0a
$ADEF 90 f5             BCC $ade6
$ADF1 60                RTS
