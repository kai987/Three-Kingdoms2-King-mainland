
void FUN_b100(void)

{
  undefined1 uStack0000;
  
  DAT_6f44 = *(char *)(DAT_04aa + 0x4ab);
  if (DAT_6f44 < '\0') {
    DAT_6f44 = *(char *)((DAT_04aa ^ 1) + 0x4ab);
  }
  uStack0000 = 0xb1;
                    /* WARNING: Subroutine does not return */
  tail_dispatch_inline_table(DAT_04a8);
}

