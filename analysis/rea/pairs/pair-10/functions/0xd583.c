
undefined1 FUN_d583(byte param_1,byte param_2)

{
  DAT_0031 = param_2;
  DAT_0032 = param_1;
  DAT_0030 = 0x1d;
  while (((*(byte *)((DAT_0030 | (&DAT_d5bf)[param_2]) + 0x580) & (&DAT_d5df)[param_2 & 7]) == 0 ||
         ((*(byte *)((DAT_0030 | (&DAT_d5bf)[param_1]) + 0x580) & (&DAT_d5df)[param_1 & 7]) == 0)))
  {
    DAT_0030 = DAT_0030 - 1;
    if ((char)DAT_0030 < '\0') {
      return 0;
    }
  }
  return 0xff;
}

