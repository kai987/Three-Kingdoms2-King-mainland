
; turn_and_duration, bank23, file$02F371
$B361 ad c0 04       LDA $04c0
$B364 d0 08          BNE $b36e
$B366 ad aa 04       LDA $04aa
$B369 49 01          EOR #$01
$B36B 8d aa 04       STA $04aa
$B36E ee c0 04       INC $04c0
$B371 ad c0 04       LDA $04c0
$B374 c9 03          CMP #$03
$B376 90 03          BCC $b37b
$B378 20 c6 b3       JSR $b3c6
$B37B ad aa 04       LDA $04aa
$B37E 49 01          EOR #$01
$B380 8d aa 04       STA $04aa
$B383 a8             TAY
$B384 b9 b5 04       LDA $04b5,Y
$B387 29 7f          AND #$7f
$B389 f0 06          BEQ $b391
$B38B 38             SEC
$B38C e9 01          SBC #$01
$B38E 99 b5 04       STA $04b5,Y
$B391 ac aa 04       LDY $04aa
$B394 b9 ab 04       LDA $04ab,Y
$B397 10 06          BPL $b39f
$B399 a9 02          LDA #$02
$B39B 8d a8 04       STA $04a8
$B39E 60             RTS
$B39F ac aa 04       LDY $04aa
$B3A2 b9 ad 04       LDA $04ad,Y
$B3A5 8d 00 00       STA $0000
$B3A8 a0 3d          LDY #$3d
$B3AA 20 07 ee 30 a0 JSR $ee07 ; inline far target$A030
$B3AF ac aa 04       LDY $04aa
$B3B2 b9 b5 04       LDA $04b5,Y
$B3B5 29 7f          AND #$7f
$B3B7 f0 02          BEQ $b3bb
$B3B9 a9 02          LDA #$02
$B3BB 8d a4 00       STA $00a4
$B3BE ee a9 04       INC $04a9
$B3C1 a9 2b          LDA #$2b
$B3C3 4c 6d f2       JMP $f26d
$B3C6 a2 00          LDX #$00
$B3C8 20 7a e8       JSR $e87a
$B3CB 29 0f          AND #$0f
$B3CD c9 0b          CMP #$0b
$B3CF b0 f7          BCS $b3c8
$B3D1 7d b3 04       ADC $04b3,X
$B3D4 9d bd 04       STA $04bd,X
$B3D7 e8             INX
$B3D8 e0 02          CPX #$02
$B3DA 90 ec          BCC $b3c8
$B3DC a2 00          LDX #$00
$B3DE ad bd 04       LDA $04bd
$B3E1 cd be 04       CMP $04be
$B3E4 90 01          BCC $b3e7
$B3E6 e8             INX
$B3E7 8e aa 04       STX $04aa
$B3EA a9 01          LDA #$01
$B3EC 8d c0 04       STA $04c0
$B3EF 60             RTS

; AI_low_health, bank23, file$02F5E8
$B5D8 ad aa 04       LDA $04aa
$B5DB 49 01          EOR #$01
$B5DD a8             TAY
$B5DE b9 b1 04       LDA $04b1,Y
$B5E1 8d 10 00       STA $0010
$B5E4 ac aa 04       LDY $04aa
$B5E7 b9 ad 04       LDA $04ad,Y
$B5EA 20 87 f3       JSR $f387
$B5ED a0 00          LDY #$00
$B5EF b1 00          LDA ($00),Y
$B5F1 4a             LSR A
$B5F2 8d 11 00       STA $0011
$B5F5 ac aa 04       LDY $04aa
$B5F8 b9 b1 04       LDA $04b1,Y
$B5FB cd 11 00       CMP $0011
$B5FE b0 1f          BCS $b61f
$B600 cd 10 00       CMP $0010
$B603 b0 1d          BCS $b622
$B605 20 62 d2       JSR $d262
$B608 b0 18          BCS $b622
$B60A 20 b3 b7       JSR $b7b3
$B60D cd 10 00       CMP $0010
$B610 b0 10          BCS $b622
$B612 ad 10 00       LDA $0010
$B615 f0 0b          BEQ $b622
$B617 a9 03          LDA #$03
$B619 8d bf 04       STA $04bf
$B61C 4c a8 b7       JMP $b7a8
$B61F ee a9 04       INC $04a9
$B622 ee a9 04       INC $04a9
$B625 60             RTS

