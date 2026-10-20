
void FUN_c337(void)

{
  byte bVar1;
  byte bVar2;
  char cVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xc3;
  FUN_f266(0x30);
  if ((*(byte *)(DAT_6f5e + 0x8ffc) & 1) != 0) {
    while( true ) {
      uStack0000 = 0xc3;
      FUN_c3ff();
      if (DAT_0038 == -1) break;
      uStack0000 = 0xc3;
      FUN_d105(DAT_6f5e);
      if ((DAT_003a & 0x1f) == 0) {
        cVar3 = '\0';
        uStack0000 = 0xc3;
        FUN_c3a4(0x18);
        if (cVar3 == '\0') break;
        bVar2 = 10;
        uStack0000 = 0xc3;
        bVar1 = FUN_d2ab(DAT_0038);
        *(byte *)(DAT_0022 + (ushort)bVar2) = bVar1 & 0x1f | DAT_003a;
        uStack0000 = 0xc3;
        FUN_d152(5);
      }
      else {
        cVar3 = '\0';
        uStack0000 = 0xc3;
        FUN_c3a4((DAT_003a & 0x1f) << 1);
        if (cVar3 == '\0') break;
        bVar2 = 10;
        uStack0000 = 0xc3;
        bVar1 = FUN_d2ab(DAT_0038);
        *(byte *)(DAT_0022 + (ushort)bVar2) = bVar1 & 0xe0 | DAT_003a;
        uStack0000 = 0xc3;
        FUN_d152(5);
      }
    }
  }
  FUN_bec7();
  return;
}

