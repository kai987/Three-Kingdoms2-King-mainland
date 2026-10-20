
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_dc99(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xdc;
  FUN_f25f(0x31);
  bVar1 = DAT_0402 << 2;
  DAT_0512 = *(byte *)(bVar1 + 0x9d5a) + 0x80;
  bVar2 = ~*(byte *)(bVar1 + 0x9d5a);
  DAT_0513 = *(byte *)(bVar1 + 0x9d5b) -
             (((bVar2 & 0x80) == 0 && (DAT_0512 & 0x80) == 0) && (DAT_0512 & bVar2 & 0x80) == 0);
  if ((DAT_0513 & ~*(byte *)(bVar1 + 0x9d5b) & 0x80) == 0) {
    DAT_0512 = 0;
    DAT_0513 = 0;
  }
  if (DAT_0513 != 0) {
    DAT_0512 = 0xfe;
    DAT_0513 = 0;
  }
  DAT_0510 = *(byte *)(bVar1 + 0x9d58) + 0xa0;
  DAT_0511 = *(byte *)(bVar1 + 0x9d59) - ((DAT_0510 & ~*(byte *)(bVar1 + 0x9d58) & 0x80) == 0);
  if ((DAT_0511 & ~*(byte *)(bVar1 + 0x9d59) & 0x80) == 0) {
    DAT_0510 = 0;
    DAT_0511 = 0;
  }
  if (0x8f < DAT_0510) {
    DAT_0510 = 0x8e;
    DAT_0511 = 0;
  }
  DAT_052a = DAT_0402;
  DAT_050c = 0;
  DAT_050d = 0;
  DAT_051a = 0;
  DAT_051b = 0;
  DAT_051c = 0;
  DAT_051d = 0;
  DAT_051e = 0;
  DAT_051f = 0;
  DAT_0520 = 0;
  DAT_0521 = 0;
  DAT_052b = 0xff;
  bVar2 = 0x27;
  do {
    *(undefined1 *)(bVar2 + 0x6f47) = 0xff;
    bVar2 = bVar2 - 1;
  } while (-1 < (char)bVar2);
  bVar2 = 0x13;
  do {
    if (*(char *)(bVar2 + 0x664) == -1) {
      *(undefined1 *)(bVar2 + 0x600) = 0xff;
      *(undefined1 *)(bVar2 + 0x614) = 0xff;
      *(undefined1 *)(bVar2 + 0x628) = 0xff;
      *(undefined1 *)(bVar2 + 0x63c) = 0xff;
      *(undefined1 *)(bVar2 + 0x650) = 0xff;
    }
    else {
      uStack0000 = 0xdd;
      officer_address();
      *(undefined1 *)(bVar2 + 0x600) = 0xff;
      *(undefined1 *)(bVar2 + 0x614) = 0xff;
      bVar1 = *(byte *)(_DAT_0000 + 0xb) >> 2 & 3;
      if (9 < bVar2) {
        bVar1 = bVar1 | 0x80;
      }
      *(byte *)(bVar2 + 0x628) = bVar1;
      *(undefined1 *)(bVar2 + 0x650) = 0;
    }
    bVar2 = bVar2 - 1;
  } while (-1 < (char)bVar2);
  uStack0000 = 0xdd;
  FUN_db03();
  return;
}

