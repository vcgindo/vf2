import { useRef, useState,useEffect } from "react";
import {
  SCProfileOverView,
  SCSubTitleBox,
  SCSubTitlePad,
  SCSubTitleSpan,
  SCSubTitlePadItem,
  SCItemBtn,
} from "./styles";
import {
  ButtonFloat,
  TableUserManagement,
  ModalManageUsers,
  ModalAdvanedPermissions,
  ButtonOutlineIcon,
} from "../../../components/index";
import {
  useGetAllRoles,
  useGetAllUsers,
  useGetAllPermissions,
  useGetHeadersData,
  useGetUserPermissions
} from "../../../services/profile";
import Spinner from "../../../components/commons/Spinner";
import { useTranslation } from "react-i18next";
// import { dataListRoles } from "./listRoles";
import { generateRolesObject } from '../../../helpers/utils';
import _ from 'lodash'
import { useNavigate } from "react-router";
import { notifyError } from "../../../helpers/notify";
import { APPLICATION_NAMES } from "../../../helpers/constants";
import { useUserData } from "../../../context";


interface ManageUsersProps{
  is_admin:boolean
  permission:Array<any>
  themeUi:string
  // isRolesDrawerOpen:boolean
  // isURLsDrawerOpen:boolean
  // toggleRolesDrawer:(v:boolean)=>void
  // toggleURLsDrawer:(v:boolean)=>void
}

