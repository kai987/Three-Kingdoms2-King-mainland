
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ce40(void)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  bool bVar4;
  byte bStack0000;
  
  bStack0000 = 0;
  do {
    if (((*(byte *)(bStack0000 + 0x650) != 0) &&
        (bVar2 = *(byte *)(bStack0000 + 0x650) & DAT_0010, bVar2 != 0)) &&
       (*(byte *)(bStack0000 + 0x650) = bVar2 - DAT_0011, DAT_0011 == '\x10')) {
      officer_address((&DAT_0664)[bStack0000]);
      do {
        bVar2 = FUN_e87a();
      } while (0x46 < bVar2);
      DAT_0002 = *(byte *)(_DAT_0000 + 8) - (bVar2 + 0x50);
      bVar1 = ~*(byte *)(_DAT_0000 + 8);
      cVar3 = *(char *)(_DAT_0000 + 9) -
              (((bVar2 + 0x50 & (bVar1 | DAT_0002) | DAT_0002 & bVar1) & 0x80) == 0);
      if (cVar3 < '\0') {
        cVar3 = '\0';
        DAT_0002 = 0;
      }
      *(char *)(_DAT_0000 + 9) = cVar3;
      *(byte *)(_DAT_0000 + 8) = DAT_0002;
      bVar4 = CARRY1(DAT_0002,DAT_000b);
      DAT_000b = DAT_0002 + DAT_000b;
      DAT_000c = DAT_000c + bVar4;
    }
    bStack0000 = bStack0000 + 1;
  } while (bStack0000 < 0x14);
  return;
}

