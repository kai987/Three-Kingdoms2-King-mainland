
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b27a(void)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xb2;
  FUN_f308((&DAT_037c)[DAT_000f]);
  bVar2 = 0;
  for (bVar3 = 0; cVar1 = *(char *)(_DAT_0000 + (ushort)bVar3), cVar1 != '\0'; bVar3 = bVar3 + 1) {
    if ((cVar1 != '9') && (cVar1 != ':')) {
      (&DAT_0166)[bVar2] = cVar1 + -0x80;
      bVar2 = bVar2 + 1;
    }
  }
  return;
}

