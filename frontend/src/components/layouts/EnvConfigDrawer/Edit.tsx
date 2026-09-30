import React,{ useState, useMemo } from "react";

import {
  InputWrapper,
  URLsForm,
  Label,
} from "../UserURLsDrawer/styles";
import {
  Input,
  PrimaryButton,
  SecondaryButton,
  TextArea,
} from "../../commons/styled";
import { useUserData } from "../../../context";
import { notifyError, notifySuccess } from "../../../helpers/notify";
import { useEditEnvironmentConfiguration } from "../../../VectorFlow/Services/MTA/MDM/index";
import { useSelector } from "react-redux";
import { RootState } from "../../../redux/store/store";

interface FormDataType {
  ConfigKey: string;
  ConfigValue: string;
  Description: string;
  Category:string
}

const EditEnvConfig = (props: { data: any; cb: () => void }) => {
  const { data, cb } = props;

  const { user } = useUserData();

  const themeUi = user.user.theme_ui;



  const [formData, setFormData] = useState<FormDataType>({ ...data });

  const {mutateAsync : editEnvConfiguration} = useEditEnvironmentConfiguration();

    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const EnvProductPermissionArray = EnvConfig['EnvProductPermissionArray']; 
    const EnvLocationPermissionArray = EnvConfig['EnvLocationPermissionArray']; 
    const PermissionArray = [...EnvProductPermissionArray , ...EnvLocationPermissionArray ]

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

const handleChangeValue = (
  e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
) => {
  const { name, value } = e.target;
  if (data?.Datatype === "Number") {
    const numberRegex = /^\d*$/; 
    if (!numberRegex.test(value)) {
      return; 
    }
    if (data?.ConfigKey?.endsWith("PAGE") && value !== "" && parseInt(value, 10) > 5000) {
        notifyError("Value for ROWS PER PAGE configuration cannot exceed 5000.");
        return;
    }
    setFormData({ ...formData, [name]: value });
  } else {
    setFormData({ ...formData, [name]: value });
  }
};

const isChanged = useMemo((): boolean => {
  return JSON.stringify(formData) !== JSON.stringify(data);
}, [formData, data]);


const getChangedFields = (original: any,current: any,keysToIgnore: string[] = []): any => {
  const payload:any = {};
  for (const key in current) {
    if (keysToIgnore.includes(key) || original[key] !== current[key]) payload[key] = current[key];
  }
  return payload;
};


  const handleSubmit = async (e: any) => {
    e.preventDefault();
    const changedData = getChangedFields(data ,formData , ['Id', 'ConfigKey' , 'ConfigValue']) as any;
    changedData.LastModifiedByUserEmail = user?.user?.email;
    try {
      const response = await editEnvConfiguration(changedData);
      console.log("RESPONSE",response);
      
      if (response.status !== 200) notifyError("Server Went Unresponsive");
      else notifySuccess(response?.data?.data);
      cb();
    } catch (error) {
      console.error(error);
      notifyError("Server Went Unresponsive");
    }
  };

  const isFormValid = useMemo((): boolean => {
    return Object.keys(formData).every((k) => {
      const key = k as keyof FormDataType;
      const value = formData[key];
      if (data?.Category === "ProductPermission" || data?.Category === "LocationPermission") {
          const isDuplicate = PermissionArray.includes(value) && value !== data.ConfigValue;
          if (isDuplicate) {
            notifyError("Each permission key value must be unique")
              return false; 
          }
      }
      if (formData?.["ConfigKey"] === "CLIENT_NAME" || formData?.["ConfigKey"] === "CLIENT_LOGO") {
        if (key === "ConfigValue" && value === "") {
          return true;
        }
      }
      return (
        value !== null &&
        value !== undefined &&
        value !== "" &&
        (!Array.isArray(value) || value.length > 0)
      );
    });
  }, [formData]);




  return (
    <URLsForm onSubmit={handleSubmit}>
      <div style={{ display: "flex" }}>
        <InputWrapper>
          <Label htmlFor="ConfigKey"> Config Key</Label>
          <Input
            type={"text"}
            required
            name="ConfigKey"
            value={formData.ConfigKey}
            placeholder="Any Config Key"
            themeUi={themeUi}
            onChange={handleChange}
            readOnly 
          />
        </InputWrapper>
        <InputWrapper style={{ marginLeft: "10px" }}>
          <Label htmlFor="ConfigValue"> Config Value</Label>
          <Input
            type={"text"}
            name="ConfigValue"
            placeholder="Any Config Value"
            themeUi={themeUi}
            value={formData.ConfigValue}
            onChange={handleChangeValue}
            maxLength={50}
          />
        </InputWrapper>
      </div>
     
      <InputWrapper>
        <Label htmlFor="Description"> Description</Label>
        <TextArea
          name="Description"
          value={formData.Description}
          style={{ minHeight: 50 }}
          required
          placeholder="Config Description"
          themeUi={themeUi}
          onChange={handleChange}
        />
      </InputWrapper>
    
        
      <div
        style={{
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "flex-end",
          flex: 10,
          gap: 10,
        }}
      >
        <SecondaryButton type="button" onClick={cb} themeUi={themeUi}>
          Cancel
        </SecondaryButton>
        <PrimaryButton disabled={!isFormValid ||  !isChanged} themeUi={themeUi}>
          Update Env Config
        </PrimaryButton>
      </div>
    </URLsForm>
  );
};

export default EditEnvConfig;
