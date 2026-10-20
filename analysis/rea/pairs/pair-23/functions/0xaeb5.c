
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_aeb5(char param_1)

{
  byte bVar1;
  byte bVar2;
  undefined1 uStack0000;
  
  DAT_000c = DAT_008e + 4;
  DAT_000d = DAT_008f + (0xfb < DAT_008e);
  DAT_000e = DAT_0090 + 0xa0;
  if ((DAT_0090 < 0x60) && (DAT_000e < 0xf0)) {
    DAT_000f = DAT_0091;
  }
  else {
    DAT_000e = DAT_0090 + 0xb0;
    DAT_000f = DAT_0091 + '\x01';
  }
  uStack0000 = 0xad;
  FUN_a604();
  uStack0000 = 0xad;
  DAT_000a._0_1_ = param_1;
  FUN_aef3();
  DAT_000a._0_1_ = *(undefined1 *)(DAT_00a8 + (ushort)(byte)((char)DAT_000a + 1));
  DAT_0006 = 0;
  DAT_0008._0_1_ = DAT_000c >> 5;
  DAT_0005 = ((DAT_000e & 0xe0) >> 2) + (byte)DAT_0008;
  uStack0000 = 0xad;
  FUN_b055();
  DAT_0007 = 8;
  if ((DAT_000c & 0x10) != 0) {
    DAT_0007 = 9;
  }
  do {
    DAT_0002 = *(undefined1 *)((short)_DAT_0000 + (ushort)DAT_0005);
    uStack0000 = 0xae;
    FUN_afb5();
    DAT_0016 = DAT_0016 + '\x02';
    DAT_0018 = DAT_0018 + '\x02';
    uStack0000 = 0xae;
    FUN_ae58();
    bVar1 = DAT_0005 + 1;
    bVar2 = DAT_0005 & 7;
    DAT_0005 = bVar1;
    if (bVar2 == 7) {
      uStack0000 = 0xae;
      FUN_aef3((char)DAT_000a);
      DAT_0005 = DAT_0005 - 1 & 0xf8;
    }
    DAT_0006 = DAT_0006 + 1;
  } while (DAT_0006 < DAT_0007);
  _DAT_0000 = &DAT_019c;
  uStack0000 = 0xae;
  FUN_a8d3();
  DAT_007e = DAT_007e | 0x10;
  return;
}

