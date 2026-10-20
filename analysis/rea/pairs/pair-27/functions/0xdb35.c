
void FUN_db35(char param_1,byte param_2)

{
  bool in_Z;
  
  if (in_Z) {
    if ((DAT_0013 == '\0') && (DAT_0011 <= param_2)) {
      DAT_0010 = 0x76;
    }
    (&DAT_031e)[param_2] = DAT_0010;
  }
  else {
    (&DAT_031e)[param_2] = param_1 + 'v';
    DAT_0010 = 0x76;
  }
  if (((DAT_0013 == '\0') && (param_2 == DAT_0011)) && ((DAT_046c & 8) == 0)) {
    (&DAT_031e)[param_2] = 1;
  }
  return;
}

