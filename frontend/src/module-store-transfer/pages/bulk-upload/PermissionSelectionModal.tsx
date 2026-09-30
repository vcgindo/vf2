import React, { useEffect, useState } from "react";
import styled from "styled-components";
import {
  SCHorizontalDivison,
  SCViewContainer,
  SCViewContainerWithBgToggle,
} from "../../../components/VectorFLOW/commons/MTO/ActionToolBar/styles";
import { useUserData } from "../../../context";
import { NewChartView, NewGridIcon } from "../../../helpers/SvgRenderer";
import PermissionHeirarchyCanvas from "../manage-users/PermissioinHeirarchyCanvas";
import PermissionForm from "./PermissionForm";
import VFButton from "../../../components/VectorFLOW/commons/VFButton";
import VFButtonOutline from "../../../components/VectorFLOW/commons/VFButtonOutline";
import { GridRef } from "../../../VectorFlow/types/MDM";
import { IRowNode } from "ag-grid-enterprise";
import { ToggleButton, ToggleContainer } from "./style";


const ViewToggle = ({
  allApplications,
  selectedApplication,
  setSelectedApplication,
}: any) => {
  return (
    <ToggleContainer>
      {allApplications.map((app: string) => (
        <ToggleButton
          key={app}
          active={selectedApplication === app}
          onClick={() => setSelectedApplication(app)}
        >
          {app}
        </ToggleButton>
      ))}
    </ToggleContainer>
  );
};

const ChartViewToggle = ({ isChartView, setIsChartView }: any) => {
  const user = useUserData();
  const themeUi = user.user.user.theme_ui;

  return (
    <SCViewContainerWithBgToggle style={{ zoom: 0.5 }}>
      <SCViewContainer
        onClick={() => {
          isChartView && setIsChartView && setIsChartView(!isChartView);
        }}
      >
        <NewChartView theme={themeUi} view={!isChartView} />
      </SCViewContainer>

      <SCHorizontalDivison />

      <SCViewContainer
        onClick={() => {
          !isChartView && setIsChartView && setIsChartView(!isChartView);
        }}
        style={{ paddingTop: "7px" }}
      >
        <NewGridIcon theme={themeUi} view={isChartView} />
      </SCViewContainer>
    </SCViewContainerWithBgToggle>
  );
};

const hasSelectedPermissions = (permissions: any): boolean => {
  if (!permissions || typeof permissions !== 'object' || Object.keys(permissions).length === 0) {
    return false; 
  }
  for (const appName in permissions) {
    const appPermissions = permissions[appName];
    if (appPermissions && typeof appPermissions === 'object') {
      
      for (const permType in appPermissions) {
        const permList = appPermissions[permType];
        
        if (Array.isArray(permList) && permList.length > 0) {
          return true; // Found at least one permission
        }
      }
    }
  }

  return false; 
};

const PermissionSelectionModal = ({selectedIndex, gridRef,dataAllPermissions,closeModal, updatePermissions, activeApplications }: {gridRef?: GridRef| any, selectedIndex?: any, dataAllPermissions: any, closeModal: any, updatePermissions: any, activeApplications: any}) => {
  const [isChartView, setIsChartView] = React.useState(false);
  const [allApplications, setAllApplications] = useState<any>(dataAllPermissions?.map(
    (ele: any) => ele.application_name
  ).filter((app: string) => activeApplications.includes(app)));
  const [selectedApplication, setSelectedApplication] = React.useState<
  string[]
  >(allApplications[0]);
  
  const [selectedPermissions, setSelectedPermissions] = useState<any>({});
  
  const ResetPermissions = ()=>{
    gridRef?.current?.api?.forEachNode((node: IRowNode, index: number)=>{
      if(selectedIndex===index){
        setSelectedPermissions(node.data.permissions || {});
      }
    })
  }

  useEffect(()=>{
    ResetPermissions();
      let currentVal:any = gridRef?.current?.api?.getSelectedRows()?.[0] || {};
      if(selectedIndex!==undefined && selectedIndex!==null){

        gridRef?.current?.api?.forEachNode((node: IRowNode, index: number)=>{
          if(selectedIndex===index){
            currentVal = node.data || {};
          }
        })
      }
      setAllApplications(
        dataAllPermissions
          ?.map((ele: any) => ele.application_name)
          .filter(
            (app: string) =>
              activeApplications.includes(app) &&
              Array.from(currentVal?.roles ?? []).some(
                (role: any) => role.application_name === app
              )
          )
      );
      
  },[selectedIndex, gridRef])

  useEffect(()=>{
    setSelectedApplication(allApplications[0]);
  },[allApplications])
  
  const user = useUserData();
  const themeUi = user.user.user.theme_ui;
  
  const clearAllPermissions = () => {
    setSelectedPermissions({});
  }
  
  const isApplyDisabled = !hasSelectedPermissions(selectedPermissions);
  return (
      <div style={{ width: "80vw", height: "80vh", padding: "25px" }}>
        <div
          style={{
            width: "100%",
            height: "28px",
            display: "flex",
            justifyContent: "space-between",  
          }}
          >
          <ViewToggle
            allApplications={allApplications}
            selectedApplication={selectedApplication}
            setSelectedApplication={setSelectedApplication}
            />
          <ChartViewToggle
            isChartView={isChartView}
            setIsChartView={setIsChartView}
            />
        </div>
        <div style={{height: '80%'}}>

        {(!isChartView) ? (
        
          <PermissionHeirarchyCanvas
          dataAllPermissions={dataAllPermissions}
          selectedApplication={selectedApplication}
          selectedPermissions={selectedPermissions}
          setSelectedPermissions={setSelectedPermissions}
          />
          
        ) : (
          <PermissionForm
          currentAppAllPermissions={dataAllPermissions.find(
            (ele: any) => ele.application_name === selectedApplication
          )}
          selectedApplication={selectedApplication}
          selectedPermissions={selectedPermissions}
          setSelectedPermissions={setSelectedPermissions}
          />
        )}
          </div>
        <div style={{display: 'flex', justifyContent: 'space-between', marginTop: '20px', gap: '10px'}}>
          <div>
          <VFButtonOutline
            style={{height: '3.5rem', fontSize: '1.2rem'}}
            themeUi={themeUi}
            onClick={() => {ResetPermissions()}}
            
            >Reset</VFButtonOutline>
            </div>
          <div style={{display: 'flex', gap: '20px'}}>

          <VFButtonOutline
            style={{height: '3.5rem', fontSize: '1.2rem'}}
            themeUi={themeUi}
            onClick={() => {clearAllPermissions()}}
            
            >Clear All</VFButtonOutline>
          <VFButton
          style={{height: '3.5rem', fontSize: '1.2rem'}}
          themeUi={themeUi}
          disabled={isApplyDisabled}
          onClick={() => {updatePermissions(selectedPermissions); closeModal()}}
          >Apply</VFButton>
          
          </div>
        </div>
      </div>
  );
};

export default PermissionSelectionModal;
