import _ from "lodash";
import React from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  UPDATE_COLDEFS,
  UPDATE_ROW_DATA,
} from "../../../../../redux/actions/MDM";
import {
  SET_EDITABLE_MAJ_ROW,
  SET_EDITABLE_MIN_ROW,
  SET_POOGI_MODIFY_DATA,
} from "../../../../../redux/actions/MTO";

const PoogiEditDeleteCell = (params: any) => {
  const activeMaster = useSelector((state: any) => state.mdm.activeMaster);
  const dispatch = useDispatch();
  const editableMajRowIndex = useSelector(
    (state: any) => state.mto.editableMajRow
  );

  const editableMinRowIndex = useSelector(
    (state: any) => state.mto.editableMinRow
  );
  const intialPoogiData = useSelector(
    (state: any) => state.mto.poogiIntialData
  );
  const poogiModifyData = useSelector(
    (state: any) => state.mto.poogiModifyData
  );

  const onSaveChange = () => {
    dispatch(
      UPDATE_COLDEFS(
        activeMaster.colDefs.map((colDef: any) => ({
          ...colDef,
          editable: false,
        }))
      )
    );
    if (params.data.minId) {
      const newRowData = _.cloneDeep(activeMaster.rowData);
      newRowData.forEach((element: any) => {
        if (element.majId === params.data.majId) {
          element.minData[params.node.rowIndex].iu = true;
        }
      });
      dispatch(UPDATE_ROW_DATA(newRowData));
      // add it in modify data
      const newModifyData = _.cloneDeep(poogiModifyData?poogiModifyData:[]);

      const existingElement = newModifyData.find(
        (element: any) => element.majId === params.data.majId
      );

      if (existingElement) {
        // If majId exists, handle minData
        const existingMinData = existingElement.minData.find(
          (minElement: any) => minElement.minId === params.data.minId
        );

        if (existingMinData) {
          // Replace existing minData with params.data
          const index = existingElement.minData.indexOf(existingMinData);
          const newData = { ...params.data, iu: true };
          existingElement.minData[index] = newData;
        } else {
          // Add params.data if not found
          const newData = { ...params.data, iu: true };
          existingElement.minData.push(newData);
        }
      } else {
        // If majId does not exist, add a new element
        const activeMasterElement = activeMaster.rowData.find(
          (row: any) => row.majId === params.data.majId
        );

        if (activeMasterElement) {
          const newElement = {
            ...activeMasterElement,
            minData: [{ ...params.data, iu: true }],
          };
          newModifyData.push(newElement);
        }
      }

      dispatch(SET_POOGI_MODIFY_DATA(newModifyData));

      dispatch(SET_EDITABLE_MIN_ROW(null));
    } else {
      const newRowData = _.cloneDeep(activeMaster.rowData);
      newRowData[params.node.rowIndex].iu = true;

      const newModifyData = _.cloneDeep(poogiModifyData?poogiModifyData:[]);

const existingElement = newModifyData.find(
  (element: any) => element.majId === params.data.majId
);

if (existingElement) {
  // If majId exists, update majdsc and set iu to true
  existingElement.majdsc = params.data.majdsc;
  existingElement.iu = true;
} else {
  // If majId does not exist, add a new element with minData as an empty array
  const activeMasterElement = activeMaster.rowData.find(
    (row: any) => row.majId === params.data.majId
  );

  if (activeMasterElement) {
    const newElement = {
      ...activeMasterElement,
      minData: [],
      iu: true,
      majdsc: params.data.majdsc,
    };
    newModifyData.push(newElement);
  }
}

dispatch(SET_POOGI_MODIFY_DATA(newModifyData));
      dispatch(UPDATE_ROW_DATA(newRowData));
      dispatch(SET_EDITABLE_MAJ_ROW(null));
    }
  };

  const onCancel = () => {
    // dispatch(UPDATE_ROW_DATA(intialPoogiData));
    if (params.data.minId) {
      const newData = _.cloneDeep(activeMaster.rowData);

      newData.forEach((ele: any) => {
        if (ele.majId === params.data.majId) {
          intialPoogiData.forEach((e: any) => {
            if (e.majId === params.data.majId) {
              ele.minData[params.node.rowIndex] =
                e.minData[params.node.rowIndex];
            }
          });
        }
      });
      dispatch(UPDATE_ROW_DATA(newData));
      dispatch(SET_EDITABLE_MIN_ROW(null));
    } else {
      const newData = _.cloneDeep(activeMaster.rowData);

      newData.forEach((ele: any) => {
        if (ele.majId === params.data.majId) {
          intialPoogiData.forEach((e: any) => {
            if (e.majId === params.data.majId) {
              ele.majdsc = e.majdsc;
              ele.iu = false;
            }
          });
        }
      });
      dispatch(UPDATE_ROW_DATA(newData));
      dispatch(SET_EDITABLE_MAJ_ROW(null));
    }
    dispatch(
      UPDATE_COLDEFS(
        activeMaster.colDefs.map((colDef: any) => ({
          ...colDef,
          editable: false,
        }))
      )
    );
  };

  if (
    (params.data.minId && editableMinRowIndex === params?.node?.rowIndex) ||
    (!params.data.minId && editableMajRowIndex === params?.node?.rowIndex)
  ) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          gap: "12px",
          justifyContent: "center",
          marginTop: "4px",
        }}
      >
        <div onClick={onSaveChange} style={{ cursor: "pointer" }}>
          <img src="/assets/img/MTOapprovalBuffer.svg" alt="ApproveMaster" />
        </div>

        <div onClick={onCancel} style={{ cursor: "pointer" }}>
          <img src="/assets/img/MTOcancelBuffer.svg" alt="CancelMaster" />
        </div>
      </div>
    );
  }

  const onDeleteClick = () => {
    if (params.data.minId === undefined) {
      const newData = _.cloneDeep(activeMaster.rowData);
      newData[params.node.rowIndex].id = true;
      dispatch(UPDATE_ROW_DATA(newData));

      ///////////
      let newModifyData = _.cloneDeep(poogiModifyData?poogiModifyData:[]);

      const existingElement = newModifyData.find(
        (element: any) => element.majId === params.data.majId
      );

      if (existingElement) {
        // If majId exists, handle minData
        newModifyData.forEach((elmm:any)=>{
          if(elmm.majId===params.data.majId){
            elmm.id = true;
          }
        })

      } else {
        // If majId does not exist, add a new element
        if(poogiModifyData && poogiModifyData.length){
          newModifyData = [{...params.data, minData: [], id: true},...poogiModifyData]
          
        }
        else{
          newModifyData = [{...params.data, minData: [], id: true}]

        }
      }

      dispatch(SET_POOGI_MODIFY_DATA(newModifyData))
     
      /////////


    } else {
      const newData = _.cloneDeep(activeMaster.rowData);
      newData.forEach((ele: any) => {
        if (ele.majId === params.data.majId) {
          ele.minData[params.node.rowIndex].id = true;
        }
      });
      dispatch(UPDATE_ROW_DATA(newData));

      ////////////

      const newModifyData = _.cloneDeep(poogiModifyData?poogiModifyData:[]);

      const existingElement = newModifyData.find(
        (element: any) => element.majId === params.data.majId
      );

      if (existingElement) {
        // If majId exists, handle minData
        const existingMinData = existingElement.minData.find(
          (minElement: any) => minElement.minId === params.data.minId
        );

        if (existingMinData) {
          // Replace existing minData with params.data
          const index = existingElement.minData.indexOf(existingMinData);
          const newData = { ...params.data, id: true };
          existingElement.minData[index] = newData;
        } else {
          // Add params.data if not found
          const newData = { ...params.data, id: true };
          existingElement.minData.push(newData);
        }
      } else {
        // If majId does not exist, add a new element
        const activeMasterElement = activeMaster.rowData.find(
          (row: any) => row.majId === params.data.majId
        );

        if (activeMasterElement) {
          const newElement = {
            ...activeMasterElement,
            minData: [{ ...params.data, id: true }],
          };
          newModifyData.push(newElement);
        }
      }
      dispatch(SET_POOGI_MODIFY_DATA(newModifyData))
      ///////////
    }
  };
  const onDeleteUndoClick = () => {
    if (params.data.minId === undefined) {
      const newData = _.cloneDeep(activeMaster.rowData);
      newData[params.node.rowIndex].id = false;
      dispatch(UPDATE_ROW_DATA(newData));

      // update the poogiModifyData

      const newModifyData = _.cloneDeep(poogiModifyData);
      newModifyData.forEach((ele:any)=>{
        if(ele.majId===params.data.majId){
          ele.id = false;
        }
      })
      dispatch(SET_POOGI_MODIFY_DATA(newModifyData))


    } else {
      const newData = _.cloneDeep(activeMaster.rowData);
      newData.forEach((ele: any) => {
        if (ele.majId === params.data.majId) {
          ele.minData[params.node.rowIndex].id = false;
        }
      });
      dispatch(UPDATE_ROW_DATA(newData));
      const newModifyData = _.cloneDeep(poogiModifyData);
      newModifyData.forEach((ele:any)=>{
        if(ele.majId===params.data.majId){
          ele.minData.forEach((elm: any)=>{
            if(elm.minId===params.data.minId){
              elm.id = false;
            }
          })
        }
      })
      dispatch(SET_POOGI_MODIFY_DATA(newModifyData));
    }
  };

  const onEditClick = () => {
    if (params.data.minId !== undefined) {
      dispatch(SET_EDITABLE_MIN_ROW(params.node.rowIndex));
    } else {
      dispatch(SET_EDITABLE_MAJ_ROW(params.node.rowIndex));
    }
    dispatch(
      UPDATE_COLDEFS(
        activeMaster?.colDefs?.map((colDef: any) => (
          {
          ...colDef,
          editable: (para: any) =>
            para.node.rowIndex === params?.node?.rowIndex,
        }))
      )
    );
  };

  return (
    <div
      style={{
        display: "flex",
        margin: "4px auto",
        width: "80px",
        justifyContent: "center",
      }}
    >
      {!activeMaster.colDefs.some(
        (colDef: any) => colDef.field === "actions"
      ) && (
        <>
          <button
            disabled={
              activeMaster.rowData.some(
                (element: any) =>
                  element.majId === params.data.majId && element.id === true
              ) || params.data.id


            }
            onClick={onEditClick}
            style={{
              background: "transparent",
              opacity: `${  activeMaster.rowData.some(
                (element: any) =>
                  element.majId === params.data.majId && element.id === true
              ) || params.data.id ? 0.2 : 1}`,
            }}
          >
            <img
              height={16}
              width={16}
              src="/assets/img/VectorFLOW/NMS/edit-draft.svg"
            />
          </button>
          {params.data.id ? (
            <button
              disabled={params.data.minId ? activeMaster.rowData.some((element:any)=> element.majId===params.data.majId && element.id===true) : false}
              onClick={onDeleteUndoClick}
              style={{ background: "transparent",
                opacity: 
              `${  params.data.minId ? activeMaster.rowData.some((element:any)=> element.majId===params.data.majId && element.id===true) ? 0.2 : 1:1}`
              }}
            >
              <img
                height={16}
                width={16}
                src="/assets/img/delete-undo.svg"
                alt="undo"
              />
            </button>
          ) : (
            <button
              onClick={onDeleteClick}
              disabled={
              activeMaster.rowData.some(
                (element: any) =>
                  element.majId === params.data.majId && element.id === true
              ) || params.data.id 
              }
              style={{ background: "transparent",
                opacity: 
              `${  activeMaster.rowData.some(
                (element: any) =>
                  element.majId === params.data.majId && element.id === true
              ) || params.data.id ? 0.2 : 1}`
               }}
            >
              <img
                height={16}
                width={16}
                src="/assets/img/VectorFLOW/NMS/delete-draft.svg"
              />
            </button>
          )}
        </>
      )}
    </div>
  );
};

export default PoogiEditDeleteCell;
