
void FUN_dbff(void)

{
  undefined1 uStack0000;
  
  if ((char)(&DAT_dc39)[DAT_0548] < '\0') {
    if ((DAT_6fea & 8) == 0) {
      DAT_6fea = DAT_6fea | 8;
      uStack0000 = 0xdc;
      FUN_e693(0x62);
    }
    return;
  }
  if ((DAT_0083 & (&DAT_dc39)[DAT_0548]) == 0) {
    DAT_0548 = 0;
    return;
  }
  if ((DAT_0081 & (&DAT_dc42)[DAT_0548]) != 0) {
    DAT_0548 = DAT_0548 + 1;
  }
  return;
}

