
void FUN_b06b(byte param_1)

{
  char cVar1;
  
  cVar1 = *(char *)(param_1 + 0x614);
  if (cVar1 == DAT_0019) {
    *(byte *)(*(byte *)(param_1 + 0x600) + 0x680) = param_1;
  }
  DAT_0019 = DAT_0019 + '\x01';
  if (cVar1 == DAT_0019) {
    *(byte *)(*(byte *)(param_1 + 0x600) + 0x6a0) = param_1;
  }
  DAT_0019 = DAT_0019 + -1;
  return;
}

