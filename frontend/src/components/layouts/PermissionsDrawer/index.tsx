// File: ../../PermissionsDrawer.tsx
import Drawer from "../../commons/Drawer"
import { Content,DrawerHeader} from "../UserURLsDrawer/styles"
import { useUserData } from "../../../context"
import { useState } from "react"
import NavigationTab from "../NavigationTab"
import ViewPermissions from "./View"
import AddProductPermission from "./AddProductPermission"
import Select from 'react-select'
import AddLocationPermission from "./AddLocationPermission"

interface PermissionsDrawerProps{
    onClose:()=>void
}

const PermissionsDrawer = (props:PermissionsDrawerProps)=>{
    const { onClose } = props
    const {user} = useUserData()
    const themeUi = user.user.theme_ui
    const [currTab,setCurrTab] = useState<number>(0)
    const [activeTab, setActiveTab] = useState(0);

    const [permissionType, setPermissionType] = useState('Product_Permissions');

    const resetTab = ()=>{
        setCurrTab(0)
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
                // Pass the state setter to the Header component
                setPermissionType={setPermissionType}
            />}
            onClose={onClose}
        >
            {currTab === 1 && (
                <Content>
                    {permissionType === "Product_Permissions" ?<AddProductPermission cb={resetTab}/> : <AddLocationPermission cb={resetTab}/>}
                </Content>
            )}
        
            {currTab === 0 && (
                <Content>
                    <ViewPermissions
                        permissionType={permissionType}
                    />
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
    setPermissionType:(type:string)=>void;
})=>{
    const {
        themeUi,
        handleAction,
        handleClose,
        activeTab,
        setActiveTab,
        setPermissionType
    } = props

    const permissionOptions = [
        { label: "Product Permissions", value: "Product_Permissions" },
        { label: "Location Permissions", value: "Location_Permissions" },
    ];
    
    const [selectedPermission, setSelectedPermission] = useState(permissionOptions[0]);

    const handlePermissionChange = (selectedOption: any) => {
        setSelectedPermission(selectedOption);
        setPermissionType(selectedOption.value);
    };


    return(
        <DrawerHeader 
            themeUi={themeUi}
            style={{ display: 'flex', alignItems: 'center', padding: '10px 15px' }}
        >
              <Select
          options={permissionOptions}
          placeholder={"Select Application"}
          onChange={handlePermissionChange}
          styles={{
            option: (baseStyles, { isSelected }) => ({
              ...baseStyles,
              fontSize: 11,
              backgroundColor: isSelected
                ? themeUi === "REGALBLAZE"
                  ? "#FCA311"
                  : "#BC3D80"
                : "white",

              "&:hover": {
                backgroundColor:
                  themeUi === "REGALBLAZE"
                    ? "rgb(252, 163, 17,0.3) "
                    : "#bc3d814d",
                color: "black",
              },
            }),
            control: (baseStyles, { isFocused }) => ({
              ...baseStyles,
              fontSize: 12,
              borderColor: !isFocused ? "transparent" : "#BC3D80",
              borderWidth: 2,
              boxShadow: "none",
              backgroundColor: "rgb(247, 247, 247)",
              "&:hover": {
                borderColor: "#BC3D80",
              },
            }),
          }}
          defaultValue={permissionOptions[0]}
          value={selectedPermission}
        />
            <div style={{flex:4, marginLeft: '15px'}}>
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

export default PermissionsDrawer