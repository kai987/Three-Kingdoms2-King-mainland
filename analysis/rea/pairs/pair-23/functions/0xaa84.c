
void FUN_aa84(void)

{
  byte unaff_retaddr;
  
  DAT_01b0 = (&DAT_ab10)[*(byte *)(unaff_retaddr + 0x63c)];
  DAT_01b1 = (&DAT_ab1b)[*(byte *)(unaff_retaddr + 0x63c)];
  if (((unaff_retaddr == 0) || (unaff_retaddr == 10)) &&
     (DAT_01b0 = 0xb6, *(char *)(unaff_retaddr + 0x63c) == '\n')) {
    DAT_01b0 = 0xb5;
    DAT_01b1 = 0x9b;
  }
  DAT_01b2 = 0x9c;
  DAT_01b3 = 0x9d;
  if ((*(byte *)(unaff_retaddr + 0x628) & 3) == 0) {
    DAT_01b2 = 0xb8;
    DAT_01b3 = 0xb9;
  }
  if ((*(byte *)(unaff_retaddr + 0x628) & 3) == 2) {
    DAT_01b2 = 0x9e;
    DAT_01b3 = 0x9f;
  }
  return;
}

