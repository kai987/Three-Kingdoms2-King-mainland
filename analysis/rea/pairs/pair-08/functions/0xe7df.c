
void FUN_e7df(void)

{
  undefined1 uStack0000;
  
  LAB_c000 = 0xe0;
  DAT_c800 = 0xe1;
                    /* WARNING: Read-only address (RAM,0xd000) is written */
  uRAMd000 = 0xe0;
  DAT_d800 = 0xe1;
  DAT_0002 = 1;
  DAT_0003 = 0xaa;
  uStack0000 = 0xe8;
  FUN_e7b5(0x20);
  DAT_0002 = 1;
  DAT_0003 = 0xaa;
  uStack0000 = 0xe8;
  FUN_e7b5(0x24);
  DAT_0002 = 1;
  DAT_0003 = 0xaa;
  FUN_e7b5(0x28);
  return;
}

