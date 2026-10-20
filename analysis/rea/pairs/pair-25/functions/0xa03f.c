
void FUN_a03f(byte param_1)

{
  undefined1 uStack0000;
  
  DAT_00a1 = param_1;
  do {
    DAT_6f41 = 0xf0;
    DAT_6f04 = DAT_6f04 + 1;
    if (6 < DAT_6f04) {
      DAT_6f04 = 0;
      DAT_6f06 = 0;
      DAT_6f01 = DAT_6f01 + 1;
      if (0xb < DAT_6f01) {
        DAT_6f01 = 0;
        DAT_6f00 = DAT_6f00 + '\x01';
      }
      uStack0000 = 0xa0;
      FUN_a209();
    }
    DAT_6f03 = (&DAT_a104)[(byte)(DAT_6f45 << 3 | DAT_6f04)];
    DAT_00ee = (char *)CONCAT11((&DAT_a0d7)[(byte)(DAT_6f03 << 1)],
                                (&DAT_a0d6)[(byte)(DAT_6f03 << 1)]);
  } while (*DAT_00ee == -1);
  uStack0000 = 0xa0;
  FUN_a240();
  if (DAT_0010._1_1_ < 0x1e) {
    DAT_0401 = 3;
    FUN_f28b(0xd5);
    return;
  }
  uStack0000 = 0xa0;
  FUN_a19f(DAT_6f03 & 7);
  DAT_6f05 = (&DAT_a0e4)[DAT_0003];
  uStack0000 = 0xa0;
  far_call_inline_word(0x3d);
  *(char *)(param_1 + 0xa0a0) = *(char *)(param_1 + 0xa0a0) << 1;
  uStack0000 = 0xa0;
  (*(code *)IRQ)();
  return;
}

