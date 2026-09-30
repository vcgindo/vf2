import { forwardRef, useEffect, useImperativeHandle, useState } from "react";
import LocationPermission from "./index";
import { useTranslation } from "react-i18next";
import { useSelector } from "react-redux";
import { RootState } from "../../../redux/store/store";

export default forwardRef(({ ...props }: any, ref) => {
  const { t } = useTranslation();
  const {
    location,
    valueSelectLc,
    handleSelectParent,
    handleSelectChild,
    handleSelectGrandChild,
    headers,
    isCheckBoxRef,
    activeApplicationId,
  } = props;

  const [listLcRegion, setListLcRegion] = useState<any>([]);
  const [listLcType, setListLcType] = useState<any>([]);
  const [listLcCluster, setListLcCluster] = useState<any>([]);

  const [lcRegion, setLcRegion] = useState<any>([]); 
  const [lcType, setLcType] = useState<any>([]);
  const [lcCluster, setLcCluster] = useState<any>([]);
  const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
  const LOCATION_PERMISSION_L1 = EnvConfig['LOCATION_PERMISSION_L1']; 
  const LOCATION_PERMISSION_L2 = EnvConfig['LOCATION_PERMISSION_L2']; 
  const LOCATION_PERMISSION_L3 = EnvConfig['LOCATION_PERMISSION_L3']; 

  useEffect(() => {
    const newListLcRegion: any = [];
    const newListLcType: any = [];
    const newListLcCluster: any = [];

    location && Object.keys(location)?.forEach((keyLcRegion: any) => {
      const dataLcRegion = { label: keyLcRegion, value: keyLcRegion };
      newListLcRegion.push(dataLcRegion);

      Object.keys(location[keyLcRegion])?.forEach((keyLcType: any) => {
        const valueLcType = `${keyLcRegion} > ${keyLcType}`;
       
          const dataLcType = {
            label: valueLcType,
            value: valueLcType,
          };

          newListLcType.push(dataLcType);
        

        location[keyLcRegion][keyLcType]?.forEach((eleLcCluster: any) => {
          const valueLcCluster = `${valueLcType} > ${eleLcCluster['location_heirarchy_3']}`;
          
            const dataLcCluster = {
              label: valueLcCluster,
              value: valueLcCluster,
            };
            newListLcCluster.push(dataLcCluster);
        });
      });
    });

    setListLcRegion(newListLcRegion);
    setListLcType(newListLcType);
    setListLcCluster(newListLcCluster);

   
    setLcRegion(valueSelectLc?.lcRegion || []);
    setLcType(valueSelectLc?.lcType || []);
    setLcCluster(valueSelectLc?.lcCluster || []);
  }, [valueSelectLc]);

  // Handle region selection
  const handleSelectLcRegion = (e: any) => {
    setLcRegion(e);
    setLcType([]); 
    setLcCluster([]); 

    handleSelectParent({
      e,
      dataAll: location,
      child: lcType,
      grandChild: lcCluster,
      setChild: setLcType,
      setGrandChild: setLcCluster,
    });
  };

  // Handle type selection
  const handleSelectLcType = (e: any) => {
    setLcType(e);
    setLcCluster([]); 

    handleSelectChild({
      e,
      grandChild: lcCluster,
      valueParent: lcRegion,
      setParent: setLcRegion,
      setGrandChild: setLcCluster,
    });
  };

  // Handle cluster selection
  const handleSelectLcCluster = (e: any) => {
    setLcCluster(e);
    handleSelectGrandChild({
      e,
      valueParent: lcRegion,
      setParent: setLcRegion,
      valueChild: lcType,
      setChild: setLcType,
    });
  };
  const onSelectAll = (event: React.ChangeEvent<HTMLInputElement>) =>{
    const check = event.target.checked;
    if(isCheckBoxRef?.current?.isLcCheck){
      isCheckBoxRef.current.isLcCheck[activeApplicationId] = check;
    }
    if(check){
      setLcType(listLcType)
      setLcRegion(listLcRegion)
      setLcCluster(listLcCluster)
    }
    else{
      setLcType([])
      setLcRegion([])
      setLcCluster([])
    }    
  }
  useImperativeHandle(ref, () => ({
    getLcPermissionValue() {
      return getLcPermissionValue();
    },
    removeLcPermissionValue() {
      removeLcPermissionValue();
    },
  }));

  const removeLcPermissionValue = () => {
    setLcRegion([]);
    setLcType([]);
    setLcCluster([]);
  };

  const getLcPermissionValue = () => {
    return {
      lcRegion,
      lcType,
      lcCluster,
    };
  };
 
  const prdPermissions = [
    {
      title: LOCATION_PERMISSION_L1 || '',
      placeholder: "",
      options: listLcRegion,
      value: lcRegion,
      setValue: setLcRegion,
      handleAction: handleSelectLcRegion,
      disabled: false,
      isCheckBoxRef,
      from:"isLcCheck",
      activeApplicationId,
    },
    {
      title: LOCATION_PERMISSION_L2 || '',
      placeholder: "",
      options: lcRegion.length === 0 ? [] : listLcType.filter((type: any) =>
        lcRegion.some((region: any) => type.value.split(" > ")[0] == region.value) // Filter lcType based on selected lcRegion
      ),
      value: lcType,
      setValue: setLcType,
      handleAction: handleSelectLcType,
      disabled: lcRegion.length === 0, 
      isCheckBoxRef,
      from:"isLcCheck",
      activeApplicationId,
    },
    {
      title: LOCATION_PERMISSION_L3 || '',
      placeholder: "", 
      options: lcType.length === 0 ? [] : (() => {    
        const currentLcTypeValues = lcType.map((type:any) => type.value); 
        const filteredClusters = listLcCluster.filter((cluster: any) => {
          const splitValue = cluster.value.split(" > ").slice(0, 3);
          const exactMatchValue = splitValue[0] + " > " + splitValue[1];
          return currentLcTypeValues.includes(exactMatchValue);
        });    
        return filteredClusters;
      })(),
      value: lcCluster,
      setValue: setLcCluster,
      handleAction: handleSelectLcCluster,
      disabled: lcType.length === 0, 
      isCheckBoxRef,
      from:"isLcCheck",
      activeApplicationId,
    }

   
    // {
    //   title: "P-L4",
    //   placeholder: "",
    //   options: [],
    //   value: select,
    //   setValue: setSelect,
    //   handleAction: () => {
    //     return;
    //   },
    //   disabled: false,
    // },
    // {
    //   title: "P-L5",
    //   placeholder: "",
    //   options: [],
    //   value: select,
    //   setValue: setSelect,
    //   handleAction: () => {
    //     return;
    //   },
    //   disabled: false,
    // },
  ];
  const updatedPermissions =  prdPermissions.map((permission:any,index:any)=>({
    ...permission,
    title: headers && headers?.Location &&  headers?.Location[index] ? (headers.Location[index]): permission.title
  })) 
  return (
    <LocationPermission
      title={headers && Object.keys(headers).length > 0 ? Object.keys(headers)[1] + " Permissions" : t(
        "profile.tabContent.manageUsers.advancedPermission.locationPermission.title"
      )}
      prdPermissions={updatedPermissions}
      onSelectAll={onSelectAll}
      isSelected={isCheckBoxRef?.current?.isLcCheck[activeApplicationId]}
    />
  );
});
