
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

byte thunk_FUN_b8d7(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xb8;
  region_address(DAT_0470);
  DAT_0498 = *(undefined1 *)(_DAT_0000 + 2);
  DAT_0499 = *(undefined1 *)(_DAT_0000 + 3);
  DAT_049a = *(undefined1 *)(_DAT_0000 + 4);
  DAT_049b = *(undefined1 *)(_DAT_0000 + 5);
  DAT_049c = *(byte *)(_DAT_0000 + 0x10);
  DAT_049d = 0;
  uStack0000 = 0xb9;
  region_address(DAT_0471);
  DAT_0010._0_1_ = 0xf - *(byte *)(_DAT_0000 + 2);
  DAT_0010._1_1_ =
       ('\'' - *(char *)(_DAT_0000 + 3)) -
       (((*(byte *)(_DAT_0000 + 2) & ((byte)DAT_0010 | 0xf0) | (byte)DAT_0010 & 0xf0) & 0x80) == 0);
  uStack0000 = 0xb9;
  FUN_b948(0);
  DAT_0010._0_1_ = 0xf - *(byte *)(_DAT_0000 + 4);
  DAT_0010._1_1_ =
       ('\'' - *(char *)(_DAT_0000 + 5)) -
       (((*(byte *)(_DAT_0000 + 4) & ((byte)DAT_0010 | 0xf0) | (byte)DAT_0010 & 0xf0) & 0x80) == 0);
  uStack0000 = 0xb9;
  FUN_b948(2);
  DAT_0010._0_1_ = 99 - *(char *)(_DAT_0000 + 0x10);
  DAT_0010._1_1_ = 0;
  bVar1 = -(((DAT_049c & (~(byte)DAT_0010 | (byte)DAT_0010 - DAT_049c) |
             (byte)DAT_0010 - DAT_049c & ~(byte)DAT_0010) & 0x80) == 0) - DAT_049d;
  if (((DAT_049d | bVar1) & 0x80) == 0) {
    bVar1 = 0;
    DAT_049d = 0;
    DAT_049c = (byte)DAT_0010;
  }
  return bVar1;
}

