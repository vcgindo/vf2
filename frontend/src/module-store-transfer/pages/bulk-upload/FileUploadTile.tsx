import React, { useRef } from "react";
import * as ManualStyle from "../../../module-store-transfer/pages/manual-upload/styles";
import {
  HeaderSection,
  HeaderText,
  LeftCommonComUploadWrapper,
  LeftCommonComWrapper,
  LeftStep,
  SubText,
} from "./style";
import { ButtonFloat } from "../../../components";

const FileUploadTile = ({ handleFileChange, handleUploadClick, file}: any) => {


  const inputRef = useRef<HTMLInputElement>(null);

  const handleClick = (): void => {
    if (inputRef.current != null) {
      inputRef.current.click();
    }
  };


  return (
    
      <LeftCommonComWrapper>
        <LeftStep>Step 2</LeftStep>
        <LeftCommonComUploadWrapper >
          <div
            style={{
              display: "flex",
              gap: "1rem",
              alignItems: "center",
              justifyContent: "center",
              cursor: 'pointer'
            }}
            onClick={handleClick}
          >
            <img src={"/assets/img/download.svg"} alt="" style={{width:"4.5rem"}} />
            <HeaderSection style={{cursor: 'pointer'}} >
              <HeaderText>{"Upload File"}<p style={{fontSize: '0.9rem', fontWeight: 'normal'}}>{" (upto 100 users only)"}</p></HeaderText>
              {file?.name &&
              <SubText>{`Selected file :  ${file.name}`}</SubText>

              }
              <SubText style={{fontWeight: 'bold'}}>{(!file?.name)?"Click here to choose a file to upload":"Click here to change file"}</SubText>
            </HeaderSection>
          </div>
          {/* <SCManualUploadButton
            style={{ height: "30px", width: "105px" }}
            onClick={handleClick}
            data-testid="view-modify-manual-upload-btn"
          > */}
          <div style={{opacity: file?"1":"0.5", cursor: file?"pointer": "default"}}>
            <ButtonFloat
              onClick={(e: any) => {
                if(!file) return;
                handleUploadClick(e);
              }}
              text={"Upload"}
              icon={"/assets/img/VectorFLOW/NMS/upload.svg"}
              styles={{width:"12rem", height:"3rem" , fontSize:"1rem",boxShadow:"0px 6px 10px rgba(33, 33, 33, 0.5)"}}
              ></ButtonFloat>
          </div>
            <ManualStyle.SCManualUploadInput
              type="file"
              accept=".xlsx"
              onChange={handleFileChange}
              ref={inputRef}
              value=""
              style={{ display: "none" }}
              data-testid="view-modify-file-upload"
            />
          {/* </SCManualUploadButton> */}
        </LeftCommonComUploadWrapper>
      </LeftCommonComWrapper>

  );
};

export default FileUploadTile;
