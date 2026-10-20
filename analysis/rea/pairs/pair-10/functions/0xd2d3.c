
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

undefined1 FUN_d2d3(byte param_1)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xd2;
  DAT_0026 = param_1;
  bVar1 = FUN_f266(0x31);
  _DAT_0024 = CONCAT11((((CARRY1(bVar1 * '\x02',bVar1) - ((char)bVar1 >> 7)) * '\x02' |
                        (byte)(bVar1 * '\x03') >> 7) << 1 | (bVar1 * '\x03' & 0x7f) >> 6) + 0x80,
                       bVar1 * '\f');
  return *(undefined1 *)(_DAT_0024 + (ushort)DAT_0026);
}

