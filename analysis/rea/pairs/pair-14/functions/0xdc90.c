
void FUN_dc90(byte param_1)

{
  char cVar1;
  
  if ((((DAT_07f4 & 0x80) != 0x80) && (*(char *)(param_1 + 0x70f) != '\0')) &&
     (cVar1 = *(char *)(param_1 + 0x711) + -1, *(char *)(param_1 + 0x711) = cVar1, cVar1 == '\0')) {
    *(undefined1 *)(param_1 + 0x711) = *(undefined1 *)(param_1 + 0x710);
    DAT_07f7 = *(byte *)(param_1 + 0x706) & 0x1f;
    if ((*(byte *)(param_1 + 0x706) & 0x10) != 0) {
      if (*(char *)(param_1 + 0x70f) < '\0') {
        *(char *)(param_1 + 0x70f) = *(char *)(param_1 + 0x70f) + '\x01';
        if (DAT_07f7 != 0x10) {
          *(char *)(param_1 + 0x706) = *(char *)(param_1 + 0x706) + -1;
          *(char *)(param_1 + 0x707) = *(char *)(param_1 + 0x707) + -1;
          return;
        }
      }
      else {
        *(char *)(param_1 + 0x70f) = *(char *)(param_1 + 0x70f) + -1;
        if (DAT_07f7 != 0x1f) {
          *(char *)(param_1 + 0x706) = *(char *)(param_1 + 0x706) + '\x01';
          *(char *)(param_1 + 0x707) = *(char *)(param_1 + 0x707) + '\x01';
        }
      }
    }
  }
  return;
}

