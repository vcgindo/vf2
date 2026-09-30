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
import {  useEditMDMConfiguration } from "../../../VectorFlow/Services/MTA/MDM/index";

import Select from "react-select";

interface FormDataType {
  MasterId: string;
  MasterName: string;
  Col_Code: string;
  TableField:string;
  Col_Position:string;
  Header:string;
  Visible:string;
  CellAlignment:string;
  IsAdd:string;
  IsEdit:string;
  IsFilter:string;
  IsDownload:string;
  IsApplicable:string;
  DataType:string;
  IsDelete:string;

}

const EditUIMDMConfig = (props: { data: any; cb: () => void }) => {
  const { data, cb } = props;

  const { user } = useUserData();

  const themeUi = user.user.theme_ui;



  const [formData, setFormData] = useState<FormDataType>({ ...data });

  const {mutateAsync : editEnvConfiguration} = useEditMDMConfiguration();

const [isDisableOptions , setIsDisabledOptions] = useState(true);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

const isChanged = useMemo((): boolean => {
  return JSON.stringify(formData) !== JSON.stringify(data);
}, [formData, data]);

const formatData = (data: any) => {
  const formatted: any = {};
  for (const key in data) {
    if (Object.prototype.hasOwnProperty.call(data, key)) {
      const value = data[key];
      if (typeof value === 'boolean') {
        formatted[key] = value ? 1 : 0;
      } else {
        formatted[key] = value;
      }
    }
  }
  return formatted;
};


  const handleSubmit = async (e: any) => {
    e.preventDefault();
    const formattedData = formatData(formData);
    const data =  {...formattedData }  as any;
    try {
      const response = await editEnvConfiguration(data);
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
      return (
        value !== null &&
        value !== undefined &&
        value !== "" &&
        (!Array.isArray(value) || value.length > 0)
      );
    });
  }, [formData]);

  const handleSelectChange = (name:any ,value:any) => {
    if(name === "CellAlignment")   return     setFormData({ ...formData, [name]: value });
    else setFormData({ ...formData, [name]: value ? 1 : 0 });
  };

  const flagOptions = [
    { value: true, label: 'Yes' },
    { value: false, label: 'No' },
  ];

