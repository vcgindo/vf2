

// const {addRow, handleCancel} = useViewModify('modify');
import _ from 'lodash';
import { useDispatch, useSelector } from 'react-redux';
import { notifyError } from '../../../../../helpers/notify';
import { UPDATE_COLDEFS, UPDATE_ROW_DATA } from '../../../../../redux/actions/MDM';
import { SET_BUFFER_MODIFY_DATA, SET_CCR_MODIFY_DATA, SET_POOGI_INITIAL_DATA, SET_POOGI_MODIFY_DATA } from '../../../../../redux/actions/MTO';
import type { RootState } from '../../../../../redux/store/store';
import { CALENDAR_VALIDATION_SCHEMA } from './MDMJoiValidations';
import { useLocation } from 'react-router';
import { validateBuffer, validateCCR } from './CommonUtils';


const AddRemoveCellRenderer = (params: any) => {
  const dispatch = useDispatch();
  const location = useLocation();
  const activeMaster = useSelector(
    (state: RootState) => state.mdm.activeMaster
  );
  const bufferInitialData = useSelector(
    (state: any) => state.mto.bufferInitialData
  );
  const bufferModifyData = useSelector(
    (state: any) => state.mto.bufferModifyData
  );
  const ccrModifyData = useSelector((state: any) => state.mto.ccrModifyData);
  const ccrInitialData = useSelector((state: any) => state.mto.ccrInitialData);
  const poogiModifyData = useSelector(
    (state: any) => state.mto.poogiModifyData
  );
  const poogiInitialData = useSelector(
    (state: any) => state.mto.poogiIntialData
  );

  // Function to add a new row
  const addNewRow = (rowData: any, id: any) => {
    const cloneRowData = _.cloneDeep(rowData);
    const newRowData: any = [];
    let newRow: any;
    cloneRowData.forEach((item: any) => {
      if (item.id === id) {
        const row = {
          ...item,
          editable: false,
        };
        newRowData.push(row);
        newRow = row;
      } else {
        newRowData.push(item);
      }
    });
    dispatch(UPDATE_ROW_DATA(newRowData));

    return newRow;
  };

  const addRow = () => {
    const allRows = [...activeMaster.rowData];
    allRows.shift();
    // Check if the entered Buffer type is unique

    if (activeMaster.id === 501) {
      const result = validateBuffer(params.data, activeMaster, bufferInitialData, bufferModifyData, params.bufferTypeData);
      if (result.error !== "") {
        notifyError(result.error);
      } else {
        const newColDefs: any = [];
        activeMaster.colDefs.forEach((ele: any) => {
          const newColDef = { ...ele };
          if (!params.data.ia) {
            delete newColDef.editable;
          }
          newColDefs.push(newColDef);
        });

        const rowToBeAdded = addNewRow(activeMaster.rowData, params.data.id);
        if (bufferModifyData && bufferModifyData.length)
          dispatch(SET_BUFFER_MODIFY_DATA([rowToBeAdded, ...bufferModifyData]));
        else dispatch(SET_BUFFER_MODIFY_DATA([rowToBeAdded]));

        dispatch(UPDATE_COLDEFS(newColDefs));
      }
    } else if (activeMaster.id === 502) {
      const result = validateCCR(params.data, activeMaster, ccrInitialData, ccrModifyData, params.CCRGroupMaterSetRef, params.plantMaster, params.deptMaster);
      if (result.error !== "") {
        notifyError(result.error);
      } else {
        const newColDefs: any = [];
        activeMaster.colDefs.forEach((ele: any) => {
          const newColDef = { ...ele };
          if (!params.data.ia) {
            delete newColDef.editable;
          }
          newColDefs.push(newColDef);
        });

        const rowToBeAdded = addNewRow(activeMaster.rowData, params.data.id);
  
        if (ccrModifyData && ccrModifyData.length)
          dispatch(SET_CCR_MODIFY_DATA([rowToBeAdded, ...ccrModifyData]));
        else dispatch(SET_CCR_MODIFY_DATA([rowToBeAdded]));
        // dispatch(SET_EDIT_STATUS("Edit online"))
        dispatch(UPDATE_COLDEFS(newColDefs));
      }
    } else if (activeMaster.id === 503) {
      const hasActionsCol = activeMaster.colDefs.some((col:any)=> col.field === 'actions' || col.field === 'pactions');

      // this is the case for adding the minor reason
      if (params.data.mindsc !== undefined) { 
        // check if minreason already exists
        if(poogiInitialData && poogiInitialData.length){
          const existingData = poogiInitialData.find(
            (item: any) => item.majId === params.data.majId
          );

          if (existingData && existingData.minData.some((ele: any) => ele.mindsc === params.data.mindsc)) {
            notifyError("Minor reason already exists for the selected major reason");
            return;
          }
        }
        ///////////////////////////////////
        if (params.data.mindsc === "") {
          notifyError("Add a minor reason for the selected major reason");
          return;
        }

        const newColDefs: any = [];
        activeMaster.colDefs.forEach((ele: any) => {
          const newColDef = { ...ele };
          delete newColDef.editable;
          newColDefs.push(newColDef);
        });
        if(hasActionsCol){

          dispatch(
            UPDATE_COLDEFS(
              newColDefs.filter(
                (item: any) =>
                  item.field !== "actions" && item.field !== "pactions"
              )
            )
          );
        }
        if (poogiModifyData && poogiModifyData.length) { 
          // Find if a node with the matching majId exists
          const existingIndex = poogiModifyData.findIndex(
            (item: any) => item.majId === params.data.majId
          );

          if (existingIndex !== -1) {
            // Replace the existing node with the new one
            const newPoogiModifyData = [...poogiModifyData];
            newPoogiModifyData[existingIndex] = activeMaster.rowData.find(
              (row) => row.majId === params.data.majId
            );
            dispatch(SET_POOGI_MODIFY_DATA([...newPoogiModifyData]));
          } else {
            // Add the new node if it doesn't exist
            const newNode = activeMaster.rowData.find(
              (row) => row.majId === params.data.majId
            );
            if (newNode) {
              dispatch(SET_POOGI_MODIFY_DATA([newNode, ...poogiModifyData]));
            }
          }
        } else {
          // Handle the case where poogiModifyData is empty
          const newNode = activeMaster.rowData.find(
            (row) => row.majId === params.data.majId
          );
          if (newNode) {
            dispatch(SET_POOGI_MODIFY_DATA([newNode]));
          }
        }

        const newInitialData = _.cloneDeep(poogiInitialData);
        newInitialData.forEach((ele: any) => {
          if (ele.majId === params.data.majId) {
            ele.minData = [params.data, ...ele.minData];
          }
        });
        dispatch(SET_POOGI_INITIAL_DATA(newInitialData));
      } else {
        if (params.data.majdsc === "") {
          notifyError("Major reason cannot be empty");
          return;
        } else if (params.data.minData[0].mindsc === "") {
          notifyError("Add atleast one minor reason for the major reason");
          return;
        } else if (params.data.plnm === "") {
          notifyError("Please select a valid plant from the dropdown");
          return;
        }
        // here is the case for adding the major reason
        // check if major reason already exists
        if (poogiInitialData && poogiInitialData.length) {
          const existingData = poogiInitialData.find(
            (item: any) => (item.majdsc === params.data.majdsc && item.plnm === params.data.plnm)
          );

          if (existingData) {
            notifyError("Major reason already exists for the selected plant");
            return;
          }
        }

        ///////////////////////////////
        const newColDefs: any = [];
        activeMaster.colDefs.forEach((ele: any) => {
          const newColDef = { ...ele };
          delete newColDef.editable;
          newColDefs.push(newColDef);
        });
        if (poogiInitialData && poogiInitialData.length)
          dispatch(SET_POOGI_INITIAL_DATA([params.data, ...poogiInitialData]));
        else dispatch(SET_POOGI_INITIAL_DATA([activeMaster.rowData[0]]));
        if (poogiModifyData && poogiModifyData.length)
          dispatch(SET_POOGI_MODIFY_DATA([params.data, ...poogiModifyData]));
        else dispatch(SET_POOGI_MODIFY_DATA([activeMaster.rowData[0]]));

        if(hasActionsCol){
          dispatch(
            UPDATE_COLDEFS(
              newColDefs.filter(
                (item: any) =>
                  item.field !== "actions" && item.field !== "pactions"
              )
            )
          );
        }
      }
    } else if (activeMaster.id === 504) {
      const { error } = CALENDAR_VALIDATION_SCHEMA.validate(params.data, {
        abortEarly: false,
      });

      if (error) {
        const fieldOrders = activeMaster.colDefs
          .filter((item: any) => item.headerName !== "Actions")
          .map((item: any) => item.field);

        const orderedErrors = fieldOrders.flatMap((key: any) =>
          error.details.filter((err: any) => err.path[0] === key)
        );

        return notifyError(orderedErrors[0]?.message);
      }
    }
  };

  const onRemoveRow = () => {
    if (params.data.mindsc !== undefined) {
      const newData = [...activeMaster.rowData];

      const finData = newData.map((item) => {
        if (item.majId === params.data.majId) {
          return {
            ...item,
            minData: [...item.minData.slice(1), item.minData[0]], // Shift array by 1
          };
        }
        return item; // Return other items unchanged
      });

      dispatch(UPDATE_ROW_DATA([...finData]));
    } else {
      const newData = [...activeMaster.rowData];
      newData.shift();
      dispatch(UPDATE_ROW_DATA([...newData]));
    }
    const newColDefs: any = [];
    activeMaster.colDefs.forEach((ele: any) => {
      const newColDef = { ...ele };
      delete newColDef.editable;
      newColDefs.push(newColDef);
    });

    dispatch(
      UPDATE_COLDEFS(
        newColDefs.filter((item: any) => item.field !== "pactions")
      )
    );
  };

  const onDeleteHandler = (id: any, rowData: any) => {
    if (activeMaster.id === 501) {
      onDelete(id, rowData, bufferModifyData, SET_BUFFER_MODIFY_DATA);
    } else {
      onDelete(id, rowData, ccrModifyData, SET_CCR_MODIFY_DATA);
    }
  };

  const onDeleteUndoHandler = (id: any, rowData: any) => {
    if (activeMaster.id === 501) {
      onDeleteUndo(id, rowData, bufferModifyData, SET_BUFFER_MODIFY_DATA);
    } else {
      onDeleteUndo(id, rowData, ccrModifyData, SET_CCR_MODIFY_DATA);
    }
  };

  const onEditHandler = (id: any, rowData: any) => {
    if (activeMaster.id === 501) {
      onEdit(id, rowData, bufferModifyData, SET_BUFFER_MODIFY_DATA);
    } else {
      onEdit(id, rowData, ccrModifyData, SET_CCR_MODIFY_DATA);
    }
  };

  const onEdit = (
    id: any,
    rowData: any,
    modifiedData: any,
    SET_MODIFY_DATA: any
  ) => {
    const newRowData = rowData.map((item: any) => {
      if (item.id === id) {
        return { ...item, editable: true };
      }
      return item;
    });
    dispatch(UPDATE_ROW_DATA(newRowData));
    const newModifiedData = modifiedData.filter((item: any) => item.id !== id);
    dispatch(SET_MODIFY_DATA(newModifiedData));
    params.addEditableToLastColumn();
  };

  const onDelete = (
    id: any,
    rowData: any,
    modifiedData: any,
    SET_MODIFY_DATA: any
  ) => {
    const newRowData = rowData.map((item: any) => {
      if (item.id === id) {
        return { ...item, isdel: true };
      }
      return item;
    });
    // Mark the item as deleted in the modified data
    const newModifiedData = modifiedData.map((item: any) => {
      if (item.id === id) {
        return { ...item, isdel: true };
      } else {
        return item;
      }
    });
    dispatch(UPDATE_ROW_DATA(newRowData));
    dispatch(SET_MODIFY_DATA(newModifiedData));
  };

  const onDeleteUndo = (
    id: any,
    rowData: any,
    modifiedData: any,
    SET_MODIFY_DATA: any
  ) => {
    const newRowData = rowData.map((item: any) => {
      if (item.id === id) {
        return { ...item, isdel: false };
      }
      return item;
    });
    // Mark the item as not deleted in the modified data
    const newModifiedData = modifiedData.map((item: any) => {
      if (item.id === id) {
        return { ...item, isdel: false };
      } else {
        return item;
      }
    });
    dispatch(UPDATE_ROW_DATA(newRowData));
    dispatch(SET_MODIFY_DATA(newModifiedData));
  };

  if (params.data.ia && params.data.editable && activeMaster.id !== 503 && activeMaster.id !== 504) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          justifyContent: "space-evenly",
          marginTop: "4px",
          gap: "8px",
        }}
      >
        <div
          //   onClick={() => dispatch(UPDATE_ROW_DATA(activeMaster.rowData.filter((item: any) => item.id !== params.data.id))) }
          onClick={() => addRow()}
          style={{ cursor: "pointer" }}
        >
          <img
            height={17}
            width={17}
            src="/assets/img/MTOapprovalBuffer.svg"
            alt="ApproveMaster"
          />
        </div>

        <div onClick={() => onRemoveRow()} style={{ cursor: "pointer" }}>
          <img
            height={17}
            width={17}
            src="/assets/img/MTOcancelBuffer.svg"
            alt="CancelMaster"
          />
        </div>
      </div>
    );
  } else if (params.data.ia && !params.data.editable && activeMaster.id !== 503 && activeMaster.id !== 504) {
    return (
      <div
        style={{
          display: "flex",
          margin: "4px auto",
          width: "80px",
          justifyContent: "center",
          opacity: params.data.isdel ? 0.6 : 1,
        }}
      >
        <button
          disabled={params.data.isdel ? true : false}
          style={{ background: "transparent" , cursor : params.data.isdel ? 'not-allowed' : 'pointer'}}
          onClick={() => onEditHandler(params.data.id, activeMaster.rowData)}
        >
          <img
            height={14}
            width={14}
            src="/assets/img/VectorFLOW/NMS/edit-draft.svg"
          />
        </button>
        {params.data.isdel ? (
          <button
            style={{ background: "transparent", color: "green" }}
            onClick={() =>
              onDeleteUndoHandler(params.data.id, activeMaster.rowData)
            }
          >
            <img
              height={18}
              width={18}
              src="/assets/img/delete-undo.svg"
              alt="undo"
            />
          </button>
        ) : (
          <button
            style={{ background: "transparent", color: "red" }}
            onClick={() =>
              onDeleteHandler(params.data.id, activeMaster.rowData)
            }
          >
            <img
              height={14}
              width={14}
              src="/assets/img/VectorFLOW/NMS/delete-draft.svg"
            />
          </button>
        )}
      </div>
    );
  }if(activeMaster.id === 503 && params?.node?.rowIndex === 0 && location?.state?.backUrl.split('/').pop() !== 'saved-drafts'){
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "row",
          justifyContent: "space-evenly",
          marginTop: "4px",
          gap: "8px",
        }}
      >
        <div
          //   onClick={() => dispatch(UPDATE_ROW_DATA(activeMaster.rowData.filter((item: any) => item.id !== params.data.id))) }
          onClick={() => addRow()}
          style={{ cursor: "pointer" }}
        >
          <img
            height={17}
            width={17}
            src="/assets/img/MTOapprovalBuffer.svg"
            alt="ApproveMaster"
          />
        </div>

        <div onClick={() => onRemoveRow()} style={{ cursor: "pointer" }}>
          <img
            height={17}
            width={17}
            src="/assets/img/MTOcancelBuffer.svg"
            alt="CancelMaster"
          />
        </div>
      </div>
    );
  }
  return null; // No buttons for other rows
}

export default AddRemoveCellRenderer