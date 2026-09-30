import { useState } from "react";
import { InputWrapper, URLsForm, Label } from "./styles";
import {
  Input,
  PrimaryButton,
  TextArea,
} from "../../../components/commons/styled";
import { useUserData } from "../../../context";
import axios from "axios";
import { notifyError,notifySuccess } from "../../../helpers/notify";


const AddURL = (props:{cb:()=>void}) => {

  const {
    cb
} = props
  const { user } = useUserData();

  const themeUi = user.user.theme_ui;



  const [isSubmitting,setIsSubmitting] = useState<boolean>(false)

  const [formData, setFormData] = useState<any>({
    name: "",
    code: "",
    url: "",
    description: "",
  });

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;

    setFormData({ ...formData, [name]: value });
  };

  const handleSubmit = async(e: any) => {
    e.preventDefault();
    setIsSubmitting(true)
    try{
      const response = await axios.post(`${process.env.REACT_APP_API_HOST}api/user/add-function/`,{
        data:[formData]
      },{
        headers: { 'Content-Type': 'application/json' }
      })
      if(response.status === 400){
        notifyError("A URL with the name " + formData.name  +" already exists" )
      }
      else{
        notifySuccess("Successfully Added " + formData.name)
        cb()
      }
    }catch(error){
      console.error(error)
      notifyError("Server Went Unresponsive")
    }finally{
      setIsSubmitting(false)
    }
  };
  return (
    <URLsForm onSubmit={handleSubmit}>
      <div style={{ display: "flex" }}>
        <InputWrapper>
          <Label htmlFor="name"> Name</Label>
          <Input
            type={"text"}
            required
            name="name"
            placeholder="Any name"
            themeUi={themeUi}
            onChange={handleChange}
          />
        </InputWrapper>
        <InputWrapper style={{ marginLeft: "10px" }}>
          <Label htmlFor="code"> Code</Label>
          <Input
            type={"text"}
            required
            name="code"
            placeholder="URL code"
            themeUi={themeUi}
            onChange={handleChange}
          />
        </InputWrapper>
      </div>
      <InputWrapper>
        <Label htmlFor="url">URL </Label>
        <Input
          type={"text"}
          name="url"
          required
          placeholder="Enter your url"
          themeUi={themeUi}
          onChange={handleChange}
        />
      </InputWrapper>
      <InputWrapper>
        <Label htmlFor="description"> Description</Label>
        <TextArea
          name="description"
          required
          placeholder="Example : BPR url"
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
        }}
      >
        <PrimaryButton themeUi={themeUi} disabled={isSubmitting}>Add Url</PrimaryButton>
      </div>
    </URLsForm>
  );
};

export default AddURL;
