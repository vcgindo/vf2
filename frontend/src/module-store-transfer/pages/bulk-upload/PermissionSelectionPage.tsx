import React, { useEffect, useMemo, useRef, useState } from "react";
import VFTable from "../../../VectorFlow/Pages/MTO/Common/VFTable";
import { TableWrapper } from "../../../VectorFlow/Pages/MTO/Procurement/InsightsAndTrends/RMPMOrderwiseCoverage/styles";
import { CellStyle, ColDef, FillOperationParams, RowStyle } from "ag-grid-enterprise";
import { AgGridReactProps } from "ag-grid-react";
import BulkUploadHeader from "./BulkUploadHeader";
import VFModalCard from "../../../components/VectorFLOW/commons/VFModalCard";
import {
  useGetAllPermissions,
  useGetAllRoles,
  useGetRoles,
  usePostBulkUploadUsers,
} from "../../../services/profile";
import RoleSelectionModal from "./RoleSelectionModal";
import RoleViewCellRenderer from "./RoleViewCellRenderer";
import { GridRef } from "../../../VectorFlow/types/MDM";
import PermissionSelectionModal from "./PermissionSelectionModal";
import PermissionViewCellRenderer from "./PermissionViewCellRenderer";
import VFButton from "../../../components/VectorFLOW/commons/VFButton";
import OverlayLoader from "../../../VectorFlow/Pages/MTO/Common/Loader";
import { SCGoBackContainer, SCGoBackText } from "../../../components/VectorFLOW/commons/MTO/ActionToolBar/styles";
import _ from "lodash";
import { notifyError, notifySuccess } from "../../../helpers/notify";
import { useUserData } from "../../../context";
import { useGetDBRsettingsData } from "../../../VectorFlow/Services/MTO/Common/DBRSettings";



type Role = {
  id: number;
  name: string;
  application_name: string;
};

