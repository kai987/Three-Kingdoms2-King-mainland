
void FUN_e51f(char param_1)

{
  byte bVar1;
  
  bVar1 = param_1 * '\b';
  DAT_00e6 = (&DAT_e567)[bVar1];
                    /* WARNING: Read-only address (RAM,0xc000) is written */
  uRAMc000 = (&DAT_e567)[bVar1];
  DAT_00e7 = (&DAT_e567)[(byte)(bVar1 + 1)];
                    /* WARNING: Read-only address (RAM,0xc800) is written */
  uRAMc800 = (&DAT_e567)[(byte)(bVar1 + 1)];
  DAT_00e8 = (&DAT_e567)[(byte)(bVar1 + 2)];
                    /* WARNING: Read-only address (RAM,0xd000) is written */
  uRAMd000 = (&DAT_e567)[(byte)(bVar1 + 2)];
  DAT_00e9 = (&DAT_e567)[(byte)(bVar1 + 3)];
  DAT_d800 = (&DAT_e567)[(byte)(bVar1 + 3)];
  DAT_00ea = (&DAT_e567)[(byte)(bVar1 + 4)];
  DAT_00eb = (&DAT_e567)[(byte)(bVar1 + 5)];
  DAT_00ec = (&DAT_e567)[(byte)(bVar1 + 6)];
  DAT_00ed = (&DAT_e567)[(byte)(bVar1 + 7)];
  return;
}

