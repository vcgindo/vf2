import React, { useEffect, useState } from "react";
import styled from "styled-components";
import {  SearchInputMultiple } from "../../../components";
import { useUserData } from "../../../context";
import Checkbox from "../../../components/VectorFLOW/commons/MTO/Checkbox";
import { set } from "lodash";
import { SelectAllWrapper, SectionContainer, SectionTitle, SelectContainer, Label, Grid, TitleContainer } from "./style";


const PermissionForm = ({
  currentAppAllPermissions,
  selectedPermissions,
  setSelectedPermissions,
  selectedApplication,
}: any) => {

  const [LL1, setLL1] = useState<any>(
    Object.keys(currentAppAllPermissions.location_permission)
  );
  const [LL2,setLL2] = useState<any>([]);
  const [LL3, setLL3] = useState<any>([]);
  const [PL1, setPL1] = useState<any>(
    Object.keys(currentAppAllPermissions.product_permission)
  );
  const [PL2, setPL2] = useState<any>([]);
  const [PL3, setPL3] = useState<any>([]);
  const [LL1Opts, setLL1Opts] = useState<any>(
    LL1?.map((e: any) => {
      return { label: e, value: e };
    })
  );
  const [LL2Opts, setLL2Opts] = useState<any>([]);
  const [LL3Opts, setLL3Opts] = useState<any>([]);

  const [PL1Opts, setPL1Opts] = useState<any>(
    PL1?.map((e: any) => {
      return { label: e, value: e };
    })
  );
  const [PL2Opts, setPL2Opts] = useState<any>([]);
  const [PL3Opts, setPL3Opts] = useState<any>([]);

  useEffect(() => {
    if (
      !currentAppAllPermissions ||
      !currentAppAllPermissions.location_permission ||
      !currentAppAllPermissions.product_permission
    ) {
      return;
    }
    const l1Keys = Object.keys(currentAppAllPermissions.location_permission);

    const l2Keys: any = [];
    const l3keys: any = [];
    l1Keys.forEach((l1Key: any) => {
      const l2Obj = currentAppAllPermissions.location_permission[l1Key];

      Object.keys(l2Obj).forEach((l2Key) => {
        l2Keys.push(`${l1Key}>${l2Key}`);

        const l3Array = l2Obj[l2Key];
        if (Array.isArray(l3Array)) {
          l3Array.forEach((entry: any) => {
            if (entry.location_heirarchy_3) {
              l3keys.push(`${l1Key}>${l2Key}>${entry.location_heirarchy_3}`);
            }
          });
        }
      });
    });
    setLL1(l1Keys);
    setLL2(l2Keys);
    setLL3(l3keys);

    const P1Keys = Object?.keys(currentAppAllPermissions?.product_permission);
    const p2Keys: any = [];
    const p3keys: any = [];
    P1Keys.forEach((p1Key: any) => {
      const p2Obj = currentAppAllPermissions?.product_permission[p1Key];

      Object.keys(p2Obj).forEach((p2Key) => {
        p2Keys.push(`${p1Key}>${p2Key}`);
        const p3Array = p2Obj[p2Key];
        if (Array.isArray(p3Array)) {
          p3Array.forEach((entry: any) => {
            if (entry.product_hierarchy_3) {
              p3keys.push(`${p1Key}>${p2Key}>${entry.product_hierarchy_3}`);
            }
          });
        }
      });
    });
    setPL1(P1Keys);
    setPL2(p2Keys);
    setPL3(p3keys);
  }, [currentAppAllPermissions]);

  useEffect(() => {
    setLL1Opts(
      LL1.map((e: any) => {
        return { label: e, value: e };
      })
    );
    setPL1Opts(
      PL1.map((e: any) => {
        return { label: e, value: e };
      })
    );
  }, [LL1, PL1]);

  // When LL1 changes → update LL2 options and selected LL2 (keep LL3 unchanged)
  useEffect(() => {
    if (!selectedApplication ) return;

    const selectedLocPerms =
      selectedPermissions[selectedApplication]?.location_permission || [];
    const newLL2Opts: any[] = [];

    const selectedL1Keys = selectedLocPerms.map((e:any)=>e[0])


    LL2.forEach((ele:any)=>{
      if(selectedL1Keys.some((val:any)=> val===ele.split('>')[0])){
        newLL2Opts.push(ele);
      }
    })
    setLL2Opts(newLL2Opts.map((e:any) => ({ label: e, value: e })));
  }, [LL2,selectedPermissions, selectedApplication]);

  useEffect(() => {
    if (!selectedApplication ) return;
  
    const selectedLocPerms =
      selectedPermissions[selectedApplication]?.location_permission || [];
    const newLL3Opts: any[] = [];
  
    const selectedL2Keys = selectedLocPerms
      .filter((e: any) => e.length >= 2)
      .map((e: any) => `${e[0]}>${e[1]}`);
  
    LL3.forEach((ele: any) => {
      if (selectedL2Keys.some((val: any) => val === ele.split('>').slice(0, 2).join('>'))) {
        newLL3Opts.push(ele);
      }
    });
  
    setLL3Opts(newLL3Opts.map(e => ({ label: e, value: e })));
  }, [LL3,selectedPermissions, selectedApplication]);

  useEffect(() => {
    if (!selectedApplication ) return;
  
    const selectedProdPerms =
      selectedPermissions[selectedApplication]?.product_permission || [];
    const newPL2Opts: any[] = [];
  
    const selectedP1Keys = selectedProdPerms.map((e: any) => e[0]);
  
    PL2.forEach((ele: any) => {
      if (selectedP1Keys.some((val: any) => val === ele.split('>')[0])) {
        newPL2Opts.push(ele);
      }
    });

  
    setPL2Opts(newPL2Opts.map(e => ({ label: e, value: e })));
  }, [PL2,selectedPermissions, selectedApplication]);

  useEffect(() => {
    if (!selectedApplication) return;
  
    const selectedProdPerms =
      selectedPermissions[selectedApplication]?.product_permission || [];
    const newPL3Opts: any[] = [];

    
    const selectedP2Keys = selectedProdPerms
    .filter((e: any) => e.length >= 2)
    .map((e: any) => `${e[0]}>${e[1]}`);
    
    PL3.forEach((ele: any) => {
      if (selectedP2Keys.some((val: any) => val === ele.split('>').slice(0, 2).join('>'))) {
        newPL3Opts.push(ele);
      }
    });

  
    setPL3Opts(newPL3Opts.map(e => ({ label: e, value: e })));
  }, [PL3,selectedPermissions, selectedApplication]);
  
  
  

  

  const getUniqueObjects=(arr:any, key:any)=> {
    const seen = new Set();
    return arr.filter((item:any) => {
      const val = item[key];
      if (seen.has(val)) return false;
      seen.add(val);
      return true;
    });
  }
  const getSelectedPermissions = ({
    selectedPermissions,
    selectedApplication,
    permissionType,
    level,
  }: any) => {
    const currentPermissions =  (selectedPermissions && selectedPermissions?.[selectedApplication]) || {};

    const permissionSet = currentPermissions?.[permissionType] || [];

    let val: { value: string; label: string }[] = [];




    if (level === 0) {
      val = permissionSet
        .filter((e: any) => e.length >= 1)
        .map((e: any) => ({
          value: e[0],
          label: e[0],
        }));
    }

    if (level === 1) {
      val = permissionSet
        .filter((e: any) => e.length >= 2)
        .map((e: any) => {
          const joined = e.slice(0, 2).join(">");
          return { value: joined, label: joined };
        })
    }

    if (level === 2) {
      val = permissionSet
        .filter((e: any) => e.length >= 3)
        .map((e: any) => {
          const joined = e.slice(0, 3).join(">");
          return { value: joined, label: joined };
        });
    }

    return getUniqueObjects(val, "value");
  };

  const updateSelectedPermissions = ({
    val,
    selectedPermissions,
    selectedApplication,
    permissionType,
    level,
  }: any) => {
    if (!val || !Array.isArray(val)) return;
  
    // Extract the `value` property from each object in `val`
    const values = val.map((item: any) => item.value);
  
    const prevPerms =
      selectedPermissions?.[selectedApplication]?.[permissionType] || [];
  
    const selectPermissions = Array.isArray(prevPerms) ? prevPerms : [];
  
    let newPerm: any[] = [];

    if (level === 0) {
      // Level 0: Update top-level permissions
      // Keep all permissions that don't start with any of the current level 0 values
      const existingLevel0Values = Array.from(
        new Set(selectPermissions.map((perm: any) => perm[0]))
      );
      // Remove permissions that start with deselected level 0 values
      const permissionsToKeep = selectPermissions.filter((perm: any) => 
        values.includes(perm[0])
      );
      
      // Add new level 0 permissions that don't exist
      const newLevel0Permissions = values
        .filter((value: string) => !existingLevel0Values.includes(value))
        .map((value: string) => [value]);
      
      newPerm = [...permissionsToKeep, ...newLevel0Permissions];
    }
  
    if (level === 1) {
      // Level 1: Update second-level permissions
      const valMap = values.map((item: string) => item.split(">"));
      
      // Get all existing level 1 combinations (parent>child)
      const existingLevel1Combinations = selectPermissions
        .filter((perm: any) => perm.length >= 2)
        .map((perm: any) => `${perm[0]}>${perm[1]}`);
      
      // Keep permissions that match selected level 1 values OR are deeper levels of selected values
      const permissionsToKeep = selectPermissions.filter((perm: any) => {
        if (perm.length === 1) {
          // Keep level 0 permissions that don't have any level 1 selections
          return !valMap.some(([parent]) => parent === perm[0]);
        } else if (perm.length >= 2) {
          // Keep level 1+ permissions that are in the selected values
          const permLevel1Key = `${perm[0]}>${perm[1]}`;
          return values.includes(permLevel1Key);
        }
        return false;
      });
      
      // Add new level 1 permissions
      const newLevel1Permissions = valMap
        .filter(([parent, child]) => {
          const key = `${parent}>${child}`;
          return !existingLevel1Combinations.includes(key);
        })
        .map(([parent, child]) => [parent, child]);
      
      // Add back level 0 permissions for parents that have level 1 selections
      const parentsWithLevel1 = Array.from(
        new Set(valMap.map(([parent]) => parent))
      );
      const level0ToAdd = parentsWithLevel1
        .filter((parent: string) => 
          !selectPermissions.some((perm: any) => 
            perm.length === 1 && perm[0] === parent
          ) && 
          !permissionsToKeep.some((perm: any) => 
            perm.length === 1 && perm[0] === parent
          )
        )
        .map((parent: string) => [parent]);
      
      newPerm = [...permissionsToKeep, ...newLevel1Permissions, ...level0ToAdd];
    }
  
    if (level === 2) {
      // Level 2: Update third-level permissions
      const valMap = values.map((item: string) => item.split(">"));
      
      // Get all existing level 2 combinations
      const existingLevel2Combinations = selectPermissions
        .filter((perm: any) => perm.length >= 3)
        .map((perm: any) => `${perm[0]}>${perm[1]}>${perm[2]}`);
      
      // Keep permissions that match selected level 2 values OR are not affected by this level
      const permissionsToKeep = selectPermissions.filter((perm: any) => {
        if (perm.length === 1) {
          // Keep level 0 permissions that don't have any level 2 selections affecting them
          return !valMap.some(([parent]) => parent === perm[0]);
        } else if (perm.length === 2) {
          // Keep level 1 permissions that don't have any level 2 selections affecting them
          return !valMap.some(([parent, child]) => 
            parent === perm[0] && child === perm[1]
          );
        } else if (perm.length >= 3) {
          // Keep level 2+ permissions that are in the selected values
          const permLevel2Key = `${perm[0]}>${perm[1]}>${perm[2]}`;
          return values.includes(permLevel2Key);
        }
        return false;
      });
      
      // Add new level 2 permissions
      const newLevel2Permissions = valMap
        .filter(([parent, child, subChild]) => {
          const key = `${parent}>${child}>${subChild}`;
          return !existingLevel2Combinations.includes(key);
        })
        .map(([parent, child, subChild]) => [parent, child, subChild]);
      
      // Add back level 0 and level 1 permissions for hierarchy
      const parentsWithLevel2 = Array.from(new Set(valMap.map(([parent]) => parent)));
      const level1WithLevel2 = Array.from(new Set(valMap.map(([parent, child]) => `${parent}>${child}`)));
      
      const level0ToAdd = parentsWithLevel2
        .filter((parent: string) => 
          !permissionsToKeep.some((perm: any) => 
            perm.length === 1 && perm[0] === parent
          )
        )
        .map((parent: string) => [parent]);
      
      const level1ToAdd = level1WithLevel2
        .filter((parentChild: string) => {
          const [parent, child] = parentChild.split('>');
          return !permissionsToKeep.some((perm: any) => 
            perm.length === 2 && perm[0] === parent && perm[1] === child
          );
        })
        .map((parentChild: string) => parentChild.split('>'));
      
      newPerm = [...permissionsToKeep, ...newLevel2Permissions, ...level0ToAdd, ...level1ToAdd];
    }
  
    // Update the selected permissions state
    setSelectedPermissions((prev: any) => ({
      ...prev,
      [selectedApplication]: {
        ...prev[selectedApplication],
        [permissionType]: newPerm,
      },
    }));
  };

  const themeUi= useUserData().user.user.theme_ui

  const isSelectAll = (selectedPermissions: any, isProduct: boolean) => {
    if (!selectedApplication) return false;

    const currentPermissions = selectedPermissions[selectedApplication] || {};
    if (isProduct) {
      const prodPerms = currentPermissions["product_permission"] || [];
      const totalProdPerms = PL3.length;
      
      const selectedProdPermsCount = prodPerms.filter((e: any) => e.length === 3).length;
      return selectedProdPermsCount === totalProdPerms;

    } else {
      const locPerms = currentPermissions["location_permission"] || [];
      
      const totalLocPerms = LL3.length;
      const selectedLocPermsCount = locPerms.filter((e: any) => e.length === 3).length;
      return selectedLocPermsCount === totalLocPerms;
    }
  }

  const setAllPermissions = (isProductPermission:boolean) => {
    if (!selectedApplication) return;

    if (isSelectAll(selectedPermissions, isProductPermission)) {
      // Deselect all
      setSelectedPermissions((prev: any) => ({
        ...prev,
        [selectedApplication]: {
          location_permission: !isProductPermission ? [] : prev[selectedApplication]?.location_permission,
          product_permission: isProductPermission ? [] : prev[selectedApplication]?.product_permission,
        },
      }));
    } else {
      // Select all
      const allLocPerms = LL3.map((e: any) => e.split(">"));
      const allProdPerms = PL3.map((e: any) => e.split(">"));

      setSelectedPermissions((prev: any) => ({
        ...prev,
        [selectedApplication]: {
          location_permission: !isProductPermission ? allLocPerms : prev[selectedApplication]?.location_permission,
          product_permission: isProductPermission ? allProdPerms : prev[selectedApplication]?.product_permission,
        },
      }));
    }
  }

  return (
    <div style={{ padding: "40px 20px 20px 20px" }}>
      <SectionContainer>
        <TitleContainer>
            <SectionTitle>Product Permission</SectionTitle>
            <div style={{ marginBottom: "20px", fontSize: "14px", fontWeight: 600, display: 'flex', justifyContent: 'right', alignItems: 'center'}}>
              <SelectAllWrapper>
              <Checkbox
                          style={{ zoom: 0.5 }}
                          theme={themeUi}
                          type="checkbox"
                          checked={isSelectAll(selectedPermissions, true)}
                          onClick={(e) => e.stopPropagation()} // prevent double trigger
                          onChange={(e: any) => {setAllPermissions(true)}}
                          />
                        <label style={{ cursor: "pointer" }}>Select All</label>

              </SelectAllWrapper>
            </div>
          
        </TitleContainer>
        <Grid>
          <SelectContainer>
              <Label>Business</Label>
            <SearchInputMultiple
              disabled={false}
              placeholder="Select"
              options={PL1Opts}
              value={getSelectedPermissions({
                selectedPermissions,
                selectedApplication,
                permissionType: "product_permission",
                level: 0,
              })}
              setValue={(e: any) => {
                updateSelectedPermissions({
                  val: e,
                  selectedPermissions,
                  selectedApplication,
                  permissionType: "product_permission",
                  level: 0,
                });
              }}
              key={1}
            />
          </SelectContainer>
          <SelectContainer>
            <Label>Category</Label>
            <SearchInputMultiple
              placeholder="Select"
              disabled={false}
              options={PL2Opts}
              value={getSelectedPermissions({
                selectedPermissions,
                selectedApplication,
                permissionType: "product_permission",
                level: 1,
              })}
              setValue={(e: any) => {
                updateSelectedPermissions({
                  val: e,
                  selectedPermissions,
                  selectedApplication,
                  permissionType: "product_permission",
                  level: 1,
                });
              }}
              key={2}
            />
          </SelectContainer>
          <SelectContainer>
            <Label>Value</Label>
            <SearchInputMultiple
              placeholder="Select"
              disabled={false}
              options={PL3Opts}
              value={getSelectedPermissions({
                selectedPermissions,
                selectedApplication,
                permissionType: "product_permission",
                level: 2,
              })}
              setValue={(e: any) => {
                updateSelectedPermissions({
                  val: e,
                  selectedPermissions,
                  selectedApplication,
                  permissionType: "product_permission",
                  level: 2,
                });
              }}
              key={3}
            />
          </SelectContainer>
        </Grid>
      </SectionContainer>

      <SectionContainer>
        <TitleContainer>
        <SectionTitle>Location Permission</SectionTitle>
              <div style={{ marginBottom: "20px", fontSize: "14px", fontWeight: 600, display: 'flex', justifyContent: 'right', alignItems: 'center'}}>
                <SelectAllWrapper>
                <Checkbox
                            style={{ zoom: 0.5 }}
                            theme={themeUi}
                            type="checkbox"
                            checked={isSelectAll(selectedPermissions, false)}
                            onClick={(e) => e.stopPropagation()} // prevent double trigger
                            onChange={(e: any) => {setAllPermissions(false)}}
                            />
                          <label style={{ cursor: "pointer" }}>Select All</label>

                </SelectAllWrapper>
              </div>
              
            </TitleContainer>
        <Grid>
          <SelectContainer>
            <Label>Zone</Label>
            <SearchInputMultiple
              placeholder="Select"
              disabled={false}
              options={LL1Opts}
              value={getSelectedPermissions({
                selectedPermissions,
                selectedApplication,
                permissionType: "location_permission",
                level: 0,
              })}
              setValue={(e: any) => {
                updateSelectedPermissions({
                  val: e,
                  selectedPermissions,
                  selectedApplication,
                  permissionType: "location_permission",
                  level: 0,
                });
              }}
              key={4}
            />
          </SelectContainer>
          <SelectContainer>
            <Label>Location Group</Label>
            <SearchInputMultiple
              placeholder="Select"
              disabled={false}
              options={LL2Opts}
              value={getSelectedPermissions({
                selectedPermissions,
                selectedApplication,
                permissionType: "location_permission",
                level: 1,
              })}
              setValue={(e: any) => {
                updateSelectedPermissions({
                  val: e,
                  selectedPermissions,
                  selectedApplication,
                  permissionType: "location_permission",
                  level: 1,
                });
              }}
              key={5}
            />
          </SelectContainer>
          <SelectContainer>
            <Label>WH Type</Label>
            <SearchInputMultiple
              placeholder="Select"
              disabled={false}
              options={LL3Opts}
              value={getSelectedPermissions({
                selectedPermissions,
                selectedApplication,
                permissionType: "location_permission",
                level: 2,
              })}
              setValue={(e: any) => {
                updateSelectedPermissions({
                  val: e,
                  selectedPermissions,
                  selectedApplication,
                  permissionType: "location_permission",
                  level: 2,
                });
              }}
              key={6}
            />
          </SelectContainer>
        </Grid>
      </SectionContainer>
    </div>
  );
};

export default PermissionForm;
