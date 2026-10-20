
void FUN_d2f5(void)

{
  DAT_00b2 = 0x88;
  if ((DAT_005e & 0x10) != 0) {
    DAT_00b2 = 0x8b;
  }
  DAT_00d6 = DAT_00b2;
  if (DAT_04c8 == '\0') {
    DAT_00c2 = DAT_00b2;
    DAT_00c6 = DAT_00b2;
    DAT_00d2 = DAT_00b2;
  }
  return;
}

