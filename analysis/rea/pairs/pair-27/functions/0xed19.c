
void FUN_ed19(void)

{
  undefined1 uStack0000;
  
  DAT_0000 = 1;
  if ((DAT_0081 & 0x80) != 0) {
    uStack0000 = 0xed;
    FUN_ed71();
  }
  if ((DAT_0081 & 0x40) != 0) {
    uStack0000 = 0xed;
    FUN_ed8d();
  }
  if ((DAT_0081 & 0x20) != 0) {
    uStack0000 = 0xed;
    FUN_eda9();
  }
  if ((DAT_0081 & 0x10) != 0) {
    uStack0000 = 0xed;
    FUN_edbe();
  }
  uStack0000 = 0xed;
  DAT_0012 = FUN_eddd();
  return;
}

