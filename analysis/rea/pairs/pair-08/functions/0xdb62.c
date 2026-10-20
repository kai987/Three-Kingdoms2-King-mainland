
void FUN_db62(void)

{
  undefined1 uStack0000;
  
  if (DAT_0541 == '\x03') {
    if ((char)(&DAT_dba3)[DAT_0546] < '\0') {
      if ((DAT_6fea & 2) == 0) {
        DAT_6fea = DAT_6fea | 2;
        uStack0000 = 0xdb;
        FUN_e693(0x62);
      }
      return;
    }
    if ((DAT_0085 & (&DAT_dba3)[DAT_0546]) == 0) {
      DAT_0546 = 0;
      return;
    }
    if ((DAT_0082 & (&DAT_dbac)[DAT_0546]) != 0) {
      DAT_0546 = DAT_0546 + 1;
    }
  }
  return;
}

