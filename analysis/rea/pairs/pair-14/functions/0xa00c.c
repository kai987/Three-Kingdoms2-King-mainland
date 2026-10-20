
void thunk_FUN_df6e(byte param_1)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xdf;
  FUN_dc31();
  if ((DAT_07f4 & 0x80) == 0x80) {
    *(undefined1 *)(DAT_07f5 + 0x4000) = *(undefined1 *)(param_1 + 0x706);
    return;
  }
  if (*(char *)(param_1 + 0x70c) != '\0') {
    FUN_dc59();
    return;
  }
  if (DAT_07f5 < 0x10) {
    *(byte *)(DAT_07f5 + 0x4000) =
         (*(byte *)(param_1 + 0x706) & 0x10) << 1 | *(byte *)(param_1 + 0x706);
    return;
  }
  LAB_f800 = (DAT_07f5 << 1 | 0x67) - 1;
  DAT_4800 = (*(byte *)(param_1 + 0x706) & 0xc0) >> 3;
  return;
}

