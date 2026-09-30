import Drawer from "../../commons/Drawer"
import { Content,DrawerHeader} from "../UserURLsDrawer/styles"
import { useUserData } from "../../../context"
import { useState } from "react"
import AddRole from "./Add"
import NavigationTab from "../NavigationTab"
import ViewURLs from "./View"
import DeleteUrl from "./Delete"
import { notifySuccess,notifyError } from "../../../helpers/notify"
import EditRole from "./Edit"

interface UserRolesDrawerProps{
    onClose:()=>void
}

const UserRolesDrawer = (props:UserRolesDrawerProps)=>{

    const {
        onClose
    } = props

    const {user} = useUserData()

    const themeUi = user.user.theme_ui


    const [currTab,setCurrTab] = useState<number>(0)

    const [currRole,setCurrRole] = useState<any>(null)

    const [activeTab, setActiveTab] = useState(0);

    const onEditRole = (row:any)=>{
        setCurrTab(3)
        setCurrRole(row)
    }

    const onDeleteRole = (row:any)=>{
        setCurrTab(2)
        setCurrRole(row)
    }

    const resetTab = ()=>{
        setCurrTab(0)
        setCurrRole(null)
        setActiveTab(0);
    }

    const handleDelete = async()=>{
        try{
            await fetch(`${process.env.REACT_APP_API_HOST}api/user/delete-role/${currRole.id}/`,{
                method:'DELETE'
            })
            notifySuccess("Deleted Role Successfully")
            setCurrTab(0)
        }catch(error){
            console.error(error)
            notifyError("Server Went Unresponsive")
        }
    }

    

    return(
        <Drawer
            isOpen
            header={<Header 
                themeUi={themeUi}
                handleAction={setCurrTab}
                handleClose={onClose}
                activeTab={activeTab}
                setActiveTab={setActiveTab}
            />}
            onClose={onClose}
        >
            
            
            {currTab === 1 && (
                <Content>
                    <AddRole cb={resetTab}/>
                </Content>
            )}
            {currTab === 0 && (
                <Content>
                    <ViewURLs
                        onEdit={onEditRole}
                        onDelete={onDeleteRole}
                    />
                </Content>
            )}
            {currTab === 2 && (
                <Content>
                    <DeleteUrl  
                        onSuccess={handleDelete}
                        onFailure={resetTab}
                    />
                </Content>
            )}
            {currTab === 3 && (
                <Content>
                    <EditRole data={currRole} cb={resetTab}/>
                </Content>
            )}
            
            
        </Drawer>
    )
}

const Header = (props:{
    themeUi:string,
    handleAction:(item:number)=>void,
    handleClose:()=>void
    activeTab: any;
    setActiveTab:any;
})=>{
    
    const {
        themeUi,
        handleAction,
        handleClose,
        activeTab,
        setActiveTab
    } = props


    return(
        <DrawerHeader 
            themeUi={themeUi}
        >
            <p>Roles</p>
            <div style={{flex:4}}>
                <NavigationTab 
                    listTabs={['View' , 'Add']} 
                    onClick={(item:number)=>(handleAction(item))}
                    activeTab ={activeTab}
                    setActiveTab={setActiveTab}
                />
            </div>
            <img 
                style={{cursor:'pointer',marginRight:'5px'}}
                onClick={handleClose}
                src="/assets/img/VectorFLOW/NMS/close-dark.svg"
                height={13}
                width={13}
            />
        </DrawerHeader>
    )
}

export default UserRolesDrawer