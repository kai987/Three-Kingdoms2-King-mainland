
void FUN_cdb9(undefined1 param_1)

{
  byte bVar1;
  byte bVar2;
  byte bVar3;
  byte bVar4;
  byte bVar5;
  undefined1 uStack0000;
  
  uStack0000 = param_1;
  FUN_d105(DAT_0038);
  DAT_0020 = CONCAT11(*(undefined1 *)(DAT_0020 + (ushort)(byte)(DAT_0036 + 1)),
                      *(undefined1 *)(DAT_0020 + (ushort)DAT_0036));
  DAT_0022._1_1_ = uStack0000;
  DAT_0022._0_1_ = 0;
  uStack0000 = 0xcd;
  FUN_d438();
  DAT_0020 = CONCAT11(DAT_0027,DAT_0026);
  DAT_0022._0_1_ = DAT_0028;
  DAT_0022._1_1_ = 100;
  DAT_0024 = 0;
  uStack0000 = 0xcd;
  FUN_d336();
  DAT_002a = (byte)DAT_0020;
  DAT_002b = DAT_0020._1_1_;
  uStack0000 = 0xcd;
  FUN_d105(DAT_0038);
  bVar5 = DAT_0036;
  bVar4 = *(byte *)(DAT_0020 + (ushort)DAT_0036) - DAT_002a;
  bVar1 = ~*(byte *)(DAT_0020 + (ushort)DAT_0036);
  bVar2 = DAT_002a & (bVar1 | bVar4);
  *(byte *)(DAT_0020 + (ushort)DAT_0036) = bVar4;
  bVar3 = *(byte *)(DAT_0020 + (ushort)(byte)(bVar5 + 1));
  bVar2 = (bVar3 - DAT_002b) - (((bVar2 | bVar4 & bVar1) & 0x80) == 0);
  bVar3 = ~bVar3;
  bVar1 = DAT_002b & (bVar3 | bVar2);
  *(byte *)(DAT_0020 + (ushort)(byte)(bVar5 + 1)) = bVar2;
  bVar4 = DAT_0036;
  if (((bVar1 | bVar2 & bVar3) & 0x80) == 0) {
    *(undefined1 *)(DAT_0020 + (ushort)DAT_0036) = 0;
    *(undefined1 *)(DAT_0020 + (ushort)(byte)(bVar4 + 1)) = 0;
  }
  return;
}

