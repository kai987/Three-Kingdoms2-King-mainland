; Phase20 original ROM bytes; offsets include 16-byte iNES header.

; three_way_choice physical10 $A19C..$A1C4
0141AC b10:$A19C ad 5f 6f                                         LDA $6f5f
0141AF b10:$A19F 18                                               CLC
0141B0 b10:$A1A0 6d 60 6f                                         ADC $6f60
0141B3 b10:$A1A3 85 21                                            STA $21
0141B5 b10:$A1A5 18                                               CLC
0141B6 b10:$A1A6 6d 61 6f                                         ADC $6f61
0141B9 b10:$A1A9 20 ad d4                                         JSR $d4ad
0141BC b10:$A1AC a0 00                                            LDY #$00
0141BE b10:$A1AE cd 5f 6f                                         CMP $6f5f
0141C1 b10:$A1B1 90 06                                            BCC $a1b9
0141C3 b10:$A1B3 c8                                               INY
0141C4 b10:$A1B4 c5 21                                            CMP $21
0141C6 b10:$A1B6 90 01                                            BCC $a1b9
0141C8 b10:$A1B8 c8                                               INY
0141C9 b10:$A1B9 98                                               TYA
0141CA b10:$A1BA 29 03                                            AND #$03
0141CC b10:$A1BC 20 94 d4                                         JSR $d494
0141CF b10:$A1BF c5 a1                                            .word $A1C5 ; inline D494 selector word
0141D1 b10:$A1C1 9c b4                                            .word $B49C ; inline D494 selector word
0141D3 b10:$A1C3 c7 be                                            .word $BEC7 ; inline D494 selector word

; primary_or_secondary physical10 $B49C..$B4AB
0154AC b10:$B49C 20 aa e8                                         JSR $e8aa
0154AF b10:$B49F 29 7f                                            AND #$7f
0154B1 b10:$B4A1 c9 32                                            CMP #$32
0154B3 b10:$B4A3 b0 f7                                            BCS $b49c
0154B5 b10:$B4A5 c9 0a                                            CMP #$0a
0154B7 b10:$B4A7 b0 03                                            BCS $b4ac
0154B9 b10:$B4A9 4c fc b5                                         JMP $b5fc

; secondary_choice physical10 $B5FC..$B618
01560C b10:$B5FC 20 9a e8                                         JSR $e89a
01560F b10:$B5FF 29 7f                                            AND #$7f
015611 b10:$B601 c9 5a                                            CMP #$5a
015613 b10:$B603 b0 f7                                            BCS $b5fc
015615 b10:$B605 c9 1e                                            CMP #$1e
015617 b10:$B607 90 07                                            BCC $b610
015619 b10:$B609 c9 3c                                            CMP #$3c
01561B b10:$B60B 90 06                                            BCC $b613
01561D b10:$B60D 4c 19 b6                                         JMP $b619
015620 b10:$B610 4c b2 bb                                         JMP $bbb2
015623 b10:$B613 4c 8b b9                                         JMP $b98b
015626 b10:$B616 4c c7 be                                         JMP $bec7

