import { LOCAL_STORAGE_KEY } from "./constants";
import axios from "axios";
import { notifyError } from "./notify";
import { decryptStorageData } from "../VectorFlow/Pages/MTO/Common/encryption";


interface Token {
  tokenType?: string
  access?: string
  refresh?: string
  expiryAt?: number
  apigeeToken: { access_token: string }
}

const useDownloadHandler = () => {

  const handleDownloadMTOVF = async (reportName: string, downloadName: string) => {
    try{
     
      const encryptedUserId = localStorage.getItem('User-ID');
      const encryptedUserName = localStorage.getItem('User-Name');
      const decryptedUserId = await decryptStorageData(encryptedUserId);
      const decryptedUserName = await decryptStorageData(encryptedUserName);
      
      
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
        };  
      
        if (decryptedUserId) headers['User-ID'] = decryptedUserId;
        if (decryptedUserName) headers['User-Name'] = decryptedUserName;
      
        const response = await fetch(`${process.env.REACT_APP_VF_API_HOST_MTO}/DownloadReportData/?report_name=${reportName}`, {
          headers,
          credentials: 'include',
        });
        if (!response.ok) {
          if (response.status == 404) {
            notifyError("File not found");
          } else {
            notifyError("Error while downloading")
          }
        } else {
          // Convert response to blob object
          const blob = await response.blob()
          // Create download URL for blob object
          const url = URL.createObjectURL(blob)
  
          // Trigger download
          const link = document.createElement('a')
          link.href = url
          if (downloadName.length !== 0) {
            link.setAttribute('download', `${downloadName}`)
          } else {
            link.setAttribute('download', `ReportFile.zip`)
          }
          document.body.appendChild(link)
          link.click()
          // Clean up download URL
          URL.revokeObjectURL(url);
        }
      
    }
    catch(err){
      notifyError('Error while downloading');
    }
  }
  
  
  const handleDownloadVF = async (reportName: string, downloadName:string) => {
  
    try {

      const encryptedUserId = localStorage.getItem('User-ID');
      const encryptedUserName = localStorage.getItem('User-Name');
      const decryptedUserId = await decryptStorageData(encryptedUserId);
      const decryptedUserName = await decryptStorageData(encryptedUserName);
      
      const headers: Record<string, string> = {};
      if (decryptedUserId) headers['User-ID'] = decryptedUserId;
      if (decryptedUserName) headers['User-Name'] = decryptedUserName;
      
        const response = await fetch(`${process.env.REACT_APP_API_HOST}api/mta/DownloadReports/${encodeURIComponent(reportName)}`, {
          headers,
          credentials: 'include',
        })
        if (!response.ok) {
          if (response.status == 404) {
            notifyError("File not found");
          } else {
            notifyError("Error while downloading")
          }
          return false;
        } else {
          // Convert response to blob object
          const blob = await response.blob()
          // Create download URL for blob object
          const url = URL.createObjectURL(blob)
  
          // Trigger download
          const link = document.createElement('a')
          link.href = url
          if (downloadName.length !== 0) {
            link.setAttribute('download', `${downloadName}`)
          } else {
            link.setAttribute('download', `ReportFile.zip`)
          }
          document.body.appendChild(link)
          link.click()
          // Clean up download URL
          URL.revokeObjectURL(url);
          return true;
        }
      
    } catch (error: any) {
      console.log(error,"error")
      notifyError('Error while downloading');
      return false;
    }
  
  }

  return { handleDownloadMTOVF,handleDownloadVF };
};

export default useDownloadHandler;
