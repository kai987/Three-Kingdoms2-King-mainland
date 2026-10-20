
void FUN_d53e(byte param_1,byte param_2)

{
  if ((*(byte *)(param_1 + 0x580) & *(byte *)(param_2 + 0x580)) != 0) {
    *(byte *)(param_2 + 0x580) = *(byte *)(param_1 + 0x580) | *(byte *)(param_2 + 0x580);
  }
  if ((*(byte *)(param_1 + 0x5a0) & *(byte *)(param_2 + 0x5a0)) != 0) {
    *(byte *)(param_2 + 0x5a0) = *(byte *)(param_1 + 0x5a0) | *(byte *)(param_2 + 0x5a0);
  }
  if ((*(byte *)(param_1 + 0x5c0) & *(byte *)(param_2 + 0x5c0)) != 0) {
    *(byte *)(param_2 + 0x5c0) = *(byte *)(param_1 + 0x5c0) | *(byte *)(param_2 + 0x5c0);
  }
  if ((*(byte *)(param_1 + 0x5e0) & *(byte *)(param_2 + 0x5e0)) != 0) {
    *(byte *)(param_2 + 0x5e0) = *(byte *)(param_1 + 0x5e0) | *(byte *)(param_2 + 0x5e0);
  }
  return;
}