; alliance_gates_quote_request_wait physical10 $B619..$B7A1
015629 b10:$B619 ad 03 6f                                         LDA $6f03
01562C b10:$B61C 20 19 d3                                         JSR $d319
01562F b10:$B61F a0 00                                            LDY #$00
015631 b10:$B621 b1 24                                            LDA ($24),Y
015633 b10:$B623 8d 40 00                                         STA $0040
015636 b10:$B626 20 37 b8                                         JSR $b837
015639 b10:$B629 ad 3d 00                                         LDA $003d
01563C b10:$B62C c9 ff                                            CMP #$ff
01563E b10:$B62E f0 26                                            BEQ $b656
015640 b10:$B630 8d 42 00                                         STA $0042
015643 b10:$B633 a9 00                                            LDA #$00
015645 b10:$B635 85 2a                                            STA $2a
015647 b10:$B637 85 2b                                            STA $2b
015649 b10:$B639 a5 2a                                            LDA $2a
01564B b10:$B63B 20 19 d3                                         JSR $d319
01564E b10:$B63E a0 00                                            LDY #$00
015650 b10:$B640 b1 24                                            LDA ($24),Y
015652 b10:$B642 c9 ff                                            CMP #$ff
015654 b10:$B644 f0 02                                            BEQ $b648
015656 b10:$B646 e6 2b                                            INC $2b
015658 b10:$B648 e6 2a                                            INC $2a
01565A b10:$B64A a5 2a                                            LDA $2a
01565C b10:$B64C c9 07                                            CMP #$07
01565E b10:$B64E 90 e9                                            BCC $b639
015660 b10:$B650 a5 2b                                            LDA $2b
015662 b10:$B652 c9 03                                            CMP #$03
015664 b10:$B654 b0 03                                            BCS $b659
015666 b10:$B656 4c 16 b6                                         JMP $b616
015669 b10:$B659 ad 03 6f                                         LDA $6f03
01566C b10:$B65C 20 19 d3                                         JSR $d319
01566F b10:$B65F a2 00                                            LDX #$00
015671 b10:$B661 a0 04                                            LDY #$04
015673 b10:$B663 b1 24                                            LDA ($24),Y
015675 b10:$B665 a0 05                                            LDY #$05
015677 b10:$B667 18                                               CLC
015678 b10:$B668 71 24                                            ADC ($24),Y
01567A b10:$B66A a0 06                                            LDY #$06
01567C b10:$B66C 18                                               CLC
01567D b10:$B66D 71 24                                            ADC ($24),Y
01567F b10:$B66F a0 07                                            LDY #$07
015681 b10:$B671 18                                               CLC
015682 b10:$B672 71 24                                            ADC ($24),Y
015684 b10:$B674 c9 00                                            CMP #$00
015686 b10:$B676 d0 de                                            BNE $b656
015688 b10:$B678 20 98 b8                                         JSR $b898
01568B b10:$B67B e0 02                                            CPX #$02
01568D b10:$B67D 90 d7                                            BCC $b656
01568F b10:$B67F a0 00                                            LDY #$00
015691 b10:$B681 8c 36 00                                         STY $0036
015694 b10:$B684 8c 37 00                                         STY $0037
015697 b10:$B687 8c 38 00                                         STY $0038
01569A b10:$B68A ac 36 00                                         LDY $0036
01569D b10:$B68D b9 73 6f                                         LDA $6f73,Y
0156A0 b10:$B690 d0 16                                            BNE $b6a8
0156A2 b10:$B692 ad 36 00                                         LDA $0036
0156A5 b10:$B695 20 80 d0                                         JSR $d080
0156A8 b10:$B698 a5 2b                                            LDA $2b
0156AA b10:$B69A cd 37 00                                         CMP $0037
0156AD b10:$B69D 90 09                                            BCC $b6a8
0156AF b10:$B69F 8d 37 00                                         STA $0037
0156B2 b10:$B6A2 ad 36 00                                         LDA $0036
0156B5 b10:$B6A5 8d 38 00                                         STA $0038
0156B8 b10:$B6A8 ee 36 00                                         INC $0036
0156BB b10:$B6AB ad 36 00                                         LDA $0036
0156BE b10:$B6AE c9 07                                            CMP #$07
0156C0 b10:$B6B0 90 d8                                            BCC $b68a
0156C2 b10:$B6B2 ad 03 6f                                         LDA $6f03
0156C5 b10:$B6B5 20 80 d0                                         JSR $d080
0156C8 b10:$B6B8 a5 2b                                            LDA $2b
0156CA b10:$B6BA 18                                               CLC
0156CB b10:$B6BB 69 02                                            ADC #$02
0156CD b10:$B6BD cd 37 00                                         CMP $0037
0156D0 b10:$B6C0 90 03                                            BCC $b6c5
0156D2 b10:$B6C2 4c 56 b6                                         JMP $b656
0156D5 b10:$B6C5 ad 37 00                                         LDA $0037
0156D8 b10:$B6C8 85 20                                            STA $20
0156DA b10:$B6CA a9 1e                                            LDA #$1e
0156DC b10:$B6CC 85 21                                            STA $21
0156DE b10:$B6CE 20 71 d4                                         JSR $d471
0156E1 b10:$B6D1 a5 2a                                            LDA $2a
0156E3 b10:$B6D3 18                                               CLC
0156E4 b10:$B6D4 69 46                                            ADC #$46
0156E6 b10:$B6D6 85 21                                            STA $21
0156E8 b10:$B6D8 a5 2b                                            LDA $2b
0156EA b10:$B6DA 69 00                                            ADC #$00
0156EC b10:$B6DC 85 22                                            STA $22
0156EE b10:$B6DE a9 0a                                            LDA #$0a
0156F0 b10:$B6E0 85 23                                            STA $23
0156F2 b10:$B6E2 a9 00                                            LDA #$00
0156F4 b10:$B6E4 85 24                                            STA $24
0156F6 b10:$B6E6 20 0f d4                                         JSR $d40f
0156F9 b10:$B6E9 a5 21                                            LDA $21
0156FB b10:$B6EB 8d 2f 04                                         STA $042f
0156FE b10:$B6EE a5 22                                            LDA $22
015700 b10:$B6F0 8d 30 04                                         STA $0430
015703 b10:$B6F3 0e 2f 04                                         ASL $042f
015706 b10:$B6F6 2e 30 04                                         ROL $0430
015709 b10:$B6F9 0e 2f 04                                         ASL $042f
01570C b10:$B6FC 2e 30 04                                         ROL $0430
01570F b10:$B6FF a9 00                                            LDA #$00
015711 b10:$B701 8d 31 04                                         STA $0431
015714 b10:$B704 a9 00                                            LDA #$00
015716 b10:$B706 8d 39 00                                         STA $0039
015719 b10:$B709 a9 64                                            LDA #$64
01571B b10:$B70B 20 bb d4                                         JSR $d4bb
01571E b10:$B70E c9 32                                            CMP #$32
015720 b10:$B710 90 28                                            BCC $b73a
015722 b10:$B712 a9 01                                            LDA #$01
015724 b10:$B714 8d 39 00                                         STA $0039
015727 b10:$B717 a5 21                                            LDA $21
015729 b10:$B719 85 20                                            STA $20
01572B b10:$B71B a5 22                                            LDA $22
01572D b10:$B71D 85 21                                            STA $21
01572F b10:$B71F a9 00                                            LDA #$00
015731 b10:$B721 85 22                                            STA $22
015733 b10:$B723 a9 06                                            LDA #$06
015735 b10:$B725 85 23                                            STA $23
015737 b10:$B727 20 38 d4                                         JSR $d438
01573A b10:$B72A ad 26 00                                         LDA $0026
01573D b10:$B72D 8d 2f 04                                         STA $042f
015740 b10:$B730 a5 27                                            LDA $27
015742 b10:$B732 8d 30 04                                         STA $0430
015745 b10:$B735 a9 00                                            LDA #$00
015747 b10:$B737 8d 31 04                                         STA $0431
01574A b10:$B73A ad 2f 04                                         LDA $042f
01574D b10:$B73D 8d 3a 00                                         STA $003a
015750 b10:$B740 ad 31 04                                         LDA $0431
015753 b10:$B743 8d 3b 00                                         STA $003b
015756 b10:$B746 20 a2 b7                                         JSR $b7a2
015759 b10:$B749 b0 03                                            BCS $b74e
01575B b10:$B74B 4c 56 b6                                         JMP $b656
01575E b10:$B74E ad 38 00                                         LDA $0038
015761 b10:$B751 20 19 d3                                         JSR $d319
015764 b10:$B754 a0 03                                            LDY #$03
015766 b10:$B756 b1 24                                            LDA ($24),Y
015768 b10:$B758 c9 03                                            CMP #$03
01576A b10:$B75A d0 09                                            BNE $b765
01576C b10:$B75C 20 0a b9                                         JSR $b90a
01576F b10:$B75F 20 ce b7                                         JSR $b7ce
015772 b10:$B762 4c 16 b6                                         JMP $b616
015775 b10:$B765 ad 03 6f                                         LDA $6f03
015778 b10:$B768 20 19 d3                                         JSR $d319
01577B b10:$B76B a0 00                                            LDY #$00
01577D b10:$B76D b1 24                                            LDA ($24),Y
01577F b10:$B76F 8d 40 00                                         STA $0040
015782 b10:$B772 ad 38 00                                         LDA $0038
015785 b10:$B775 20 19 d3                                         JSR $d319
015788 b10:$B778 a0 00                                            LDY #$00
01578A b10:$B77A b1 24                                            LDA ($24),Y
01578C b10:$B77C 8d 41 00                                         STA $0041
01578F b10:$B77F a0 03                                            LDY #$03
015791 b10:$B781 b1 24                                            LDA ($24),Y
015793 b10:$B783 8d 44 6f                                         STA $6f44
015796 b10:$B786 a9 f8                                            LDA #$f8
015798 b10:$B788 8d 8b 6f                                         STA $6f8b
01579B b10:$B78B ad 8b 6f                                         LDA $6f8b
01579E b10:$B78E c9 f8                                            CMP #$f8
0157A0 b10:$B790 f0 f9                                            BEQ $b78b
0157A2 b10:$B792 c9 00                                            CMP #$00
0157A4 b10:$B794 f0 03                                            BEQ $b799
0157A6 b10:$B796 4c 16 b6                                         JMP $b616
0157A9 b10:$B799 20 0a b9                                         JSR $b90a
0157AC b10:$B79C 20 ce b7                                         JSR $b7ce
0157AF b10:$B79F 4c 16 b6                                         JMP $b616

