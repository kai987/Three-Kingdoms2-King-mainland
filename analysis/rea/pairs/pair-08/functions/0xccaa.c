
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ccaa(void)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  bool bVar4;
  byte bStack0000;
  
  bStack0000 = 0xcc;
  FUN_f25f(0x31);
  bVar2 = 0;
  DAT_001a = 0;
  DAT_001b = 0;
  DAT_001c = 0;
  DAT_001d = 0;
  do {
    cVar3 = (&DAT_0664)[bVar2];
    if (cVar3 != -1) {
      DAT_0002 = cVar3;
      bStack0000 = bVar2;
      officer_address(cVar3);
      bVar2 = bStack0000;
      DAT_0002 = *(byte *)(_DAT_0000 + 8);
      DAT_0003 = *(char *)(_DAT_0000 + 9);
      bVar1 = 0;
      cVar3 = '\0';
      bStack0000 = 0xcc;
      FUN_cc92();
      if (cVar3 != '\0') {
        bVar1 = 2;
      }
      bVar4 = CARRY1(*(byte *)(bVar1 + 0x1a),DAT_0002);
      *(byte *)(bVar1 + 0x1a) = *(byte *)(bVar1 + 0x1a) + DAT_0002;
      *(char *)(bVar1 + 0x1b) = *(char *)(bVar1 + 0x1b) + DAT_0003 + bVar4;
    }
    bVar2 = bVar2 + 1;
  } while (bVar2 < 0x14);
  return;
}

