
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a485(char param_1)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  DAT_000c = DAT_008e;
  DAT_000d = DAT_008f;
  DAT_000f = DAT_0091;
  DAT_000e = DAT_0090;
  if ((char)(DAT_007e << 1) < '\0') {
    return;
  }
  uStack0000 = 0xa4;
  FUN_a604(DAT_007e << 1);
  uStack0000 = 0xa4;
  DAT_001a = param_1;
  FUN_a61f();
  DAT_0010 = *(undefined1 *)(DAT_00a8 + (ushort)(byte)(DAT_001a + 1));
  uStack0000 = 0xa4;
  FUN_a961();
  DAT_0008._0_1_ = DAT_000c >> 4;
  DAT_0005 = (DAT_000e & 0xf0) + (byte)DAT_0008;
  DAT_0006 = 0;
  do {
    uStack0000 = 0xa4;
    FUN_a5a5(*(undefined1 *)((short)_DAT_0000 + (ushort)DAT_0005));
    DAT_0018 = DAT_0018 + '\x01';
    bVar1 = DAT_0005 + 1;
    bVar2 = DAT_0005 & 0xf;
    DAT_0005 = bVar1;
    if (bVar2 == 0xf) {
      uStack0000 = 0xa4;
      FUN_a61f(DAT_0010);
      DAT_0005 = DAT_0005 - 1 & 0xf0;
    }
    DAT_0006 = DAT_0006 + 1;
  } while (DAT_0006 < 0x11);
  _DAT_0000 = &DAT_0164;
  uStack0000 = 0xa5;
  FUN_a89a();
  DAT_007e = DAT_007e | 0x40;
  return;
}

