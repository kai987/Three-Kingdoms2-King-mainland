
void FUN_cd00(void)

{
  undefined1 uStack0000;
  
  DAT_001e = '\x1e' - DAT_0506;
  uStack0000 = 0xcd;
  FUN_ccaa();
  DAT_0000 = DAT_001a;
  DAT_0001 = DAT_001b;
  uStack0000 = 0xcd;
  FUN_cd43();
  DAT_001a = DAT_0006;
  DAT_001b = DAT_0007;
  DAT_0000 = DAT_001c;
  DAT_0001 = DAT_001d;
  uStack0000 = 0xcd;
  FUN_cd43();
  DAT_001c = DAT_0006;
  DAT_001d = DAT_0007;
  return;
}

