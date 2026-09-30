import React from "react"
import useSavedDrafts from "./useSavedDrafts"
import { mapDraftDataToMTOTableRowData,  mapDraftToMTOColumnDefs } from "../../../../../helpers/utils"
import { useUserData } from "../../../../../context"

import VFTable from "../../Common/VFTable"
import VFLoader from "../../../../../components/VectorFLOW/commons/VFLoader"
import VFModalCard from "../../../../../components/VectorFLOW/commons/VFModalCard"
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton"
import VFButtonOutline from "../../../../../components/VectorFLOW/commons/VFButtonOutline"



const MTOSavedDrafts = ()=>{


  const {user} = useUserData()

  const {
    isDeleteModalOpen,
    openDeleteModal,
    closeDeleteModal,
    onDeleteDraft,
    onEditDraft,
    allDrafts,
    isLoading
  } = useSavedDrafts()

  if(isLoading){
    return <VFLoader/>
  }

  return(
    <div style={{paddingTop:'20px',paddingLeft: '25px',height:'90%'}}>
      <VFTable
          columnDefs={mapDraftToMTOColumnDefs([
            {
                
              displayName: "Sr No.",
              key: "sr_no",
              visible: true,
              isAdd:true,
              isDownload:true,
              isEdit:true,
              isDelete:true,
              "col_Position":'1',
              "isApplicable":true,
              dataType:'String'
            },
            {
              displayName: "Last Modification Date",
              key: "LastModifiedDateTime",
              visible: true,
              isAdd:true,
              isDownload:true,
              isEdit:true,
              isDelete:true,
              "col_Position":'2',
              "isApplicable":true,
              dataType:'String'
            },
            {
              displayName: "Instance Name",
              key: "Masters",
              visible: true,
              isAdd:true,
              isDownload:true,
              isEdit:true,
              isDelete:true,
              "col_Position":'3',
              "isApplicable":true,
              dataType:'String'
            },
            // {
            //   displayName: "Search Key",
            //   key: "SearchKeys",
            //   visible: true,
            //   isAdd:true,
            //   isDownload:true,
            //   isEdit:true,
            //   "col_Position":'4',
            //   "isApplicable":true
            // },
            {
                displayName:"Action",
                key:"action",
                visible:true,
                isAdd:true,
                isDownload:true,
                isDelete:true,
                isEdit:true,
                "col_Position":'5',
                "isApplicable":true,
                dataType:'String'
            }
          ],{
            cellRendererParams:{
              onEdit:onEditDraft,
              onDelete:openDeleteModal
            }
          })}
          rowData={mapDraftDataToMTOTableRowData(allDrafts)}
          pagination={true}
          // paginationPageSize={50}
          paginationPageSize={parseInt(process.env.REACT_APP_SAVEDRAFT_PAGE || '100')}

          gridOptions={{
            getRowStyle: (params: any) => {
              if (params.node.rowIndex % 2 === 0) {
                return { background: "#EBEBEB" };
              }
              return { background: "#F7F7F7" };
            },
              enableRangeSelection:false,
              rowSelection:'multiple',
          }}
          statusBar={{
            statusPanels:[
              { statusPanel: 'agTotalAndFilteredRowCountComponent', align: 'left' },
              { statusPanel: 'agTotalRowCountComponent', align: 'left' },
              { statusPanel: 'agFilteredRowCountComponent', align: 'left' },
              { statusPanel: 'agSelectedRowCountComponent', align: 'left' },
              { statusPanel: 'agAggregationComponent', align: 'left' },
            ]
          }}
          height={"100%"}
          
        />

        <VFModalCard headerText={"Warning"} openModal={isDeleteModalOpen} closeModal={closeDeleteModal} headerIcon={'/assets/img/VectorFLOW/NMS/warning.svg'} closeIcon={'/assets/img/VectorFLOW/NMS/close-dark.svg'}>
        <p style={{textAlign:"center", color: "#313131", paddingTop:"36px", fontStyle:"normal", fontVariant:"normal",fontWeight:300,fontSize:"14px",fontFamily:"Roboto"}}>
          Are you sure you want to delete the draft ?
        </p> 
        <div style={{zoom:0.9,display:"flex",gap:"28px", alignItems:"center", justifyContent:"flex-end",padding:'10px 20px 10px 30px',margin:'50px -80px 0px -80px',borderTop:'dashed 1px gray'}}>
          <VFButtonOutline color={"gray"} themeUi={user.user.theme_ui} onClick={closeDeleteModal}>No</VFButtonOutline>
          <VFButton themeUi={user.user.theme_ui} onClick={onDeleteDraft}>Yes</VFButton>
        </div>
       </VFModalCard>
    </div>
  )
}

export default MTOSavedDrafts