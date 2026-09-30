import { BUFFER_VALIDATION_SCHEMA, CCR_VALIDATION_SCHEMA } from "./MDMJoiValidations";

export const validateCCR = (rowData: any, activeMaster: any, ccrInitialData: any, ccrModifyData: any, CCRGroupMaterSetRef: any, plantMaster: any, deptMaster: any) => {
  let fieldError = { error: "", warning: "" };

  const { error } = CCR_VALIDATION_SCHEMA.validate(rowData, {
    abortEarly: false,
  });

  if (error) {
    const fieldOrders = activeMaster.colDefs
      .filter((item: any) => item.field !== "actions")
      .map((item: any) => item.field);

    const orderedErrors = fieldOrders.flatMap((key: any) =>
      error.details.filter((err: any) => err.path[0] === key)
    );

    fieldError = {
      error: orderedErrors.length > 0 ? orderedErrors[0].message : "",
      warning: ""
    }

  } else {

    let isValideCCRGroup = true;

    const isCcrCodeDuplicate = ccrInitialData?.some((master: any) => master.ccd === rowData.ccd);
    if (isCcrCodeDuplicate) {
      fieldError = {
        error: "CCR code already exists in the master data!",
        warning: "",
      };
    }

    const isCcrCodeDuplicateInCurr = ccrModifyData?.some((ccr: any) => ccr.ccd === rowData.ccd);
    if (isCcrCodeDuplicateInCurr) {
      fieldError = { error: "CCR code must be unique!", warning: "" };
    }
  
    if (CCRGroupMaterSetRef.current.size &&
      !CCRGroupMaterSetRef.current.has(String(rowData.cgid))) {
      isValideCCRGroup = false;
    }
    if (!isValideCCRGroup) {
      fieldError = {
        error: "Please select a valid CCR Group from the dropdown",
        warning: ""
      };
    }
    if (
      plantMaster.length &&
      !plantMaster?.some(
        (plant: any) => plant.plant_name === rowData.pl || plant.plant_id === rowData.pl
      )
    ) {
      fieldError = {
        error: "Please select a valid plant from the dropdown",
        warning: "",
      };
    } else if (
      deptMaster.length &&
      !deptMaster?.some(
        (dept: any) => dept.dept_name === rowData.dp || dept.dept_id === rowData.dp
      )
    ) {
      fieldError = {
        error: "Please select a valid department from the dropdown",
        warning: "",
      };
    }

  }
    
  return fieldError;
};

export const validateBuffer = (rowData: any, activeMaster: any, bufferInitialData: any, bufferModifyData: any, bufferTypeData: any, allRows?:any) => {
  let fieldError = { error: "", warning: "" };

  const { error } = BUFFER_VALIDATION_SCHEMA.validate(rowData, {
    abortEarly: false,
  });
  
  if (error) {
    const fieldOrders = activeMaster.colDefs
      .filter((item: any) => item.field !== "actions")
      .map((item: any) => item.field);
  
    const orderedErrors = fieldOrders.flatMap((key: any) =>
      error.details.filter((err) => err.path[0] === key)
    );
  
    fieldError = {
      error: orderedErrors.length > 0 ? orderedErrors[0].message : "",
      warning: ""
    }
  } else {

    const isBufferCodeExist = bufferInitialData?.some(
      (master: any) => master.bcd === rowData.bcd
    );
    const isBufferCodeDuplicate = bufferModifyData?.some(
      (master: any) => master.bcd === rowData.bcd
    );

    const duplicateBuffCodeInAllRows = allRows?.filter((allrow: any) => allrow.bcd === rowData.bcd);
    
    if (isBufferCodeExist) {
      fieldError = {
        error: "Buffer code already exists in master!",
        warning: "",
      };
    }
    if (isBufferCodeDuplicate || duplicateBuffCodeInAllRows?.length > 1) {
      fieldError = {
        error: "Buffer code must be unique!",
        warning: "",
      };
    }

    const isBufferTypeValid = bufferTypeData?.some(
      (btData: any) => btData.nm === rowData.bt || btData.id === rowData.bt
    );
    if (!isBufferTypeValid) {
      fieldError = {
        error: "Choose a valid buffer type from the drop down",
        warning: "",
      };
    } 

    const isBufferTypeAndSizeExist = bufferInitialData?.some(
      (master: any) => master.bt === rowData.bt && master.bsz === rowData.bsz
    );
    if (isBufferTypeAndSizeExist) {
      fieldError = {
        error: "Buffer size for the buffer type already exists in master",
        warning: "",
      };
    }

    const isBufferTypeAndSizeDuplicate = bufferModifyData?.some(
      (modifiedData: any) => modifiedData.bt === rowData.bt && modifiedData.bsz === rowData.bsz
    );

    const isBufferSizeExists = allRows?.filter((allrow: any) => {
      return allrow.bt === rowData.bt && allrow.bsz === rowData.bsz
    });

    if (isBufferTypeAndSizeDuplicate || isBufferSizeExists?.length > 1) {
      fieldError = {
        error: "Buffer size for the buffer type already exists",
        warning: "",
      };
    }
    
  }
  return fieldError;
}

export const convertDateFormat = (inputDate: string)=>{

  // Extract parts of the string
  const [date, ltime] = inputDate.split("T");
  const time = ltime.split(".")[0]; // Remove milliseconds
  const [year, month, day] = date.split("-");
  const [hours, minutes, seconds] = time.split(":");

  // Convert to 12-hour format
  const isPM = parseInt(hours) >= 12;
  const newHours = (parseInt(hours) % 12 || 12).toString().padStart(2, "0");
  const period = isPM ? "PM" : "AM";

  const newMonth = month;
  // Format the output
  const formattedDate = `${year}/${newMonth}/${day}  ${newHours}:${minutes}:${seconds} ${period}`;
  return formattedDate;
}
  
