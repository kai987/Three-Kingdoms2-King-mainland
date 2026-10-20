
void FUN_b091(char param_1,byte param_2)

{
  char in_Z;
  
  if (in_Z == '\0') {
    (&DAT_0160)[param_2] = param_1 + DAT_0017;
    DAT_0016 = DAT_0017;
  }
  else {
    (&DAT_0160)[param_2] = DAT_0016;
  }
  return;
}