const PermissionSelectionPage = ({
  validUserData,
  themeUi,
  setValidUsersData,
  setIsAssignPage
}: {
  validUserData: any;
  setValidUsersData: any
  themeUi: any;
  setIsAssignPage: any
}) => {
  const user = useUserData();
  const { mutateAsync: getDBRsettingsData} = useGetDBRsettingsData(); 
  const [isFinalView, setIsFinalView] = useState(false);
  const [isPermissionModalOpen, setIsPermissionModalOpen] =
    React.useState(false);
  const [isPermissionModalOpenForRow, setIsPermissionModalOpenForRow] =
    React.useState(false);

  const {mutateAsync: postPostBulkUploadUsers, isLoading} = usePostBulkUploadUsers();
  const [isRoleModalOpen, setIsRoleModalOpen] = React.useState(false);
  const { data: dataPermissions, isLoading: isDataPermissions } = useGetAllPermissions();
  const { data: dataRoles, isLoading: isDataRoles } = useGetRoles();
  const [listRoles, setListRoles] = useState<any>([]);
  const gridRef = useRef<GridRef>(null);
  const [compulsoryPermissions, setCompulsoryPermissions] = useState<any>([]);

  const dataAllPermissions = dataPermissions?.data;
  const dataAllRole = dataRoles?.data;

  const addMTOToCompulsoryPermissions = async(dataAllRole:any)=>{
    try{
      const response = await getDBRsettingsData();
      if(response.status===200){
        const DBRSettings = response?.data?.data || [];
        const isMTOPermissionRequired = DBRSettings?.find((data: any) => data.flag === "IsDataPermissionEnabled" && data.value == 1);
        const MTAPerm = _.uniq(dataAllRole?.filter((ele:any)=>ele.application_name==='Distribution').map((role:any)=>role.application_id)) || [];
        if(isMTOPermissionRequired){
          const MTOPerm = _.uniq(dataAllRole?.filter((ele:any)=>ele.application_name==='Orders').map((role:any)=>role.application_id)) || [];
          setCompulsoryPermissions([...MTAPerm,...MTOPerm]);
        }
        else{
          setCompulsoryPermissions([...MTAPerm]);
        }
      }
      else{
        notifyError("Failed to fetch MTO setttings permission check might not work properly!");
      }
    }catch(e){
      notifyError("Failed to fetch MTO setttings permission check might not work properly!");
      return [];
    }
  }

  const activeApplications = useMemo(() => {
    const apps: string[] = [];
  
    if (user?.user?.config_data?.MTO_ACTIVE) {
      apps.push('Orders');
    }
    if (user?.user?.config_data?.MTA_ACTIVE) {
      apps.push('Distribution');
    }
  
    return apps;
  }, [user]);
  

  useEffect(() => {
    if (!dataAllPermissions?.length) return;
    if (!dataAllRole?.length) return;

    if (compulsoryPermissions.length === 0 && dataAllRole.length > 0) {
      
      if (activeApplications.includes('Orders')) {
        addMTOToCompulsoryPermissions(dataAllRole);
      } else {
        const MTAPerm = _.uniq(dataAllRole?.filter((ele: any) => ele.application_name === 'Distribution').map((role: any) => role.application_id)) || [];
        setCompulsoryPermissions([...MTAPerm]);
      }
      setListRoles(dataAllRole);
    }
  }, [dataAllPermissions, dataAllRole]);

  const updateRolesForSelected = (selectedRoles: Set<Role>) => {
    gridRef.current?.api.forEachNode((node: any) => {
      if (node.isSelected()) {
        const userData = node.data;
        userData.roles = selectedRoles;
        node.setData(userData);
       
      }
    });
  };

  const updatePermissionsForSelected = (selectedPermissions: Set<string>) => {
    gridRef.current?.api.forEachNode((node: any) => {
      if (node.isSelected()) {
        const userData = node.data;
        userData.permissions = selectedPermissions;
        node.setData(userData);
      }
    });
  };

  const [rowIndex, setRowIndex] = useState<number | null>(0);

  const updatePermissionsForTheRow = (selectedPermissions: Set<string>) => {
    if(rowIndex === null || rowIndex === undefined) return;
    gridRef.current?.api.forEachNode((node: any) => {
      if (
        node.rowIndex === rowIndex
      ) {
        const userData = node.data;

        userData.permissions = selectedPermissions;
        node.setData(userData);
      }
    });
    setRowIndex(null);

  }

    useEffect(() => {
      if (!isFinalView) {
        return;
      }  
      if (!gridRef.current?.api) {
        return;
      }
      const hasErrors = validUserData.some((row:any) => 
        row.error && 
        (Array.isArray(row.error) ? row.error.length > 0 : !!row.error)
      );
      gridRef.current.api.setColumnsVisible(['error'], hasErrors);
    }, [ isFinalView]); 


    const transformUserData=(inputUsers: any[])=> {
      const output: any = {
        users: [],
        permissions: {},
        roles: {}
      };
    
      let permIdCounter = 1;
    
      for (const user of inputUsers) {
        const currentPermId = permIdCounter++;
        const currentRoleId = currentPermId;// Linking role ID to perm ID (can be adjusted if needed)
    
        // Push to users array 
        output.users.push({
          srNo: user.srNo || "",
          id: user.id || "",
          email: user.email || "",
          name: user.username || "",
          pwd: user.pwd || "",
          tc: true,
          rid: currentRoleId,
          perm_id: currentPermId
        });
    
        // Set roles
        const roleIds = [...(user.roles || [])]?.map((r: any) => r.id || "") || [];
        output.roles[currentRoleId] = { roles: roleIds };
    
        // Set permissions
        const userPerms:any = user.permissions || {};
        const formattedPerms:any = {
          location_permissions: [],
          product_permissions: []
        };
    
        for (const [appName, perms] of Object.entries(userPerms) as [string, any][]) {
          const application_id = getAppId(appName); // You can customize this mapping
          if (perms?.location_permission) {
            formattedPerms.location_permissions.push({
              application_id,
              permissions: perms.location_permission.map((locPath: string[]) => {
                const obj: any = {};
                locPath.forEach((lvl, i) => {
                  obj[`location_heirarchy_${i + 1}`] = lvl || "";
                });
                return obj;
              })
            });
          }
    
          if (perms?.product_permission) {
            formattedPerms.product_permissions.push({
              application_id,
              permissions: perms.product_permission.map((prodPath: string[]) => {
                const obj: any = {};
                prodPath.forEach((lvl, i) => {
                  obj[`product_hierarchy_${i + 1}`] = lvl || "";
                });
                return obj;
              })
            });
          }
        }
    
        output.permissions[currentPermId] = formattedPerms;
      }
    
      return output;
    }
    
    // Helper to assign application IDs (you can customize this)
    const getAppId=(appName: string)=> {
      const appMap: Record<string, number> = {
        Distribution: 2,
        Orders: 3
      };
      return appMap[appName] || 1;
    }


    const [errorRes, setErrorRes] = useState(0);

    const optimizePermissionsAndRoles = (data:any) => {
      const { users, permissions, roles } = data;
      
      // Import lodash for deep comparison (assuming it's available)
      // const _ = require('lodash'); // for Node.js
      // or use the imported lodash from your environment
      
      // Arrays to store unique permissions and roles with their objects and new IDs
      const uniquePermissions:any = []; // [{obj, newId}]
      const uniqueRoles:any = []; // [{obj, newId}]
      const permissionIdMapping = new Map(); // old_id -> new_id
      const roleIdMapping = new Map(); // old_id -> new_id
      
      let nextPermId = 1;
      let nextRoleId = 1;
      
      // Process permissions using lodash isEqual for deep comparison
      Object.entries(permissions).forEach(([oldPermId, permissionObj]) => {
        // Check if this permission object already exists
        const existingPermission = uniquePermissions.find((item:any) => 
          _.isEqual(item.obj, permissionObj)
        );
        
        if (existingPermission) {
          // Permission already exists, map old ID to existing new ID
          permissionIdMapping.set(oldPermId, existingPermission.newId);
        } else {
          // New unique permission, create new ID and store
          const newPermId = nextPermId++;
          uniquePermissions.push({ obj: permissionObj, newId: newPermId });
          permissionIdMapping.set(oldPermId, newPermId);
        }
      });
      
      // Process roles using lodash isEqual for deep comparison
      Object.entries(roles).forEach(([oldRoleId, roleObj]) => {
        // Check if this role object already exists
        const existingRole = uniqueRoles.find((item:any) => 
          _.isEqual(item.obj, roleObj)
        );
        
        if (existingRole) {
          // Role already exists, map old ID to existing new ID
          roleIdMapping.set(oldRoleId, existingRole.newId);
        } else {
          // New unique role, create new ID and store
          const newRoleId = nextRoleId++;
          uniqueRoles.push({ obj: roleObj, newId: newRoleId });
          roleIdMapping.set(oldRoleId, newRoleId);
        }
      });
      
      // Create optimized permissions object
      const optimizedPermissions:any = {};
      uniquePermissions.forEach(({ obj, newId }:any) => {
        optimizedPermissions[newId] = obj;
      });
      
      // Create optimized roles object
      const optimizedRoles:any = {};
      uniqueRoles.forEach(({ obj, newId }:any) => {
        optimizedRoles[newId] = obj;
      });
      
      // Update users with new permission and role IDs
      const optimizedUsers = users.map((user:any) => ({
        ...user,
        perm_id: permissionIdMapping.get(user.perm_id.toString()),
        rid: roleIdMapping.get(user.rid.toString())
      }));
      
      // Return optimized data structure
      const optimizedData = {
        users: optimizedUsers,
        permissions: optimizedPermissions,
        roles: optimizedRoles
      };
      
      return optimizedData;
    };
    
    // Example usage:
    // const optimizedData = optimizePermissionsAndRoles(yourDataObject);

    /**
     * A function to validate if all selected users have roles of the same application.
     * @returns boolean
     */

    function validateUserPermissions({roles, finalData, compulsoryPermissionsApps}:any) {
      const errors:any = [];
      const warnings:any = [];
      
      // Create a map of role id to application_id for quick lookup
      const roleToAppMap:any = {};
      roles.forEach((role:any) => {
          roleToAppMap[role.id] = role.application_id;
      });
      
      // Task 1: Check if users with roles from compulsory apps have corresponding permissions
      finalData.users.forEach((user:any )=> {
          const userRoles = finalData.roles[user.rid]?.roles || [];
          const userPermissions = finalData.permissions[user.perm_id] || {};
          const userLocationPermissions = userPermissions.location_permissions || [];
        const userProductPermissions = userPermissions.product_permissions || [];
          
          // Get application IDs from user's permissions (both location and product)
          const userPermissionAppIdsLoc = new Set();
          const userPermissionAppIdsPerm = new Set();
          
          // Add application IDs from location permissions
        userLocationPermissions.forEach((perm: any) => {
          if (perm?.permissions?.length) {
            userPermissionAppIdsLoc.add(perm.application_id);
          }
        });
          
          // Add application IDs from product permissions
        userProductPermissions.forEach((perm: any) => {
          if (perm?.permissions?.length) {
            userPermissionAppIdsPerm.add(perm.application_id);
          }
        });

          if(userRoles.length === 0){
            errors.push({
              type: 'MISSING_ROLES',
              message: `All users must have at least one role assigned`,
              srNo: user.srNo,
              userId: user.id,
              userName: user.name,
              email: user.email,
              permId: user.perm_id
          });
          }
          
          // Check each role assigned to the user
          userRoles.forEach((roleId:any) => {
              const appId = roleToAppMap[roleId];
              // If the role belongs to a compulsory permissions app
              if (compulsoryPermissions.includes(appId)) {
                  // Check if user has permissions for this application
                  if (!userPermissionAppIdsLoc.has(appId) || !userPermissionAppIdsPerm.has(appId)) {
                      errors.push({
                          type: 'MISSING_COMPULSORY_PERMISSION',
                          message: `All users with a role of application: ${dataAllPermissions.find((ele:any)=>ele.application_id===appId).application_name} must have Location and Product Permissions`,
                          userId: user.id,
                          userName: user.name,
                          email: user.email,
                          roleId: roleId,
                          applicationId: appId,
                          permId: user.perm_id
                      });
                  }
              }
          });
      });
      
      // Task 2: Remove permissions for applications where user has no roles
      const modifiedFinalData = JSON.parse(JSON.stringify(finalData)); // Deep clone
      
      finalData.users.forEach((user:any )=> {
          const userRoles = finalData.roles[user.perm_id]?.roles || [];
          const userPermissions = modifiedFinalData.permissions[user.perm_id];
          
          if (!userPermissions) {
              return;
          }
          
          // Get application IDs from user's roles
          const userRoleAppIds = new Set(
              userRoles.map((roleId:any) => roleToAppMap[roleId]).filter((appId:any) => appId !== undefined)
          );
          
          // Handle location permissions
          if (userPermissions.location_permissions) {
              userPermissions.location_permissions = userPermissions.location_permissions.filter((perm:any) => {
                  const shouldKeep = userRoleAppIds.has(perm.application_id);
                  
                  if (!shouldKeep) {
                      warnings.push({
                          type: 'LOCATION_PERMISSION_REMOVED',
                          message: `Location permission for application id ${perm.application_id} removed for user ${user.name} (no corresponding role)`,
                          srNo: user.srNo,
                          userId: user.id,
                          userName: user.name,
                          email: user.email,
                          permId: user.perm_id,
                          removedApplicationId: perm.application_id,
                          removedPermission: perm,
                          permissionType: 'location'
                      });
                  }
                  
                  return shouldKeep;
              });
          }
          
          // Handle product permissions
          if (userPermissions.product_permissions) {
              const originalProductPermissions = [...userPermissions.product_permissions];
              userPermissions.product_permissions = userPermissions.product_permissions.filter((perm:any) => {
                  const shouldKeep = userRoleAppIds.has(perm.application_id);
                  
                  if (!shouldKeep) {
                      warnings.push({
                          type: 'PRODUCT_PERMISSION_REMOVED',
                          message: `Product permission for application ${perm.application_id} removed for user ${user.name} (no corresponding role)`,
                          srNo: user.srNo,
                          userId: user.id,
                          userName: user.name,
                          email: user.email,
                          permId: user.perm_id,
                          removedApplicationId: perm.application_id,
                          removedPermission: perm,
                          permissionType: 'product'
                      });
                  }
                  
                  return shouldKeep;
              });
          }
      });
      
      return {
          isValid: errors.length === 0,
          errors: errors,
          warnings: warnings,
          modifiedData: modifiedFinalData,
          summary: {
              totalErrors: errors.length,
              totalWarnings: warnings.length,
              compulsoryPermissionErrors: errors.filter((e:any) => e.type === 'MISSING_COMPULSORY_PERMISSION').length,
              locationPermissionsRemoved: warnings.filter((w:any) => w.type === 'LOCATION_PERMISSION_REMOVED').length,
              productPermissionsRemoved: warnings.filter((w:any) => w.type === 'PRODUCT_PERMISSION_REMOVED').length
          }
      };
  }

    const createUsers = async()=>{
      const userDataAll: string[] = [];
      gridRef?.current?.api.forEachNode((node: any)=>{
        userDataAll.push(node.data);
      })
      try{
        const finalData = optimizePermissionsAndRoles(transformUserData(userDataAll));
        const {isValid, errors, modifiedData} = validateUserPermissions({roles: listRoles, finalData, compulsorPermissions: compulsoryPermissions});
        if (!isValid) {
          const newValidData = validUserData.map((userData:any) => {
            const error = errors.find((error: any) => error.userId === userData.id);
            if (error) {
              if (error.type === "MISSING_ROLES") {
                userData.errorRole = true;
                userData.errorPermission = true;
              } else if (error.type === "MISSING_COMPULSORY_PERMISSION"){
                userData.errorPermission = true;
              }
            } else {
              delete userData.errorRole;
              delete userData.errorPermission;
            }
            return userData;
          })

          const sortedUsers = [...newValidData].sort((userA, userB) => {
            const aHasError = userA.errorRole || userA.errorPermission;
            const bHasError = userB.errorRole || userB.errorPermission;
            
            if (aHasError && !bHasError) return -1;
            if (!aHasError && bHasError) return 1;
            return 0;
          });

          setValidUsersData(sortedUsers);
          
          let errorMsg = "Errors found:\n";
          errorMsg += `${errors[0].message}\n`;
          notifyError(errorMsg);
          console.error("Errors in user data:", errors);
          return;
        }

        const response = await postPostBulkUploadUsers({...modifiedData})
        if(response.status===200){
          // setIsFinalView(true);
          const errorUserData = response?.data?.failed_users || [];
          const updatedUserData:any = userDataAll;
          errorUserData.forEach((ele:any)=>{
            const index = updatedUserData.findIndex((user:any)=>user.id === ele.id);
            if(index !== -1){
              updatedUserData[index].error = ele.error;
            }
          })
          notifySuccess("Following users created successfully!")
          setErrorRes(errorUserData.length);
          setIsFinalView(true);
          setValidUsersData(validUserData)
        }
        else{
          setIsFinalView(false);
          notifyError("Failed to register Users! Please try again!")
          console.error("Failed to register Users! Please try again!", response);
        }
        
      }catch(e){
        notifyError("Failed to register Users! Please try again!")
        console.error("Error updating roles for selected users", e);
      }

    }


    const columnDefs: ColDef[] = [
      {
        headerName: isFinalView?"Error":"",
        field: isFinalView?"error":"checkbox",
        checkboxSelection: isFinalView?false:true,
        headerCheckboxSelection: isFinalView?false:true,
        initialWidth: isFinalView?200: 50,
        maxWidth: isFinalView? 200: 50,
        pinned: isFinalView?'left':undefined,
        suppressFloatingFilterButton: true,
        filter: isFinalView?"agMultiColumnFilter": false,
        enablePivot: false,
        valueFormatter: (params) => {
          if (isFinalView) {
            if (!params.value){
              return "";
            }
            else{
              let error  = "";
              params.value.forEach((ele:string)=>{
                error+= ele;
              })
              return error;
            }
          }
          return "";
        },
        suppressFillHandle: true,
        hide: isFinalView,
      },
      {
        headerName: "Sr.No",
        field: "srNo",
        maxWidth: 80,
        enablePivot: true,
        filter: 'agNumberColumnFilter',
        suppressFillHandle: true,
      },
      { headerName: "Username", field: "username", suppressFillHandle: true, filter: 'agMultiColumnFilter' },
      { headerName: "Email ID", field: "email", suppressFillHandle: true, filter: 'agMultiColumnFilter' },
      { headerName: "Password", field: "pwd", suppressFillHandle: true, filter: 'agMultiColumnFilter'},
      {
        headerName: "Role",
        field: "roles",
        suppressHeaderFilterButton: true,
        floatingFilter: false,
        cellRenderer: isFinalView?()=>{return <VFButton onClick={()=>{return;}}  disabled={true}
        style={{ width: "90px", height: "25px", fontSize: "1rem" }}
        themeUi={themeUi} >Edit Role</VFButton>}: RoleViewCellRenderer,
        cellRendererParams: {
          allRoles: listRoles,
          allPermissions: dataAllPermissions,
          setIsPermissionModalOpen: setIsPermissionModalOpenForRow,
          setRowIndex: setRowIndex
        },
        cellStyle: (props:any)=>{
          if (isFinalView && props.data.error) {
            return { cursor: "not-allowed"  }as CellStyle;
          }
          else if(isFinalView){
            return { cursor: "not-allowed" } as CellStyle;
          }
          return {};
        }
      },
      {
        headerName: "Permissions",
        field: "permissions",
        floatingFilter: false,
        suppressHeaderFilterButton: true,
        cellRenderer:isFinalView?()=>{return <VFButton onClick={()=>{return;}}  disabled={true}
        style={{ width: "120px", height: "25px", fontSize: "1rem" }}
        themeUi={themeUi} >Edit Permission</VFButton>}: PermissionViewCellRenderer,
        cellRendererParams: {
          allPermissions: dataAllPermissions,
          setIsPermissionModalOpen: setIsPermissionModalOpenForRow,
          setRowIndex: setRowIndex
        },
      },
      
    ];

  const [isBulkActionEnabled, setIsBulkActionEnabled] = useState({ removeUserEnable: false, bulkActionEnable: false });

  const agGridProps: AgGridReactProps = useMemo(() => {
    return {
      rowSelection: "multiple",
    
      getRowStyle: (params) => {
        if (isFinalView && params.data.error) {
          return { backgroundColor: "rgb(242, 75, 75,0.3)", } as RowStyle;
        }
        else if (isFinalView) {
          return { backgroundColor: "rgb(103, 242, 75,0.4)", } as RowStyle;

        }
    
      },
      enableFillHandle: true,
      sideBar: false,
      defaultColDef: {
        flex: 1,
        resizable: true,
        sortable: true,
        filter: true,
        floatingFilter: true,
        suppressMenu: true,
        cellRendererParams: {
          roles: [],
        },
      },
      onSelectionChanged: (params) => {
        const selectedRows = params.api.getSelectedRows();
        const totalRows = params.api.getDisplayedRowCount();

        setIsBulkActionEnabled(
          {
            removeUserEnable: (selectedRows.length > 0 && totalRows > 1 && selectedRows.length !== totalRows),
            bulkActionEnable: selectedRows.length > 0
          });
      },
      suppressRowClickSelection: true,
      pagination: true,
    };
  }, [isFinalView]);
    
  const removeSelectedUser = () => {
    if (gridRef.current) {

      const selectedUsersIds = gridRef.current.api.getSelectedRows()?.map((user: any) => user.id);
      
      const newValidUser = validUserData.filter((validUserData: any) => !selectedUsersIds.includes(validUserData.id));
  
      newValidUser.forEach((row: any, index: number) => {
        row.srNo = index + 1;
      });
      
      setValidUsersData(newValidUser);
    }
  }

    return (
      <TableWrapper style={{ paddingBottom: "50px" }}>
        {(isLoading || isDataPermissions || isDataRoles) && <OverlayLoader message="Creating Users..." />}
        {!isFinalView && (
          <BulkUploadHeader
            gridRef={gridRef}
            themeUi={themeUi}
            isBulkActionEnabled={isBulkActionEnabled}
            setIsPermissionModalOpen={setIsPermissionModalOpen}
            setIsRoleModalOpen={setIsRoleModalOpen}
            resetState={() => {
              const result = confirm("Are you sure you want to reupload? All the progress will be lost.");
              if (!result) return;
              setIsFinalView(false);
              setIsAssignPage(false);
            }}
            removeSelectedUser={removeSelectedUser}
          />
        )}
        {isFinalView && (
          <div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <SCGoBackContainer
                  style={{ paddingLeft: "10px" }}
                  onClick={() => {
                    setIsFinalView(false);
                    setIsAssignPage(false);
                  }}
                >
                  <img
                    src="/assets/img/VectorFLOW/BPR/goback.svg"
                    alt=""
                    style={{ height: "20px" }}
                  />
                  <SCGoBackText style={{ fontSize: "1.5rem" }}>
                    <b>Go Back</b>
                  </SCGoBackText>
                </SCGoBackContainer>
              </div>
            </div>

            <div
              style={{
                fontSize: "1.4rem",
                padding: "34px 0 8px 20px",
                fontWeight: "bold",
              }}
            >
              {errorRes
                ? "* " + errorRes + " of the following users failed to created."
                : "All users created successfully!"}
            </div>
          </div>
        )}
        <VFTable
          ref={gridRef}
          {...agGridProps}
          columnDefs={columnDefs}
          rowData={validUserData}
          getRowId={(params) => params.data.id}
          tooltipHideDelay={100000}
          tooltipShowDelay={0}
          tooltipMouseTrack={true}
          enableFillHandle={true}
          fillHandleDirection={"y"}
          fillOperation={(params: FillOperationParams) => {
            if (params.column.getColId() === "roles") {
              params.api.forEachNode((node: any, index: number) => {
                if (params.rowNode.rowIndex === index) {
                  const userData = node.data;
                  userData.roles = params.initialValues[0];
                  node.setData(userData);
                }
              });
            }
            if (params.column.getColId() === "permissions") {
              params.api.forEachNode((node: any, index: number) => {
                if (params.rowNode.rowIndex === index) {                
                  const userData = node.data;
                  userData.permissions = params.initialValues[0];
                  node.setData(userData);
                }
              });
            }
          }}
          statusBar={{
            statusPanels: [
              { statusPanel: "agTotalRowCountComponent", align: "left" },
            ],
          }}
          maintainColumnOrder
        />
        {!isFinalView && (
          <div
            style={{
              display: "flex",
              width: "100%",
              justifyContent: "flex-end",
              marginTop: "1.2rem",
            }}
          >
            <VFButton
              style={{ height: "3.5rem", fontSize: "1.2rem" }}
              onClick={() => {
                createUsers();
              }}
              themeUi={themeUi}
            >
              Create All Users
            </VFButton>
          </div>
        )}
        {
          isPermissionModalOpen &&
          <VFModalCard
            openModal={isPermissionModalOpen}
            headerIcon={"/assets/img/profile/icon_upload.svg"}
            closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"}
            closeModal={() => {
              setIsPermissionModalOpen(false);
            }}
            headerText={"Set Permissions"}
          >
            {/* <PermissionHeirarchyCanvas  allPermissions={dataAllPermissions}/> */}
            <PermissionSelectionModal
              gridRef={gridRef}
              dataAllPermissions={dataAllPermissions}
              updatePermissions={updatePermissionsForSelected}
              closeModal={() => {
                setIsPermissionModalOpen(false);
              }}
              activeApplications={activeApplications}
            />
          </VFModalCard>
        }
        {
          isPermissionModalOpenForRow &&
          <VFModalCard
            openModal={isPermissionModalOpenForRow}
            headerIcon={""}
            closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"}
            closeModal={() => {
              setIsPermissionModalOpenForRow(false);
            }}
            headerText={"Set Permissions"}
          >
            {/* <PermissionHeirarchyCanvas  allPermissions={dataAllPermissions}/> */}
            <PermissionSelectionModal
              selectedIndex={rowIndex}
              gridRef={gridRef}
              dataAllPermissions={dataAllPermissions}
              updatePermissions={(selectedPermissions: any) => {
                updatePermissionsForTheRow(selectedPermissions);
              }}
              closeModal={() => {
                setIsPermissionModalOpenForRow(false);
              }}
              activeApplications={activeApplications}
            />
          </VFModalCard>
        }
        {
          <VFModalCard
            headerText={"Set Roles"}
            openModal={isRoleModalOpen}
            headerIcon={""}
            closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"}
            closeModal={() => {
              setIsRoleModalOpen(false);
            }}
          >
            <RoleSelectionModal
              activeApplications={activeApplications}
              listRoles={listRoles}
              updateRoles={updateRolesForSelected}
              closeModal={() => {
                setIsRoleModalOpen(false);
              }}
            />
          </VFModalCard>
        }
      </TableWrapper>
    );
  };
export default PermissionSelectionPage;
