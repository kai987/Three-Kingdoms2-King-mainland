
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a19f(byte param_1)

{
  char cStack0000;
  
  DAT_0003 = '\0';
  cStack0000 = '\x1d';
  DAT_0002 = param_1;
  do {
    region_address();
    if ((*_DAT_0000 & 0xf) == DAT_0002) {
      DAT_0003 = DAT_0003 + '\x01';
    }
    cStack0000 = cStack0000 + -1;
  } while (-1 < cStack0000);
  return;
}

