
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a976(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xa9;
  bVar2 = FUN_f308();
  for (bVar3 = 0; cVar1 = *(char *)(_DAT_0000 + (ushort)bVar3), cVar1 != '\0'; bVar3 = bVar3 + 1) {
    if ((cVar1 != '9') && (cVar1 != ':')) {
      *(char *)(bVar2 + 0x3b1) = cVar1;
      bVar2 = bVar2 + 1;
    }
  }
  return;
}

