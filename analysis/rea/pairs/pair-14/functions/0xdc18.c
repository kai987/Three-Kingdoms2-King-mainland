
void FUN_dc18(byte param_1,byte param_2)

{
  if (param_2 < 0x10) {
    *(byte *)(param_2 + 0x4003) = param_1 & 7 | 8;
    return;
  }
  LAB_f800 = param_2 << 1 | 0x62;
  DAT_4800 = param_1;
  return;
}

