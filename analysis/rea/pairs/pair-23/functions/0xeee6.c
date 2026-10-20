
char FUN_eee6(void)

{
  char cVar1;
  
  if ((char)DAT_007e < '\0') {
    DAT_007e = DAT_007e & 0x7f;
    cVar1 = FUN_ef0b();
    return cVar1;
  }
  if ((char)(DAT_007e << 1) < '\0') {
    DAT_007e = DAT_007e & 0xbf;
    cVar1 = FUN_ef71();
    return cVar1;
  }
  if ((char)(DAT_007e << 2) < '\0') {
    DAT_007e = DAT_007e & 0xdf;
    cVar1 = FUN_efc0();
    return cVar1;
  }
  if (-1 < (char)(DAT_007e << 3)) {
    return DAT_007e << 3;
  }
  DAT_007e = DAT_007e & 0xef;
  cVar1 = FUN_f028();
  return cVar1;
}

