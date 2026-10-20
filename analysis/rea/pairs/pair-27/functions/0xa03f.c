
byte FUN_a03f(byte param_1)

{
  char in_C;
  
  thunk_FUN_da02 = (code)((char)thunk_FUN_da02 + '\x01');
  return param_1 + DAT_00a0 + in_C + DAT_75a0 + CARRY1(param_1,DAT_00a0) & DAT_07c0;
}

