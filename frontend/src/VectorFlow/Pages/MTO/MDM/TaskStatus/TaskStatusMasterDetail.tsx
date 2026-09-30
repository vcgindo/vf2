import VFStepper,{StepItem} from "../../../../../components/VectorFLOW/commons/VFStepper"
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton"
import { VFTaskStatusWrapper,VFTaskStatusContentWrapper, VFTaskStatusStepperWrapper, VFTastStatusDownloadWrapper,VFTaskStatusNoData } from "./styles"
import { useUserData } from "../../../../../context"
import StepperPrefix from "./StepperPrefix"
import { useEffect } from "react"



export interface TaskStatusMasterDetailProps{
    data:any
    onDownload:(body:{taskId:string,approverId:number})=>void
}

const getStepperState = (data:any):StepItem[]=>{
    switch(data.TaskStatus){
        case "DB Update Pending":
            return [
                {
                    label:"Submission",
                    status:'completed',
                    description:data.PendingSince,
                    prefix:<StepperPrefix label={data.Requester} subLabel={"Requester"} />
                    //description: formatMDMDate(data.PendingSince, 'dd/MM/yy hh:mm:ss a'),
                 
                    
                },
                {
                    label:"DB Update Pending",
                    status:'pending',
                    description:'',
                    prefix:<StepperPrefix label={data.Approver} subLabel={"Approver"} />
                },
                {
                    label:"DB Updated",
                    status:'pending',
                    description:'',
                    prefix:<div style={{height:'15px'}}/>
                }
            ]
        case "Rejected":
            return [
                {
                    label:"Submission",
                    status:'completed',
                    description:data.date,
                    prefix:<StepperPrefix label={data.Requester} subLabel={"Requester"} />
                    //description: formatMDMDate(data.date, 'dd/MM/yy hh:mm:ss a'),
                   
                },
                {
                    label:"Rejected",
                    status:'rejected',
                    description:data.date,
                    prefix:<StepperPrefix label={data.Approver} subLabel={"Approver"} />,
                    //description: formatMDMDate(data.date, 'dd/MM/yy hh:mm:ss a'),
                    
                }
            ]
        case "Approved":
            return [
                {
                    label:"Submission",
                    status:'completed',
                    description:data.PendingSince,
                    prefix:<StepperPrefix label={data.Requester} subLabel={"Requester"} />
                    //description:formatMDMDate(data.PendingSince, 'dd/MM/yy hh:mm:ss a'),
                },
                {
                    label:"Approved",
                    status:'completed',
                    description:data.ApprovedDate,
                    prefix:<StepperPrefix label={data.Approver} subLabel={"Approver"} />
                    //description:formatMDMDate(data.ApprovedDate, 'dd/MM/yy hh:mm:ss a')
                    
                },
                {
                    label:"DB Updated",
                    status:'completed',
                    description:data.DBUpdatedDate,
                    prefix:<div style={{height:'15px'}}/>
                    //description:formatMDMDate(data.DBUpdatedDate,'dd/MM/yy hh:mm:ss a' )
                }
            ]
        case "Approved - DB Updated":
            return [
                {
                    label:"Submission",
                    status:'completed',
                    description:data.PendingSince,
                    prefix:<StepperPrefix label={data.Requester} subLabel={"Requester"} />
                    //description:formatMDMDate(data.PendingSince, 'dd/MM/yy hh:mm:ss a')
                },
                {
                    label:"Approved - DB Updated",
                    status:'completed',
                    description:data.ApprovedDate,
                    prefix:<StepperPrefix label={data.Approver} subLabel={"Approver"} />
                    //description:formatMDMDate(data.ApprovedDate, 'dd/MM/yy hh:mm:ss a')
                },
                {
                    label:"DB Updated",
                    status:'completed',
                    description:data.DBUpdatedDate,
                    prefix:<div style={{height:'15px'}}/>
                    //description:formatMDMDate(data.DBUpdatedDate, 'dd/MM/yy hh:mm:ss a')
                }
            ]
        case "Partially Approved - DB update Pending":
            return [
                {
                    label:"Submission",
                    status:'completed',
                    description:data.PendingSince,
                    prefix:<StepperPrefix label={data.Requester} subLabel={"Requester"} />
                    //description:formatMDMDate(data.PendingSince, 'dd/MM/yy hh:mm:ss a')
                },
                {
                    label:"Partially Approved",
                    status:'completed',
                    description:data.ApprovedDate,
                    prefix:<StepperPrefix label={data.Approver} subLabel={"Approver"} />
                    //description:formatMDMDate(data.ApprovedDate, 'dd/MM/yy hh:mm:ss a')
                },
                {
                    label:"Partially Approved - DB Update Pending",
                    status:'pending',
                    description:'',
                    prefix:<div style={{height:'15px'}}/>
                }
            ]
        case "Approved - DB update Pending":
            return [
                {
                    label:"Submission",
                    status:'completed',
                    description:data.PendingSince,
                    prefix:<StepperPrefix label={data.Requester} subLabel={"Requester"} />
                    //description:formatMDMDate(data.PendingSince, 'dd/MM/yy hh:mm:ss a')
                },
                {
                    label:"Approved - DB update Pending",
                    status:'completed',
                    description:data.ApprovedDate,
                    prefix:<StepperPrefix label={data.Approver} subLabel={"Approver"} />
                    //description:formatMDMDate(data.ApprovedDate, 'dd/MM/yy hh:mm:ss a')
                },
                {
                    label:"DB Updated",
                    status:'pending',
                    description:'',
                    prefix:<div style={{height:'15px'}}/>
                }
            ]
        case "Pending":
            return [
                {
                    label:"Submission",
                    status:'completed',
                    description:data.PendingSince,
                    prefix:<StepperPrefix label={data.Requester} subLabel={"Requester"} />
                    //description:formatMDMDate(data.PendingSince, 'dd/MM/yy hh:mm:ss a')
                },
                {
                    label:"Approval Pending",
                    status:'pending',
                    description:data.ApprovedDate,
                    prefix:<StepperPrefix label={data.Approver} subLabel={"Approver"} />
                    //description:formatMDMDate(data.ApprovedDate, 'dd/MM/yy hh:mm:ss a')
                },
                {
                    label:"DB Updated",
                    status:'pending',
                    description:'',
                    prefix:<div style={{height:'15px'}}/>
                }
            ]
        default:
            return [
                {
                    label:"Submission",
                    status:'completed',
                    description:data.PendingSince,
                    prefix:<StepperPrefix label={data.Requester} subLabel={"Requester"} />
                    //description:formatMDMDate(data.PendingSince, 'dd/MM/yy hh:mm:ss a')
                },
                {
                    label:"DB Update Pending",
                    status:'pending',
                    description:'',
                    prefix:<StepperPrefix label={data.Approver} subLabel={"Approver"} />
                },
                {
                    label:"DB Updated",
                    status:'pending',
                    description:'',
                    prefix:<div style={{height:'15px'}}/>
                }
            ]
    }
}

