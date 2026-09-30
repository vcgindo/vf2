import React, { useEffect, useState } from "react";
import FileUploadTile from "./components/FileUploadTile";
import styled from "styled-components";
import { useUserData } from "../../../../../context";
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton";
import {
  useGetFileConfiguration,
  useGetFileDownloadForSchedular,
  usePostFileUploadForSchedular,
} from "../../../../Services/MTO/Scheduling";
import { format } from "date-fns";
import {
  notifyError,
  notifyLoader,
  notifySuccess,
} from "../../../../../helpers/notify";
import { CheckUpdatesWrapper, FileUploadSkeletonTile, GridContainer, LastUpdateStatus, SideTab, Wrapper } from "./FileUploadSectionStyles";



const FileUploadSection = ({setIsRunEnabled}:any) => {
  const [fileObjects, setFileObjects] = useState<any>([]);
  const themeUi = useUserData().user.user.themeUi;

  const { mutateAsync: getFileConfiguration, isLoading } =
    useGetFileConfiguration();

  const { mutateAsync: postUploadSchedulerFile } =
    usePostFileUploadForSchedular();

  const { mutateAsync: getFileDownload } = useGetFileDownloadForSchedular();

  const [lastRefreshTime, setLastRefreshTime] = useState<string>(
    new Date().toString()
  );

  const GetFileConfiguration = async () => {
    try{

      const result = await getFileConfiguration();
      if(result.status !== 200){
        notifyError("Failed to fetch file configuration")
      }
      else{
        setFileObjects(result.data.data);
        setLastRefreshTime(new Date().toString());
      }
    }
    catch(e){
      notifyError("Failed to fetch file configuration");
      console.log(e);
    }
  };

  useEffect(()=>{
    if(fileObjects && fileObjects.length>0){
      const allUploaded = fileObjects.every((file: any) => file.last_updated !== null);
      setIsRunEnabled(allUploaded);
    }
  },[fileObjects])

  const user = useUserData().user.user;

  const UploadFile = async ({
    file,
    file_name,
  }: {
    file: File;
    file_type: string;
    file_name: string;
  }) => {

    if (file.name.split('.')[0] !== file_name) {
      notifyError(
        `Please upload a file with the correct name and extension: ${file_name}`
      );
      return;
    }
    if (file === null) {
      notifyError("Select a file to upload!");
      return;
    }
    try {
      notifyLoader("Uploading file...");
      const formData = new FormData();
      formData.append("file", file);
      formData.append("userid", user.id);
      formData.append("username", user.name);
      formData.append("day", "0");
      formData.append("file_type", "I");
      formData.append("is_critical", "True");
      const response = await postUploadSchedulerFile(formData);
      if (response.status !== 200) {
        throw new Error("Failed to upload file");
      } else {
        notifySuccess("File uploaded successfully!");
        GetFileConfiguration(); // Refresh the file list
      }
    } catch (e: any) {
      console.log("error", e);
      notifyError(e?.message || "Failed to upload file");
      console.log(e);
    }
  };

  const DownloadExcel = async (filename: string, expected_extension: string) => {
    try {
      notifyLoader("Downloading file...");
  
      // Ensure the filename has the correct extension
      const fileWithExtension = filename.endsWith(".csv") || filename.endsWith(".xlsx")
        ? filename
        : `${filename}${expected_extension}`;
  
      const response = await getFileDownload(filename);
      const blob = new Blob([response.data], {
        type: response.headers["content-type"],
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", fileWithExtension); // Use the filename with the correct extension
      document.body.appendChild(link);
      link.click();
      URL.revokeObjectURL(url);
      document.body.removeChild(link);
      notifySuccess("File downloaded successfully! Check your downloads!");
    } catch (e: any) {
      console.log("error", e);
      notifyError(e?.message || "Failed to download file");
      console.log(e);
    }
  };

  const [timeAgo, setTimeAgo] = useState("");

  const getTimeAgo = (time: string) => {
    const now = new Date().getTime();
    const past = new Date(time).getTime();
    const diffInSec = Math.floor((now - past) / 1000);

    if (diffInSec < 60) return `${diffInSec} sec ago`;
    if (diffInSec < 3600) return `${Math.floor(diffInSec / 60)} min ago`;
    if (diffInSec < 86400) return `${Math.floor(diffInSec / 3600)} hr ago`;
    return `${Math.floor(diffInSec / 86400)} day(s) ago`;
  };

  useEffect(() => {
    const updateTime = () => setTimeAgo(getTimeAgo(lastRefreshTime));

    updateTime(); 
    const interval = setInterval(updateTime, 1000); // update every sec

    return () => clearInterval(interval);
  }, [lastRefreshTime]);

  useEffect(() => {
    GetFileConfiguration();
  }, []);

  return (
    <Wrapper>
      {isLoading ? (
        <div
          style={{
            display: "flex",
            width: "100%",
            gap: "40px",
            marginTop: "50px",
            flexDirection: "column",
          }}
        >
          <FileUploadSkeletonTile />
          <FileUploadSkeletonTile />
        </div>
      ) : (
        <>
          <CheckUpdatesWrapper>
            <LastUpdateStatus>Last Updated: {timeAgo}</LastUpdateStatus>
            <VFButton
              style={{
                fontSize: "1rem",
                height: "3rem",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                padding: "0 12px",
                width: "fit-content",
              }}
              themeUi={themeUi}
              onClick={() => GetFileConfiguration()}
            >
              <img
                height={"13rem"}
                src="/assets/img/scheduling/refresh_icon.svg"
              />
              <p>Check for Updates</p>
            </VFButton>
          </CheckUpdatesWrapper>

{
  fileObjects.some((file: any) => file.file_from === "UI") && (

          <GridContainer>
            <SideTab>UI Generated Files</SideTab>

            {fileObjects.map(
              (file: any, index: number) =>
                file.file_from === "UI" && (
                  <FileUploadTile
                    key={index}
                    expected_extension={file.expected_extension}
                    fileUploadType={file.file_from}
                    lastUpdateStatus={
                      file.last_updated
                        ? format(
                          new Date(file.last_updated),
                            "dd MMM yyyy, hh:mm a"
                          ) +
                          " " +
                          "by " +
                          file.uploaded_by
                          : null
                    }
                    title={file.file_name}
                    onDownload={DownloadExcel}
                    onUpload={UploadFile}
                  />
                )
            )}
          </GridContainer>
  )

          }

{
  fileObjects.some((file: any) => file.file_from === "FTP") && (

          <GridContainer>
            <SideTab>Automated Files</SideTab>

            {fileObjects.map(
              (file: any, index: number) =>
                file.file_from === "FTP" && (
                  <FileUploadTile
                    key={index}
                    expected_extension={file.expected_extension}
                    fileUploadType={file.file_from}
                    lastUpdateStatus={
                      file.last_updated
                        ? format(
                            new Date(file.last_updated),
                            "dd MMM yyyy, hh:mm a"
                          )
                        : null
                    }
                    title={file.file_name}
                    onDownload={DownloadExcel}
                    onUpload={UploadFile}
                  />
                )
            )}
          </GridContainer>
)}

{fileObjects.length === 0 && (
  <div style={{fontSize: "1.2rem", color: "rgb(96, 93, 93)", marginTop: "80px", textAlign: "center"}}>
            No files configured. Please contact administrator.
  </div>)}
        </>
      )}
    </Wrapper>
  );
};

export default FileUploadSection;
