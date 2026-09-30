import React, { useRef } from "react";
import { LeftSectionWrapper } from "./style";
import LeftCommonCom from "./LeftCommonCom";
import VFTable from "../../../VectorFlow/Pages/MTO/Common/VFTable";
import { AgGridReact } from "ag-grid-react";
import FileUploadTile from "./FileUploadTile";
import { ExcelExportName } from "../../../VectorFlow/Pages/MTO/Common/Enum";


interface LeftCommonComProps {
  setNoData: React.Dispatch<React.SetStateAction<boolean>>;
  setErrorCount: any;
  setErrorData: any;
  setValidData: any;
  handleFileChange: any;
  handleUploadClick: any;
  file: any
}


function UploadLeftSection({setNoData,setErrorCount, setErrorData, setValidData, handleFileChange, handleUploadClick,file}: LeftCommonComProps) {

 

  const downloadGridRef = useRef<AgGridReact>(null);
 
  const onDownloadClick = () => {
    downloadGridRef &&  downloadGridRef.current && downloadGridRef.current.api.exportDataAsExcel(
      {fileName:ExcelExportName.UserData, sheetName: ExcelExportName.UserData}
    );
  }

  
  return (
    <LeftSectionWrapper>
      <LeftCommonCom
        step={1}
        img="/assets/img/download.svg"
        headerText="Download Template"
        subText="You can download attached sample templates"
        btnText="Download"
        btnImg="/assets/img/VectorFLOW/NMS/download.svg"
        btnStyles={{width:"12rem", height:"3rem" , fontSize:"1rem",boxShadow:"0px 6px 10px rgba(33, 33, 33, 0.5)"}}
        imgStyles={{width:"4.5rem"}}
        handleClick={onDownloadClick}
      />
      <FileUploadTile setNoData={setNoData} setErrorCount={setErrorCount}  setErrorData={setErrorData} setValidData={setValidData} handleUploadClick={handleUploadClick} handleFileChange={handleFileChange} file={file}/>
      
      <div style={{ display: "none" }}>
        <VFTable
          columnDefs={[
            { headerName: "Username", field: "name" },
            { headerName: "Email ID", field: "email" },
            { headerName: "Password", field: "phone" }
          ]}
          ref={downloadGridRef}
        />
      </div>
    </LeftSectionWrapper>
  );
}

export default UploadLeftSection;
