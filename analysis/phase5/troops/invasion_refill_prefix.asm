;WritesE8/03: exactly1000; prior funding and later AP excluded.
;Exact bounded entry/prefix; no linear-data-as-code claim.
01455B b10:$A54B A0 08      LDY  #$08
01455D b10:$A54D A9 E8      LDA  #$E8
01455F b10:$A54F 91 22      STA  ($22),Y
014561 b10:$A551 C8         INY
014562 b10:$A552 A9 03      LDA  #$03
014564 b10:$A554 91 22      STA  ($22),Y
