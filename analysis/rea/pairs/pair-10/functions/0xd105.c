
byte FUN_d105(byte param_1)

{
  undefined1 uStack0000;
  
  DAT_0020 = (byte *)CONCAT11((((((param_1 >> 7) << 1 | (param_1 & 0x7f) >> 6) << 1 |
                                (param_1 & 0x3f) >> 5) << 1 | (param_1 & 0x1f) >> 4) << 1 |
                              (param_1 & 0xf) >> 3) + 0x60,param_1 * ' ');
  uStack0000 = 0xd1;
  FUN_d69d();
  return *DAT_0020 & 7;
}

