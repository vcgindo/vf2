import React, { useState } from "react";
import { ToggleCircle, ToggleContainer, ToggleText } from "./styles";
import { useSelector, useDispatch } from 'react-redux';
import { UPDATE_ROW_DATA} from '../../../../../redux/actions/MDM';
import type { RootState } from '../../../../../redux/store/store';
import _ from "lodash";
import { SET_BUFFER_MODIFY_DATA, SET_CCR_MODIFY_DATA } from "../../../../../redux/actions/MTO";



const ToggleButton: React.FC = (props: any) => {
    
    const dispatch = useDispatch();
    const activeMaster = useSelector((state: RootState) => state.mdm.activeMaster);
  const [isActive, setIsActive] = useState(props.data.iv===undefined?true: props.data.iv);

  const bufferModifyData = useSelector((state: any)=> state.mto.bufferModifyData);
  const ccrModifyData = useSelector((state: any) => state.mto.ccrModifyData);
  const isDisabled = props.data.ia ?? false;

  // Check which activeMaster we're dealing with
  const updateDataForMaster = (modifyData: any, dispatchAction: any, filterKey: string, secondaryKey: string) => {
    const newData = _.cloneDeep(activeMaster.rowData);
    const propsData = props.data;

    // Toggle the 'iv' field based on criteria
    newData.forEach((row: any) => {
      if (
        (row[filterKey] !== undefined && row[filterKey] !== null && row[filterKey] === propsData[filterKey]) ||
        (row[secondaryKey] === propsData[secondaryKey])
      ) {
        row.iv = !isActive;
        if (!propsData?.ia) {
          row.iu = true;
        }
      }
    });

    // Prepare modifyData for dispatch based on primary key presence
    const exists = modifyData
      ? modifyData.some((item: any) => item[secondaryKey] === propsData[secondaryKey])
      : false;

    if (propsData[filterKey] || exists) {
      const newModifyData = _.cloneDeep(modifyData || []).filter((row: any) => row[filterKey] !== propsData[filterKey] && row[secondaryKey] !== propsData[secondaryKey]);
      newModifyData.push({ ...propsData, iv: !isActive , iu: true });
      dispatch(dispatchAction(newModifyData));
    }

    return newData;
  };

   // Generic function to update row data
   const updateRowDataAndToggleState = (newData: any) => {
    dispatch(UPDATE_ROW_DATA(newData));
    setIsActive(!isActive);
  };

  const toggleHandler = () => {
    if (isDisabled) return; // Skip if the toggle function is disabled    

    if (activeMaster.id === 501) {
      const newData = updateDataForMaster(bufferModifyData, SET_BUFFER_MODIFY_DATA, 'bid', 'bcd');
      updateRowDataAndToggleState(newData);
    } else if (activeMaster.id === 502) {
      const newData = updateDataForMaster(ccrModifyData, SET_CCR_MODIFY_DATA, 'cid', 'ccd');
      updateRowDataAndToggleState(newData);
    }
  };

  return (
    <ToggleContainer style={{zoom: 0.6}} isActive={isActive} isDisabled={isDisabled} onClick={toggleHandler}>
      <ToggleCircle isActive={isActive} />
      <ToggleText isActive={isActive}>{isActive ? "Active" : "Inactive"}</ToggleText>
    </ToggleContainer>
  );
};

export default ToggleButton;
