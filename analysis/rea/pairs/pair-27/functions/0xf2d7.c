
void officer_address(byte param_1)

{
  DAT_0000 = param_1 * '\f' - 0x40;
  DAT_0001 = (((CARRY1(param_1 * '\x02',param_1) - ((char)param_1 >> 7)) * '\x02' |
              (byte)(param_1 * '\x03') >> 7) << 1 | (param_1 * '\x03' & 0x7f) >> 6) + 99 +
             (0x3f < (byte)(param_1 * '\f'));
  return;
}