; AI_desperate, bank23, file$02F636
$B626 ad aa 04       LDA $04aa
$B629 49 01          EOR #$01
$B62B a8             TAY
$B62C b9 b1 04       LDA $04b1,Y
$B62F 8d 10 00       STA $0010
$B632 ac aa 04       LDY $04aa
$B635 b9 b1 04       LDA $04b1,Y
$B638 18             CLC
$B639 69 1e          ADC #$1e
$B63B cd 10 00       CMP $0010
$B63E b0 15          BCS $b655
$B640 20 dd b7       JSR $b7dd
$B643 cd 10 00       CMP $0010
$B646 b0 0d          BCS $b655
$B648 ad 10 00       LDA $0010
$B64B f0 08          BEQ $b655
$B64D a9 06          LDA #$06
$B64F 8d bf 04       STA $04bf
$B652 4c a8 b7       JMP $b7a8
$B655 ee a9 04       INC $04a9
$B658 60             RTS

; AI_attack, bank23, file$02F669
$B659 ac aa 04       LDY $04aa
$B65C b9 b1 04       LDA $04b1,Y
$B65F c9 1e          CMP #$1e
$B661 b0 22          BCS $b685
$B663 ac aa 04       LDY $04aa
$B666 49 01          EOR #$01
$B668 a8             TAY
$B669 b9 b1 04       LDA $04b1,Y
$B66C c9 32          CMP #$32
$B66E 90 15          BCC $b685
$B670 20 16 b8       JSR $b816
$B673 cd 10 00       CMP $0010
$B676 b0 0d          BCS $b685
$B678 ad 10 00       LDA $0010
$B67B f0 08          BEQ $b685
$B67D a9 02          LDA #$02
$B67F 8d bf 04       STA $04bf
$B682 4c a8 b7       JMP $b7a8
$B685 ee a9 04       INC $04a9
$B688 60             RTS

; AI_tactics, bank23, file$02F699
$B689 ac aa 04       LDY $04aa
$B68C b9 b5 04       LDA $04b5,Y
$B68F 29 7f          AND #$7f
$B691 f0 03          BEQ $b696
$B693 4c 15 b7       JMP $b715
$B696 b9 ad 04       LDA $04ad,Y
$B699 20 d7 f2       JSR $f2d7
$B69C a0 02          LDY #$02
$B69E b1 00          LDA ($00),Y
$B6A0 8d 10 00       STA $0010
$B6A3 ad aa 04       LDA $04aa
$B6A6 49 01          EOR #$01
$B6A8 a8             TAY
$B6A9 b9 ad 04       LDA $04ad,Y
$B6AC 20 d7 f2       JSR $f2d7
$B6AF a0 02          LDY #$02
$B6B1 b1 00          LDA ($00),Y
$B6B3 cd 10 00       CMP $0010
$B6B6 b0 15          BCS $b6cd
$B6B8 20 51 b8       JSR $b851
$B6BB cd 10 00       CMP $0010
$B6BE b0 0d          BCS $b6cd
$B6C0 ad 10 00       LDA $0010
$B6C3 f0 08          BEQ $b6cd
$B6C5 a9 07          LDA #$07
$B6C7 8d bf 04       STA $04bf
$B6CA 4c a8 b7       JMP $b7a8
$B6CD ac aa 04       LDY $04aa
$B6D0 b9 ad 04       LDA $04ad,Y
$B6D3 20 d7 f2       JSR $f2d7
$B6D6 a0 01          LDY #$01
$B6D8 b1 00          LDA ($00),Y
$B6DA 8d 10 00       STA $0010
$B6DD ad aa 04       LDA $04aa
$B6E0 49 01          EOR #$01
$B6E2 a8             TAY
$B6E3 b9 ad 04       LDA $04ad,Y
$B6E6 20 d7 f2       JSR $f2d7
$B6E9 a0 01          LDY #$01
$B6EB b1 00          LDA ($00),Y
$B6ED cd 10 00       CMP $0010
$B6F0 90 23          BCC $b715
$B6F2 20 9b b8       JSR $b89b
$B6F5 cd 10 00       CMP $0010
$B6F8 b0 1b          BCS $b715
$B6FA ac aa 04       LDY $04aa
$B6FD b9 b5 04       LDA $04b5,Y
$B700 30 13          BMI $b715
$B702 98             TYA
$B703 49 01          EOR #$01
$B705 a8             TAY
$B706 b9 b5 04       LDA $04b5,Y
$B709 29 7f          AND #$7f
$B70B d0 08          BNE $b715
$B70D a9 08          LDA #$08
$B70F 8d bf 04       STA $04bf
$B712 4c a8 b7       JMP $b7a8
$B715 ee a9 04       INC $04a9
$B718 60             RTS

