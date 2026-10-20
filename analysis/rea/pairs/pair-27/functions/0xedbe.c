
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_edbe(void)

{
  char cVar1;
  byte bVar2;
  
  cVar1 = DAT_0425 + -1;
  if (((char)(DAT_0425 + -1) < '\0') && (cVar1 = DAT_0425, DAT_0012 == '\0')) {
    cVar1 = -1;
    bVar2 = DAT_0424;
    do {
      cVar1 = cVar1 + '\x01';
      bVar2 = bVar2 + DAT_0000;
    } while (-1 < *(char *)(_DAT_0010 + (ushort)bVar2));
  }
  DAT_0425 = cVar1;
  return;
}

