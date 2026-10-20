
void FUN_dc59(char param_1,byte param_2)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  bool bVar4;
  
  DAT_07f7 = 0;
  bVar2 = *(byte *)(param_2 + 0x70e);
  cVar3 = '\x03';
  do {
    bVar1 = bVar2 * '\x02';
    bVar4 = false;
    bVar2 = bVar1;
    if (*(byte *)(param_2 + 0x70d) <= bVar1) {
      bVar2 = bVar1 - *(byte *)(param_2 + 0x70d);
      bVar4 = ((*(byte *)(param_2 + 0x70d) & (~bVar1 | bVar2) | bVar2 & ~bVar1) & 0x80) != 0;
    }
    DAT_07f7 = DAT_07f7 << 1 | bVar4;
    cVar3 = cVar3 + -1;
  } while (-1 < cVar3);
  bVar2 = *(byte *)(param_2 + 0x706) & 0xc0;
  if (DAT_07f5 < 0x10) {
    *(byte *)(DAT_07f5 + 0x4000) =
         bVar2 | (&DAT_de6e)
                 [*(byte *)(param_2 + 0x706) & 0xf | (&DAT_ddce)[(byte)(param_1 << 4 | DAT_07f7)]];
    return;
  }
  LAB_f800 = (DAT_07f5 << 1 | 0x67) - 1;
  DAT_4800 = (bVar2 | (&DAT_de6e)
                      [*(byte *)(param_2 + 0x706) & 0xf |
                       (&DAT_ddce)[(byte)(param_1 << 4 | DAT_07f7)]] & 0xc0) >> 3;
  return;
}