; AI_fallback, bank23, file$02F729
$B719 a2 00          LDX #$00
$B71B ad aa 04       LDA $04aa
$B71E 49 01          EOR #$01
$B720 a8             TAY
$B721 b9 b1 04       LDA $04b1,Y
$B724 c9 1f          CMP #$1f
$B726 90 08          BCC $b730
$B728 a2 18          LDX #$18
$B72A c9 3d          CMP #$3d
$B72C 90 02          BCC $b730
$B72E a2 30          LDX #$30
$B730 ac aa 04       LDY $04aa
$B733 b9 b1 04       LDA $04b1,Y
$B736 c9 1f          CMP #$1f
$B738 90 11          BCC $b74b
$B73A 8a             TXA
$B73B 18             CLC
$B73C 69 08          ADC #$08
$B73E aa             TAX
$B73F b9 b1 04       LDA $04b1,Y
$B742 c9 3d          CMP #$3d
$B744 90 05          BCC $b74b
$B746 8a             TXA
$B747 18             CLC
$B748 69 08          ADC #$08
$B74A aa             TAX
$B74B 20 56 e8       JSR $e856
$B74E 8d 00 00       STA $0000
$B751 8a             TXA
$B752 18             CLC
$B753 6d 00 00       ADC $0000
$B756 aa             TAX
$B757 bd 60 b7       LDA $b760,X
$B75A 8d bf 04       STA $04bf
$B75D 4c a8 b7       JMP $b7a8

; pointer_high_gate, bank23, file$02F7C3
$B7B3 ac aa 04       LDY $04aa
$B7B6 b9 b1 04       LDA $04b1,Y
$B7B9 8d 10 00       STA $0010
$B7BC b9 ad 04       LDA $04ad,Y
$B7BF 4c d7 f2       JMP $f2d7

; desperate_threshold, bank23, file$02F7ED
$B7DD ac aa 04       LDY $04aa
$B7E0 b9 ad 04       LDA $04ad,Y
$B7E3 20 d7 f2       JSR $f2d7
$B7E6 a0 01          LDY #$01
$B7E8 b1 00          LDA ($00),Y
$B7EA 8d 10 00       STA $0010
$B7ED a0 02          LDY #$02
$B7EF b1 00          LDA ($00),Y
$B7F1 cd 10 00       CMP $0010
$B7F4 90 03          BCC $b7f9
$B7F6 8d 10 00       STA $0010
$B7F9 ac aa 04       LDY $04aa
$B7FC b9 b1 04       LDA $04b1,Y
$B7FF 18             CLC
$B800 6d 10 00       ADC $0010
$B803 8d 10 00       STA $0010
$B806 a9 7c          LDA #$7c
$B808 38             SEC
$B809 ed 10 00       SBC $0010
$B80C 10 02          BPL $b810
$B80E a9 00          LDA #$00
$B810 8d 10 00       STA $0010
$B813 4c 43 e8       JMP $e843

; attack_threshold, bank23, file$02F826
$B816 ad aa 04       LDA $04aa
$B819 49 01          EOR #$01
$B81B a8             TAY
$B81C b9 ad 04       LDA $04ad,Y
$B81F 20 d7 f2       JSR $f2d7
$B822 a0 01          LDY #$01
$B824 b1 00          LDA ($00),Y
$B826 8d 10 00       STA $0010
$B829 ac aa 04       LDY $04aa
$B82C b9 ad 04       LDA $04ad,Y
$B82F 20 d7 f2       JSR $f2d7
$B832 a0 01          LDY #$01
$B834 b1 00          LDA ($00),Y
$B836 38             SEC
$B837 ed 10 00       SBC $0010
$B83A 10 02          BPL $b83e
$B83C a9 00          LDA #$00
$B83E 8d 10 00       STA $0010
$B841 a9 32          LDA #$32
$B843 38             SEC
$B844 ed 10 00       SBC $0010
$B847 10 02          BPL $b84b
$B849 a9 00          LDA #$00
$B84B 8d 10 00       STA $0010
$B84E 4c 43 e8       JMP $e843