const alignmentOptions: any = [
  { label: "left", value: "left" },
  { label: "right", value: "right" },
];

  return (
    <URLsForm onSubmit={handleSubmit}>
      <div style={{ display: "flex" }}>
        <InputWrapper>
          <Label htmlFor="MasterId">MasterId</Label>
          <Input
            type={"text"}
            required
            name="MasterId"
            value={formData.MasterId}
            placeholder="Any Master Id"
            themeUi={themeUi}
            onChange={handleChange}
            readOnly 
          />
        </InputWrapper>
        <InputWrapper style={{ marginLeft: "10px" }}>
          <Label htmlFor="MasterName">MasterName</Label>
          <Input
            type={"text"}
            required
            name="MasterName"
            placeholder="Any Master Name"
            themeUi={themeUi}
            value={formData.MasterName}
            onChange={handleChange}
            maxLength={50}
            readOnly
          />
        </InputWrapper>
      </div>
      <div style={{ display: "flex" }}>
      <InputWrapper >
        <Label htmlFor="Col_Code"> Column Code</Label>
      
          <Input
            type={"text"}
            required
            name="Col_Code"
            value={formData.Col_Code}
            placeholder="Any Column Code"
            themeUi={themeUi}
            onChange={handleChange}
            readOnly 
          />
      </InputWrapper>
    
      <InputWrapper style={{ marginLeft: "10px" }}>
        <Label htmlFor="TableField"> Table Field</Label>
        <Input
            type={"text"}
            required
            name="TableField"
            placeholder="Any Table Field"
            themeUi={themeUi}
            value={formData.TableField}
            onChange={handleChange}
            maxLength={50}
            readOnly
          />
      </InputWrapper>
      </div>
      <div style={{ display: "flex" }}>
      <InputWrapper>
        <Label htmlFor="Col_Position"> Column Position</Label>
        <Input
            type={"text"}
            required
            name="Col_Position"
            placeholder="Any Column Position"
            themeUi={themeUi}
            value={formData.Col_Position}
            onChange={handleChange}
            maxLength={50}
            readOnly
          />
      
      </InputWrapper>
        
      <InputWrapper style={{ marginLeft: "10px" }}>
      <Label htmlFor="DataType"> Data Type</Label>
        <Input
            type={"text"}
            required
            name="DataType"
            placeholder="Any Data Type"
            themeUi={themeUi}
            value={formData.DataType}
            onChange={handleChange}
            maxLength={50}
            readOnly
          />
      
      </InputWrapper>
      </div>

      <div style={{ display: "flex" }}>

      <InputWrapper>
        <Label htmlFor="IsEdit"> Is Edit</Label>
          <Select
         options={flagOptions}
          placeholder={"Select Edit"}
          onChange={(data: any) => handleSelectChange("IsEdit" ,data.value)}
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
          isDisabled={isDisableOptions}  
      value={flagOptions.find((option: any) => option.value === formData.IsEdit)}
        />

      </InputWrapper>
      <InputWrapper style={{ marginLeft: "10px" }}>
        <Label htmlFor="IsAdd"> Is Add</Label>


      <Select
         options={flagOptions}
          placeholder={"Select Add"}
          onChange={(data: any) => handleSelectChange("IsAdd" ,data.value)}
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
      value={flagOptions.find((option: any) => option.value === formData.IsAdd)}
      isDisabled={isDisableOptions}
        />

      </InputWrapper>
      </div>
      
      <div style={{ display: "flex" }}>
      <InputWrapper>
        <Label htmlFor="IsDownload"> Is Download</Label>
        <Select
         options={flagOptions}
          placeholder={"Select Download"}
          onChange={(data: any) => handleSelectChange("IsDownload" ,data.value)}
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
          value={flagOptions.find((option: any) => option.value === formData.IsDownload)}
          isDisabled={isDisableOptions}
       />

      </InputWrapper>
      <InputWrapper style={{ marginLeft: "10px" }}>
        <Label htmlFor="IsFilter"> Is Filter</Label>
<Select
         options={flagOptions}
          placeholder={"Select Filter"}
          onChange={(data: any) => handleSelectChange("IsFilter" ,data.value)}
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
          value={flagOptions.find((option: any) => option.value === formData.IsFilter)}
          isDisabled={isDisableOptions}
        />

      </InputWrapper>
    
        </div>
        <div style={{ display: "flex" }}>
      <InputWrapper >
        <Label htmlFor="IsApplicable"> Is Applicable</Label>

<Select
         options={flagOptions}
          placeholder={"Select Applicable"}
          onChange={(data: any) => handleSelectChange("IsApplicable" ,data.value)}
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
          value={flagOptions.find((option: any) => option.value === formData.IsApplicable)}
          isDisabled={isDisableOptions}
        />
      </InputWrapper>
      <InputWrapper style={{ marginLeft: "10px" }}>
        <Label htmlFor="IsDelete"> Is Delete</Label>

    <Select
         options={flagOptions}
          placeholder={"Select Delete"}
          onChange={(data: any) => handleSelectChange("IsDelete" ,data.value)}
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
          value={flagOptions.find((option: any) => option.value === formData.IsDelete)}
          isDisabled={isDisableOptions}
        />
      </InputWrapper>
      </div>
      <div style={{ display: "flex" }}>

      <InputWrapper >
        <Label htmlFor="Visible"> Visible</Label>

      <Select
         options={flagOptions}
          placeholder={"Select Visible"}
          onChange={(data: any) => handleSelectChange("Visible" ,data.value)}
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
          value={flagOptions.find((option: any) => option.value === formData.Visible)}
          isDisabled={isDisableOptions}
        />
        
      </InputWrapper>
      <InputWrapper style={{ marginLeft: "10px" }}>
      <Label htmlFor="CellAlignment"> Cell Alignment</Label>
  

      <Select
              options={alignmentOptions}
                placeholder={"Select Cell Alignment"}
                onChange={(data: any) => handleSelectChange("CellAlignment" ,data.value)}
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
                value={alignmentOptions.find((option: any) => String(formData.CellAlignment || '').trim() === option.value?.trim())}
                isDisabled={isDisableOptions}
              />

      </InputWrapper>
      </div>
      <div style={{ display: "flex" , marginBottom :"20px" }}>
      <InputWrapper>
        <Label htmlFor="Header"> Header</Label>
        <TextArea
          name="Header"
          value={formData.Header}
          style={{ minHeight: 50 }}
          required
          placeholder="Any Header name"
          themeUi={themeUi}
          onChange={handleChange}
        />
      </InputWrapper>
      </div>
      <div
        style={{
           display: "flex",
           alignItems: "flex-end",
          justifyContent: "flex-end",
         flex: 1,
          marginTop: "auto",
         gap: 20,
        }}
      >
        <SecondaryButton type="button" onClick={cb} themeUi={themeUi}>
          Cancel
        </SecondaryButton>
        <PrimaryButton disabled={!isFormValid ||  !isChanged} themeUi={themeUi}>
          Update UI MDM Config
        </PrimaryButton>
      </div>
    </URLsForm>
  );
};

export default EditUIMDMConfig;
