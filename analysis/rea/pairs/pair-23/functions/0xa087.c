
void FUN_a087(void)

{
  char cVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  DAT_2000 = DAT_008b & 0xfb;
  DAT_2006 = DAT_0000;
  bVar2 = 0;
  DAT_0002 = *DAT_000a;
  uStack0000 = 0xa0;
  FUN_a0d2();
  while( true ) {
    while (DAT_000a[bVar2] != DAT_0002) {
      uStack0000 = 0xa0;
      DAT_2007 = DAT_000a[bVar2];
      FUN_a0d2();
    }
    uStack0000 = 0xa0;
    FUN_a0d2();
    cVar1 = DAT_000a[bVar2];
    if (cVar1 == '\0') break;
    uStack0000 = 0xa0;
    FUN_a0d2();
    DAT_2007 = DAT_000a[bVar2];
    do {
      cVar1 = cVar1 + -1;
    } while (cVar1 != '\0');
    uStack0000 = 0xa0;
    FUN_a0d2();
  }
  return;
}

