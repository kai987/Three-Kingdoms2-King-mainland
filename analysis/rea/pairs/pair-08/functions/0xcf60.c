
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_cf60(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = 0;
  do {
    if ((&DAT_0664)[bVar1] == 'm') {
      uStack0000 = 0xcf;
      DAT_052f = bVar1;
      officer_address(0x6d);
      if ((*(byte *)(_DAT_0000 + 0xb) & 3) != 3) {
        DAT_052c = *(byte *)(_DAT_0000 + 0xb) & 0xf0;
        DAT_052e = *(undefined1 *)(_DAT_0000 + 1);
      }
      return;
    }
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x14);
  return;
}

