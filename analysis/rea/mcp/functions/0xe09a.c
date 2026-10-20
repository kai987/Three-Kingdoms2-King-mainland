
void state_or_entry_e09a(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xe0;
  FUN_e768();
  uStack0000 = 0xe0;
  DAT_2001 = FUN_e74d();
  uStack0000 = 0xe0;
  FUN_e57f();
  bVar1 = 0x1f;
  do {
    *(undefined1 *)(bVar1 + 0x100) = 0xf;
    bVar1 = bVar1 - 1;
  } while (-1 < (char)bVar1);
  do {
  } while (-1 < DAT_2002);
  DAT_00a5 = 0x4c;
  nmi = (code)0x4c;
  uStack0000 = 0xe0;
  FUN_e51f(0);
  DAT_008b = 0x10;
  DAT_2000 = 0x10;
  DAT_008c = 0;
  DAT_2001 = 0;
  DAT_007a = 9;
  DAT_004e = (code *)CONCAT11(uRAMe08f,uRAMe08e);
                    /* WARNING: Could not recover jumptable at 0xe079. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*DAT_004e)();
  return;
}