; negotiation_threshold, bank23, file$02F861
$B851 ac aa 04       LDY $04aa
$B854 b9 ad 04       LDA $04ad,Y
$B857 20 d7 f2       JSR $f2d7
$B85A a0 02          LDY #$02
$B85C b1 00          LDA ($00),Y
$B85E 8d 10 00       STA $0010
$B861 a0 04          LDY #$04
$B863 b1 00          LDA ($00),Y
$B865 18             CLC
$B866 6d 10 00       ADC $0010
$B869 8d 10 00       STA $0010
$B86C a0 01          LDY #$01
$B86E b1 00          LDA ($00),Y
$B870 8d 11 00       STA $0011
$B873 ad aa 04       LDA $04aa
$B876 49 01          EOR #$01
$B878 a8             TAY
$B879 b9 ad 04       LDA $04ad,Y
$B87C 20 d7 f2       JSR $f2d7
$B87F a0 03          LDY #$03
$B881 b1 00          LDA ($00),Y
$B883 18             CLC
$B884 6d 11 00       ADC $0011
$B887 8d 11 00       STA $0011
$B88A ad 10 00       LDA $0010
$B88D 38             SEC
$B88E ed 11 00       SBC $0011
$B891 10 02          BPL $b895
$B893 a9 00          LDA #$00
$B895 8d 10 00       STA $0010
$B898 4c 43 e8       JMP $e843

; status_threshold, bank23, file$02F8AB
$B89B ad aa 04       LDA $04aa
$B89E 49 01          EOR #$01
$B8A0 a8             TAY
$B8A1 b9 ad 04       LDA $04ad,Y
$B8A4 20 d7 f2       JSR $f2d7
$B8A7 a0 02          LDY #$02
$B8A9 b1 00          LDA ($00),Y
$B8AB 8d 10 00       STA $0010
$B8AE a0 01          LDY #$01
$B8B0 b1 00          LDA ($00),Y
$B8B2 38             SEC
$B8B3 ed 10 00       SBC $0010
$B8B6 b0 02          BCS $b8ba
$B8B8 a9 00          LDA #$00
$B8BA 18             CLC
$B8BB 69 0a          ADC #$0a
$B8BD 10 02          BPL $b8c1
$B8BF a9 00          LDA #$00
$B8C1 8d 10 00       STA $0010
$B8C4 4c 43 e8       JMP $e843

; retreat_response_gate, bank23, file$02FB28
$BB18 ad aa 04       LDA $04aa
$BB1B 49 01          EOR #$01
$BB1D a8             TAY
$BB1E b9 b3 04       LDA $04b3,Y
$BB21 0a             ASL A
$BB22 18             CLC
$BB23 8d 11 00       STA $0011
$BB26 20 43 e8       JSR $e843
$BB29 cd 11 00       CMP $0011
$BB2C b0 0a          BCS $bb38
$BB2E a9 09          LDA #$09
$BB30 8d a9 04       STA $04a9
$BB33 a9 3c          LDA #$3c
$BB35 4c 6d f2       JMP $f26d
$BB38 ee a9 04       INC $04a9
$BB3B a9 00          LDA #$00
$BB3D 4c 8b f2       JMP $f28b

; retreat_hp_penalty, bank23, file$02FB6B
$BB5B a9 0a          LDA #$0a
$BB5D 20 62 e8       JSR $e862
$BB60 18             CLC
$BB61 69 05          ADC #$05
$BB63 8d 2f 04       STA $042f
$BB66 a9 00          LDA #$00
$BB68 8d 30 04       STA $0430
$BB6B 8d 31 04       STA $0431
$BB6E ad aa 04       LDA $04aa
$BB71 49 01          EOR #$01
$BB73 a8             TAY
$BB74 b9 ad 04       LDA $04ad,Y
$BB77 8d 2c 04       STA $042c
$BB7A 20 d7 f2       JSR $f2d7
$BB7D a0 00          LDY #$00
$BB7F b1 00          LDA ($00),Y
$BB81 38             SEC
$BB82 ed 2f 04       SBC $042f
$BB85 10 02          BPL $bb89
$BB87 a9 00          LDA #$00
$BB89 91 00          STA ($00),Y
$BB8B ee a9 04       INC $04a9
$BB8E a9 3d          LDA #$3d
$BB90 4c 8b f2       JMP $f28b

