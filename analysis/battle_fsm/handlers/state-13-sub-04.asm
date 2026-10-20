; main=13 sub=4: 败方武将转移或转为在野
; entry bank13 $CE76; file $01AE86
; Direct calls within bank12/13 execute recovered local IR; fixed/far calls are explicit dependencies.
01AE86 b13:$CE76 20 29 CC       JSR  $CC29 ; draw_postbattle_units
01AE89 b13:$CE79 20 27 DF       JSR  $DF27 ; text_jobs_idle
01AE8C b13:$CE7C 90 1F          BCC  $CE9D
01AE8E b13:$CE7E AE 0A 05       LDX  $050A
01AE91 b13:$CE81 A9 FF          LDA  #$FF
01AE93 b13:$CE83 9D 2C 04       STA  $042C,X
01AE96 b13:$CE86 A9 E0          LDA  #$E0
01AE98 b13:$CE88 85 E6          STA  $E6
01AE9A b13:$CE8A 85 E7          STA  $E7
01AE9C b13:$CE8C EE 01 05       INC  $0501
01AE9F b13:$CE8F A9 00          LDA  #$00
01AEA1 b13:$CE91 85 8E          STA  $8E
01AEA3 b13:$CE93 85 90          STA  $90
01AEA5 b13:$CE95 A9 00          LDA  #$00
01AEA7 b13:$CE97 8D 24 04       STA  $0424
01AEAA b13:$CE9A 8D 25 04       STA  $0425
01AEAD b13:$CE9D 60             RTS
