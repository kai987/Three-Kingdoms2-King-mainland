
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_ab94(char param_1)

{
  byte bVar1;
  byte bStack0000;
  
  DAT_000c = DAT_008e;
  DAT_000d = DAT_008f;
  DAT_000e = DAT_0090;
  DAT_000f = DAT_0091;
  DAT_001c = DAT_008e;
  DAT_001d = DAT_008f + '\x01';
  DAT_001e = DAT_0090;
  DAT_001f = DAT_0091;
  bStack0000 = 0xab;
  FUN_a604();
  bStack0000 = 0xab;
  DAT_000a._0_1_ = param_1;
  FUN_aef3();
  bVar1 = (char)DAT_000a + 2;
  DAT_000a._0_1_ = *(undefined1 *)(DAT_00a8 + (ushort)bVar1);
  bStack0000 = 0xab;
  FUN_a610();
  bStack0000 = 0xab;
  DAT_001a = bVar1;
  FUN_af0c();
  DAT_001a = *(undefined1 *)(DAT_00a8 + (ushort)(byte)(DAT_001a + 2));
  DAT_0006 = 0;
  DAT_0008._0_1_ = DAT_000c >> 5;
  DAT_0005 = ((DAT_000e & 0xe0) >> 2) + (byte)DAT_0008;
  bStack0000 = 0xac;
  FUN_aff9();
  DAT_0007 = 8;
  if ((DAT_000e & 0x10) != 0) {
    DAT_0007 = 9;
  }
  do {
    DAT_0002 = *(undefined1 *)((short)_DAT_0000 + (ushort)DAT_0005);
    DAT_0003 = *(undefined1 *)(_DAT_0010 + (ushort)DAT_0005);
    bStack0000 = 0xac;
    FUN_af1b();
    DAT_0017 = DAT_0017 + '\x02';
    DAT_0019 = DAT_0019 + '\x02';
    bStack0000 = 0xac;
    FUN_ac80();
    bStack0000 = DAT_0005 + 8;
    if (0x3f < bStack0000) {
      bStack0000 = bStack0000 & 7;
      FUN_aef3((char)DAT_000a);
      FUN_af0c(DAT_001a);
    }
    DAT_0006 = DAT_0006 + 1;
    DAT_0005 = bStack0000;
  } while (DAT_0006 < DAT_0007);
  _DAT_0000 = &DAT_0188;
  bStack0000 = 0xac;
  FUN_a8d3();
  DAT_007e = DAT_007e | 0x20;
  return;
}

