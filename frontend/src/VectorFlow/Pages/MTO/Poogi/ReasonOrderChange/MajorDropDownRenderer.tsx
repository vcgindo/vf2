
import React, { useMemo } from 'react';
import VFSelect from '../../../../../../src/components/VectorFLOW/commons/MTO/VFSelect';
import { useUserData } from "../../../../../context/index";

const CustomCellEditor = (props: any) => {
  const { user } = useUserData();
  const themeUi = user.user.theme_ui;

  if (!props.data) return <></>;
  
  const getOuterObjectByKey = (data: any, searchKey: string) => {
    return data[searchKey];
  }

  const initialData = useMemo(() => {
    if (props.reasonData && Object.entries(props.reasonData.data.data).length) {
      const result = getOuterObjectByKey(props.reasonData?.data?.data, props.data.pid);  
      if (result) {
        const selectedVal = Object.values(result).map((item: any) => {
          return { 'des': item.majd, 'id': item.majid, 'min': item.min };
        });
        return selectedVal;
      } 
    }
    return undefined;
  }, [props.reasonData]);
  

  const extractMinDetails = (data: any, keyId: string) => {
    const item = data.find((d: any) => d.id == keyId);
    if (item && item.min.length > 0) {
      const { mind, minid } = item.min[0];
      return [{ 'des': mind, 'id': minid }];
    }
    return null;
  };

  const handleChange = (event: any) => {
    try {
      if (event !== null) {
        if (event.value != '') {
          const minRsnData = extractMinDetails(initialData, event.value);
          props.data["minordropval"] = minRsnData
          
          props.data["maj"] = event.value;

          props.data["min"] = null;
          props.data["selected"] = true;
        }
      } else {
          
        props.data["min"] = null;

        props.data["maj"] = null;
        
        props.data["selected"] = false;
        
      }
      props.api.refreshCells({ force: true, rowNodes: [props.node] });
      props.api.dispatchEvent({
        type: "cellValueChanged",
        column: props.column,
        colDef: props.colDef,
        data: props.data,
        node: props.node,
        oldValue: props.oldValue,
        newValue: props.data.age,
      });
    } catch (e) {
      console.log(e)
    }
  }

  const handleMinorChange = (event: any) => {
    if (event !== null) {
      props.data["min"] = event.value;
    } else {
      props.data["min"] = null;
    }
    props.api.refreshCells({ force: true, rowNodes: [props.node] });
    props.api.dispatchEvent({
      type: "cellValueChanged",
      column: props.column,
      colDef: props.colDef,
      data: props.data,
      node: props.node,
      oldValue: props.oldValue,
      newValue: props.data.age,
    });
  };

  const renderMajorSelect = () => {
    const reasonOptions = (initialData && Object.entries(initialData).length) ?
      initialData?.map((reason: any) => {
        return { label: reason.des, value: reason.id }
      }) : [];
    
    const defaultSelected = reasonOptions !== undefined ? reasonOptions.find((reason: any) => reason.value === props.data.maj) : undefined;
    
    return (
      <VFSelect
        isClearable ={props.isWip}
        themeUi={themeUi}
        placeholder={"Select Major Reason"}
        options={reasonOptions}
        value={defaultSelected}
        onChange={handleChange}
      />
    )
  }

  const renderMinorSelect = () => {

    const majList: Array<any> = props.reasonData?.data.data
    const majId = parseInt(props.data.maj)

    function getMinArrayByMajid(majid: number): Array<{ label: string | null; value: number | null }> {

      for (const categoryKey in majList) {
        const category = majList[categoryKey];
        for (const itemKey in category) {
          const item = category[itemKey];
          if (item.majid === majid) {
            return item.min.map(({ mind, minid }: any) => ({
              label: mind,
              value: minid
            }));
          }
        }
      }
      return [];
    }

    const optionsList = (props.data.minordropVal || !majId) ? props.data.minordropVal : getMinArrayByMajid(majId)
    const defaultSelected = (optionsList !== undefined) ? optionsList.find((options: any) => options.value === props.data.min) : '';

    return (
      <VFSelect
        isClearable ={props.isWip}
        themeUi={themeUi}
        placeholder={"Select Minor Reason"}
        options={optionsList}
        value={defaultSelected ? defaultSelected : ''}
        onChange={handleMinorChange}
        isDisabled={props.data.maj == undefined}
      />
    )
  }

  return (
    <div style={{
      height: '100%', width: "100%", display: 'flex', border: '1px solid #707070', borderRadius: '4px',
      // marginRight: "20px"
    }}>
      <div style={{ width: '100%', height: "100%", paddingLeft: "2px", paddingRight: "2px" }} >
        {props.colDef.colId === 'MajorReason' ? renderMajorSelect() : renderMinorSelect()}
      </div>
    </div>
  )
}

export default CustomCellEditor;