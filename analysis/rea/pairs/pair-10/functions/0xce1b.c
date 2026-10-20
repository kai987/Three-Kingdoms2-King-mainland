
void FUN_ce1b(undefined1 param_1)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  byte bVar4;
  undefined1 uStack0000;
  
  uStack0000 = param_1;
  FUN_d105(DAT_0038);
  DAT_0022._1_1_ = uStack0000;
  DAT_0020 = (ushort)*(byte *)(DAT_0020 + DAT_0036);
  DAT_0022._0_1_ = 0;
  uStack0000 = 0xce;
  FUN_d438();
  DAT_0020 = CONCAT11(DAT_0027,DAT_0026);
  DAT_0022._0_1_ = DAT_0028;
  DAT_0022._1_1_ = 100;
  DAT_0024 = 0;
  uStack0000 = 0xce;
  FUN_d336();
  DAT_002a = (byte)DAT_0020;
  uStack0000 = 0xce;
  FUN_d105(DAT_0038);
  bVar4 = DAT_0036;
  bVar3 = *(byte *)(DAT_0020 + DAT_0036) - DAT_002a;
  bVar1 = ~*(byte *)(DAT_0020 + DAT_0036);
  bVar2 = DAT_002a & (bVar1 | bVar3);
  *(byte *)(DAT_0020 + DAT_0036) = bVar3;
  if (((bVar2 | bVar3 & bVar1) & 0x80) == 0) {
    *(undefined1 *)(DAT_0020 + bVar4) = 0;
  }
  return;
}

