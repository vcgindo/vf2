import { forwardRef, useEffect, useImperativeHandle, useState } from "react";
import ProductPermission from "./index";
import { useTranslation } from "react-i18next";
import { useSelector } from "react-redux";
import { RootState } from "../../../redux/store/store";

type Option = {
  label: string;
  value: string;
};

export default forwardRef(({ ...props }: any, ref) => {
  const { t } = useTranslation();
  const {
    product,
    valueSelectPrd,
    handleSelectParent,
    handleSelectChild,
    handleSelectGrandChild,
    headers,
    isCheckBoxRef,
    activeApplicationId
  } = props;

  const [listBrand, setListBrand] = useState<Option[]>([]);
  const [listSubBrand, setListSubBrand] = useState<Option[]>([]);
  const [listCategory, setListCategory] = useState<Option[]>([]);

  const [brand, setBrand] = useState<Option[]>([]);
  const [subBrand, setSubBrand] = useState<Option[]>([]);
  const [category, setCategory] = useState<Option[]>([]);

  const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
  const PRODUCT_PERMISSION_L1 = EnvConfig['PRODUCT_PERMISSION_L1']; 
  const PRODUCT_PERMISSION_L2 = EnvConfig['PRODUCT_PERMISSION_L2']; 
  const PRODUCT_PERMISSION_L3 = EnvConfig['PRODUCT_PERMISSION_L3']; 
  // Update the lists whenever the product data or initial values change
  useEffect(() => {
    const newListBrand: Option[] = [];
    const newListSubBrand: Option[] = [];
    const newListCategory: Option[] = [];


    product && Object.keys(product)?.forEach((keyBrand: any) => {
      const dataBrand = { label: keyBrand, value: keyBrand };
      newListBrand.push(dataBrand);

      Object.keys(product[keyBrand])?.forEach((keySubBrand: string) => {
        const valueSubBrand = `${keyBrand} > ${keySubBrand}`;
        
          const dataSubBrand = {
            label: valueSubBrand,
            value: valueSubBrand,
          };

          newListSubBrand.push(dataSubBrand);
        

        product[keyBrand][keySubBrand]?.forEach((eleCategory: any) => {
          const valueCategory = `${valueSubBrand} > ${eleCategory['product_hierarchy_3']}`;

            const dataCategory = {
              label: valueCategory,
              value: valueCategory,
            };
            newListCategory.push(dataCategory);
          
        });
      });
    });

    setListBrand(newListBrand);
    setListSubBrand(newListSubBrand);
    setListCategory(newListCategory);

    
    setBrand(valueSelectPrd?.brand || []);
    setSubBrand(valueSelectPrd?.subBrand || []);
    setCategory(valueSelectPrd?.category || []);
  }, [valueSelectPrd, product]);

  
  const handleSelectBrand = (e: Option[]) => {
    setBrand(e);
    
    setSubBrand([]);
    setCategory([]);

    handleSelectParent({
      e,
      dataAll: product,
      child: subBrand,
      grandChild: category,
      setChild: setSubBrand,
      setGrandChild: setCategory,
    });
  };

  // Handle subBrand selection
  const handleSelectSubBrand = (e: Option[]) => {
    setSubBrand(e);
    // Reset category whenever subBrand is changed
    setCategory([]);

    handleSelectChild({
      e,
      grandChild: category,
      valueParent: brand,
      setParent: setBrand,
      setGrandChild: setCategory,
    });
  };

  // Handle category selection
  const handleSelectCategory = (e: Option[]) => {
    setCategory(e);
    handleSelectGrandChild({
      e,
      valueParent: brand,
      setParent: setBrand,
      valueChild: subBrand,
      setChild: setSubBrand,
    });
  };

  useImperativeHandle(ref, () => ({
    getPrdPermissionValue() {
      return getPrdPermissionValue();
    },
    removePrdPermissionValue() {
      removePrdPermissionValue();
    },
    getSetPrdPermission() {
      return getSetPrdPermission();
    },
    setBrand,
  }));

  
  const removePrdPermissionValue = () => {
    setBrand([]);
    setSubBrand([]);
    setCategory([]);
  };

  
  const getPrdPermissionValue = () => {
    return {
      brand,
      subBrand,
      category,
    };
  };

  
  const getSetPrdPermission = () => {
    return {
      setBrand,
      setSubBrand,
      setCategory,
    };
  };
  
  const onSelectAll = (event: React.ChangeEvent<HTMLInputElement>) =>{
    const check = event.target.checked;
    if (isCheckBoxRef?.current?.isPrdCheck) {
      isCheckBoxRef.current.isPrdCheck[activeApplicationId] = check;
    }
    
    if(check){
      setBrand(listBrand)
      setCategory(listCategory)
      setSubBrand(listSubBrand)
    }
    else{
      setBrand([])
      setCategory([])
      setSubBrand([])
    }    
  }

  const prdPermissions = [
    {
      title: PRODUCT_PERMISSION_L1 || '',
      placeholder: "", 
      options: listBrand,
      value: brand,
      setValue: setBrand,
      handleAction: handleSelectBrand,
      disabled: false,
      from:"isPrdCheck",
      activeApplicationId,
      isCheckBoxRef,
    },
    {
      title: PRODUCT_PERMISSION_L2 || '',
      placeholder:"", 
      options: brand.length === 0 ? [] : listSubBrand.filter((sub: Option) =>
        brand.some((b) => sub.value.split(" > ")[0] == b.value)  // Filter based on selected brand
      ),
      value: subBrand,
      setValue: setSubBrand,
      handleAction: handleSelectSubBrand,
      disabled: brand.length === 0, // Disable if no brand is selected
      from:"isPrdCheck",
      activeApplicationId,
      isCheckBoxRef,
    },
    {
      title: PRODUCT_PERMISSION_L3 || '',
      placeholder: "", 
      options: subBrand.length === 0 ? [] : (() => {
        const currentSubBrandValues = subBrand.map(sub => sub.value);
        const filteredCategories = listCategory.filter((category: Option) => {
          const splitValue = category.value.split(" > ").slice(0, 3);
          const exactMatchValue = splitValue[0] + " > " + splitValue[1];
          return currentSubBrandValues.includes(exactMatchValue);
        });
        return filteredCategories;
      })(),
      value: category,
      setValue: setCategory,
      handleAction: handleSelectCategory,
      disabled: subBrand.length === 0, 
      from:"isPrdCheck",
      activeApplicationId,
      isCheckBoxRef,
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

  const updatedPermissions =prdPermissions.map((permission:any,index:any)=>({
    ...permission,
    title: headers && headers?.Orders && headers?.Orders[index] ? headers.Orders[index] :  permission.title
  })) 

  return (
    <ProductPermission
      title={ headers && Object.keys(headers).length > 0 ? Object.keys(headers)[0] + " Permissions" : t(
        "profile.tabContent.manageUsers.advancedPermission.productPermission.title"
      )}
      prdPermissions={updatedPermissions }
      onSelectAll={onSelectAll}
      isSelected={isCheckBoxRef?.current?.isPrdCheck[activeApplicationId]}
    />
  );
});
