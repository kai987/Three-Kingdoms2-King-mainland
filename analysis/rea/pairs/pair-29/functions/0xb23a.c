
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void FUN_b23a(char param_1)

{
  char cVar1;
  byte bVar2;
  byte bVar3;
  undefined1 uStack0000;
  
  uStack0000 = 0xb2;
  DAT_000f = param_1;
  region_address(DAT_0402);
  if (*_DAT_0000 != '\a') {
    bVar2 = 1;
    if (DAT_000f != '\0') {
      bVar2 = 2;
    }
    uStack0000 = 0xb2;
    FUN_f308((&DAT_037c)[bVar2]);
    bVar2 = 0;
    for (bVar3 = 0; cVar1 = _DAT_0000[bVar3], cVar1 != '\0'; bVar3 = bVar3 + 1) {
      if ((cVar1 == '9') || (cVar1 == ':')) {
        bVar2 = bVar2 - 1;
        (&DAT_0190)[bVar2] = cVar1 + -0x80;
      }
      bVar2 = bVar2 + 1;
    }
  }
  return;
}

