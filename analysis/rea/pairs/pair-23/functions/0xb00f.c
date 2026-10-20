
void FUN_b00f(byte param_1)

{
  char cVar1;
  
  cVar1 = *(char *)(param_1 + 0x600);
  if (cVar1 == DAT_0018) {
    *(byte *)(*(byte *)(param_1 + 0x614) + 0x680) = param_1;
  }
  DAT_0018 = DAT_0018 + '\x01';
  if (cVar1 == DAT_0018) {
    *(byte *)(*(byte *)(param_1 + 0x614) + 0x6a0) = param_1;
  }
  if (cVar1 == DAT_0016) {
    *(byte *)(*(byte *)(param_1 + 0x614) + 0x6c0) = param_1;
  }
  DAT_0016 = DAT_0016 + '\x01';
  if (cVar1 == DAT_0016) {
    *(byte *)(*(byte *)(param_1 + 0x614) + 0x6e0) = param_1;
  }
  DAT_0016 = DAT_0016 + -1;
  DAT_0018 = DAT_0018 + -1;
  return;
}

