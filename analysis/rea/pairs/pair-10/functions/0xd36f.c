
byte FUN_d36f(undefined1 param_1)

{
  byte bVar1;
  byte bVar2;
  undefined1 uVar3;
  byte bVar4;
  bool bVar5;
  undefined1 uStack0000;
  
  uStack0000 = param_1;
  FUN_d105();
  if (DAT_0024 != '\0') {
    bVar4 = FUN_d4bb();
    bVar5 = CARRY1(bVar4,(byte)DAT_0022);
    DAT_0022._0_1_ = bVar4 + (byte)DAT_0022;
    DAT_0022._1_1_ = DAT_0022._1_1_ + bVar5;
  }
  uVar3 = uStack0000;
  uStack0000 = 0xd3;
  FUN_d105(uVar3);
  uStack0000 = 0xd3;
  FUN_d69d();
  bVar1 = *(byte *)(DAT_0020 + 2) - (byte)DAT_0022;
  bVar4 = ~*(byte *)(DAT_0020 + 2);
  bVar2 = (*(byte *)(DAT_0020 + 3) - DAT_0022._1_1_) -
          ((((byte)DAT_0022 & (bVar4 | bVar1) | bVar1 & bVar4) & 0x80) == 0);
  bVar4 = ~*(byte *)(DAT_0020 + 3);
  if (((DAT_0022._1_1_ & (bVar4 | bVar2) | bVar2 & bVar4) & 0x80) == 0) {
    return bVar1;
  }
  *(byte *)(DAT_0020 + 3) = bVar2;
  *(byte *)(DAT_0020 + 2) = bVar1;
  uStack0000 = 0xd3;
  bVar4 = FUN_d69d();
  return bVar4;
}

