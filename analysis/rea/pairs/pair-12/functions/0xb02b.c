
void FUN_b02b(void)

{
  byte bVar1;
  undefined1 uStack0000;
  
  bVar1 = 0;
  do {
    *(undefined1 *)(bVar1 + 0x42c) = 0;
    bVar1 = bVar1 + 1;
  } while (bVar1 < 9);
  DAT_0544 = 0;
  uStack0000 = 0xb0;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_0543 & 0xf);
}