; three_domestic_random_cursors physical31 $E88A..$E8B9
03E89A b31:$E88A 8e 53 00                                         STX $0053
03E89D b31:$E88D ae 52 00                                         LDX $0052
03E8A0 b31:$E890 bd ba e8                                         LDA $e8ba,X
03E8A3 b31:$E893 ee 52 00                                         INC $0052
03E8A6 b31:$E896 ae 53 00                                         LDX $0053
03E8A9 b31:$E899 60                                               RTS
03E8AA b31:$E89A 8e 53 00                                         STX $0053
03E8AD b31:$E89D ae 54 00                                         LDX $0054
03E8B0 b31:$E8A0 bd ba e8                                         LDA $e8ba,X
03E8B3 b31:$E8A3 ee 54 00                                         INC $0054
03E8B6 b31:$E8A6 ae 53 00                                         LDX $0053
03E8B9 b31:$E8A9 60                                               RTS
03E8BA b31:$E8AA 8e 53 00                                         STX $0053
03E8BD b31:$E8AD ae 55 00                                         LDX $0055
03E8C0 b31:$E8B0 bd ba e8                                         LDA $e8ba,X
03E8C3 b31:$E8B3 ee 55 00                                         INC $0055
03E8C6 b31:$E8B6 ae 53 00                                         LDX $0053
03E8C9 b31:$E8B9 60                                               RTS

