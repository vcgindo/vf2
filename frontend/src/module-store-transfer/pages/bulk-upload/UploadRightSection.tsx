import { HeaderText, RightSectionWrapper } from "./style";
import ProgressBox from "./ProgressBox";
import RightSectionFilePanel from "./RightSectionFilePanel";
import VFTable from "../../../VectorFlow/Pages/MTO/Common/VFTable";
import { GridRef } from "../../../VectorFlow/types/MDM";
import { useRef } from "react";
import { ExcelExportName } from "../../../VectorFlow/Pages/MTO/Common/Enum";

interface UploadRightSectionProps {
  errorCount?: number;
  errorData?: any[];
  validData?: any[];
  setIsAssignPageOpen: (e: boolean) => void;
  progress: number;
}

function UploadRightSection({
  errorData,
  validData,
  setIsAssignPageOpen,
  progress
}: UploadRightSectionProps) {
  const errorGridRef = useRef<GridRef>(null);
  const exportingRef = useRef(false);

  const onErrorFileDownload = () => {
    
    if (errorGridRef && errorGridRef.current) {

      if (exportingRef.current) return;
      exportingRef.current = true;

      errorGridRef.current.api.exportDataAsExcel({
        fileName: ExcelExportName.ErrorData,
        sheetName: ExcelExportName.ErrorData,

        processHeaderCallback: (params) => {
          return String(params.column.getColDef().headerName ?? '');
        },

        processCellCallback: (params) => {
          const cellValue = params.value;

          if (cellValue === null || cellValue === undefined) return '';

          if (Array.isArray(cellValue)) {
            return cellValue.join(' ');
          }
          if (typeof cellValue === 'object') {
            return JSON.stringify(cellValue);
          }
      
          return String(cellValue);

        },
      });

      setTimeout(() => {
        exportingRef.current = false;
      }, 0);
    }
  };

  const onValidDataClick = () => {
    if (validData) {
      setIsAssignPageOpen(true);
    }
  };
  return (
    <RightSectionWrapper>
      <ProgressBox label={progress===100?"Uploaded Succesfully":"Uploading file..."}  progress={progress}/>
      {(progress===100) &&
        <HeaderText>
        {(errorData?.length && errorData.length>0) ? `${errorData.length} rows contain errors` : "No errors found"}
      </HeaderText>
      }
      <div style={{ display: "flex", flexDirection: "column", gap: "3rem" }}>
        {
          !!(errorData?.length && (errorData?.length>0) && (progress===100)) &&
          <RightSectionFilePanel
          onClick={onErrorFileDownload}
          text={"Error File"}
          img="/assets/img/excel.svg"
          iconStyles={{ width: "1.6rem", padding: "0px" }}
          imgStyles={{ width: "2.5rem", height: "2.5rem"}}
          disabled = {!(progress==100) && !errorData?.length}
          btnIcon="/assets/img/VectorFLOW/NMS/download.svg"
          />
        }
        {
          !!(validData && validData.length && (validData?.length>0) && (progress===100)) &&
          <RightSectionFilePanel
          onClick={onValidDataClick}
          text={"Assign Roles & Permission"}
          img="/assets/img/excel.svg"
          iconStyles={{ width: "1.6rem", padding: "0px" }}
          disabled={!(progress===100) && !validData?.length}
          imgStyles={{width: "2.5rem", height: "2.5rem" }}
          btnIcon="/assets/img/Open new link icon.svg"
          />
        }
      </div>
      <div style={{ display: "none" }}>
        <VFTable
          ref={errorGridRef}
          columnDefs={[
            {
              headerName: "Error",
              field: "error",
              valueFormatter: (params: any) => {
                return (params?.value || []).map((e: any) => `${e}`).join('\n');
              }
            },
            { headerName: "Username", field: "username" },
            { headerName: "Email ID", field: "email" },
            { headerName: "Password", field: "pwd" },
          ]}
          rowData={errorData}
        />
      </div>
    </RightSectionWrapper>
  );
}

export default UploadRightSection;