; retreat_zero_result, bank23, file$02FBE0
$BBD0 ad aa 04       LDA $04aa
$BBD3 49 01          EOR #$01
$BBD5 a8             TAY
$BBD6 b9 ad 04       LDA $04ad,Y
$BBD9 8d 2c 04       STA $042c
$BBDC c0 01          CPY #$01
$BBDE d0 02          BNE $bbe2
$BBE0 a0 02          LDY #$02
$BBE2 a9 02          LDA #$02
$BBE4 99 15 05       STA $0515,Y
$BBE7 98             TYA
$BBE8 49 02          EOR #$02
$BBEA a8             TAY
$BBEB a9 00          LDA #$00
$BBED 99 15 05       STA $0515,Y
$BBF0 a9 0e          LDA #$0e
$BBF2 8d a8 04       STA $04a8
$BBF5 a9 00          LDA #$00
$BBF7 8d a9 04       STA $04a9
$BBFA a9 ff          LDA #$ff
$BBFC 8d c0 04       STA $04c0
$BBFF 60             RTS

; retreat_exit_result, bank23, file$02FC26
$BC16 ad aa 04       LDA $04aa
$BC19 49 01          EOR #$01
$BC1B 8d aa 04       STA $04aa
$BC1E f0 02          BEQ $bc22
$BC20 a0 02          LDY #$02
$BC22 a9 01          LDA #$01
$BC24 99 15 05       STA $0515,Y
$BC27 98             TYA
$BC28 49 02          EOR #$02
$BC2A a8             TAY
$BC2B a9 00          LDA #$00
$BC2D 99 15 05       STA $0515,Y
$BC30 a9 0f          LDA #$0f
$BC32 8d a8 04       STA $04a8
$BC35 a9 00          LDA #$00
$BC37 8d a9 04       STA $04a9
$BC3A 60             RTS

; surrender_exit, bank23, file$02FE4F
$BE3F a9 04          LDA #$04
$BE41 20 cb bd       JSR $bdcb
$BE44 20 99 d2       JSR $d299
$BE47 90 2e          BCC $be77
$BE49 20 3d d1       JSR $d13d
$BE4C ad 81 00       LDA $0081
$BE4F 29 03          AND #$03
$BE51 f0 24          BEQ $be77
$BE53 ac aa 04       LDY $04aa
$BE56 f0 02          BEQ $be5a
$BE58 a0 02          LDY #$02
$BE5A a9 03          LDA #$03
$BE5C 99 15 05       STA $0515,Y
$BE5F 98             TYA
$BE60 49 02          EOR #$02
$BE62 a8             TAY
$BE63 a9 00          LDA #$00
$BE65 99 15 05       STA $0515,Y
$BE68 a9 80          LDA #$80
$BE6A 8d c0 04       STA $04c0
$BE6D a9 0e          LDA #$0e
$BE6F 8d a8 04       STA $04a8
$BE72 a9 00          LDA #$00
$BE74 8d a9 04       STA $04a9
$BE77 60             RTS

