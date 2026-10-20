
/* WARNING: Removing unreachable block (RAM,0xcb80) */
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_cb52(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  uStack0000 = 0xcb;
  FUN_d319(DAT_0040);
  DAT_0033 = *_DAT_0024;
  *_DAT_0024 = DAT_0027;
  bVar1 = 3;
  uStack0000 = 0xcb;
  FUN_d2ab();
  *(undefined1 *)(DAT_0022 + (ushort)bVar1) = 100;
  uStack0000 = DAT_0027;
  FUN_cb81();
  do {
  } while( true );
}

