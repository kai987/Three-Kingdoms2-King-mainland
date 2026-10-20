; troop_loss: physical bank 12, CPU $B68B..$B6EF
; File offset $01969B, exact byte SHA256 f01f7c3f15bf35c7cb8deee7011e115bd3141409add5f3257c11cea117008dcb
; Reconstructed evidence listing, not original source. Known pointer/table data is marked.
$B68B | $01969B | A0 08    | LDY  #$08
$B68D | $01969D | B1 00    | LDA  ($00),Y
$B68F | $01969F | 85 04    | STA  $04
$B691 | $0196A1 | C8       | INY
$B692 | $0196A2 | B1 00    | LDA  ($00),Y
$B694 | $0196A4 | 29 03    | AND  #$03
$B696 | $0196A6 | 85 05    | STA  $05
$B698 | $0196A8 | A5 04    | LDA  $04
$B69A | $0196AA | 38       | SEC
$B69B | $0196AB | E5 02    | SBC  $02
$B69D | $0196AD | 85 06    | STA  $06
$B69F | $0196AF | A5 05    | LDA  $05
$B6A1 | $0196B1 | E5 03    | SBC  $03
$B6A3 | $0196B3 | 85 07    | STA  $07
$B6A5 | $0196B5 | B0 0E    | BCS  $B6B5
$B6A7 | $0196B7 | A5 04    | LDA  $04
$B6A9 | $0196B9 | 85 02    | STA  $02
$B6AB | $0196BB | A5 05    | LDA  $05
$B6AD | $0196BD | 85 03    | STA  $03
$B6AF | $0196BF | A9 00    | LDA  #$00
$B6B1 | $0196C1 | 85 06    | STA  $06
$B6B3 | $0196C3 | 85 07    | STA  $07
$B6B5 | $0196C5 | A0 08    | LDY  #$08
$B6B7 | $0196C7 | A5 06    | LDA  $06
$B6B9 | $0196C9 | 91 00    | STA  ($00),Y
$B6BB | $0196CB | C8       | INY
$B6BC | $0196CC | A5 07    | LDA  $07
$B6BE | $0196CE | 91 00    | STA  ($00),Y
$B6C0 | $0196D0 | A5 02    | LDA  $02
$B6C2 | $0196D2 | 18       | CLC
$B6C3 | $0196D3 | 6D 2C 04 | ADC  $042C
$B6C6 | $0196D6 | 8D 2C 04 | STA  $042C
$B6C9 | $0196D9 | A5 03    | LDA  $03
$B6CB | $0196DB | 6D 2D 04 | ADC  $042D
$B6CE | $0196DE | 8D 2D 04 | STA  $042D
$B6D1 | $0196E1 | A9 00    | LDA  #$00
$B6D3 | $0196E3 | 8D 2E 04 | STA  $042E
$B6D6 | $0196E6 | AC 0A 05 | LDY  $050A
$B6D9 | $0196E9 | B9 64 06 | LDA  $0664,Y
$B6DC | $0196EC | 85 0A    | STA  $0A
$B6DE | $0196EE | AD 2C 04 | LDA  $042C
$B6E1 | $0196F1 | 85 0B    | STA  $0B
$B6E3 | $0196F3 | AD 2D 04 | LDA  $042D
$B6E6 | $0196F6 | 85 0C    | STA  $0C
$B6E8 | $0196F8 | A0 2E    | LDY  #$2E
$B6EA | $0196FA | 20 07 EE | JSR  $EE07
$B6ED | $0196FD | .word $A006 ; EE07 inline far-call target
$B6EF | $0196FF | 60       | RTS
