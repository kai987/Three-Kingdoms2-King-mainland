
void FUN_c8c3(undefined1 param_1)

{
  byte bVar1;
  char cVar2;
  undefined1 uStack0000;
  
  uStack0000 = 200;
  DAT_0038 = param_1;
  bVar1 = FUN_d105();
  cVar2 = DAT_6f03 <= bVar1;
  if (bVar1 == DAT_6f03) {
    uStack0000 = 200;
    FUN_c86a(DAT_0038);
    if (cVar2 != '\0') {
      DAT_0037 = DAT_0038;
      FUN_c8e6();
      return;
    }
  }
  return;
}

