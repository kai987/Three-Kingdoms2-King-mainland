
void FUN_d94e(byte param_1)

{
  undefined1 uStack0000;
  
  do {
    uStack0000 = 0xd9;
    FUN_d96f(*(byte *)(param_1 + 7) >> 4);
    if (param_1 == 0) {
      DAT_000a = 0x76;
    }
    uStack0000 = 0xd9;
    FUN_d96f(*(byte *)(param_1 + 7) & 0xf);
    param_1 = param_1 - 1;
  } while (param_1 != 0xff);
  return;
}

