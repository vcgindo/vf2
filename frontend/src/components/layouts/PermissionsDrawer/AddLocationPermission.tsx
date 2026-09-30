import React, { useState, useEffect, useMemo } from "react";
import {
  InputWrapper,
  URLsForm,
  Label,
  ButtonsWrapper,
} from "../UserURLsDrawer/styles";
import { Input, PrimaryButton, Skeleton } from "../../commons/styled";
import { useUserData } from "../../../context";
import { notifyError, notifySuccess } from "../../../helpers/notify";
import { useAddLocationPermissions } from "../../../VectorFlow/Services/MTA/MDM";
import  UploadModal  from "../../../VectorFlow/Pages/MTA/MDM/ViewModify/UploadModal";
import useView from "./useView";
import { getErrorLocationColumns, getLocationColumns } from './View';
import { useSelector } from "react-redux";
import { RootState } from '../../../redux/store/store'
import ErrorPermissions from "./ErrorPermissions";

interface FormDataType {
  locationHierarchy1: string;
  locationHierarchy2: string;
  locationHierarchy3: string;
  
}

const AddLocationPermission = (props: { cb: () => void }) => {
  const { cb } = props;

  const { user } = useUserData();

  const themeUi = user.user.theme_ui;

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const EnvConfig = useSelector((state: RootState) => state.mta.EnvConfig);
  const locationColumns = getLocationColumns(EnvConfig);

  const [formData, setFormData] = useState<FormDataType>({
    locationHierarchy1: "",
    locationHierarchy2: "",
    locationHierarchy3: "",
  });

   const {
    downloadFileName,
    setDownloadFileName,
    file,
    setFile,
    isUploadModalOpen,
    toggleUploadModal,
    onUpload,
    setUploadCallback,
    exportToExcel,
    RECORD_UPLOAD_LIMIT,
    showErrorRows,
    errorRowData
  } = useView(locationColumns);

  const {mutateAsync : addLocationPermission} = useAddLocationPermissions();
  
  const errorLocationcolumn = getErrorLocationColumns(EnvConfig)
  const headerNameMap: Record<string, string> = {};
  locationColumns.forEach(col => {
        headerNameMap[col.colId] = col.headerName;
    });
  const headersList = locationColumns?.filter(col => col.colId !== 'id').map(col => col.headerName);
  useEffect(() => {
    setIsLoading(false);
  }, []);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;

    setFormData({ ...formData, [name]: value });
  };

  const handleSubmit = async (e: any) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const data = {permissionType : "Location" ,Headers: headersList, data :[ {...formData } ]} as any;
      const response = await addLocationPermission(data);
      const responseData = response?.data?.data;
      
      if (responseData?.errorCount === 1) { 
        notifyError(responseData?.errors[0]?.rowData?.error);
      } else {
        notifySuccess(`${responseData?.inserted} record inserted successfully`);
      }
      cb();
    
    } catch (error) {
      console.error(error);
      notifyError("Server Went Unresponsive");
    }
  };

  const handleUpload = async () => {  
   await onUpload(RECORD_UPLOAD_LIMIT);
    setUploadCallback(cb);
  }
  
  const isFormInvalid = useMemo((): boolean => {
    const { locationHierarchy1, locationHierarchy2, locationHierarchy3 } = formData;

    const filledValues = [locationHierarchy1, locationHierarchy2, locationHierarchy3].filter(v => v !== '');
    const lowerCaseFilledValues = filledValues.map(v => v.toLowerCase());

    if (new Set(lowerCaseFilledValues).size < filledValues.length)   return true;
    if(!locationHierarchy1 && !locationHierarchy2 && !locationHierarchy3 )  return true
    if (!locationHierarchy1 && locationHierarchy2) return true;
    if (!locationHierarchy2 && locationHierarchy3) return true;
    return false;
  }, [formData]);

  if (isLoading) {
    return (
      <URLsForm>
        <div style={{ display: "flex", height: 30, gap: 20 }}>
          <Skeleton style={{ height: "100%", flex: 1, width: "100%" }} />
          <Skeleton style={{ height: "100%", flex: 1, width: "100%" }} />
        </div>
        <Skeleton style={{ height: 30, width: "100%", marginTop: 20 }} />
        <Skeleton style={{ height: 30, width: "100%", marginTop: 20 }} />

        <Skeleton style={{ height: 80, width: "100%", marginTop: 20 }} />
        <ButtonsWrapper
          style={{
            alignItems: "flex-end",
            justifyContent: "flex-end",
            flex: 10,
          }}
        >
          <Skeleton style={{ height: 30, width: "100px" }} />
        </ButtonsWrapper>
      </URLsForm>

    );
  }
  if(showErrorRows ) return <ErrorPermissions columnDefs={errorLocationcolumn} rowData={errorRowData}/>
  
  return (
    <>
       <URLsForm onSubmit={handleSubmit}>
      <div style={{ display: "flex" }}>
       
        <InputWrapper >
          <Label htmlFor="locationHierarchy1">{locationColumns[1]?.headerName}</Label>
          <Input
            type={"text"}
            required
            name="locationHierarchy1"
            placeholder={`Any ${locationColumns[1]?.headerName}`}
            themeUi={themeUi}
            onChange={handleChange}
            maxLength={190}
          />
        </InputWrapper>

        <InputWrapper style={{ marginLeft: "10px" }}>
          <Label htmlFor="locationHierarchy2">{locationColumns[2]?.headerName}</Label>
          <Input
            type={"text"}
            name="locationHierarchy2"
            placeholder={`Any ${locationColumns[2]?.headerName}`}
            themeUi={themeUi}
            onChange={handleChange}
            maxLength={190}
          />
        </InputWrapper>
      </div>
      <div style={{ display: "flex" }}>
       
        <InputWrapper style={{ marginLeft: "10px" }}>
          <Label htmlFor="locationHierarchy3">{locationColumns[3]?.headerName}</Label>
          <Input
            type={"text"}
            name="locationHierarchy3"
            placeholder={`Any ${locationColumns[3]?.headerName}`}
            themeUi={themeUi}
            onChange={handleChange}
            maxLength={190}
          />
        </InputWrapper>
      </div>
      
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "flex-end",
          flex: 10,
          gap: 20
        }}
      >
        <PrimaryButton
          type="button" 
          themeUi={themeUi}
          onClick={() => toggleUploadModal(true)}
        >
          Bulk Upload
        </PrimaryButton>
        <PrimaryButton disabled={isFormInvalid || isSubmitting} themeUi={themeUi}>
          Add Permission
        </PrimaryButton>
      </div>
    </URLsForm>
    {isUploadModalOpen && (
      <UploadModal 
        header={"Upload Location Permissions"}
        openModal={isUploadModalOpen} 
        onCloseModal={()=>{setFile(undefined);toggleUploadModal(false)}} 
        onDownload={()=>exportToExcel(true)} 
        onUpload={async ()=>{
              await handleUpload()
            }}
        inputText={downloadFileName}
        setInputText={setDownloadFileName}
        file={file}
        setFile={setFile}
        uploadButtonStatus={false}
      />
    )}
    </>
  );
};

export default AddLocationPermission;
