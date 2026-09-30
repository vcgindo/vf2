import React from "react"
import { useUserData } from "../../../../../context"
import VFButtonOutline from "../../../../../components/VectorFLOW/commons/VFButtonOutline"
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton"
import { TaskBarContainer, VFTaskBarButtonGroup } from "./styles"
import VFStepper, { StepItem } from "../../../../../components/VectorFLOW/commons/VFStepper"
import { ViewModifyProgressState } from "../../../../../VectorFlow/types/MDM"

export interface VFTaskBarProps {
    masterProgress: ViewModifyProgressState | any
    disableSubmit?: boolean
    disableDeleteSelected?: boolean
    editOnline?: boolean
    deleteOnline?: boolean
    onReset: () => void
    onBack: () => void
    onExportData: () => void
    onModifyData: () => void
    onClearAndExportErrors: (skipClear?: boolean) => void
    onSubmit: () => void
    onSubmitConflictData: () => void
    onEditOnline: () => void
    onEditOnlineSave: () => void
    onSaveToDraft: () => void
    onDeleteSelected: () => void
    onPhaseInPhaseOutStop: () => void
    onDeleteOnline: () => void
    onDeleteOnlineReset: () => void
    onDeleteOnlineSubmit: () => void
    onDeleteData: () => void
    enableEditOnlineReset: boolean
    showSubmittedExportError: boolean
    masterId: number
    mtoSaveData?: boolean
    onMTOSaveData?: () => void
    isMTOSaveDataDisabled?: boolean
    onMTOSaveAsDraft?: () => void
    isMTODraftDisabled?: boolean
    isMTOExcludeButton?: boolean
}


