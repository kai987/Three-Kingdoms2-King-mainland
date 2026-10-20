
undefined1 switchD_f878::caseD_0(void)

{
  undefined1 uStack0000;
  undefined1 in_stack_00000003;
  
  uStack0000 = 0xfa;
  FUN_fb0b();
  uStack0000 = 0xfa;
  FUN_f206();
  uStack0000 = 0xfa;
  FUN_e6c6();
  uStack0000 = 0xfa;
  FUN_ff62();
  uStack0000 = 0xfa;
  FUN_fb28();
  DAT_007b = DAT_007b + -1;
  reset_dispatch = cRAM00de;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
  bRAMe800 = bRAM00df | 0xc0;
                    /* WARNING: Read-only address (RAM,0xf000) is written */
  uRAMf000 = uRAM00e0;
  DAT_0050 = DAT_0050 + '\x01';
  cRAM0052 = cRAM0052 + '\x01';
  cRAM0054 = cRAM0054 + '\x01';
  cRAM0055 = cRAM0055 + '\x01';
  DAT_005e = DAT_005e + '\x01';
  if (DAT_005e == '\0') {
    DAT_005f = DAT_005f + '\x01';
  }
  return in_stack_00000003;
}

