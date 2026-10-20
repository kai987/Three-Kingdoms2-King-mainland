
void FUN_aebf(void)

{
  byte bVar1;
  char cVar2;
  bool bVar3;
  undefined1 uStack0000;
  
  DAT_0024 = 0;
  DAT_0025 = 0;
  DAT_0026 = '\0';
  do {
    if (*(char *)(DAT_0024 + 0x664) != -1) {
      cVar2 = '\b';
      uStack0000 = 0xae;
      bVar1 = FUN_d2ab();
      bVar3 = CARRY1(bVar1,DAT_0025);
      DAT_0025 = bVar1 + DAT_0025;
      DAT_0026 = *(char *)(DAT_0022 + (ushort)(byte)(cVar2 + 1)) + DAT_0026 + bVar3;
    }
    DAT_0024 = DAT_0024 + 1;
  } while (DAT_0024 < 10);
  DAT_0020._1_1_ = DAT_0025;
  DAT_0022 = CONCAT11(100,DAT_0026);
  DAT_0024 = 0;
  uStack0000 = 0xae;
  FUN_d40f();
  DAT_0020._0_1_ = DAT_0020._1_1_;
  DAT_0020._1_1_ = (undefined1)DAT_0022;
  DAT_0022 = (ushort)(byte)(DAT_6f8d << 2) << 8;
  uStack0000 = 0xaf;
  FUN_d438();
  DAT_0020._1_1_ = DAT_0026;
  DAT_0022 = CONCAT11(10,DAT_0027);
  DAT_0024 = 0;
  uStack0000 = 0xaf;
  FUN_d40f();
  DAT_002a = DAT_0020._1_1_;
  DAT_002b = (undefined1)DAT_0022;
  DAT_0024 = 0;
  DAT_0025 = 0;
  DAT_0026 = '\0';
  do {
    if (*(char *)(DAT_0024 + 0x66e) != -1) {
      cVar2 = '\b';
      uStack0000 = 0xaf;
      bVar1 = FUN_d2ab();
      bVar3 = CARRY1(bVar1,DAT_0025);
      DAT_0025 = bVar1 + DAT_0025;
      DAT_0026 = *(char *)(DAT_0022 + (ushort)(byte)(cVar2 + 1)) + DAT_0026 + bVar3;
    }
    DAT_0024 = DAT_0024 + 1;
  } while (DAT_0024 < 10);
  DAT_0020._1_1_ = DAT_0025;
  DAT_0022 = CONCAT11(100,DAT_0026);
  DAT_0024 = 0;
  uStack0000 = 0xaf;
  FUN_d40f();
  DAT_0020._0_1_ = DAT_0020._1_1_;
  DAT_0020._1_1_ = (undefined1)DAT_0022;
  DAT_0022 = (ushort)(byte)(DAT_6f8d << 2) << 8;
  uStack0000 = 0xaf;
  FUN_d438();
  DAT_0020._1_1_ = DAT_0026;
  DAT_0022 = CONCAT11(10,DAT_0027);
  DAT_0024 = 0;
  uStack0000 = 0xaf;
  FUN_d40f();
  DAT_002c = DAT_0020._1_1_;
  DAT_002d = (undefined1)DAT_0022;
  return;
}

