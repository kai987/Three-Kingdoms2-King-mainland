
void FUN_bbde(void)

{
  if (DAT_04e4 == '\0') {
    return;
  }
  *(byte *)((DAT_0402 >> 3) + 0x4e0) =
       *(byte *)((DAT_0402 >> 3) + 0x4e0) | (&DAT_bbfa)[DAT_0402 & 7];
  return;
}

