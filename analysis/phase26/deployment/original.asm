08:B2AE a0 30        LDY imm $0030
08:B2B0 20 66 f2     JSR abs $F266
08:B2B3 ad 0e 05     LDA abs $050E
08:B2B6 0a           ASL acc $0000
08:B2B7 0a           ASL acc $0000
08:B2B8 0a           ASL acc $0000
08:B2B9 a8           TAY imp $0000
08:B2BA b9 72 9d     LDA aby $9D72
08:B2BD 10 05        BPL rel $B2C4
08:B2BF a9 00        LDA imm $0000
08:B2C1 4c d9 b2     JMP abs $B2D9
08:B2C4 cd 2a 05     CMP abs $052A
08:B2C7 f0 04        BEQ rel $B2CD
08:B2C9 c8           INY imp $0000
08:B2CA 4c ba b2     JMP abs $B2BA
08:B2CD 98           TYA imp $0000
08:B2CE 48           PHA imp $0000
08:B2CF a0 31        LDY imm $0031
08:B2D1 20 66 f2     JSR abs $F266
08:B2D4 68           PLA imp $0000
08:B2D5 a8           TAY imp $0000
08:B2D6 b9 b4 9a     LDA aby $9AB4
08:B2D9 8d 20 00     STA abs $0020
08:B2DC 0a           ASL acc $0000
08:B2DD 0a           ASL acc $0000
08:B2DE 0a           ASL acc $0000
08:B2DF 0a           ASL acc $0000
08:B2E0 0a           ASL acc $0000
08:B2E1 8d 20 00     STA abs $0020
08:B2E4 a0 26        LDY imm $0026
08:B2E6 20 66 f2     JSR abs $F266
08:B2E9 ad 0e 05     LDA abs $050E
08:B2EC 0a           ASL acc $0000
08:B2ED a8           TAY imp $0000
08:B2EE b9 52 8c     LDA aby $8C52
08:B2F1 18           CLC imp $0000
08:B2F2 6d 20 00     ADC abs $0020
08:B2F5 8d 20 00     STA abs $0020
08:B2F8 b9 53 8c     LDA aby $8C53
08:B2FB 69 00        ADC imm $0000
08:B2FD 8d 21 00     STA abs $0021
08:B300 a0 00        LDY imm $0000
08:B302 b9 0e b3     LDA aby $B30E
08:B305 99 22 00     STA aby $0022
08:B308 c8           INY imp $0000
08:B309 c0 04        CPY imm $0004
08:B30B 90 f5        BCC rel $B302
08:B30D 60           RTS imp $0000
08:B312 a0 30        LDY imm $0030
08:B314 20 66 f2     JSR abs $F266
08:B317 ad 0e 05     LDA abs $050E
08:B31A 0a           ASL acc $0000
08:B31B 0a           ASL acc $0000
08:B31C 0a           ASL acc $0000
08:B31D a8           TAY imp $0000
08:B31E b9 72 9d     LDA aby $9D72
08:B321 10 05        BPL rel $B328
08:B323 a9 00        LDA imm $0000
08:B325 4c 34 b3     JMP abs $B334
08:B328 cd 2a 05     CMP abs $052A
08:B32B f0 04        BEQ rel $B331
08:B32D c8           INY imp $0000
08:B32E 4c 1e b3     JMP abs $B31E
08:B331 b9 62 9e     LDA aby $9E62
08:B334 8d 20 00     STA abs $0020
08:B337 0a           ASL acc $0000
08:B338 0a           ASL acc $0000
08:B339 0a           ASL acc $0000
08:B33A 0a           ASL acc $0000
08:B33B 18           CLC imp $0000
08:B33C 6d 20 00     ADC abs $0020
08:B33F 0a           ASL acc $0000
08:B340 8d 20 00     STA abs $0020
08:B343 a0 26        LDY imm $0026
08:B345 20 66 f2     JSR abs $F266
08:B348 ad 0e 05     LDA abs $050E
08:B34B 0a           ASL acc $0000
08:B34C a8           TAY imp $0000
08:B34D b9 00 80     LDA aby $8000
08:B350 18           CLC imp $0000
08:B351 6d 20 00     ADC abs $0020
08:B354 8d 20 00     STA abs $0020
08:B357 b9 01 80     LDA aby $8001
08:B35A 69 00        ADC imm $0000
08:B35C 8d 21 00     STA abs $0021
08:B35F a0 00        LDY imm $0000
08:B361 b9 6d b3     LDA aby $B36D
08:B364 99 22 00     STA aby $0022
08:B367 c8           INY imp $0000
08:B368 c0 04        CPY imm $0004
08:B36A 90 f5        BCC rel $B361
08:B36C 60           RTS imp $0000
