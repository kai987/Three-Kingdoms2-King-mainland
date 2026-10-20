
void FUN_b040(byte param_1)

{
  undefined1 uStack0000;
  
  DAT_0016 = 1;
  if (DAT_0013 != '\x02') {
    if (DAT_0013 != '\x03') {
      if (DAT_0013 != '\x04') {
        if (DAT_0013 != '\x05') {
          uStack0000 = 0xb0;
          FUN_b091(DAT_0009 >> 4);
        }
        uStack0000 = 0xb0;
        FUN_b091(DAT_0009 & 0xf);
      }
      uStack0000 = 0xb0;
      FUN_b091(DAT_0008 >> 4);
    }
    uStack0000 = 0xb0;
    FUN_b091(DAT_0008 & 0xf);
  }
  uStack0000 = 0xb0;
  FUN_b091(DAT_0007 >> 4);
  DAT_0016 = DAT_0017;
  if ((DAT_0007 & 0xf) == 0) {
    (&DAT_0160)[param_1] = DAT_0017;
  }
  else {
    (&DAT_0160)[param_1] = (DAT_0007 & 0xf) + DAT_0017;
    DAT_0016 = DAT_0017;
  }
  return;
}