const VFTaskBar = (props: VFTaskBarProps) => {

    const {
        masterProgress,
        editOnline,
        disableSubmit,
        disableDeleteSelected,
        deleteOnline,
        enableEditOnlineReset,
        showSubmittedExportError,
        onBack,
        onExportData,
        onModifyData,
        onClearAndExportErrors,
        onSubmit,
        onSubmitConflictData,
        onReset,
        onEditOnline,
        onEditOnlineSave,
        onSaveToDraft,
        onDeleteSelected,
        onDeleteOnline,
        onDeleteOnlineReset,
        onDeleteData,
        onPhaseInPhaseOutStop,
        masterId,
        mtoSaveData,
        onMTOSaveData,
        isMTOSaveDataDisabled,
        onMTOSaveAsDraft,
        isMTODraftDisabled,
        isMTOExcludeButton
    } = props

    const { user, isSideBarOpen } = useUserData()
    const themeUi = user.user.theme_ui

    const width = isSideBarOpen ? "77%" : '97%'

    const getStepperState = (): StepItem[] => {
        switch (masterProgress) {
            case "uploaded":
                return [
                    {
                        label: 'File Uploaded',
                        status: 'completed',
                        description: ''
                    },
                    {
                        label: 'Submitted',
                        status: 'pending',
                        description: ''
                    },
                ]
            case "deleteUploaded":
                return [
                    {
                        label: 'File Uploaded',
                        status: 'completed',
                        description: ''
                    },
                    {
                        label: 'Submitted',
                        status: 'pending',
                        description: ''
                    },
                ]
            case 'conflicts':
                return [
                    {
                        label: 'File Uploaded',
                        status: 'completed',
                        description: ''
                    },
                    {
                        label: 'Submitted',
                        status: 'pending',
                        description: ''
                    },
                ]
            case 'editOnlineConflicts':
                return [
                    {
                        label: 'Edit Online',
                        status: 'completed',
                        description: ''
                    },
                    {
                        label: 'Submitted',
                        status: 'pending',
                        description: ''
                    },
                ]
            case "submitted":
                return [
                    {
                        label: 'File Uploaded',
                        status: 'completed',
                        description: ''
                    },
                    {
                        label: 'Submitted',
                        status: 'completed',
                        description: ''
                    },
                ]
            case "editOnline":
                return [
                    {
                        label: 'Edit Online',
                        status: 'completed',
                        description: ''
                    },
                    {
                        label: "Submitted",
                        status: "pending",
                        description: ""
                    }
                ]
            case "initial":
                return [
                    {
                        label: 'Edit Online',
                        status: 'pending',
                        description: ''
                    },
                    {
                        label: "Submitted",
                        status: "pending",
                        description: ""
                    }
                ]
            // case "editOnlineSaved":
            //     return [
            //         {
            //              label:'Edit Online',
            //             status:'completed',
            //             description:''
            //         },
            //         {
            //             label:'Save',
            //             status:'completed',
            //             description:''
            //         },
            //         {
            //             label:"Submit",
            //             status:"pending",
            //             description:""
            //         }
            //     ]
            case "editOnlineSubmitted":
                return [
                    {
                        label: 'Edit Online',
                        status: 'completed',
                        description: ''
                    },
                    {
                        label: "Submitted",
                        status: "completed",
                        description: ""
                    }
                ]
            case "deleteOnline":
                return [
                    {
                        label: 'Delete Online',
                        status: 'completed',
                        description: ''
                    },
                    {
                        label: "Submitted",
                        status: "pending",
                        description: ""
                    }
                ]
            //  case "deleteOnlineSaved":
            //     return [
            //         {
            //              label:'Delete Online',
            //             status:'completed',
            //             description:''
            //         },
            //         {
            //             label:'Save',
            //             status:'completed',
            //             description:''
            //         },
            //         {
            //             label:"Submit",
            //             status:"pending",
            //             description:""
            //         }
            //     ]
            case "deleteOnlineSubmitted":
                return [
                    {
                        label: 'Delete Online',
                        status: 'completed',
                        description: ''
                    },
                    {
                        label: "Submitted",
                        status: "completed",
                        description: ""
                    }
                ]
            default:
                return [

                ]
        }
    }


    const BackButton = () => {

        const { user } = useUserData()
        const themeUi = user.user.theme_ui

        return (
            <VFButtonOutline onClick={onBack} themeUi={themeUi} width={50} onHoverChild={
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                    <img src={"/assets/img/VectorFLOW/NMS/back-btn-white.svg"} data-testid="back-btn" />
                </div>
            }>
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                    <img src={themeUi === "REGALBLAZE" ? "/assets/img/VectorFLOW/NMS/back-btn-regal.svg" : "/assets/img/VectorFLOW/NMS/back-btn.svg"} data-testid="back-btn" />
                </div>
            </VFButtonOutline>
        )
    }

    if (mtoSaveData) {
        return (
            <div style={{ zoom: 0.8 }}>
                <TaskBarContainer data-testid="taskbar" style={{ width: width }}>
                    <VFTaskBarButtonGroup>
                        <BackButton />
                        <VFButtonOutline onClick={onExportData} themeUi={themeUi} disabled={false} width={139}>
                            Export Data
                        </VFButtonOutline>
                        {
                            isMTOExcludeButton &&
                        
                            (<VFButton onClick={() => onClearAndExportErrors(false)} themeUi={themeUi} disabled={false} width={183}>
                                Clear & Export Errors
                            </VFButton>)
                        }
                        <VFButtonOutline style={{ display: "none" }} onClick={onMTOSaveAsDraft ? onMTOSaveAsDraft : () => { return null; }} themeUi={themeUi} disabled={isMTODraftDisabled} width={139}>
                            Save As Draft
                        </VFButtonOutline>
                        <VFButtonOutline onClick={onMTOSaveData && (!isMTOSaveDataDisabled) ? onMTOSaveData : () => { return null; }} themeUi={themeUi} disabled={isMTOSaveDataDisabled} width={139}>
                            Save As Task
                        </VFButtonOutline>
                    </VFTaskBarButtonGroup>
                    <div>
                        <VFStepper
                            items={getStepperState()}
                        />
                    </div>
                </TaskBarContainer>
            </div>
        )
    }

    switch (masterProgress) {
        case "view":
            return (
                <TaskBarContainer data-testid="taskbar" style={{ width: width }}>
                    <VFTaskBarButtonGroup>
                        <BackButton />
                        <VFButtonOutline onClick={onExportData} themeUi={themeUi} width={130}>
                            Export Data
                        </VFButtonOutline>
                        {/* <VFButtonOutline onClick={onSaveToDraft} themeUi={themeUi} disabled={false} width={139}>
                       Save as draft
                    </VFButtonOutline> */}
                        <VFButtonOutline onClick={onEditOnline} themeUi={themeUi} disabled={!editOnline} width={164} onHoverChild={
                            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                                <img src={"/assets/img/VectorFLOW/NMS/edit-online-disabled.svg"} style={{ marginRight: '11px' }} />
                                <p>Edit Online</p>
                            </div>
                        }>
                            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                                <img src={editOnline ? themeUi === "REGALBLAZE" ? "/assets/img/VectorFLOW/NMS/edit-online-regal.svg" : "/assets/img/VectorFLOW/NMS/edit-online.svg" : "/assets/img/VectorFLOW/NMS/edit-online-disabled.svg"} style={{ marginRight: '11px' }} />
                                <p>Edit Online</p>
                            </div>
                        </VFButtonOutline>
                    <VFButtonOutline onClick={onModifyData} themeUi={themeUi} disabled={false} width={164}>
                        Modify Data
                    </VFButtonOutline>
                    </VFTaskBarButtonGroup>
                </TaskBarContainer>
            )

        case "error":
            return (
                <TaskBarContainer data-testid="taskbar" style={{ width: width }}>
                    <VFTaskBarButtonGroup>
                        <BackButton />
                        <VFButtonOutline onClick={onSaveToDraft} themeUi={themeUi} disabled={false} width={139}>
                            Save as draft
                        </VFButtonOutline>
                        <VFButton onClick={() => onClearAndExportErrors(false)} themeUi={themeUi} disabled={false} width={183}>
                            Clear & Export Errors
                        </VFButton>
                    </VFTaskBarButtonGroup>
                </TaskBarContainer>
            )

        case "uploaded":
            return (
                <TaskBarContainer data-testid="taskbar" style={{ width: width }}>
                    <VFTaskBarButtonGroup>
                        <BackButton />
                        <VFButtonOutline onClick={onDeleteSelected} themeUi={themeUi} disabled={disableDeleteSelected} width={139}>
                            Delete Selected
                        </VFButtonOutline>
                        <VFButtonOutline onClick={onSaveToDraft} themeUi={themeUi} disabled={masterId > 14} width={139}>
                            Save as draft
                        </VFButtonOutline>
                        <VFButton onClick={onSubmit} themeUi={themeUi} disabled={disableSubmit} width={139}>
                            Submit All
                        </VFButton>
                    </VFTaskBarButtonGroup>
                    <div>
                        <VFStepper
                            items={getStepperState()}
                        />
                    </div>
                </TaskBarContainer>
            )

        case "submitted":
            return (
                <TaskBarContainer data-testid="taskbar" style={{ width: width, justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', gap: '20px' }}>
                        <BackButton />
                        {showSubmittedExportError ? (
                            <VFButton onClick={onClearAndExportErrors} themeUi={themeUi} disabled={false} width={183}>
                                Export Errors
                            </VFButton>
                        ) :
                            <div style={{ width: '100%' }} />
                        }
                    </div>
                    <div >


                        <VFStepper
                            items={getStepperState()}
                        />
                    </div>

                </TaskBarContainer>
            )
        case "editOnline":
            return (
                <TaskBarContainer data-testid="taskbar" style={{ width: width }}>
                    <VFTaskBarButtonGroup>
                        <BackButton />
                        <VFButtonOutline themeUi={themeUi} onClick={onReset} disabled={!enableEditOnlineReset}>
                            Reset
                        </VFButtonOutline>
                        <VFButton themeUi={themeUi} onClick={onEditOnlineSave} disabled={masterId > 14}>
                            Save as Draft
                        </VFButton>
                        <VFButtonOutline themeUi={themeUi} onClick={onSubmit} >
                            Submit
                        </VFButtonOutline>
                    </VFTaskBarButtonGroup>
                    <div >
                        <VFStepper
                            items={getStepperState()}
                        />
                    </div>
                </TaskBarContainer>
            )
        // case "editOnlineSaved":
        //     return(
        //         <TaskBarContainer data-testid="taskbar" style={{width:width}}>
        //            <VFTaskBarButtonGroup>
        //             <BackButton/>
        //                 <VFButtonOutline themeUi={themeUi} onClick={onReset} disabled={!enableEditOnlineReset}>
        //                     Reset
        //                 </VFButtonOutline>
        //                 <VFButton themeUi={themeUi} onClick={onSubmit}>
        //                     Submit
        //                 </VFButton>
        //            </VFTaskBarButtonGroup>
        //             <div>
        //                 <VFStepper
        //                     items={getStepperState()}
        //                 />
        //             </div>
        //         </TaskBarContainer>
        //     )
        case "editOnlineSubmitted":
            return (
                <TaskBarContainer data-testid="taskbar" style={{ width: width, justifyContent: 'space-between' }}>
                    <VFTaskBarButtonGroup>
                        <BackButton />
                    </VFTaskBarButtonGroup>
                    <div >
                        <VFStepper
                            items={getStepperState()}
                        />
                    </div>
                </TaskBarContainer>
            )
        case 'phaseInPhaseOut':
            return (
                <TaskBarContainer data-testid="taskbar" style={{ width: width }}>
                    <VFTaskBarButtonGroup>
                        <BackButton />
                        <VFButton themeUi={themeUi} onClick={onPhaseInPhaseOutStop}>
                            Stop Selected
                        </VFButton>
                        <VFButtonOutline onClick={onSaveToDraft} themeUi={themeUi} disabled={masterId > 14} width={139}>
                            Save as draft
                        </VFButtonOutline>
                    </VFTaskBarButtonGroup>
                </TaskBarContainer>
            )
        case 'deleteView':
            return (
                <TaskBarContainer data-testid="taskbar" style={{ width: width }}>
                    <VFTaskBarButtonGroup>
                        <BackButton />
                        <VFButtonOutline themeUi={themeUi} onClick={onDeleteOnline} disabled={!deleteOnline}>
                            Delete Online
                    </VFButtonOutline >
                    <VFButtonOutline themeUi={themeUi} onClick={onDeleteData} disabled={false}>
                            Delete Data
                        </VFButtonOutline>
                    </VFTaskBarButtonGroup>

                </TaskBarContainer>
            )
        case 'deleteOnline':
            return (
                <TaskBarContainer data-testid="taskbar" style={{ width: width }}>
                    <VFTaskBarButtonGroup>
                        <BackButton />
                        <VFButtonOutline themeUi={themeUi} onClick={onDeleteOnlineReset}>
                            Reset
                        </VFButtonOutline >
                        <VFButton themeUi={themeUi} onClick={onSaveToDraft} disabled={masterId > 14}>
                            Save as draft
                        </VFButton>
                        <VFButtonOutline themeUi={themeUi} onClick={onSubmit}>
                            Submit
                        </VFButtonOutline >
                    </VFTaskBarButtonGroup>
                    <div >
                        <VFStepper
                            items={getStepperState()}
                        />
                    </div>
                </TaskBarContainer>
            )
        //  case "deleteOnlineSaved":
        //     return(
        //         <TaskBarContainer data-testid="taskbar" style={{width:width}}>
        //            <VFTaskBarButtonGroup>
        //             <BackButton/>
        //                 <VFButtonOutline themeUi={themeUi} onClick={onDeleteOnlineReset}>
        //                     Reset
        //                 </VFButtonOutline>
        //                 <VFButton themeUi={themeUi} onClick={onDeleteOnlineSubmit}>
        //                     Submit
        //                 </VFButton>
        //            </VFTaskBarButtonGroup>
        //             <div >
        //                 <VFStepper
        //                     items={getStepperState()}
        //                 />
        //             </div>
        //         </TaskBarContainer>
        //     )
        case "deleteOnlineSubmitted":
            return (
                <TaskBarContainer data-testid="taskbar" style={{ width: width, justifyContent: 'flex-end' }}>
                    <div>
                        <VFStepper
                            items={getStepperState()}
                        />
                    </div>
                </TaskBarContainer>
            )
        case 'deleteUploaded':
            return (
                <TaskBarContainer data-testid="taskbar" style={{ width: width }}>
                    <VFTaskBarButtonGroup>
                        <BackButton />
                        <VFButtonOutline themeUi={themeUi} onClick={onDeleteSelected} width={139}>
                            Remove Selected
                        </VFButtonOutline >
                        <VFButtonOutline onClick={onSaveToDraft} themeUi={themeUi} disabled={false} width={139}>
                            Save as draft
                        </VFButtonOutline>
                        <VFButton themeUi={themeUi} onClick={onSubmit}>
                            Delete All
                        </VFButton>
                    </VFTaskBarButtonGroup>
                    <div >
                        <VFStepper
                            items={getStepperState()}
                        />
                    </div>
                </TaskBarContainer>
            )
        case "conflicts":
            return (
                <TaskBarContainer data-testid="taskbar" style={{ width: width }}>
                    <VFTaskBarButtonGroup>
                        <BackButton />
                        <VFButtonOutline onClick={onDeleteSelected} themeUi={themeUi} disabled={false} width={139}>
                            Delete Selected
                        </VFButtonOutline>
                        <VFButton onClick={onSubmitConflictData} themeUi={themeUi} disabled={disableSubmit} width={139}>
                            Submit All
                        </VFButton>
                    </VFTaskBarButtonGroup>
                    <div>
                        <VFStepper
                            items={getStepperState()}
                        />
                    </div>
                </TaskBarContainer>
            )
        case "editOnlineConflicts":
            return (
                <TaskBarContainer data-testid="taskbar" style={{ width: width }}>
                    <VFTaskBarButtonGroup>
                        <BackButton />
                        <VFButtonOutline onClick={onDeleteSelected} themeUi={themeUi} disabled={false} width={139}>
                            Delete Selected
                        </VFButtonOutline>
                        <VFButton onClick={onSubmitConflictData} themeUi={themeUi} disabled={disableSubmit} width={139}>
                            Submit All
                        </VFButton>
                    </VFTaskBarButtonGroup>
                    <div>
                        <VFStepper
                            items={getStepperState()}
                        />
                    </div>
                </TaskBarContainer>
            )
        case "mtoView":
            return (
                <TaskBarContainer data-testid="taskbar" style={{ width: width }}>
                    <VFTaskBarButtonGroup>
                        <BackButton />
                        <VFButtonOutline onClick={onDeleteSelected} themeUi={themeUi} disabled={false} width={139}>
                            Delete Selected
                        </VFButtonOutline>
                        <VFButton onClick={onSubmitConflictData} themeUi={themeUi} disabled={disableSubmit} width={139}>
                            Submit All
                        </VFButton>
                    </VFTaskBarButtonGroup>
                    <div>
                        <VFStepper
                            items={getStepperState()}
                        />
                    </div>
                </TaskBarContainer>
            )
        default:
            return (
                <React.Fragment>
                    <div >
                        <VFStepper
                            items={getStepperState()}
                        />
                    </div>
                </React.Fragment>
            )
    }


}

export default VFTaskBar