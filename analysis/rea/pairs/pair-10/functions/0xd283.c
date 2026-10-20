
undefined1 FUN_d283(byte param_1,byte param_2)

{
  DAT_0020 = CONCAT11((((CARRY1(param_1 * '\x02',param_1) - ((char)param_1 >> 7)) * '\x02' |
                       (byte)(param_1 * '\x03') >> 7) << 1 | (param_1 * '\x03' & 0x7f) >> 6) + 99 +
                      (0x3f < (byte)(param_1 * '\f')),param_1 * '\f' - 0x40);
  return *(undefined1 *)(DAT_0020 + (ushort)param_2);
}

