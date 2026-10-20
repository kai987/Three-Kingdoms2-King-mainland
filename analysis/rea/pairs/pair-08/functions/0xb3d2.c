
void FUN_b3d2(byte param_1)

{
  undefined1 uVar1;
  
  uVar1 = (&DAT_0664)[param_1];
  (&DAT_0664)[param_1] = *(undefined1 *)(param_1 + 0x665);
  *(undefined1 *)(param_1 + 0x665) = uVar1;
  uVar1 = *(undefined1 *)(param_1 + 0x628);
  *(undefined1 *)(param_1 + 0x628) = *(undefined1 *)(param_1 + 0x629);
  *(undefined1 *)(param_1 + 0x629) = uVar1;
  uVar1 = *(undefined1 *)(param_1 + 0x63c);
  *(undefined1 *)(param_1 + 0x63c) = *(undefined1 *)(param_1 + 0x63d);
  *(undefined1 *)(param_1 + 0x63d) = uVar1;
  return;
}

