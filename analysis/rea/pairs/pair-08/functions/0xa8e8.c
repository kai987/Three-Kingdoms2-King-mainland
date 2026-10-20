
void FUN_a8e8(void)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  bVar3 = 0;
  do {
    *(undefined1 *)(bVar3 + 0x6fc9) = 0;
    if ((&DAT_0664)[bVar3] != -1) {
      bVar2 = *(char *)(bVar3 + 0x600) - DAT_0020;
      if ((char)bVar2 < '\0') {
        bVar2 = (bVar2 ^ 0xff) + 1;
      }
      if ((bVar2 == DAT_0022) || (bVar2 < DAT_0022)) {
        bVar1 = *(byte *)(bVar3 + 0x614);
        if (0xf < bVar1) {
          bVar1 = bVar1 - 1;
        }
        bVar1 = bVar1 - DAT_0021;
        if ((char)bVar1 < '\0') {
          bVar1 = (bVar1 ^ 0xff) + 1;
        }
        if ((bVar1 == DAT_0022) || (DAT_0023._0_1_ = bVar2, DAT_0022 > bVar1)) {
          DAT_0023._0_1_ = bVar1 + bVar2 + (DAT_0022 <= bVar1);
          uStack0000 = 0xa9;
          bVar2 = FUN_a944();
          *(byte *)(bVar3 + 0x6fc9) = bVar2 | (byte)DAT_0023;
        }
      }
    }
    bVar3 = bVar3 + 1;
  } while (bVar3 < 0x14);
  return;
}

