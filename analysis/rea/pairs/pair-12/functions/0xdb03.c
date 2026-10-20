
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_db03(void)

{
  char cVar1;
  byte bVar2;
  byte bStack0000;
  
  bStack0000 = 0xdb;
  FUN_f25f(0x31);
  bVar2 = 0x13;
  do {
    cVar1 = *(char *)(bVar2 + 0x664);
    bStack0000 = bVar2;
    if (*(char *)(bVar2 + 0x664) != -1) {
      bStack0000 = 0xdb;
      officer_address();
      _DAT_0000 = *(ushort *)(_DAT_0000 + 8) & 0x3ff;
      DAT_0002 = 0;
      DAT_0003 = 100;
      DAT_0004 = 0;
      bStack0000 = bVar2;
      FUN_eaa5();
      cVar1 = DAT_0000;
    }
    *(char *)(bStack0000 + 0x63c) = cVar1;
    bVar2 = bStack0000 - 1;
  } while (-1 < (char)bVar2);
  return;
}

