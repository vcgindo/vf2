import React, { useState } from 'react'
import UploadWrapperSection from './UploadWrapperSection'
import PermissionSelectionPage from './PermissionSelectionPage';
import { useUserData } from '../../../context';

function BulkUploadPage() {
  const [isAssignPageOpen, setIsAssignPage] = useState<any>(false);

  const [validUserData, setValidUserData] = useState<any>([]);
  const user = useUserData()

  const themeUi = user.user.themeUi;



  return (
    <div style={{overflow:'hidden',width:'100%', height: "100%"}}>
      {
        isAssignPageOpen?
        <PermissionSelectionPage validUserData={validUserData} setValidUsersData={setValidUserData} themeUi={themeUi} setIsAssignPage={setIsAssignPage}/>
        :
        <UploadWrapperSection setIsAssignPageOpen={setIsAssignPage} setValidUserData={setValidUserData} validUserData={validUserData}/>
      }
    </div>
  )
}

export default BulkUploadPage