const TaskStatusMasterDetail = (props:TaskStatusMasterDetailProps)=>{
    const{
        data,
        onDownload
    } = props
    const approvedStatuses = ["Approved","Partially Approved - DB update Pending","Approved - DB update Pending","Approved - DB Updated"]
    const {user} = useUserData()
    const {Approvers} = data;

    const showDisplayDownloadButton = (status:string):boolean=>{
        return approvedStatuses.includes(status)
    }
    const gridFraction ="5fr 1fr"

    console.log("A[[rodf", Approvers, Approvers?.length);
    return (
        <VFTaskStatusWrapper data-testid="task-status-master-detail">
            {(Approvers && Approvers.length>0)?Approvers?.map((approver:any,index:number)=>{
                
                return(
                    <VFTaskStatusContentWrapper key={index}>
                        <VFTaskStatusStepperWrapper gridFraction={gridFraction}>
                        {/* <VFTaskStatusStepperLabel></VFTaskStatusStepperLabel> */}
                            <VFStepper
                                items={getStepperState({...approver, Requester: props.data.Requester, Approver: props.data.Approvers[index], TaskStatus: props.data.TaskStatus})}
                                dashWidth="500px"
                                zoom={0.7}
                            />
                            {showDisplayDownloadButton(approver.TaskStatus) && (
                                <VFButton 
                                    onClick={()=>onDownload(approver)} 
                                    themeUi={user.user.theme_ui}
                                    width={167}
                                >
                                    <VFTastStatusDownloadWrapper>
                                        <img src="/assets/img/VectorFLOW/NMS/download-task-status.svg" height={25}/>
                                        <p style={{marginLeft:10,fontWeight:500}}> Download</p>
                                    </VFTastStatusDownloadWrapper>
                                </VFButton>
                            )}
                        </VFTaskStatusStepperWrapper>
                    </VFTaskStatusContentWrapper>
                )
            })
            :
            <VFTaskStatusNoData>
                No data to show
            </VFTaskStatusNoData>
        }
        </VFTaskStatusWrapper>
    )
}   

export default TaskStatusMasterDetail