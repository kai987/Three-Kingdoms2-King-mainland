
void FUN_c84d(undefined1 param_1)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  undefined1 unaff_retaddr;
  
  uStack0000 = 200;
  DAT_0037 = param_1;
  bVar1 = FUN_d105();
  cVar2 = DAT_6f03 <= bVar1;
  if (bVar1 != DAT_6f03) {
    return;
  }
  uStack0000 = 200;
  FUN_c86a(DAT_0037);
  if (cVar2 != '\0') {
    FUN_c8e6(unaff_retaddr);
    return;
  }
  uStack0000 = 200;
  FUN_c885();
  return;
}

