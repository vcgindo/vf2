import Drawer from "../../commons/Drawer"
import { Content,DrawerHeader} from "../UserURLsDrawer/styles"
import { useUserData } from "../../../context"
import { useState } from "react"
import NavigationTab from "../NavigationTab"
import ViewUiMDMConfig from "./View"
import EditUIMDMConfig from "./Edit"

interface UIMDMConfigDrawerProps{
    onClose:()=>void
}

const UIMDMConfigDrawer = (props:UIMDMConfigDrawerProps)=>{

    const {
        onClose
    } = props

    const {user} = useUserData()

    const themeUi = user.user.theme_ui


    const [currTab,setCurrTab] = useState<number>(0)

    const [currUIMDMConfig,setCurrUIMDMConfig] = useState<any>(null)

    const [activeTab, setActiveTab] = useState(0);

    const [savedFilters, setSavedFilters] = useState<any>(null);


    const onEditRole = (row:any)=>{
        setCurrTab(3); 
        setCurrUIMDMConfig(row)
    }


    const resetTab = ()=>{
        setCurrTab(0)
        setCurrUIMDMConfig(null)
        setActiveTab(0);
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
            
            
       
            {currTab === 0 && (
                <Content>
                    <ViewUiMDMConfig
                        onEdit={onEditRole}
                        savedFilters={savedFilters}
                        onSaveFilters={setSavedFilters}
                    />
                </Content>
            )}          
            {currTab === 3 && (
                <Content>
                    <EditUIMDMConfig data={currUIMDMConfig} cb={resetTab}/>
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
            <p>UI MDM Config</p>
            <div style={{flex:4}}>
                <NavigationTab 
                    listTabs={['View']} 
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

export default UIMDMConfigDrawer