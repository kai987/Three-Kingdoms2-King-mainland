
void FUN_d99b(byte param_1)

{
  byte bVar1;
  char cVar2;
  byte bVar3;
  byte bVar4;
  byte bVar5;
  undefined1 uVar6;
  byte bVar7;
  byte *pbVar8;
  bool bVar9;
  
code_r0xd99b:
  *(undefined1 *)(param_1 + 0x715) = *(undefined1 *)(param_1 + 0x714);
  bVar7 = *(char *)(param_1 + 0x700) * '\x02';
  DAT_00f0 = CONCAT11((*(char *)(param_1 + 0x703) - (*(char *)(param_1 + 0x700) >> 7)) +
                      CARRY1(bVar7,*(byte *)(param_1 + 0x702)),bVar7 + *(byte *)(param_1 + 0x702));
  bVar7 = 0xff;
LAB_d9bd:
  bVar3 = *(byte *)(DAT_00f0 + (ushort)(byte)(bVar7 + 1));
  *(char *)(param_1 + 0x700) = *(char *)(param_1 + 0x700) + '\x01';
  bVar7 = bVar7 + 2;
  if (0xef < bVar3) {
    if (bVar3 == 0xfd) {
      *(undefined1 *)(param_1 + 0x713) = *(undefined1 *)(param_1 + 0x700);
      goto LAB_d9bd;
    }
    if (bVar3 != 0xff) goto LAB_d9bd;
    *(undefined1 *)(param_1 + 0x700) = 0xff;
LAB_dbf1:
    bVar7 = *(byte *)(param_1 + 0x706) & 0xc0;
    if ((DAT_07f4 & 0x80) == 0x80) {
      bVar7 = 0;
    }
    *(byte *)(param_1 + 0x706) = bVar7;
    FUN_df6e();
    return;
  }
  if (bVar3 < 0xe0) {
    if (bVar3 < 0xd0) {
      if (0xbf < bVar3) {
        DAT_07f7 = bVar3 & 0xf;
        if (((DAT_07f4 & 0x80) != 0x80) && ((*(byte *)(param_1 + 0x706) & 0x10) != 0)) {
          *(undefined1 *)(param_1 + 0x70d) = *(undefined1 *)(DAT_00f0 + (ushort)bVar7);
          *(byte *)(param_1 + 0x70c) = DAT_07f7;
        }
        goto LAB_d9bd;
      }
      if (0xaf < bVar3) goto LAB_da37;
      if (0x9f < bVar3) {
        if (bVar3 == 0xa0) {
          if ((DAT_07f4 & 0x80) == 0x80) goto LAB_d9bd;
          bVar3 = *(byte *)(param_1 + 0x706) & 0xc0 | *(byte *)(DAT_00f0 + (ushort)bVar7);
        }
        else {
          if (bVar3 == 0xa1) {
            *(undefined1 *)(param_1 + 0x709) = *(undefined1 *)(DAT_00f0 + (ushort)bVar7);
            goto LAB_d9bd;
          }
          bVar9 = 0xa1 < bVar3;
          if (bVar3 != 0xa2) {
            if (bVar3 == 0xa3) {
              bVar3 = *(byte *)(DAT_00f0 + (ushort)bVar7);
              if (-1 < (char)bVar3) {
                *(byte *)register0x22 = bVar3;
                cVar2 = (bVar3 & 0xf) << 1;
                *(char *)(param_1 + 0x714) = cVar2;
                *(char *)(param_1 + 0x715) = cVar2;
                *(byte *)(param_1 + 0x701) =
                     *(byte *)register0x22 & 0x70 | *(byte *)(param_1 + 0x701) | 0x80;
                goto LAB_d9bd;
              }
            }
            else if (bVar3 != 0xa4) {
              if (bVar3 == 0xad) {
                *(undefined1 *)register0x22 = *(undefined1 *)(DAT_00f0 + (ushort)bVar7);
                bVar4 = *(byte *)(param_1 + 0x700) * '\x02';
                DAT_00f0 = CONCAT11(*(byte *)(param_1 + 0x700) >> 7,(char)DAT_00f0);
                bVar3 = *(byte *)(param_1 + 0x702);
                *(byte *)(param_1 + 0x702) = bVar4 + bVar3;
                *(char *)(param_1 + 0x703) =
                     *(char *)(param_1 + 0x703) + DAT_00f0._1_1_ + CARRY1(bVar4,bVar3);
                *(undefined1 *)(param_1 + 0x700) = 0;
                if (*(char *)register0x22 == '\0') {
                  FUN_d958();
                  return;
                }
              }
              else if (bVar3 == 0xae) {
                *(char *)(param_1 + 0x704) = *(char *)(param_1 + 0x704) << 1;
                *(byte *)(param_1 + 0x704) =
                     *(byte *)(param_1 + 0x704) >> 1 | *(byte *)(DAT_00f0 + (ushort)bVar7) & 0x80;
              }
              else if (bVar3 == 0xaf) {
                *(byte *)(param_1 + 0x705) = *(byte *)(DAT_00f0 + (ushort)bVar7) & 0xf;
                *(byte *)(param_1 + 0x704) =
                     *(byte *)(param_1 + 0x704) & 0xf0 | *(byte *)(param_1 + 0x705);
              }
              goto LAB_d9bd;
            }
            *(byte *)(param_1 + 0x701) = *(byte *)(param_1 + 0x701) & 7;
            goto LAB_d9bd;
          }
          *(byte *)((short)register0x22 + -1) = 0x89;
          *(byte *)((short)register0x22 + 0x10000) = 0xda;
          bVar3 = FUN_dc3f();
          if (!bVar9) {
            bVar3 = *(byte *)(param_1 + 0x706) & 0x1f | DAT_07f7;
          }
        }
        *(byte *)(param_1 + 0x706) = bVar3;
        *(byte *)(param_1 + 0x707) = bVar3;
        goto LAB_d9bd;
      }
      DAT_07f7 = bVar3;
      *(undefined1 *)(param_1 + 0x708) = *(undefined1 *)(DAT_00f0 + (ushort)bVar7);
      if ((DAT_07f4 & 0x40) != 0x40) {
        *(byte *)register0x22 = DAT_07f7;
        if (0xb < (DAT_07f7 & 0xf)) goto LAB_dbf1;
        bVar3 = (DAT_07f7 & 0xf) * '\x02';
        if (*(char *)(param_1 + 0x704) < '\0') {
          bVar3 = bVar3 + 0x18;
        }
        if (3 < DAT_07f3) {
          bVar3 = bVar3 + 0x30;
        }
        DAT_07f7 = (&DAT_dd06)[bVar3];
        bVar4 = *(byte *)register0x22 & 0x70;
        bVar7 = DAT_07f3;
        if (3 < DAT_07f3) {
          if (bVar4 == 0x40) {
            bVar4 = DAT_07f7 >> 7;
            DAT_07f7 = DAT_07f7 << 1;
            DAT_07f8 = (&DAT_dd07)[bVar3] << 1 | bVar4;
            goto LAB_db96;
          }
          bVar5 = (bVar4 - 0x30) - (bVar4 < 0x40);
          bVar1 = ~bVar4;
          bVar4 = 0;
          if (bVar5 != 0) {
            if ((bVar5 & bVar1 & 0x80) != 0) {
              bVar5 = 0xb0;
            }
            bVar4 = (bVar5 ^ 0xff) + 1;
          }
        }
        DAT_07f8 = (&DAT_dd07)[bVar3];
        for (bVar4 = bVar4 >> 4; bVar4 != 0; bVar4 = bVar4 - 1) {
          DAT_07f7 = DAT_07f7 >> 1 | DAT_07f8 << 7;
          bVar7 = 0;
          DAT_07f8 = DAT_07f8 >> 1;
        }
LAB_db96:
        *(undefined1 *)(param_1 + 0x70e) = 0;
        *(undefined1 *)(param_1 + 0x706) = *(undefined1 *)(param_1 + 0x707);
        *(byte *)((short)register0x22 + -1) = 0xa4;
        *(byte *)((short)register0x22 + 0x10000) = 0xdb;
        FUN_dc31();
        if (bVar7 < 4) {
          DAT_07f6 = (&DAT_dd4e)[bVar7] | DAT_07f6;
          DAT_4015 = DAT_07f6;
        }
        *(byte *)register0x22 = DAT_07f8;
        *(byte *)((short)register0x22 + -1) = DAT_07f7;
        *(byte *)((short)register0x22 + -3) = 0xbf;
        *(byte *)((short)register0x22 + -2) = 0xdb;
        FUN_df71();
        if (bVar7 < 0x10) {
          (&DAT_4001)[bVar7] = *(undefined1 *)(param_1 + 0x709);
        }
        uVar6 = *(byte *)((short)register0x22 + -1);
        *(byte *)((short)register0x22 + -2) = 0xcd;
        *(byte *)((short)register0x22 + -1) = 0xdb;
        bVar7 = FUN_dc03(uVar6);
        if (bVar7 < 2) {
          bVar7 = 2;
        }
        else if (0xfd < bVar7) {
          bVar7 = 0xfd;
        }
        *(byte *)(param_1 + 0x712) = bVar7;
        FUN_dc18(*(undefined1 *)register0x22);
        return;
      }
      if (DAT_07f7 < 0x10) {
        DAT_07f8 = 0;
        goto LAB_db96;
      }
      goto LAB_dbf1;
    }
    bVar3 = bVar3 & 0xf;
  }
  else {
    bVar3 = (bVar3 & 0xf ^ 0xff) + 1;
  }
  if ((DAT_07f4 & 0x80) != 0x80) {
    *(byte *)(param_1 + 0x70f) = bVar3;
    uVar6 = *(undefined1 *)(DAT_00f0 + (ushort)bVar7);
    *(undefined1 *)(param_1 + 0x710) = uVar6;
    *(undefined1 *)(param_1 + 0x711) = uVar6;
  }
  goto LAB_d9bd;
LAB_da37:
  if ((bVar3 & 0xf) != 0) {
    *(byte *)register0x22 = bVar3 & 0xf;
    pbVar8 = (byte *)((short)register0x22 + -1);
    if (*(char *)(DAT_00f0 + (ushort)bVar7) == '\0') {
      uVar6 = *(undefined1 *)register0x22;
      cVar2 = *(char *)(param_1 + 0x70a) + -1;
      *(char *)(param_1 + 0x70a) = cVar2;
      if (cVar2 == '\0') goto code_r0xd99b;
      if ((cVar2 >= '\0') ||
         (*(undefined1 *)(param_1 + 0x70a) = uVar6, pbVar8 = (byte *)register0x22, cVar2 < '\0'))
      goto LAB_da58;
    }
    register0x22 = (BADSPACEBASE *)(pbVar8 + 1);
    uVar6 = pbVar8[1];
    cVar2 = *(char *)(param_1 + 0x70b) + -1;
    *(char *)(param_1 + 0x70b) = cVar2;
    if (cVar2 == '\0') goto code_r0xd99b;
    register0x22 = (BADSPACEBASE *)(pbVar8 + 1);
    if (cVar2 < '\0') {
      *(undefined1 *)(param_1 + 0x70b) = uVar6;
      register0x22 = (BADSPACEBASE *)(pbVar8 + 1);
    }
  }
LAB_da58:
  cVar2 = *(char *)(DAT_00f0 + (ushort)bVar7);
  if (cVar2 == '\0') {
    cVar2 = *(char *)(param_1 + 0x713);
  }
  *(char *)(param_1 + 0x700) = cVar2;
  goto code_r0xd99b;
}

