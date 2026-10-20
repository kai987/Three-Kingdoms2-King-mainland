
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b371(void)

{
  char cVar1;
  byte bVar2;
  byte bStack0000;
  
  DAT_002a = DAT_6f91 + 10;
  cVar1 = '\0';
  bVar2 = DAT_6f91;
  do {
    if ((&DAT_0664)[bVar2] != -1) {
      cVar1 = cVar1 + '\x01';
    }
    bVar2 = bVar2 + 1;
  } while (bVar2 < DAT_002a);
  DAT_6f94 = cVar1 - 1;
  if (DAT_6f94 < 2) {
    return;
  }
  bStack0000 = 1;
  do {
    DAT_002b = DAT_6f91 + DAT_6f94;
    bVar2 = DAT_6f91 + 1;
    do {
      FUN_b491((&DAT_0664)[bVar2]);
      DAT_002a = *(byte *)(_DAT_0020 + 1);
      FUN_b491(*(undefined1 *)(bVar2 + 0x665));
      if (DAT_002a <= *(byte *)(_DAT_0020 + 1)) {
        FUN_b3d2();
      }
      bVar2 = bVar2 + 1;
    } while (bVar2 < DAT_002b);
    bStack0000 = bStack0000 + 1;
  } while (bStack0000 < DAT_6f94);
  return;
}

