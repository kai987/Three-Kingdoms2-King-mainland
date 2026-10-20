
void FUN_c80a(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = 0xf;
  do {
    (&DAT_6f73)[bVar1] = 0xff;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  uStack0000 = 200;
  FUN_f266(0x30);
  DAT_0024 = DAT_0036 << 3;
  do {
    uStack0000 = 200;
    bVar1 = FUN_d4ad(8);
    if (((&DAT_6f73)[bVar1] != '\0') &&
       ((&DAT_6f73)[bVar1] = 0, -1 < *(char *)((byte)(bVar1 + DAT_0024) + 0x9d72))) {
      uStack0000 = 200;
      FUN_c84d();
    }
    bVar1 = 0;
    while ((&DAT_6f73)[bVar1] != -1) {
      bVar1 = bVar1 + 1;
      if (7 < bVar1) {
        return;
      }
    }
  } while( true );
}

