import { Dialog, Transition } from "@headlessui/react";
import { Fragment, useEffect, useState } from "react";
import "./styles.css";
import { useTranslation } from "react-i18next";
import { notifyError, notifySuccess, notifyWarning } from "../../../helpers/notify";
import { useRegisterUser, usePutEditUser } from "../../../services/profile";
import LoadingSpinner from "../LoadingSpinner";
import PrdPermissions from "../../../components/layouts/ProductPermission/common-mulselect";
import LcPermissions from "../../../components/layouts/LocationPermission/common-mulselect";
import UserMangementStepper from "../../VectorFLOW/commons/UserManagementStepper";
import { useGetDBRsettingsData } from '../../../VectorFlow/Services/MTO/Common/DBRSettings';
import {
  formDataPermission,
  handleSelectParent,
  handleSelectChild,
  handleSelectGrandChild
} from "./common-func";
import { useUserData } from "../../../context";
import _ from "lodash";
import { APPLICATION_NAMES } from "../../../helpers/constants";

const ModalAdvanedPermissions = (props: any) => {
  const { t } = useTranslation();
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;
  const [isMTOPermissionsRequired, setIsMTOPermissionsRequired] = useState(false);

  const {
    openModal,
    closeModal,
    contentModal,
    setIsOpenUser,
    setIsOpenAdvanced,
    infoUser,
    refetch,
    prdPermissionRef,
    lcPermissionRef,
    stepperDetails,
    activeApplication,
    setActiveApplication,
    allPermissions,
    updateAllPermissions,
    storePermission,
    setStorePermission,
    setStepperDetails,
    headers,
    isCheckBoxRef,
  } = props;

  const [isLoadSpinner, setIsLoadSpinner] = useState<any>(false);
  const { mutateAsync: mutateRegister } = useRegisterUser();
  const { mutateAsync: mutatePutEditUser } = usePutEditUser();  
  const {mutateAsync: getDBRsettingsData} = useGetDBRsettingsData();

  const getSettingsData = async () => {
    const DBRSettingsData: any = await getDBRsettingsData()
    const DBRSettings = DBRSettingsData.data?.data;
    setIsMTOPermissionsRequired(DBRSettings?.find((DBRSetting: any) => DBRSetting.flag === "isPermissionRequiredMTO")?.value == 1 ? true : false || false);
  };
  
  useEffect(() => {
    getSettingsData()
  }, []);
  
  const backModalUser = () => {
 
    //Reset Current Application Permissions
    const storePermissionCopy = [...storePermission]
    const currentPermission:any = storePermissionCopy.find((app:any)=>app.application_id === activeApplication);
    const currentProductPermission = prdPermissionRef.current?.getPrdPermissionValue();
    const currentLocationPermission = lcPermissionRef.current?.getLcPermissionValue();


    if(currentPermission){
      currentPermission.productPermission = currentProductPermission;
      currentPermission.locationPermission = currentLocationPermission;
      setStorePermission(storePermissionCopy)
    }

    if(getActiveApplicationIndex() <= 0){
      setIsOpenUser(true);
      setIsOpenAdvanced(false);
    }
    else{
      const newApplicationId = storePermission[getActiveApplicationIndex()-1].application_id;
      setStepperDetails([...stepperDetails.map((step:any)=>{
        const stepCopy = {...step};
        if(step.id === newApplicationId) stepCopy.currentState='active';
        if(step.id === activeApplication) stepCopy.currentState='pending';
        return stepCopy;
      })]);
      setActiveApplication(newApplicationId);
      updateAllPermissions(newApplicationId);
    } 
    
  };

  const isValidPermission = (storePermission: any[]): boolean => {
    if (!storePermission.some((permission) => permission.application_id === 1)) {
      return true;
    }
    return storePermission.some((permission) => 
      permission.application_id === 1 &&
      permission.productPermission?.brand?.length > 0 && 
      permission.locationPermission?.lcRegion?.length > 0
    );
  };

  const handleSubmit = () => {
    let product:any;
    let location:any;

    const productPermissions:any = [];
    const locationPermissions:any = [];

   let isValid = true;
    
    storePermission.forEach((app:any,index:number) => {
      if(!isValid) return;
      if(index===storePermission.length-1){
        product = prdPermissionRef.current?.getPrdPermissionValue();
        location = lcPermissionRef.current?.getLcPermissionValue();

        //Store Permissions
        const storePermissionCopy = [...storePermission]
        const currentPermission:any = storePermissionCopy.find((app:any)=>app.application_id === activeApplication);
        currentPermission.productPermission = product;
        currentPermission.locationPermission = location;
        if(!isValidPermission(storePermissionCopy)){
          isValid = false;
          notifyError(
            "Please select permission for the selected application!"
          );
          setIsLoadSpinner(false);
          return;
        }
        setStorePermission(storePermissionCopy)
      }
      else{
        product =
      // eslint-disable-next-line no-unsafe-optional-chaining
      app.productPermission

      location =
      // eslint-disable-next-line no-unsafe-optional-chaining
      app.locationPermission
      }


    
      
      const dataPrdPermission = formDataPermission({
        parent: product.brand,
        child: product.subBrand,
        grandChild: product.category,
        keyParent: "product_hierarchy_1",
        keyChild: "product_hierarchy_2",
        keyGrandChild: "product_hierarchy_3",
      });

     

      const dataLcPermission = formDataPermission({
        parent: location.lcRegion,
        child: location.lcType,
        grandChild: location.lcCluster,
        keyParent: "location_heirarchy_1",
        keyChild: "location_heirarchy_2",
        keyGrandChild: "location_heirarchy_3",
      });

      productPermissions.push({
        application_id:app.application_id,
        permissions:dataPrdPermission
      })
      locationPermissions.push({
        application_id:app.application_id,
        permissions:dataLcPermission
      })
  
    });

    if(!isValid)return;

    const application_names = [APPLICATION_NAMES.MTA, APPLICATION_NAMES.MTO];
    const applicationIds = storePermission
      .filter((dataAllPermission: any) => application_names.includes(dataAllPermission.application_name))
      .map((filterItem: any) => filterItem.application_id);
    
    if (!applicationIds.length) {
      notifyError(t("profile.tabContent.manageUsers.notifyError.RoleMismatch"));
      return;
    }

    //check if permissions are filled for MTA, have added check for MTA.
    const MTARole = storePermission.find((storePermission: any) => storePermission.application_name == APPLICATION_NAMES.MTA);
    const isProductPermission = productPermissions.find((productPermission: any) => productPermission.application_id == MTARole?.application_id)?.permissions;
    const isLocationPermission = locationPermissions.find((locationPermission: any) => locationPermission.application_id == MTARole?.application_id)?.permissions;
      
    if (MTARole && (!isProductPermission || !isLocationPermission)) {
      notifyError(
        t("profile.tabContent.manageUsers.notifyError.PleaseSelectPermissionMTA")
      );
      setIsLoadSpinner(false);
      return;
    }
    
    const MTORole = storePermission.find((storePermission: any) => storePermission.application_name == APPLICATION_NAMES.MTO);
    if (MTORole && isMTOPermissionsRequired) {
      const isMTOProductPermission = isMTOPermissionsRequired && productPermissions.find((productPermission: any) => productPermission.application_id == MTORole?.application_id)?.permissions;
      const isMTOLocationPermission = isMTOPermissionsRequired && locationPermissions.find((locationPermission: any) => locationPermission.application_id == MTORole?.application_id)?.permissions;

      if (!isMTOProductPermission || !isMTOLocationPermission) {
        notifyError(
          t("profile.tabContent.manageUsers.notifyError.PleaseSelectPermissionMTO")
        );
        setIsLoadSpinner(false);
        return;
      }
    }
      
      setIsLoadSpinner(true);
      const formData: any = {
        ...infoUser,
        tc: true,
        product_permissions: productPermissions || [],
        location_permissions: locationPermissions || [],
        // product_permissions: [],
        // location_permissions: []
      };

      formData.location_permissions.forEach((element:any) => {
        if(!element.permissions){
          element.permissions = []
        }
      })
      formData.product_permissions.forEach((element:any) => {
        if(!element.permissions){
          element.permissions = [];
        }
      })

      if (contentModal.callApi === 1 ) {
        mutateRegister(formData, {
          onSuccess: (res: any) => {
            setIsLoadSpinner(false);
            if (res?.status === 400) {
              res?.response?.email?.forEach((element: any) => {
                notifyError(element);
              });
              res?.response?.name?.forEach((element: any) => {
                notifyError(element);
              });
              
              res?.response?.msg &&  notifyError(res?.response?.msg);
              res?.response?.password?.forEach((element: any) => {
                notifyError(element);
              });
            } else {
              notifySuccess(res?.data?.msg || res?.data?.msg?.message);
              if (res?.data?.msg.warning) {
                notifyWarning(res?.data?.msg.warning);
              }
              setStorePermission([]);
              closeModal();
              refetch();
            }
          },
          onError: (error: any) => {
            setIsLoadSpinner(false);
            error.response?.email?.forEach((element: any) => {
              notifyError(element);
            });
            error.response?.name?.forEach((element: any) => {
              notifyError(element);
            });
            error?.response?.password?.forEach((element: any) => {
              notifyError(element);
            });
          },
        });
      } else if (contentModal.callApi === 2) {
        mutatePutEditUser(formData, {
          onSuccess: (res: any) => {
            setIsLoadSpinner(false);
            if (res?.status === 400) {
              if(typeof res?.response?.msg === 'object' && Array.isArray(res?.response?.msg)) {
                res?.response?.msg?.forEach((element: any) => {
                  notifyError(element);
                });
              } else if (typeof res?.response?.msg === 'string') {
                notifyError(res?.response?.msg);
              }
              res?.response?.name?.forEach((element: any) => {
                notifyError(element);
              });
            } else {
              notifySuccess(res?.data?.msg);
              refetch();
              closeModal();
            }
          },
          onError: (error: any) => {
            console.log("error", error);
            setIsLoadSpinner(false);
            error.response?.msg?.forEach((element: any) => {
              notifyError(element);
            });
            error.response?.name?.forEach((element: any) => {
              notifyError(element);
            });
          },
        });
      }
  };

  const saveAndGoToNext = () => {
    const storePermissionCopy = [...storePermission]
    const currentPermission:any = storePermissionCopy.find((app:any)=>app.application_id === activeApplication);
    const currentProductPermission = prdPermissionRef.current?.getPrdPermissionValue();
    const currentLocationPermission = lcPermissionRef.current?.getLcPermissionValue();



    if(currentProductPermission.brand === undefined || currentLocationPermission.lcRegion === undefined) return notifyError(
      t("profile.tabContent.manageUsers.notifyError.PleaseSelectPermission")
    );


    if(currentPermission){
      currentPermission.productPermission = currentProductPermission;
      currentPermission.locationPermission = currentLocationPermission;
      setStorePermission(storePermissionCopy)
    }
    
    const newApplicationId = storePermission[getActiveApplicationIndex()+1].application_id;
    setStepperDetails([...stepperDetails.map((step:any)=>{
      const stepCopy = {...step};
      if(step.id === newApplicationId) stepCopy.currentState='active';
      if(step.id === activeApplication) stepCopy.currentState='completed';
      return stepCopy;
    })]);
    setActiveApplication(newApplicationId);
    updateAllPermissions(newApplicationId);
    
  }


  const getCurrentProductPermission = ()=>{
    if(storePermission?.length > 0) return _.cloneDeep(storePermission?.find((app:any)=>app.application_id === activeApplication)?.productPermission);
    return {};
  }

  const getCurrentLocationPermission = ()=>{
    if(storePermission?.length > 0) return {...storePermission?.find((app:any)=>app.application_id === activeApplication)?.locationPermission};
    return {};
  }

  const getActiveApplicationIndex = ()=>{
    return storePermission?.findIndex((app:any)=>app.application_id === activeApplication);
  }



  return (
    <>
      {
        <Transition appear show={openModal} as={Fragment}>
          <Dialog as="div" className="modal-box" onClose={closeModal}>
            <Transition.Child
              as={Fragment}
              enter="transition"
              enterFrom="opa-0"
              enterTo="opa"
              leave="leave-modal"
              leaveFrom="opa"
              leaveTo="opa-0"
            >
              <div className="modal-bg inset" />
            </Transition.Child>

            <div className="modal-content">
              <div className="modal-content--box">
                <Transition.Child
                  as={Fragment}
                  enter="transition"
                  enterFrom="opa-0 tranlate "
                  enterTo="opa translate-y-0 "
                  leave="leave-modal"
                  leaveFrom="opa translate-y-0"
                  leaveTo="opacity-0 tranlate"
                >
                  <Dialog.Panel className="modal-forced--block">
                    <Dialog.Title as="h3" className="modal-user-title">
                      <span className="modal-title--left">
                        <img
                          src="/assets/img/ist/avatar_contact.png"
                          className="modal-img-user"
                          alt="user"
                        />
                        {t(
                          "profile.tabContent.manageUsers.advancedPermission.title"
                        )}
                      </span>
                      <span onClick={()=>{setIsOpenUser(false);setIsOpenAdvanced(false);setStorePermission([]);}} className="close-forced">
                        x
                      </span>
                    </Dialog.Title>
                    <div className="advanced-permission-container">
                      {stepperDetails?.length > 1 && 
                        (<div style={{margin:'20px',minWidth:'500px'}}>
                          <UserMangementStepper
                            list={stepperDetails}
                            // activeStep={getActiveApplicationIndex()}
                            themeUi={themeUi}
                          />
                        </div>)
                      }

                      
                      <PrdPermissions
                        ref={prdPermissionRef}
                        product={allPermissions?.product_permission}
                        valueSelectPrd={getCurrentProductPermission()}
                        handleSelectParent={handleSelectParent}
                        handleSelectChild={handleSelectChild}
                        headers={ headers && headers[activeApplication] }
                        handleSelectGrandChild={handleSelectGrandChild}
                        isCheckBoxRef={isCheckBoxRef}
                        activeApplicationId={activeApplication}
                      />
                      <LcPermissions
                        ref={lcPermissionRef}
                        location={allPermissions?.location_permission}
                        valueSelectLc={getCurrentLocationPermission()}
                        handleSelectParent={handleSelectParent}
                        handleSelectChild={handleSelectChild}
                        handleSelectGrandChild={handleSelectGrandChild}
                        headers={ headers && headers[activeApplication] }
                        isCheckBoxRef={isCheckBoxRef}
                        activeApplicationId={activeApplication}
                      />

                      <div className="modal-bottom upper-line">
                        {
                          getActiveApplicationIndex() === storePermission?.length-1 ? 
                          (
                            <button
                              type="button"
                              className={`btn_submit ${themeUi} ${
                                isLoadSpinner ? "btn-disabled" : ""
                              }`}
                              onClick={handleSubmit}
                              disabled={isLoadSpinner}
                            >
                              {contentModal.buttonSubmit}
                            </button>) : 
                          (<button
                            type="button"
                            className={`btn_submit ${themeUi} ${
                              isLoadSpinner ? "btn-disabled" : ""
                            }`}
                            onClick={saveAndGoToNext}
                            disabled={isLoadSpinner}
                            style={{width:'190px'}}
                          >
                            {"Save & Go To Next"}
                          </button>)
                        }
                        
                        <button
                          type="button"
                          className="btn_cancel"
                          disabled={isLoadSpinner}
                          onClick={backModalUser}
                        >
                          {t("profile.tabContent.manageUsers.button.goBack")}
                        </button>
                      </div>
                    </div>
                  </Dialog.Panel>
                </Transition.Child>
              </div>
            </div>
          </Dialog>
        </Transition>
      }

      {isLoadSpinner && <LoadingSpinner />}
    </>
  );
};

export default ModalAdvanedPermissions;
