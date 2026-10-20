
void FUN_ccf8(void)

{
  byte bVar1;
  char cVar2;
  bool bVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xcc;
  FUN_d105(DAT_0036);
  DAT_0037 = 0x11;
  DAT_0038 = 0;
  DAT_0039 = '\0';
  do {
    if (*(char *)(DAT_0020 + (ushort)DAT_0037) != -1) {
      cVar2 = '\b';
      uStack0000 = 0xcd;
      bVar1 = FUN_d2ab();
      bVar3 = CARRY1(bVar1,DAT_0038);
      DAT_0038 = bVar1 + DAT_0038;
      DAT_0039 = DAT_0039 + *(char *)(DAT_0022 + (ushort)(byte)(cVar2 + 1)) + bVar3;
    }
    DAT_0037 = DAT_0037 + 1;
  } while (DAT_0037 < 0x1b);
  bVar1 = DAT_0039 << 1 | DAT_0038 >> 7;
  DAT_0020._1_1_ = DAT_0038 * '\x03';
  DAT_0022 = CONCAT11(0x19,bVar1 + DAT_0039 + CARRY1(DAT_0038 * '\x02',DAT_0038));
  DAT_0024 = 0;
  uStack0000 = 0xcd;
  DAT_0038 = DAT_0038 * '\x02';
  DAT_0039 = bVar1;
  FUN_d40f();
  DAT_0039 = DAT_0020._1_1_;
  DAT_003a = (undefined1)DAT_0022;
  return;
}

