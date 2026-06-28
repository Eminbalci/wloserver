/*
 * Wonderland Online - Nesne Market (Item Mall) Fonksiyonlari
 * aLogin.exe.1.c dosyasindan analiz edilmistir.
 */

/*
 * FUN_001aec08 - Nesne Market Arayuzunun Yuklenmesi
 * Form_EightTwelve form nesnesini bellege yukler ve Btn_Buy vb. elementleri baglar.
 */
int * FUN_001aec08(int *param_1,char param_2)

{
  int iVar1;
  uint uVar2;
  int *piVar3;
  int iVar4;
  char extraout_DL;
  char cVar5;
  undefined2 extraout_var;
  undefined2 extraout_var_00;
  undefined2 extraout_var_01;
  undefined4 *in_FS_OFFSET;
  undefined4 uVar6;

  cVar5 = '\0';
  if (param_2 != '\0') {
    param_1 = (int *)FUN_00013484();
    cVar5 = extraout_DL;
  }
  FUN_0048e788(param_1,0);
  if (param_1[0x52] == 0) {
    iVar1 = FUN_003c7c48(&PTR_FUN_003c6850,1,0);
    param_1[0x52] = iVar1;
    *(undefined4 *)(iVar1 + 4) = 0x37c1;
    *(undefined1 *)(iVar1 + 8) = 0;
    uVar2 = FUN_0049b0a0(*(undefined4 *)PTR_DAT_004c88fc,CONCAT22(extraout_var,0x37c1));
    iVar1 = param_1[0x52];
    FUN_00012bec(iVar1 + 9,*(int *)PTR_DAT_004c88fc + 4 + (uVar2 & 0xffff) * 0x8a,
                 CONCAT31((int3)((uint)*(int *)PTR_DAT_004c88fc >> 8),0x11));
    *(undefined1 *)(iVar1 + 0xb1) = 3;
    *(ushort *)(iVar1 + 0xb6) =
         *(ushort *)(*(int *)PTR_DAT_004c88fc + 0x12 + (uVar2 & 0xffff) * 0x8a) % 1000;
  }
  FUN_00012d10(param_1 + 0x47,0xb,0);
  *(undefined1 *)((int)param_1 + 0x127) = 0;
  FUN_00013eac(param_1 + 0x3b);
  param_1[0x4e] = 0;
  *(undefined1 *)(param_1 + 0x4f) = 0;
  *(undefined1 *)(param_1 + 0x51) = 0;
  uVar2 = *(int *)(*(int *)(*(int *)PTR_DAT_004c96ac + 0x2d0) + 0x3c) - 0x20d;
  iVar1 = (int)uVar2 >> 1;
  if (iVar1 < 0) {
    iVar1 = iVar1 + (uint)((uVar2 & 1) != 0);
  }
  uVar2 = *(int *)(*(int *)(*(int *)PTR_DAT_004c96ac + 0x2d0) + 0x38) - 0x199;
  iVar4 = (int)uVar2 >> 1;
  if (iVar4 < 0) {
    iVar4 = iVar4 + (uint)((uVar2 & 1) != 0);
  }
  (**(code **)(*param_1 + 8))(param_1,"Form_EightTwelve",iVar4,0,0,0,0,0,0x20d,0x199,iVar1);
  *(undefined1 *)(param_1 + 0x2a) = 0;
  FUN_00012d10((int)param_1 + 0x13d,7,0);
  iVar1 = FUN_004920f4(&PTR_LAB_0047ef90,1,param_1);
  param_1[0x3a] = iVar1;
  *(undefined4 *)(iVar1 + 0x134) = 0xf5bf89;
  FUN_0048c810(iVar1,0x38);
  piVar3 = (int *)param_1[0x3a];
  piVar3[0x51] = 3;
  (**(code **)(*piVar3 + 0x70))(piVar3,0x1a,0x52,0x124,0x161);
  (**(code **)(*(int *)param_1[0x3a] + 4))((int *)param_1[0x3a],CONCAT22(extraout_var_00,0x841));
  iVar1 = param_1[0x3a];
  *(undefined1 *)(iVar1 + 0x13c) = 0;
  *(undefined1 *)(iVar1 + 0x13d) = 0;
  *(int **)(iVar1 + 0xfc) = param_1;
  *(code **)(iVar1 + 0xf8) = FUN_001af118;
  *(undefined1 *)(iVar1 + 0x15c) = 1;
  *(undefined1 *)(iVar1 + 0x15d) = 100;
  *(undefined1 *)(iVar1 + 0x15e) = 1;
  *(undefined1 *)(iVar1 + 0x15f) = 200;
  *(undefined1 *)(iVar1 + 199) = 0;
  *(int **)(iVar1 + 0x7c) = param_1;
  *(undefined1 **)(iVar1 + 0x78) = &LAB_001af764;
  iVar1 = FUN_00438254(&PTR_LAB_0019abe0,1,param_1);
  param_1[0x3c] = iVar1;
  iVar1 = 1;
  do {
    iVar4 = FUN_00438254(&PTR_LAB_0019abe0,1,param_1);
    param_1[iVar1 + 0x3c] = iVar4;
    FUN_00013f00(iVar4 + 4,"NpcStoreSelectedItem");
    (**(code **)(*(int *)param_1[iVar1 + 0x3c] + 8))
              ((int *)param_1[iVar1 + 0x3c],0,(iVar1 + -1) * 0x22 + 0x1e,0x20,0x20,0,0,1,0x20,0x20,
               0x192);
    piVar3 = (int *)param_1[iVar1 + 0x3c];
    piVar3[0x2c] = iVar1;
    piVar3[0x21] = (int)param_1;
    piVar3[0x20] = (int)&LAB_001af520;
    *(undefined1 *)(piVar3 + 0x46) = 0;
    (**(code **)(*piVar3 + 4))(piVar3,CONCAT22(extraout_var_01,0x841));
    iVar4 = param_1[iVar1 + 0x3c];
    *(undefined1 *)(iVar4 + 199) = 0xff;
    *(undefined1 *)(iVar4 + 200) = 1;
    *(undefined1 *)(iVar4 + 0xcb) = 1;
    iVar1 = iVar1 + 1;
  } while (iVar1 != 0xb);
  piVar3 = (int *)FUN_004853d8(&PTR_LAB_0047f28c,1,param_1);
  param_1[0x4a] = (int)piVar3;
  (**(code **)(*piVar3 + 8))(piVar3,"Btn_Buy_1",0x88,0x14,0x38,0,0,1,0x14,0x38,0x1e9);
  iVar1 = param_1[0x4a];
  *(int **)(iVar1 + 0x54) = param_1;
  *(code **)(iVar1 + 0x50) = FUN_001af620;
  piVar3 = (int *)FUN_004853d8(&PTR_LAB_0047f28c,1,param_1);
  param_1[0x4b] = (int)piVar3;
  (**(code **)(*piVar3 + 8))(piVar3,"Btn_Close_1",0xd6,0x14,0x38,0,0,1,0x14,0x38,0x1e9);
  iVar1 = param_1[0x4b];
  *(int **)(iVar1 + 0x54) = param_1;
  uVar6 = *(undefined4 *)(*param_1 + 0x24);
  *(undefined4 *)(iVar1 + 0x50) = uVar6;
  *(undefined1 *)(iVar1 + 0xca) = 1;
  piVar3 = (int *)FUN_004853d8(&PTR_LAB_0047f28c,CONCAT31((int3)((uint)uVar6 >> 8),1),param_1);
  param_1[0x4c] = (int)piVar3;
  uVar6 = 0x12;
  (**(code **)(*piVar3 + 8))(piVar3,"Btn_Close_S_1",0x166,0x12,0x12,0,0,1,0x12,0x12,0x19);
  iVar1 = param_1[0x4c];
  *(int **)(iVar1 + 0x54) = param_1;
  *(undefined4 *)(iVar1 + 0x50) = *(undefined4 *)(*param_1 + 0x24);
  *(undefined1 *)(iVar1 + 0xca) = 1;
  iVar1 = 1;
  do {
    *(int *)(param_1[iVar1 + 0x3c] + 0x18) = (iVar1 + -1) * 0x22 + 0x22;
    iVar1 = iVar1 + 1;
  } while (iVar1 != 0xb);
  if (cVar5 != '\0') {
    FUN_000134dc(param_1);
    *in_FS_OFFSET = uVar6;
  }
  return param_1;
}

