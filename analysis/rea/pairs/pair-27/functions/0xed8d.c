
void FUN_ed8d(void)

{
  char cVar1;
  char cVar2;
  undefined1 uStack0000;
  
  cVar1 = DAT_0424 + -1;
  if (((char)(DAT_0424 + -1) < '\0') && (cVar1 = DAT_0424, DAT_0012 == '\0')) {
    DAT_0424 = DAT_0000;
    do {
      DAT_0424 = DAT_0424 + -1;
      uStack0000 = 0xed;
      cVar2 = FUN_eddd();
      cVar1 = DAT_0424;
    } while (cVar2 == -1);
  }
  DAT_0424 = cVar1;
  return;
}

