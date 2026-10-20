
void FUN_dc3f(byte param_1)

{
  if ((DAT_07f4 & 0x80) != 0x80) {
    DAT_07f7 = (*(byte *)(DAT_00f0 + (ushort)param_1) & 1) << 6 |
               (*(byte *)(DAT_00f0 + (ushort)param_1) >> 1) << 7;
    return;
  }
  DAT_07f7 = *(byte *)(DAT_00f0 + (ushort)param_1) & 0x7f;
  return;
}

