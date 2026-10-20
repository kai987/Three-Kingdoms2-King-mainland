
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ca19(void)

{
  char cVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  DAT_0040 = 0;
  do {
    uStack0000 = 0xca;
    FUN_d319(DAT_0040);
    cVar1 = *_DAT_0024;
    if ((cVar1 != -1) && (DAT_0038 = cVar1, _DAT_0024[3] == '\x03')) {
      uStack0000 = 0xca;
      bVar2 = FUN_d2ab(cVar1,0xb);
      if ((bVar2 & 3) != 2) {
        *(byte *)(DAT_0022 + 0xb) = *(byte *)(DAT_0022 + 0xb) & 0xfc | 3;
        uStack0000 = 0xca;
        FUN_ca68();
      }
      uStack0000 = 0xca;
      FUN_c98f(DAT_0040);
    }
    DAT_0040 = DAT_0040 + 1;
  } while (DAT_0040 < 7);
  uStack0000 = 0xca;
  FUN_d249();
  FUN_bec7();
  return;
}

