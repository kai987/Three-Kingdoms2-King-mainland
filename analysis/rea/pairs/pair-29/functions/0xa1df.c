
void FUN_a1df(void)

{
  DAT_00a6._0_1_ = (char)DAT_00a6 + '\x01';
  if ((char)DAT_00a6 == '\0') {
    DAT_00a6._1_1_ = DAT_00a6._1_1_ + '\x01';
  }
  return;
}

