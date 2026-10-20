
void thunk_FUN_ab53(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = (byte)(DAT_008e - 6U) >> 3;
  if (bVar1 != DAT_0095) {
    uStack0000 = 0xab;
    DAT_0095 = bVar1;
    FUN_ab7b();
    return;
  }
  if (DAT_0090 >> 4 != DAT_0094) {
    uStack0000 = 0xab;
    DAT_0094 = DAT_0090 >> 4;
    FUN_ab87();
  }
  return;
}

