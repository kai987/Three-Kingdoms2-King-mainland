
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_d8b0(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xd8;
  officer_address(DAT_000b);
  DAT_000c = CARRY1(*(byte *)(_DAT_0000 + 1),*(byte *)(_DAT_0000 + 2));
  DAT_000b = *(byte *)(_DAT_0000 + 1) + *(byte *)(_DAT_0000 + 2);
  FUN_d7fb();
  return;
}

