
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a465(char param_1)

{
  byte bStack0000;
  
  DAT_000c = DAT_008e - 8;
  DAT_000d = DAT_008f + (7 < DAT_008e);
  DAT_000e = DAT_0090;
  DAT_000f = DAT_0091;
  if ((char)DAT_007e < '\0') {
    return;
  }
  bStack0000 = 0xa3;
  FUN_a604();
  bStack0000 = 0xa3;
  DAT_001a = param_1;
  FUN_a61f();
  DAT_0010 = *(undefined1 *)(DAT_00a8 + (ushort)(byte)(DAT_001a + 2));
  bStack0000 = 0xa3;
  FUN_a93f();
  DAT_0006 = 0;
  DAT_0007 = '\0';
  DAT_0008._0_1_ = DAT_000c >> 4;
  DAT_0005 = (DAT_000e & 0xf0) + (byte)DAT_0008;
  do {
    bStack0000 = 0xa4;
    FUN_a545(*(undefined1 *)((short)_DAT_0000 + (ushort)DAT_0005));
    DAT_0019 = DAT_0019 + '\x01';
    bStack0000 = DAT_0005 + 0x10;
    if (0xef < bStack0000) {
      bStack0000 = bStack0000 & 0xf;
      FUN_a61f(DAT_0010);
      DAT_0007 = DAT_0007 + '\x01';
      DAT_0019 = DAT_0019 + '\x01';
    }
    DAT_0006 = DAT_0006 + 1;
    DAT_0005 = bStack0000;
  } while (DAT_0006 < 0x10);
  _DAT_0000 = &DAT_0140;
  bStack0000 = 0xa4;
  FUN_a89a();
  DAT_007e = DAT_007e | 0x80;
  return;
}

