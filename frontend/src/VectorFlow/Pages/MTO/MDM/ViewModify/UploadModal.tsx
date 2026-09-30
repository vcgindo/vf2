import React, { Dispatch, SetStateAction,useRef } from 'react'
import VFModalCard from "../../../../../components/VectorFLOW/commons/VFModalCard"
import { UploadModalWrapper, UploadModalSection, UploadBorderContainer, UploadModalContent, TextContent, InputWrapper, UploadModalInput, UploadModalText, UploadFileText, UploadModalRadioWrapper } from "./styles"
import { SCManualUploadBtn, SCManualUploadButton } from "../../../../../module-store-transfer/pages/manual-upload/styles"
import { useUserData } from "../../../../../context"
import * as ManualStyle from "../../../../../module-store-transfer/pages/manual-upload/styles"; 
import {notifyError} from '../../../../../helpers/notify';
interface UploadModalProps{
   openModal:boolean
   header?:string
   onCloseModal:()=>void
   onDownload:()=>void
   onUpload:()=>void
   inputText:string,
   setInputText:Dispatch<SetStateAction<string>>,
   file:File | undefined,
   setFile:Dispatch<SetStateAction<File | undefined>>
   uploadButtonStatus:boolean
   radioButtons?:Array<{label:string,value:any}>
   handleRadioButton?:(params:number)=>void
   downloadFileText?:string
}


const UploadModal = (props:UploadModalProps)=>{

   const{
      openModal,
      header,
      onCloseModal,
      onDownload,
      onUpload,
      inputText,
      setInputText,
      file,
      setFile,
      radioButtons,
      uploadButtonStatus,
      handleRadioButton,
      downloadFileText
   }   = props 

   const {user} = useUserData()
   const inputRef = useRef<HTMLInputElement>(null);

   const handleClick = (): void => {
      if (inputRef.current != null) {
        inputRef.current.click();
      }
    };
  
    const handleFileChange = (e: any) => {
      if (e.target.files.length < 1) {
        return;
      }
  
      const file = e.target.files[0];
      switch (file.type) {
        case "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
          setFile(file);
          break;
        default:
          notifyError("Only xlsx files are accepted");
      }
    };

   return(
   <VFModalCard headerText={header} headerIcon={"/assets/img/VectorFLOW/NMS/settings.svg"} openModal={openModal} closeModal={onCloseModal} closeIcon={"/assets/img/VectorFLOW/NMS/close-dark.svg"} >
      <UploadModalWrapper>
         <UploadModalSection>
            <UploadModalText>
               <p style={{ color: "#292C2E", marginBottom: '11px'}}><b>Step 1</b></p>
            </UploadModalText>
            <UploadBorderContainer>
               <UploadModalContent>
                  <TextContent>
                     <img src="/assets/img/manual/excel.png"  height={29} width={29} style={{marginBottom:'10px'}}/>
                     <p>{downloadFileText ? downloadFileText : 'Download selected data'} </p>
                  </TextContent>
                  {
                     radioButtons && radioButtons.length>0 && handleRadioButton ? (
                        <UploadModalRadioWrapper>
                           {radioButtons.map((r,index)=>{
                              return(
                                 <React.Fragment>
                                     <input type={'radio'} placeholder={r.label} key={index} name='file name'  onClick={()=>handleRadioButton(r.value)} style={{marginLeft:15}} defaultChecked={index==0}/>
                                     <label htmlFor={r.label}>{r.label}</label>
                                 </React.Fragment>
                              )
                           })}
                        </UploadModalRadioWrapper>
                     )
                     :
                     <UploadFileText>
                        File Name
                     </UploadFileText>
                  }
                  
                  
                  <InputWrapper>
                     <UploadModalInput value={inputText} onChange={(e:any)=>setInputText(e.target.value)} data-testid="view-modify-text"/>
                     <SCManualUploadBtn themeUi={user.user.theme_ui} 
                        onClick={onDownload}
                        style={{
                           height:'30px',
                           width:'91px',
                           borderRadius:'0',
                           display:'flex',
                           alignItems:'center',
                           justifyContent:'center',
                           borderBottomRightRadius:'6px',
                           fontStyle:'normal',
                           fontVariant:'normal',
                           fontWeight: '400',
                           fontSize: '12px',
                           lineHeight: '14px',
                           fontFamily:'Roboto'
                        }}>
                           
                        <img src="/assets/img/VectorFLOW/NMS/download.svg" style={{margin:'5px'}}></img> 
                        Download
                     </SCManualUploadBtn>
                  </InputWrapper>
               </UploadModalContent>
            </UploadBorderContainer>
         </UploadModalSection>
         <UploadModalSection style={{margin:0}}>
            <UploadModalText>
               <p style={{ color: "#292C2E", marginBottom: '11px'}}><b>Step 2</b></p>
            </UploadModalText>
            <UploadBorderContainer>
            <UploadModalContent>
               <TextContent>
               <img src="/assets/img/manual/excel.png"  style={{height:'29px', width:'29px',marginBottom:'10px'}}/>
                  <p>Select your file here</p>
               </TextContent>     
               <InputWrapper>
               <SCManualUploadButton style={{height:'30px', width:'105px'}} onClick={handleClick} data-testid="view-modify-manual-upload-btn">
                  <img src="/assets/img/manual/plus.png" width={19} height={19} />
                  <ManualStyle.SCManualUploadInput
                     type="file"
                     accept=".xlsx"
                     onChange={handleFileChange}
                     ref={inputRef}
                     value=""
                     style={{ display: "none" }}
                     data-testid="view-modify-file-upload"
                  />
               </SCManualUploadButton>
                  <UploadModalInput placeholder="Click here to upload new file" value={file?.name}/>
                     <SCManualUploadBtn themeUi={user.user.theme_ui} 
                        onClick={onUpload}
                        disabled={uploadButtonStatus}
                        style={{
                           height:'30px',
                           borderRadius:'0',
                           display:'flex',
                           alignItems:'center',
                           justifyContent:'center',
                           width:'82px',
                           borderBottomRightRadius:'6px',
                           fontStyle:'normal',
                           fontVariant:'normal',
                           fontWeight: '400',
                           fontSize: '12px',
                           lineHeight: '14px',
                           fontFamily:'Roboto'
                        }}>
                        <img src="/assets/img/VectorFLOW/NMS/upload.svg" style={{margin:'6px'}}></img> 
                        Upload
                        </SCManualUploadBtn>
                  </InputWrapper>
               </UploadModalContent>
            </UploadBorderContainer>
         </UploadModalSection>
      </UploadModalWrapper>
   </VFModalCard>
   )
}

export default UploadModal