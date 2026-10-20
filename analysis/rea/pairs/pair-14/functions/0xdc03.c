
void FUN_dc03(undefined1 param_1,byte param_2)

{
  if (param_2 < 0x10) {
    *(undefined1 *)(param_2 + 0x4002) = param_1;
    return;
  }
  LAB_f800 = param_2 << 1 | 0x60;
  DAT_4800 = param_1;
  return;
}