; random_literal_table physical31 $E8BA..$E9B9
03E8CA b31:$E8BA 3e 4e 4f 83 0e c9 7f 5d fc e6 ba 01 f8 00 f4 0a  .byte $3E,$4E,$4F,$83,$0E,$C9,$7F,$5D,$FC,$E6,$BA,$01,$F8,$00,$F4,$0A
03E8DA b31:$E8CA e5 a9 8d d1 e8 db de 81 95 72 08 9a c7 49 c8 23  .byte $E5,$A9,$8D,$D1,$E8,$DB,$DE,$81,$95,$72,$08,$9A,$C7,$49,$C8,$23
03E8EA b31:$E8DA 39 37 e0 91 c3 33 9b 5f be 41 ee 74 e2 0b 47 7e  .byte $39,$37,$E0,$91,$C3,$33,$9B,$5F,$BE,$41,$EE,$74,$E2,$0B,$47,$7E
03E8FA b31:$E8EA bf 60 bb 20 61 05 b2 94 b6 e4 3a 21 1e b4 8c ce  .byte $BF,$60,$BB,$20,$61,$05,$B2,$94,$B6,$E4,$3A,$21,$1E,$B4,$8C,$CE
03E90A b31:$E8FA 7b fe 22 dc 18 c4 6d fb cd 27 a0 09 6e 38 8a 04  .byte $7B,$FE,$22,$DC,$18,$C4,$6D,$FB,$CD,$27,$A0,$09,$6E,$38,$8A,$04
03E91A b31:$E90A 7c 56 97 5a a8 4d 78 b5 6c aa 03 1a 4a 0d 26 82  .byte $7C,$56,$97,$5A,$A8,$4D,$78,$B5,$6C,$AA,$03,$1A,$4A,$0D,$26,$82
03E92A b31:$E91A ad 02 a1 b9 a3 6b d8 0c 4c ae 19 45 5b 9c 16 07  .byte $AD,$02,$A1,$B9,$A3,$6B,$D8,$0C,$4C,$AE,$19,$45,$5B,$9C,$16,$07
03E93A b31:$E92A 89 51 90 29 f5 62 f7 cb f1 53 ff 14 65 d0 87 35  .byte $89,$51,$90,$29,$F5,$62,$F7,$CB,$F1,$53,$FF,$14,$65,$D0,$87,$35
03E94A b31:$E93A 10 73 7a 9f eb d9 3c ef 9e d7 3d 6f d6 84 ab 11  .byte $10,$73,$7A,$9F,$EB,$D9,$3C,$EF,$9E,$D7,$3D,$6F,$D6,$84,$AB,$11
03E95A b31:$E94A ca d2 88 17 e1 a6 52 8e 5e 36 24 44 28 a4 55 a7  .byte $CA,$D2,$88,$17,$E1,$A6,$52,$8E,$5E,$36,$24,$44,$28,$A4,$55,$A7
03E96A b31:$E95A c2 fd 76 2e b7 d5 f6 64 15 31 99 93 c0 8f b3 fa  .byte $C2,$FD,$76,$2E,$B7,$D5,$F6,$64,$15,$31,$99,$93,$C0,$8F,$B3,$FA
03E97A b31:$E96A e9 e3 67 4b 85 32 c6 69 48 df a2 ec 98 6a e7 d4  .byte $E9,$E3,$67,$4B,$85,$32,$C6,$69,$48,$DF,$A2,$EC,$98,$6A,$E7,$D4
03E98A b31:$E97A 1c f3 58 50 ed 2b 1d 86 f0 71 bd 34 1b af 30 2d  .byte $1C,$F3,$58,$50,$ED,$2B,$1D,$86,$F0,$71,$BD,$34,$1B,$AF,$30,$2D
03E99A b31:$E98A 68 cc 0f 57 ea 92 8b 3f 3b ac b8 c1 2f f2 46 75  .byte $68,$CC,$0F,$57,$EA,$92,$8B,$3F,$3B,$AC,$B8,$C1,$2F,$F2,$46,$75
03E9AA b31:$E99A 96 7d 2a 79 40 da 9d 25 12 42 54 d3 1f 80 5c 59  .byte $96,$7D,$2A,$79,$40,$DA,$9D,$25,$12,$42,$54,$D3,$1F,$80,$5C,$59
03E9BA b31:$E9AA 43 f9 b0 dd 63 a5 77 cf 13 2c 66 bc 70 b1 c5 06  .byte $43,$F9,$B0,$DD,$63,$A5,$77,$CF,$13,$2C,$66,$BC,$70,$B1,$C5,$06

; full_NMI_cursor_advance physical31 $F8A1..$F8B4
03F8B1 b31:$F8A1 e6 50                                            INC $50
03F8B3 b31:$F8A3 e6 52                                            INC $52
03F8B5 b31:$F8A5 e6 54                                            INC $54
03F8B7 b31:$F8A7 e6 55                                            INC $55
03F8B9 b31:$F8A9 e6 5e                                            INC $5e
03F8BB b31:$F8AB d0 02                                            BNE $f8af
03F8BD b31:$F8AD e6 5f                                            INC $5f
03F8BF b31:$F8AF 68                                               PLA
03F8C0 b31:$F8B0 a8                                               TAY
03F8C1 b31:$F8B1 68                                               PLA
03F8C2 b31:$F8B2 aa                                               TAX
03F8C3 b31:$F8B3 68                                               PLA
03F8C4 b31:$F8B4 40                                               RTI
