
void FUN_ed71(void)

{
  bool bVar1;
  undefined1 uStack0000;
  
  DAT_0424 = DAT_0424 + 1;
  bVar1 = (char)DAT_0424 < '\0';
  uStack0000 = 0xed;
  FUN_eddd();
  if (((bVar1) || (DAT_0000 <= DAT_0424)) && (DAT_0424 = DAT_0424 - 1, DAT_0012 == '\0')) {
    DAT_0424 = 0;
  }
  return;
}