; negotiation_choice, bank23, file$02FE96
$BE86 ad aa 04       LDA $04aa
$BE89 49 01          EOR #$01
$BE8B a8             TAY
$BE8C b9 ad 04       LDA $04ad,Y
$BE8F 20 d7 f2       JSR $f2d7
$BE92 a0 03          LDY #$03
$BE94 b1 00          LDA ($00),Y
$BE96 8d 10 00       STA $0010
$BE99 a0 00          LDY #$00
$BE9B b1 00          LDA ($00),Y
$BE9D 8d 11 00       STA $0011
$BEA0 ac aa 04       LDY $04aa
$BEA3 b9 ad 04       LDA $04ad,Y
$BEA6 20 d7 f2       JSR $f2d7
$BEA9 a0 02          LDY #$02
$BEAB b1 00          LDA ($00),Y
$BEAD 8d 12 00       STA $0012
$BEB0 a0 04          LDY #$04
$BEB2 b1 00          LDA ($00),Y
$BEB4 18             CLC
$BEB5 6d 12 00       ADC $0012
$BEB8 8d 12 00       STA $0012
$BEBB a2 00          LDX #$00
$BEBD ad 10 00       LDA $0010
$BEC0 c9 50          CMP #$50
$BEC2 b0 11          BCS $bed5
$BEC4 8a             TXA
$BEC5 18             CLC
$BEC6 69 18          ADC #$18
$BEC8 aa             TAX
$BEC9 ad 10 00       LDA $0010
$BECC c9 32          CMP #$32
$BECE b0 05          BCS $bed5
$BED0 8a             TXA
$BED1 18             CLC
$BED2 69 18          ADC #$18
$BED4 aa             TAX
$BED5 ad 11 00       LDA $0011
$BED8 c9 50          CMP #$50
$BEDA b0 11          BCS $beed
$BEDC 8a             TXA
$BEDD 18             CLC
$BEDE 69 08          ADC #$08
$BEE0 aa             TAX
$BEE1 ad 11 00       LDA $0011
$BEE4 c9 32          CMP #$32
$BEE6 b0 05          BCS $beed
$BEE8 8a             TXA
$BEE9 18             CLC
$BEEA 69 08          ADC #$08
$BEEC aa             TAX
$BEED ad 12 00       LDA $0012
$BEF0 c9 b4          CMP #$b4
$BEF2 b0 11          BCS $bf05
$BEF4 8a             TXA
$BEF5 18             CLC
$BEF6 69 48          ADC #$48
$BEF8 aa             TAX
$BEF9 ad 12 00       LDA $0012
$BEFC c9 82          CMP #$82
$BEFE b0 05          BCS $bf05
$BF00 8a             TXA
$BF01 18             CLC
$BF02 69 48          ADC #$48
$BF04 aa             TAX
$BF05 20 56 e8       JSR $e856
$BF08 8d 10 00       STA $0010
$BF0B 8a             TXA
$BF0C 18             CLC
$BF0D 6d 10 00       ADC $0010
$BF10 aa             TAX
$BF11 bd b2 bf       LDA $bfb2,X
$BF14 8d bf 04       STA $04bf
$BF17 18             CLC
$BF18 69 33          ADC #$33
$BF1A 8d be 04       STA $04be
$BF1D ad bf 04       LDA $04bf
$BF20 18             CLC
$BF21 69 2f          ADC #$2f
$BF23 8d bd 04       STA $04bd
$BF26 ad bf 04       LDA $04bf
$BF29 c9 03          CMP #$03
$BF2B b0 0b          BCS $bf38
$BF2D ad aa 04       LDA $04aa
$BF30 49 01          EOR #$01
$BF32 a8             TAY
$BF33 a9 02          LDA #$02
$BF35 99 c3 04       STA $04c3,Y
$BF38 a9 09          LDA #$09
$BF3A 8d a8 04       STA $04a8
$BF3D a9 00          LDA #$00
$BF3F 8d a9 04       STA $04a9
$BF42 60             RTS

; negotiation_exit, bank23, file$02FF53
$BF43 ad aa 04       LDA $04aa
$BF46 49 01          EOR #$01
$BF48 a8             TAY
$BF49 f0 02          BEQ $bf4d
$BF4B a0 02          LDY #$02
$BF4D a9 01          LDA #$01
$BF4F 99 15 05       STA $0515,Y
$BF52 98             TYA
$BF53 49 02          EOR #$02
$BF55 a8             TAY
$BF56 a9 00          LDA #$00
$BF58 99 15 05       STA $0515,Y
$BF5B a9 0f          LDA #$0f
$BF5D 8d a8 04       STA $04a8
$BF60 a9 00          LDA #$00
$BF62 8d a9 04       STA $04a9
$BF65 60             RTS
$BF66 a9 00          LDA #$00
$BF68 8d 15 05       STA $0515
$BF6B 8d 17 05       STA $0517
$BF6E a9 0e          LDA #$0e
$BF70 8d a8 04       STA $04a8
$BF73 a9 00          LDA #$00
$BF75 8d a9 04       STA $04a9
$BF78 a9 ff          LDA #$ff
$BF7A 8d c0 04       STA $04c0
$BF7D 60             RTS
$BF7E 20 99 d2       JSR $d299
$BF81 90 2e          BCC $bfb1
$BF83 20 3d d1       JSR $d13d
$BF86 ad 81 00       LDA $0081
$BF89 29 03          AND #$03
$BF8B f0 24          BEQ $bfb1
$BF8D ac aa 04       LDY $04aa
$BF90 f0 02          BEQ $bf94
$BF92 a0 02          LDY #$02
$BF94 a9 00          LDA #$00
$BF96 99 15 05       STA $0515,Y
$BF99 98             TYA
$BF9A 49 02          EOR #$02
$BF9C a8             TAY
$BF9D a9 04          LDA #$04
$BF9F 99 15 05       STA $0515,Y
$BFA2 a9 0e          LDA #$0e
$BFA4 8d a8 04       STA $04a8
$BFA7 a9 00          LDA #$00
$BFA9 8d a9 04       STA $04a9
$BFAC a9 ff          LDA #$ff
$BFAE 8d c0 04       STA $04c0
$BFB1 60             RTS

