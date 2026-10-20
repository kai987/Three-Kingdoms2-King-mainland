
void FUN_d96f(char param_1,byte param_2)

{
  bool in_Z;
  
  if (in_Z) {
    (&DAT_031e)[param_2] = DAT_000a;
  }
  else {
    (&DAT_031e)[param_2] = param_1 + 'v';
    DAT_000a = 0x76;
  }
  return;
}

