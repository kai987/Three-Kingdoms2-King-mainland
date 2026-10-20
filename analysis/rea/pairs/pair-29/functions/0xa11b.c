
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a11b(void)

{
  char cVar1;
  byte bVar2;
  
  DAT_2000 = DAT_008b & 0xfb;
  _DAT_0000 = 0x380;
  bVar2 = 0;
  while (cVar1 = *(char *)(bVar2 + 0x380), cVar1 != -1) {
    DAT_2006 = *(undefined1 *)((byte)(bVar2 + 2) + 0x380);
    bVar2 = bVar2 + 3;
    do {
      DAT_2007 = *(undefined1 *)(bVar2 + 0x380);
      bVar2 = bVar2 + 1;
      cVar1 = cVar1 + -1;
    } while (cVar1 != '\0');
  }
  return;
}

