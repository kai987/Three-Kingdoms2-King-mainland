
void FUN_ceab(void)

{
  undefined1 uStack0000;
  
  DAT_052b = DAT_066e;
  if (DAT_050f == '\x03') {
    uStack0000 = 0xce;
    FUN_cf92();
    DAT_0509 = 0;
    DAT_042c = DAT_0507 & 0xf;
    DAT_00a4 = 3;
    DAT_050a = 0xb5;
  }
  else {
    DAT_6f44 = DAT_050f;
    DAT_0509 = 10;
    DAT_042c = DAT_0507 >> 4;
    DAT_00a4 = 4;
    if (DAT_0000 < '\0') {
      DAT_050a = 0xbf;
    }
    else {
      DAT_050a = 0xbe;
    }
  }
  DAT_0514 = 1;
  return;
}

