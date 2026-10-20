
void FUN_ab10(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xab;
  FUN_d105(DAT_0038);
  bVar2 = 0;
  bVar3 = 0x11;
  do {
    if (*(char *)(bVar2 + 0x664) != -1) {
      *(char *)(DAT_0020 + (ushort)bVar3) = *(char *)(bVar2 + 0x664);
      bVar3 = bVar3 + 1;
    }
    bVar2 = bVar2 + 1;
  } while (bVar2 < 10);
  DAT_0024 = 0;
  do {
    cVar1 = *(char *)(DAT_0024 + 0x66e);
    if (cVar1 != -1) {
      DAT_0026 = cVar1;
      *(undefined1 *)(DAT_0024 + 0x66e) = 0xff;
      uStack0000 = 0xab;
      DAT_0025 = FUN_d2ab(cVar1,3);
      uStack0000 = 0xab;
      bVar2 = FUN_d4bb(100);
      if (bVar2 < DAT_0025) {
        DAT_0040 = DAT_6f03;
        DAT_0041 = DAT_0026;
        DAT_0042 = 1;
        uStack0000 = 0xab;
        FUN_aba3();
      }
      else {
        uStack0000 = 0xab;
        FUN_ab71();
      }
    }
    DAT_0024 = DAT_0024 + 1;
  } while (DAT_0024 < 10);
  return;
}

