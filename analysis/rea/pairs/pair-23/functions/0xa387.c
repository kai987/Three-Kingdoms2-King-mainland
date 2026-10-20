
void FUN_a387(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = DAT_008e;
  if (0xfd < DAT_008e) {
    bVar1 = DAT_008e + 2;
  }
  if (bVar1 >> 3 != DAT_0093) {
    uStack0000 = 0xa3;
    DAT_0093 = bVar1 >> 3;
    FUN_a3b1();
  }
  if (DAT_0090 >> 3 != DAT_0092) {
    uStack0000 = 0xa3;
    DAT_0092 = DAT_0090 >> 3;
    FUN_a3bc();
  }
  return;
}

