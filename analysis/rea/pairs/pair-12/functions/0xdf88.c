
void FUN_df88(void)

{
  if (DAT_0061 == '\x05') {
    if (DAT_008e < 0x10) {
      DAT_0068 = 0x72;
      return;
    }
    DAT_0068 = 0x74;
  }
  return;
}

