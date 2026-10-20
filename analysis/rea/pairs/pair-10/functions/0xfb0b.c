
void FUN_fb0b(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xfb;
  FUN_eaf7();
                    /* WARNING: Read-only address (RAM,0xc000) is written */
  uRAMc000 = DAT_00e6;
                    /* WARNING: Read-only address (RAM,0xc800) is written */
  uRAMc800 = DAT_00e7;
                    /* WARNING: Read-only address (RAM,0xd000) is written */
  uRAMd000 = DAT_00e8;
  DAT_d800 = DAT_00e9;
  do {
  } while ((DAT_2002 & 0x40) == 0x40);
  return;
}