; status_effect, bank24, file$03009A
$C08A ac aa 04       LDY $04aa
$C08D a9 80          LDA #$80
$C08F 99 b5 04       STA $04b5,Y
$C092 98             TYA
$C093 49 01          EOR #$01
$C095 a8             TAY
$C096 b9 ad 04       LDA $04ad,Y
$C099 20 d7 f2       JSR $f2d7
$C09C a0 02          LDY #$02
$C09E b1 00          LDA ($00),Y
$C0A0 8d 11 00       STA $0011
$C0A3 ac aa 04       LDY $04aa
$C0A6 b9 ad 04       LDA $04ad,Y
$C0A9 20 d7 f2       JSR $f2d7
$C0AC a0 02          LDY #$02
$C0AE b1 00          LDA ($00),Y
$C0B0 8d 10 00       STA $0010
$C0B3 a0 04          LDY #$04
$C0B5 b1 00          LDA ($00),Y
$C0B7 18             CLC
$C0B8 6d 10 00       ADC $0010
$C0BB 38             SEC
$C0BC ed 11 00       SBC $0011
$C0BF b0 02          BCS $c0c3
$C0C1 a9 00          LDA #$00
$C0C3 8d 10 00       STA $0010
$C0C6 ee 10 00       INC $0010
$C0C9 20 5c e8       JSR $e85c
$C0CC c9 0a          CMP #$0a
$C0CE b0 f9          BCS $c0c9
$C0D0 6d 10 00       ADC $0010
$C0D3 c9 6e          CMP #$6e
$C0D5 b0 08          BCS $c0df
$C0D7 a9 2f          LDA #$2f
$C0D9 8d be 04       STA $04be
$C0DC 4c 03 c1       JMP $c103
$C0DF 20 50 e8       JSR $e850
$C0E2 8d 10 00       STA $0010
$C0E5 f0 f8          BEQ $c0df
$C0E7 ee 10 00       INC $0010
$C0EA ee 10 00       INC $0010
$C0ED ad aa 04       LDA $04aa
$C0F0 49 01          EOR #$01
$C0F2 a8             TAY
$C0F3 ad 10 00       LDA $0010
$C0F6 99 b5 04       STA $04b5,Y
$C0F9 a9 02          LDA #$02
$C0FB 99 c3 04       STA $04c3,Y
$C0FE a9 2e          LDA #$2e
$C100 8d be 04       STA $04be
$C103 a9 2d          LDA #$2d
$C105 8d bd 04       STA $04bd
$C108 a9 09          LDA #$09
$C10A 8d a8 04       STA $04a8
$C10D a9 00          LDA #$00
$C10F 8d a9 04       STA $04a9
$C112 8d bf 04       STA $04bf
$C115 60             RTS

