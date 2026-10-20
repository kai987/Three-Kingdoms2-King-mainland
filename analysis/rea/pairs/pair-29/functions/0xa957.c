
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_a957(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xa9;
  bVar2 = FUN_f308();
  bVar3 = 0;
  while (cVar1 = *(char *)(_DAT_0000 + (ushort)bVar3), cVar1 != '\0') {
    if ((cVar1 == '9') || (cVar1 == ':')) {
      (&DAT_03a5)[bVar2] = cVar1;
      bVar3 = bVar3 + 1;
    }
    else {
      bVar3 = bVar3 + 1;
      bVar2 = bVar2 + 1;
    }
  }
  return;
}

