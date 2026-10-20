
void FUN_db10(void)

{
  undefined1 uStack0000;
  
  if (DAT_0541 == '\x01') {
    if ((char)(&DAT_db51)[DAT_0545] < '\0') {
      if ((DAT_6fea & 1) == 0) {
        DAT_6fea = DAT_6fea | 1;
        uStack0000 = 0xdb;
        FUN_e693(0x62);
      }
      return;
    }
    if ((DAT_0083 & (&DAT_db51)[DAT_0545]) == 0) {
      DAT_0545 = 0;
      return;
    }
    if ((DAT_0081 & (&DAT_db5a)[DAT_0545]) != 0) {
      DAT_0545 = DAT_0545 + 1;
    }
  }
  return;
}