const ManageUsers = ({ is_admin, permission, themeUi }: ManageUsersProps) => {
  const { t } = useTranslation();
  const [contentModal, setContentModal] = useState({
    callApi: 0,
    title: "",
    buttonSubmit: "",
  });

  const [listRoles, setListRoles] = useState<any>([]);
  const [isOpenUser, setIsOpenUser] = useState(false);
  const [isOpenAdvanced, setIsOpenAdvanced] = useState(false);
  const [infoUser, setInfoUser] = useState<any>({
    name: "",
    email: "",
    roles: [],
  });

  const [valueSelect, setvalueSelect] = useState<any>();

  const prdPermissionRef = useRef<any>();
  const lcPermissionRef = useRef<any>();

  const { data: dataFetch, refetch, isFetching } = useGetAllUsers();
  const { data: dataPermissions } = useGetAllPermissions();
  const { mutateAsync : usegetHeaderData } = useGetHeadersData();
  const [headers , setHeaders] = useState<any>();

  const { mutateAsync: getUserPermissions,isLoading:edit } = useGetUserPermissions();
  
  useGetAllRoles((data:any)=>{
    const dataAllRoles = data.data ? generateRolesObject(data.data) : [];
    setListRoles(dataAllRoles);
  });
  
  const getHeaderDatafunct = async() =>{
    const reponse = await usegetHeaderData();
    setHeaders(reponse.data);
  }
  useEffect(() => {
    getHeaderDatafunct();
  },[])
  const dataAllPermissions = dataPermissions?.data;

  const dataAllUsers = dataFetch?.data;

  const [stepperDetails,setStepperDetails] = useState();
  const [activeApplication,setActiveApplication] = useState<number>(0);
  const [allPermissions,setAllPermissions] = useState<any>([]);
  const [storePermission,setStorePermission] = useState([]);
  const [currentItem,setCurrentItem] = useState();
  const [isEditUser,setIsEditUser] = useState<boolean | undefined>()

  const {user} = useUserData()
  const feature_permission = user?.feature_permission || [];
  const bulkUploadEnabled = feature_permission.includes("Bulk_upload");

  const isCheckBoxRef = useRef<any>({
    isPrdCheck: {},
    isLcCheck: {},
  });
  
  //Follwing Function Updates All Permissions according to current active Application/Application Id provided
  const updateAllPermissions = (applicationId:number) => {
    setAllPermissions(dataAllPermissions.find((app:any)=>app.application_id===applicationId))
  }

  const getApplicationIds = () => {
    const application_names = [APPLICATION_NAMES.MTA, APPLICATION_NAMES.MTO];
    const applicationIds = dataAllPermissions
      .filter((dataAllPermission: any) => application_names.includes(dataAllPermission.application_name))
      .map((filterItem: any) => filterItem.application_id);
    return applicationIds;
  }

  const handleClickAddNewUser = () => {
    if (!getApplicationIds().length) {
      notifyError(t("profile.tabContent.manageUsers.notifyError.RoleMismatch"))
      return;
    }
    setvalueSelect({});
    setInfoUser({
      name: "",
      email: "",
      roles: [],
      edit:false
    });
    setContentModal({
      callApi: 1,
      title: t("profile.tabContent.manageUsers.modal.addNewTitle"),
      buttonSubmit: "Add User",
    });
    setIsOpenUser(true);
    setIsEditUser(false)
    setStorePermission([]);
    isCheckBoxRef.current.isPrdCheck = {},
    isCheckBoxRef.current.isLcCheck = {}
  };
  
  const onCloseModal = () => {
    setIsOpenUser(false);
  };

  const onCloseModalAdvanced = () => {
    setIsOpenAdvanced(false);
  };


  const getPermission = ({ data, txtParent, txtChild, txtGrandChild }: any) => {
    const parent: any = [];
    const child: any = [];
    const grandChild: any = [];
    const checkAddParent: any = [];
    const checkAddChild: any = [];
    const checkAddGrandChild: any = [];

    data.forEach((item: any) => {
      const valueParent = item[txtParent];
      const valueChild = `${valueParent} > ${item[txtChild]}`;
      const valueGrandChild = `${valueChild} > ${item[txtGrandChild]}`;

      if (!checkAddParent?.includes(valueParent) && valueParent?.length > 0) {
        checkAddParent.push(valueParent);
        parent.push({ label: valueParent, value: valueParent });
      }

      if (!checkAddChild?.includes(valueChild) && txtChild in item) {
        checkAddChild.push(valueChild);
        child.push({ label: valueChild, value: valueChild });
      }

      if (!checkAddGrandChild?.includes(valueGrandChild) && txtGrandChild in item) {
        checkAddGrandChild.push(valueGrandChild);
        grandChild.push({ label: valueGrandChild, value: valueGrandChild });
      }
    });

    return {
      parent,
      child,
      grandChild,
      checkAddParent,
      checkAddChild,
      checkAddGrandChild,
    };
  };

  const fillAdvancedPermissionsModalData = (item?:any)=>{
    //Application Ids with valid Selected Roles
    const prevPremission = storePermission

    const validApplications:Array<number> = [];
    listRoles.forEach((app:any)=>{
      const commonRoles = _.intersection(app.child.map((perm:any)=>perm.id),infoUser.roles);
      if(commonRoles.length > 0) validApplications.push(app.id);
    });
    validApplications.sort((a:number,b:number)=>a-b);
    
    
    if(contentModal.callApi === 1){

      const fillStepperDetails = dataAllPermissions.map((app:any,index:number)=>validApplications.includes(app.application_id) ? ({
        label:app.application_name,
        id:app.application_id,
        currentState:'pending',
        isLast:index===dataAllPermissions.length-1,
        themeUi:themeUi
      }) : undefined).filter((element:any) => element !== undefined);
      fillStepperDetails.sort((a:any,b:any)=>a.id-b.id)
      fillStepperDetails && fillStepperDetails[0] &&  (fillStepperDetails[0].currentState = 'active');
      
      const fillEmptyPermission = dataAllPermissions.map((app:any)=>validApplications.includes(app.application_id) ? ({
        application_id:app.application_id,
        application_name:app.application_name,
        productPermission:[],
        locationPermission:[]
      }) : undefined).filter((element:any) => element !== undefined)
  
      fillEmptyPermission.sort((a:any,b:any)=>a.application_id-b.application_id);
      
      const prevValidApplications = prevPremission.map((perm: any) => perm.application_id).sort((a: number, b: number) => a - b);
      const isValidApplicationChanged = !_.isEqual(prevValidApplications, validApplications);
     
      if(prevPremission.length > 0 && !isValidApplicationChanged){
        setStorePermission(prevPremission);
      }else{

        setStorePermission(fillEmptyPermission);
      }
      setStepperDetails(fillStepperDetails);
      setActiveApplication(validApplications[0]);
      updateAllPermissions(validApplications[0]);
    }
    if(contentModal.callApi === 2){
      const productPermissionAllApp:any = [];
      const locationPermissionAllApp:any = [];

      item?.product_id.forEach((app:any)=>{
        const getProductPermissions = getPermission({
          data: app.permissions,
          txtParent: "product_hierarchy_1",
          txtChild: "product_hierarchy_2",
          txtGrandChild: "product_hierarchy_3",
        });

        const productPermission = {
          brand: getProductPermissions.parent,
          subBrand: getProductPermissions.child,
          category: getProductPermissions?.grandChild,
          checkAddBrand: getProductPermissions?.checkAddParent,
          checkAddSubBrand: getProductPermissions.checkAddChild,
          checkAddCategory: getProductPermissions.checkAddGrandChild,
        };

        productPermissionAllApp.push({
          'application_id':app.application_id,
          'application_name':app.application_name,
          'productPermission':productPermission
        })
      })

      item?.location_id.forEach((app:any)=>{
        const getLocationPermissions = getPermission({
          data: app.permissions,
          txtParent: "location_heirarchy_1",
          txtChild: "location_heirarchy_2",
          txtGrandChild: "location_heirarchy_3",
        });

        const locationPermission = {
          lcRegion: getLocationPermissions.parent,
          lcType: getLocationPermissions.child,
          lcCluster: getLocationPermissions.grandChild,
          checkAddLcRegion: getLocationPermissions.checkAddParent,
          checkAddLcType: getLocationPermissions.checkAddChild,
          checkAddLcCluster: getLocationPermissions.checkAddGrandChild,
        };

        locationPermissionAllApp.push({
          'application_id':app?.application_id,
          'application_name':app?.application_name,
          'locationPermission':locationPermission
        })

    })

    const initialPermissions = productPermissionAllApp?.map((prodApp:any)=>{
      const coLocationPermission = locationPermissionAllApp?.find((locApp:any)=>prodApp.application_id === locApp.application_id);
      if(coLocationPermission){
        return {
          ...prodApp,
          locationPermission:coLocationPermission.locationPermission
        }
      }
      return {...prodApp}
    })

    //Enable Product Permissions of Applications With Selected Roles
    const newStepperDetails:any = validApplications?.map((valid_id:any,index:number)=>{
      //Find if Application Permission Already Exist
      const oldPermissions = initialPermissions?.find((app:any)=>app?.application_id === valid_id);
      if(oldPermissions){
        return {
          label:oldPermissions.application_name,
          id:valid_id,
          currentState:'pending',
          isLast:index===initialPermissions.length-1,
          themeUi:themeUi
        }
      }
      else{
        return {
          label:dataAllPermissions.find((app:any)=>app.application_id === valid_id)?.application_name,
          id:valid_id,
          currentState:'pending',
          isLast:index===initialPermissions.length-1,
          themeUi:themeUi
        }
      }
    })
    newStepperDetails.sort((a:any,b:any)=>a.id-b.id)
    newStepperDetails[0].currentState = 'active';
    setStepperDetails(newStepperDetails);

    //Set Permissions For Selected Applications

    const validApplicationPermissions:any = validApplications?.map((id:any)=>{
      //Find if Application Permission Already Exist
      const oldPermissions = initialPermissions.find((app:any)=>app.application_id === id);
      if(oldPermissions){
        return _.cloneDeep(oldPermissions)
      }
      else{
        return {
          application_id: id,
          application_name: listRoles.find((app:any) => app.id === id)?.title || "",
          productPermission:[],
          locationPermission:[]
        }
      }
    })
    validApplicationPermissions.sort((a:any,b:any)=>a.id-b.id);
    setStorePermission(validApplicationPermissions);

    setvalueSelect(_.cloneDeep(validApplicationPermissions));

    setActiveApplication(validApplicationPermissions[0].application_id)

    updateAllPermissions(validApplicationPermissions[0].application_id)
    }
  }


  const handleClickEdit = async(initialItem: any) => {
    const applicationIds = getApplicationIds();
    if (!applicationIds.length) {
      notifyError(t("profile.tabContent.manageUsers.notifyError.RoleMismatch"));
      return;
    }
    const response = await getUserPermissions(initialItem.id);
    const item = {...initialItem, ...response.data? response.data: {}}
    setCurrentItem(item)
    setIsEditUser(true)
    const roles = item.role_id.map((role: any) => role.id);

    setInfoUser({
      id: item.id,
      name: item.name,
      email: item.email,
      roles: roles,
      edit: true
    });

    setContentModal({
      callApi: 2,
      title: t("profile.tabContent.manageUsers.modal.editUserTitle"),
      buttonSubmit: "Update User",
    });

    const isPRDCheck: any = {};
    const isLcCheck: any = {};

    const findPermissionLength = (array: any, appId: any) =>
      array.find((entry: any) => entry.application_id === appId)?.permissions?.length;

    const findPermissionAllLength = (array: any, appId: any, key: any) =>
      array.find((entry: any) => entry.application_id === appId)?.[key]?.length;

    applicationIds.forEach((applicationId: any) => {

      const productPermission = findPermissionLength(item.product_id, applicationId);
      const locationPermission = findPermissionLength(item.location_id, applicationId);

      const productPermissionAll = findPermissionAllLength(dataAllPermissions, applicationId, 'product_permission_ids');
      const locationPermissionAll = findPermissionAllLength(dataAllPermissions, applicationId, 'location_permission_ids');

      isPRDCheck[applicationId] = productPermission === productPermissionAll;
      isLcCheck[applicationId] = locationPermission === locationPermissionAll;

    });

    isCheckBoxRef.current.isPrdCheck = isPRDCheck;
    isCheckBoxRef.current.isLcCheck = isLcCheck;

    setIsOpenUser(true);
  }


  const navigate = useNavigate()
  const handleClickBulkUpload = ()=>{
    navigate("/profile/bulk-upload")
  }
  

  return (
    <>
    {edit && (
  <div
    style={{
      position: "fixed",
      top: 0,
      left: 0,
      width: "100%",
      height: "100%",
      background: "rgba(255, 255, 255, 0.6)", 
      backdropFilter: "blur(3px)",            
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      zIndex: 2000,                           
    }}
  >
    <Spinner />
  </div>
)}
      <SCProfileOverView>
        <SCSubTitleBox>
          <SCSubTitlePad>
            <SCSubTitleSpan>
              {t("profile.tabContent.manageUsers.title")}
            </SCSubTitleSpan>
            <SCSubTitlePadItem>              
              <SCItemBtn>
                <ButtonFloat
                  text={t("profile.tabContent.manageUsers.button.addNewUser")}
                  onClick={handleClickAddNewUser}
                  icon="/assets/img/profile/icon_plus.svg"
                />
              </SCItemBtn>
             
             {
              bulkUploadEnabled &&

                <SCItemBtn>
                  <ButtonOutlineIcon
                    text={t("profile.tabContent.manageUsers.button.bulkUpload")}
                    icon={`/assets/img/profile/${
                      themeUi === "REGALBLAZE"
                        ? "icon_upload_yellow"
                        : "icon_upload"
                        }.svg`}
                        disabled={false}
                        onClick={handleClickBulkUpload}
                        />
                </SCItemBtn>
                      }
            
            </SCSubTitlePadItem>
          </SCSubTitlePad>
        </SCSubTitleBox>

        {isFetching ? (
          <Spinner />
        ) : (
          <TableUserManagement
            dataAllUsers={dataAllUsers}
            handleClickEdit={handleClickEdit}
            refetch={refetch}
            is_admin={is_admin}
            permission={permission}
          />
        )}
      </SCProfileOverView>

      {/* {isURLsDrawerOpen && (
        <UserURLsDrawer
        onClose={()=>toggleURLsDrawer(false)}
        />
        )}
        
        {isRolesDrawerOpen && (
          <UserRolesDrawer
          onClose={()=>toggleRolesDrawer(false)}
          />
        )} */}


      <ModalManageUsers
        contentModal={contentModal}
        openModal={isOpenUser}
        closeModal={onCloseModal}
        setIsOpenAdvanced={setIsOpenAdvanced}
        infoUser={infoUser}
        setInfoUser={setInfoUser}
        listRoles={listRoles}
        setListRoles={setListRoles}
        fillAdvancedPermissionsModalData={fillAdvancedPermissionsModalData}
        currentItem={currentItem}
        isEditUser={isEditUser}
        setIsEditUser={setIsEditUser}
        />

      <ModalAdvanedPermissions
        contentModal={contentModal}
        openModal={isOpenAdvanced}
        closeModal={onCloseModalAdvanced}
        setIsOpenUser={setIsOpenUser}
        setIsOpenAdvanced={setIsOpenAdvanced}
        prdPermissionRef={prdPermissionRef}
        lcPermissionRef={lcPermissionRef}
        infoUser={infoUser}
        refetch={refetch}
        dataAllPermissions={dataAllPermissions}
        valueSelect={valueSelect}
        stepperDetails={stepperDetails}
        activeApplication={activeApplication}
        setActiveApplication={setActiveApplication}
        allPermissions={allPermissions}
        updateAllPermissions={updateAllPermissions}
        storePermission={storePermission}
        setStorePermission={setStorePermission}
        setStepperDetails={setStepperDetails}
        headers = {headers}
        isCheckBoxRef={isCheckBoxRef}
        />


        
      
    </>
  );
};

export default ManageUsers;
