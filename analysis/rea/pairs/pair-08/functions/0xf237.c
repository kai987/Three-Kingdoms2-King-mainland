
undefined1 FUN_f237(undefined1 param_1,byte param_2)

{
  DAT_00e2 = param_2;
  DAT_00e3 = param_2 + 1;
                    /* WARNING: Read-only address (RAM,0xf000) is written */
  cRAMf000 = param_2 + 1;
                    /* WARNING: Read-only address (RAM,0xe800) is written */
  bRAMe800 = param_2 | 0xc0;
  return param_1;
}

