
void FUN_b4bf(void)

{
  undefined1 uStack0000;
  
  if (0xec < *(byte *)(DAT_040c + 0x410)) {
    return;
  }
  uStack0000 = 0xb4;
  officer_address();
  DAT_0010._0_1_ = DAT_0000;
  DAT_0010._1_1_ = DAT_0001;
  uStack0000 = 0xb4;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_040d);
}

