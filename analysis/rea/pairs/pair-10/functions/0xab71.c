
void FUN_ab71(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xab;
  FUN_d105(DAT_0038);
  bVar1 = 0x11;
  do {
    if (*(char *)(DAT_0020 + (ushort)bVar1) == -1) {
      *(undefined1 *)(DAT_0020 + (ushort)bVar1) = DAT_0026;
      DAT_0020 = CONCAT11(DAT_0020._1_1_,DAT_0026);
      uStack0000 = 0xab;
      FUN_d00c();
      return;
    }
    bVar1 = bVar1 + 1;
  } while (bVar1 < 0x1b);
  DAT_0040 = DAT_003e;
  DAT_0041 = DAT_0026;
  DAT_0042 = 0;
  FUN_aba3();
  return;
}

