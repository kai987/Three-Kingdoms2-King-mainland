
void FUN_dbb4(void)

{
  undefined1 uStack0000;
  
  if ((char)(&DAT_dbee)[DAT_0547] < '\0') {
    if ((DAT_6fea & 4) == 0) {
      DAT_6fea = DAT_6fea | 4;
      uStack0000 = 0xdb;
      FUN_e693(0x62);
    }
    return;
  }
  if ((DAT_0083 & (&DAT_dbee)[DAT_0547]) == 0) {
    DAT_0547 = 0;
    return;
  }
  if ((DAT_0081 & (&DAT_dbf7)[DAT_0547]) != 0) {
    DAT_0547 = DAT_0547 + 1;
  }
  return;
}

