
void thunk_FUN_a983(void)

{
  char cVar1;
  byte bStack0000;
  byte bStack_1;
  
  bStack0000 = DAT_0000;
  bStack_1 = DAT_0507;
  if (*(char *)(DAT_0000 + 0x628) < '\0') {
    bStack_1 = DAT_0507 >> 4;
  }
  cVar1 = FUN_a9a8(bStack_1 & 0xf);
  if (cVar1 != '\0') {
    if (cVar1 != '\x01') {
      FUN_aa84();
      return;
    }
    DAT_01b0 = (&DAT_aafa)[*(byte *)(bStack0000 + 0x63c)];
    DAT_01b1 = (&DAT_ab05)[*(byte *)(bStack0000 + 0x63c)];
    if (((bStack0000 == 0) || (bStack0000 == 10)) &&
       (DAT_01b0 = 0xb1, *(char *)(bStack0000 + 0x63c) == '\n')) {
      DAT_01b0 = 0xb0;
      DAT_01b1 = 0x8b;
    }
    DAT_01b2 = 0x8c;
    DAT_01b3 = 0x8d;
    if ((*(byte *)(bStack0000 + 0x628) & 3) == 0) {
      DAT_01b2 = 0xb3;
      DAT_01b3 = 0xb4;
    }
    if ((*(byte *)(bStack0000 + 0x628) & 3) == 2) {
      DAT_01b2 = 0x8e;
      DAT_01b3 = 0x8f;
    }
    return;
  }
  DAT_01b0 = (&DAT_aae4)[*(byte *)(bStack0000 + 0x63c)];
  DAT_01b1 = (&DAT_aaef)[*(byte *)(bStack0000 + 0x63c)];
  if (((bStack0000 == 0) || (bStack0000 == 10)) &&
     (DAT_01b0 = 0xbb, *(char *)(bStack0000 + 0x63c) == '\n')) {
    DAT_01b0 = 0xba;
    DAT_01b1 = 0xab;
  }
  DAT_01b2 = 0xae;
  DAT_01b3 = 0xaf;
  if ((*(byte *)(bStack0000 + 0x628) & 3) == 0) {
    DAT_01b2 = 0xbd;
    DAT_01b3 = 0xbe;
  }
  if ((*(byte *)(bStack0000 + 0x628) & 3) == 1) {
    DAT_01b2 = 0xac;
    DAT_01b3 = 0xad;
  }
  return;
}

