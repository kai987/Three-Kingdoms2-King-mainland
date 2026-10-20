
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b517(char param_1,undefined1 param_2)

{
  undefined1 unaff_retaddr;
  undefined1 unaff_retaddr_00;
  
  _DAT_0021 = CONCAT11(unaff_retaddr_00,unaff_retaddr);
  DAT_0023 = (code *)CONCAT11(*(undefined1 *)(_DAT_0021 + (ushort)(byte)(param_1 * '\x02' + 2)),
                              *(undefined1 *)(_DAT_0021 + (ushort)(byte)(param_1 * '\x02' + 1)));
  DAT_0020 = param_2;
                    /* WARNING: Could not recover jumptable at 0xb533. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*DAT_0023)(param_2);
  return;
}

