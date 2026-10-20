
void FUN_a01e(byte param_1,byte param_2)

{
  undefined2 uStack0000;
  
                    /* WARNING: Subroutine does not return */
  uStack0000 = 0xa025;
  far_call_inline_word(param_1 & (&DAT_a0df)[param_2]);
}

