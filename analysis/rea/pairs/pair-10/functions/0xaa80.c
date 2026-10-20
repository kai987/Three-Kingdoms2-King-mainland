
void FUN_aa80(void)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  uStack0000 = 0xaa;
  FUN_d105(DAT_0038);
  bVar1 = 0;
  bVar2 = 0x11;
  do {
    if (*(char *)(bVar1 + 0x66e) != -1) {
      *(char *)(DAT_0020 + (ushort)bVar2) = *(char *)(bVar1 + 0x66e);
      bVar2 = bVar2 + 1;
    }
    bVar1 = bVar1 + 1;
  } while (bVar1 < 10);
  DAT_0024 = 0;
  do {
    if (*(char *)(DAT_0024 + 0x664) != -1) {
      uStack0000 = 0xaa;
      DAT_0026 = *(char *)(DAT_0024 + 0x664);
      bVar1 = FUN_d2ab(3);
      if (bVar1 != 100) {
        uStack0000 = 0xaa;
        DAT_0025 = bVar1;
        bVar1 = FUN_d4bb(100);
        if (DAT_0025 <= bVar1) {
          uStack0000 = 0xaa;
          FUN_aade();
          goto LAB_aad5;
        }
      }
      DAT_0040 = DAT_003e;
      DAT_0041 = DAT_0026;
      DAT_0042 = 1;
      uStack0000 = 0xaa;
      FUN_aba3();
    }
LAB_aad5:
    DAT_0024 = DAT_0024 + 1;
    if (9 < DAT_0024) {
      return;
    }
  } while( true );
}

