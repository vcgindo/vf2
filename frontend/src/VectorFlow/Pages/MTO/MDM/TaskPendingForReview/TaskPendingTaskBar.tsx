import { TaskBarContainer, VFTaskBarButtonGroup } from "../ViewModify/styles"
import VFButtonOutline from "../../../../../components/VectorFLOW/commons/VFButtonOutline"
import VFButton from "../../../../../components/VectorFLOW/commons/VFButton"
import { useUserData } from "../../../../../context"

interface TaskPendingTaskBarProps{
    onSubmit:()=>void
    onCancel:()=>void
    disableSubmit:boolean
    isSideBarOpen:boolean
}

const TaskPendingTaskBar = (props:TaskPendingTaskBarProps) =>{

    const {
        onCancel,
        onSubmit,
        disableSubmit,
        isSideBarOpen
    } = props


    const {user} = useUserData()

    return(
        <TaskBarContainer data-testid="taskbar" style={{width:isSideBarOpen?'77%':'97%'}}>
            <VFTaskBarButtonGroup>
                <VFButtonOutline onClick={onCancel} themeUi={user.user.theme_ui} disabled={false} width={137}>
                    Cancel
                </VFButtonOutline>            
                <VFButton onClick={onSubmit} themeUi={user.user.theme_ui} disabled={disableSubmit} width={137}>
                    Submit
                </VFButton>
            </VFTaskBarButtonGroup>
        </TaskBarContainer>
    )
}

export default TaskPendingTaskBar