/*
 * FUN_001af620 - Nesne Market Satin Alma ve Bakiye Kontrolu (Btn_Buy Handler)
 * Bakiye yetersizse "Not enough Points" uyarisi gosterir.
 */
void FUN_001af620(undefined1 *param_1)

{
  undefined1 *puVar1;
  undefined4 *in_FS_OFFSET;
  undefined4 uStack_1c;
  undefined1 *puStack_18;
  undefined1 *puStack_14;
  undefined1 *local_c;
  undefined4 local_8;

  puStack_14 = &stack0xfffffffc;
  local_8 = 0;
  local_c = (undefined1 *)0x0;
  puStack_18 = &LAB_001af6e7;
  uStack_1c = *in_FS_OFFSET;
  *in_FS_OFFSET = &uStack_1c;
  if (*(int *)(param_1 + 0x134) < *(int *)(param_1 + 0x138)) {
    puStack_14 = &stack0xfffffffc;
    (**(code **)(**(int **)PTR_DAT_004c8d24 + 0x9c))
              (*(int **)PTR_DAT_004c8d24,"Not enough Points",0x5dc,0,0);
    puVar1 = puStack_14;
  }
  else {
    puVar1 = &stack0xfffffffc;
    if (param_1[0x127] != '\0') {
      FUN_00013eac(&local_8);
      FUN_0001953c(*(undefined4 *)(param_1 + 0x138),&local_c);
      FUN_000141ec(&local_8,6);
      puStack_18 = &DAT_001af760;
      uStack_1c = 0;
      puStack_14 = param_1;
      local_c = param_1;
      FUN_00366ebc(*(undefined4 *)PTR_DAT_004c881c,local_8,1);
      puVar1 = puStack_14;
    }
  }
  puStack_14 = puVar1;
  puVar1 = puStack_14;
  *in_FS_OFFSET = uStack_1c;
  puStack_14 = &LAB_001af6ee;
  puStack_18 = (undefined1 *)0x1af6e6;
  FUN_00013ed0(&local_c,2,puVar1);
  return;
}
