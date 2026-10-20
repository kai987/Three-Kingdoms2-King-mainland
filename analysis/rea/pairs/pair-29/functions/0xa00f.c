
/* WARNING: Globals starting with '_' overlap smaller symbols at the same address */

void thunk_FUN_b989(void)

{
  undefined1 uVar1;
  char cVar2;
  byte bVar3;
  byte bVar4;
  bool bVar5;
  undefined1 uStack0000;
  
  if (((DAT_0140 == '\0') && ((DAT_007e & 2) == 0)) && (DAT_0478 != 0)) {
    if ((char)DAT_0478 < '\0') {
      DAT_0479 = DAT_0478 & 0xf;
      DAT_0478 = 0;
      DAT_047a = 0;
      DAT_047b = '\0';
      DAT_0486 = '\0';
      DAT_0480 = 0xc0;
      DAT_0481 = '#';
      uStack0000 = 0xba;
      FUN_f25f(0x30);
      if (DAT_047c == -1) {
        DAT_047c = '\x0f';
        bVar3 = 0;
        do {
          if ((&DAT_0151)[bVar3] != -1) {
            DAT_047b = DAT_047b + '\x01';
          }
          bVar3 = bVar3 + 1;
        } while (bVar3 < 10);
      }
      else {
        uVar1 = DAT_0402;
        if (DAT_0479 == 2) {
          DAT_0479 = 0;
          uVar1 = DAT_040c;
        }
        uStack0000 = 0xba;
        region_address(uVar1);
        bVar4 = 0x11;
        bVar3 = 0;
        do {
          cVar2 = *(char *)(_DAT_0000 + (ushort)bVar4);
          (&DAT_0151)[bVar3] = cVar2;
          if (cVar2 != -1) {
            DAT_047b = DAT_047b + '\x01';
          }
          bVar3 = bVar3 + 1;
          bVar4 = bVar4 + 1;
        } while (bVar3 < 10);
      }
      if (DAT_0479 == 0) {
        DAT_0482 = 0xc9;
        DAT_0483 = -0x48;
      }
      else {
        DAT_0482 = 9;
        DAT_0483 = -0x48;
      }
    }
    else {
      if (DAT_0478 == 0x10) {
        DAT_0478 = 0;
        DAT_047a = 0;
        DAT_0480 = 0;
        DAT_0424 = 0;
        DAT_0425 = 0;
        if (DAT_047c == '\x0f') {
          DAT_047b = DAT_047b + -1;
        }
        DAT_0061 = 6;
        DAT_00b2 = 8;
        DAT_00b3 = 9;
        DAT_00b4 = 6;
        bVar3 = 1;
        DAT_008f = 1;
        do {
          (&DAT_0480)[bVar3] = 0xff;
          bVar3 = bVar3 + 1;
        } while (bVar3 < 0xb);
        return;
      }
      if ((1 < DAT_0478) && (DAT_0478 < 0xc)) {
        bVar3 = DAT_047a + 1;
        cVar2 = (&DAT_0151)[DAT_047a];
        DAT_047a = bVar3;
        if (cVar2 != -1) {
          uStack0000 = 0xb9;
          officer_address(cVar2);
          DAT_001c = _DAT_0000;
          bVar3 = 0;
          do {
            (&DAT_0160)[bVar3] = 1;
            bVar3 = bVar3 + 1;
          } while (bVar3 < 0x40);
          uStack0000 = 0xbb;
          FUN_f308(cVar2);
          bVar3 = 0;
          for (bVar4 = 0; cVar2 = *(char *)(_DAT_0000 + (ushort)bVar4), cVar2 != '\0';
              bVar4 = bVar4 + 1) {
            if ((cVar2 == '9') || (cVar2 == ':')) {
              bVar3 = bVar3 - 1;
              (&DAT_0163)[bVar3] = cVar2;
            }
            else {
              (&DAT_0183)[bVar3] = cVar2;
            }
            bVar3 = bVar3 + 1;
          }
          DAT_0017 = 0x76;
          DAT_0013 = 2;
          DAT_0014 = 0x2b;
          bVar3 = 0;
          do {
            bVar4 = DAT_0014;
            DAT_0002 = 0;
            DAT_0003 = 0;
            _DAT_0000 = CONCAT11(*(char *)(DAT_001c + (ushort)bVar3),DAT_0000);
            if ((*(char *)(DAT_001c + (ushort)bVar3) == 'd') && (bVar3 == 3)) {
              (&DAT_0160)[DAT_0014] = 0x32;
              (&DAT_0160)[(byte)(bVar4 + 1)] = 0x32;
            }
            else {
              uStack0000 = 0xbb;
              FUN_e9ba();
              uStack0000 = 0xbb;
              FUN_b040(DAT_0014);
            }
            DAT_0014 = DAT_0014 + 3;
            bVar3 = bVar3 + 1;
          } while (bVar3 < 4);
          if (DAT_0479 == 0) {
            DAT_0002 = 0;
            DAT_0003 = 0;
            _DAT_0000 = CONCAT11(*(undefined1 *)(DAT_001c + 4),DAT_0000);
            uStack0000 = 0xbb;
            FUN_e9ba();
            uStack0000 = 0xbb;
            FUN_b040(0x37);
          }
          _DAT_0000 = CONCAT11(*(byte *)(DAT_001c + 6) << 1,DAT_0000);
          DAT_0003 = *(byte *)(DAT_001c + 7) >> 7;
          DAT_0002 = *(byte *)(DAT_001c + 7) << 1 | *(byte *)(DAT_001c + 6) >> 7;
          uStack0000 = 0xbb;
          FUN_e9ba();
          DAT_0007 = DAT_0008;
          DAT_0008 = DAT_0009;
          DAT_0013 = 3;
          if (DAT_0479 == 0) {
            uStack0000 = 0xbb;
            FUN_b040(0x3a);
          }
          else {
            uStack0000 = 0xbb;
            FUN_b040(0x37);
            _DAT_0000 = CONCAT11(*(undefined1 *)(DAT_001c + 8),DAT_0000);
            DAT_0002 = *(byte *)(DAT_001c + 9) & 3;
            DAT_0003 = 0;
            uStack0000 = 0xbc;
            FUN_e9ba();
            DAT_0013 = 4;
            uStack0000 = 0xbc;
            FUN_b040(0x3b);
          }
          bVar5 = 0xbf < DAT_0480;
          DAT_0480 = DAT_0480 + 0x40;
          DAT_0481 = DAT_0481 + bVar5;
          DAT_0478 = DAT_0478 + 1;
          DAT_007e = DAT_007e | 2;
          return;
        }
      }
    }
    if (DAT_0478 == 0xf) {
      bVar3 = 0;
      do {
        (&DAT_0160)[bVar3] = 0xaa;
        bVar3 = bVar3 + 1;
      } while (bVar3 < 0x40);
      DAT_0480 = -0x40;
      DAT_0481 = '\'';
    }
    else {
      if ((DAT_0478 < 2) || ((DAT_0486 == '\0' && (DAT_0486 = '\x01', DAT_047c != '\x0f')))) {
        DAT_001a = CONCAT11(DAT_0483,DAT_0482);
        bVar3 = 0;
        do {
          (&DAT_0160)[bVar3] = *(undefined1 *)(DAT_001a + (ushort)bVar3);
          bVar3 = bVar3 + 1;
        } while (bVar3 < 0x40);
        bVar5 = 0xbf < DAT_0482;
        DAT_0482 = DAT_0482 + 0x40;
        DAT_0483 = DAT_0483 + bVar5;
      }
      else {
        bVar3 = 0;
        do {
          (&DAT_0160)[bVar3] = 1;
          bVar3 = bVar3 + 1;
        } while (bVar3 < 0x40);
      }
      bVar5 = 0xbf < DAT_0480;
      DAT_0480 = DAT_0480 + 0x40;
      DAT_0481 = DAT_0481 + bVar5;
    }
    DAT_0478 = DAT_0478 + 1;
    DAT_007e = DAT_007e | 2;
    return;
  }
  return;
}

