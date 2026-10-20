
void bank12_entry_00(void)

{
  undefined1 uStack0000;
  
  uStack0000 = 0xa0;
  FUN_df88();
  uStack0000 = 0xa0;
                    /* WARNING: Subroutine does not return */
  far_call_inline_word(0x28);
}