; win_rewards, bank24, file$03036D
$C35D ae bd 04       LDX $04bd
$C360 bd 14 05       LDA $0514,X
$C363 c9 83          CMP #$83
$C365 d0 03          BNE $c36a
$C367 4c aa c3       JMP $c3aa
$C36A c9 ad          CMP #$ad
$C36C d0 03          BNE $c371
$C36E 4c c0 c3       JMP $c3c0
$C371 c9 b6          CMP #$b6
$C373 d0 03          BNE $c378
$C375 4c 01 c4       JMP $c401
$C378 c9 de          CMP #$de
$C37A d0 03          BNE $c37f
$C37C 4c 2e c4       JMP $c42e
$C37F ad e1 6f       LDA $6fe1
$C382 29 01          AND #$01
$C384 d0 1e          BNE $c3a4
$C386 a9 00          LDA #$00
$C388 8d 10 00       STA $0010
$C38B 20 68 f3       JSR $f368
$C38E a0 00          LDY #$00
$C390 b1 00          LDA ($00),Y
$C392 dd 14 05       CMP $0514,X
$C395 d0 03          BNE $c39a
$C397 4c e3 c3       JMP $c3e3
$C39A ee 10 00       INC $0010
$C39D ad 10 00       LDA $0010
$C3A0 c9 07          CMP #$07
$C3A2 90 e7          BCC $c38b
$C3A4 a9 01          LDA #$01
$C3A6 8d a9 04       STA $04a9
$C3A9 60             RTS
$C3AA a9 64          LDA #$64
$C3AC 20 62 e8       JSR $e862
$C3AF c9 1e          CMP #$1e
$C3B1 b0 f1          BCS $c3a4
$C3B3 a9 06          LDA #$06
$C3B5 8d 10 00       STA $0010
$C3B8 a9 3f          LDA #$3f
$C3BA 8d 11 00       STA $0011
$C3BD 4c 0b c4       JMP $c40b
$C3C0 ad bd 04       LDA $04bd
$C3C3 49 02          EOR #$02
$C3C5 aa             TAX
$C3C6 bd 14 05       LDA $0514,X
$C3C9 20 d7 f2       JSR $f2d7
$C3CC a0 0b          LDY #$0b
$C3CE b1 00          LDA ($00),Y
$C3D0 29 f0          AND #$f0
$C3D2 c9 20          CMP #$20
$C3D4 b0 ce          BCS $c3a4
$C3D6 a9 07          LDA #$07
$C3D8 8d 10 00       STA $0010
$C3DB a9 40          LDA #$40
$C3DD 8d 11 00       STA $0011
$C3E0 4c 0b c4       JMP $c40b
$C3E3 a9 64          LDA #$64
$C3E5 20 62 e8       JSR $e862
$C3E8 c9 32          CMP #$32
$C3EA b0 b8          BCS $c3a4
$C3EC ad e1 6f       LDA $6fe1
$C3EF 09 01          ORA #$01
$C3F1 8d e1 6f       STA $6fe1
$C3F4 a9 0e          LDA #$0e
$C3F6 8d 10 00       STA $0010
$C3F9 a9 41          LDA #$41
$C3FB 8d 11 00       STA $0011
$C3FE 4c 0b c4       JMP $c40b
$C401 a9 05          LDA #$05
$C403 8d 10 00       STA $0010
$C406 a9 3e          LDA #$3e
$C408 8d 11 00       STA $0011
$C40B ad bd 04       LDA $04bd
$C40E 49 02          EOR #$02
$C410 aa             TAX
$C411 bd 14 05       LDA $0514,X
$C414 8d 2c 04       STA $042c
$C417 20 d7 f2       JSR $f2d7
$C41A a0 0a          LDY #$0a
$C41C b1 00          LDA ($00),Y
$C41E 29 e0          AND #$e0
$C420 0d 10 00       ORA $0010
$C423 91 00          STA ($00),Y
$C425 ee a9 04       INC $04a9
$C428 ad 11 00       LDA $0011
$C42B 4c 8b f2       JMP $f28b
$C42E ad bd 04       LDA $04bd
$C431 49 02          EOR #$02
$C433 aa             TAX
$C434 bd 14 05       LDA $0514,X
$C437 8d 2c 04       STA $042c
$C43A 20 d7 f2       JSR $f2d7
$C43D a0 0a          LDY #$0a
$C43F b1 00          LDA ($00),Y
$C441 29 1f          AND #$1f
$C443 09 e0          ORA #$e0
$C445 91 00          STA ($00),Y
$C447 ee a9 04       INC $04a9
$C44A a9 42          LDA #$42
$C44C 4c 8b f2       JMP $f28b

; ruler_predicate, bank24, file$031272
$D262 ac aa 04       LDY $04aa
$D265 b9 ad 04       LDA $04ad,Y
$D268 8d 10 00       STA $0010
$D26B a2 00          LDX #$00
$D26D 8a             TXA
$D26E 20 68 f3       JSR $f368
$D271 a0 00          LDY #$00
$D273 b1 00          LDA ($00),Y
$D275 cd 10 00       CMP $0010
$D278 f0 07          BEQ $d281
$D27A e8             INX
$D27B e0 07          CPX #$07
$D27D 90 ee          BCC $d26d
$D27F 18             CLC
$D280 60             RTS
$D281 38             SEC
$D282 60             RTS
