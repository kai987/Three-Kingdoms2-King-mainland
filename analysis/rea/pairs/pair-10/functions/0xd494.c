
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_d494(char param_1,undefined1 param_2)

{
  undefined1 unaff_retaddr;
  undefined1 unaff_retaddr_00;
  
  RAM0x0021 = CONCAT11(unaff_retaddr_00,unaff_retaddr);
  RAM0x0023 = (code *)CONCAT11(*(undefined1 *)(RAM0x0021 + (ushort)(byte)(param_1 * '\x02' + 2)),
                               *(undefined1 *)(RAM0x0021 + (ushort)(byte)(param_1 * '\x02' + 1)));
  DAT_0020._0_1_ = param_2;
                    /* WARNING: Could not recover jumptable at 0xd4aa. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  (*RAM0x0023)(param_2);
  return;
}

