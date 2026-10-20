
void FUN_af1b(void)

{
  undefined1 uStack0000;
  
  if ((DAT_000c + 8U & 0x10) != 0) {
    uStack0000 = 0xaf;
    FUN_af30();
    uStack0000 = 0xaf;
    FUN_af71();
    return;
  }
  uStack0000 = 0xaf;
  FUN_af30();
  return;
}

