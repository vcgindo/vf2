import React,{ useState, useEffect, useMemo, useCallback } from "react";

import Select from "react-select";

import {
  InputWrapper,
  URLsForm,
  Label,
  ButtonsWrapper,
  CheckBoxesWrapper,
  CheckBoxesHeader,
  CheckBoxesContainer,
  CheckBoxWrapper,
  CheckBoxesHeaderContainer,
  SearchWrapper,
  CheckBoxLabel,
  URLSearch,
} from "../UserURLsDrawer/styles";
import {
  Input,
  PrimaryButton,
  SecondaryButton,
  Skeleton,
  TextArea,
} from "../../commons/styled";
import { useUserData } from "../../../context";
import axios from "axios";
import { notifyError, notifySuccess } from "../../../helpers/notify";

interface FormDataType {
  name: string;
  code: string;
  description: string;
  application_id: string;
  application_name: string;
  id: number;
  urls: Array<any>;
  features:Array<any>
}

const EditRole = (props: { data: any; cb: () => void }) => {
  const { data, cb } = props;

  const { user } = useUserData();

  const themeUi = user.user.theme_ui;

  const [isLoading, setIsLoading] = useState<boolean>(true);

  const [allUrls, setAllUrls] = useState<Array<any>>([]);

  const [allApplications, setAllApplications] = useState<Array<any>>([]);

  const [formData, setFormData] = useState<FormDataType>({ ...data });

  const [urlSearchQuery,setUrlSearchQuery] = useState<string>("")

  const sortUrls = (allUrlsArray: Array<any>): Array<any> => {
    const selectedUrls = formData.urls.map((url) => url.id);
    const result = [
      ...formData.urls,
      ...allUrlsArray.filter((url) => !selectedUrls.includes(url.id)),
    ];
    return result;
  };

  const getAllUrls = useCallback(async () => {
    try {
      const { data } = await axios.get(
        `${process.env.REACT_APP_API_HOST}api/user/get-all-functions/`
      );

      setAllUrls(sortUrls(data));
    } catch (error: any) {
      console.error(error);
      notifyError("Server Went Unresponsive");
    }
  }, []);

  const getAllApplications = useCallback(async () => {
    try {
      const { data } = await axios.get(
        `${process.env.REACT_APP_API_HOST}api/user/get-all-applications/`
      );
      setAllApplications(data);
    } catch (error: any) {
      console.error(error);
      notifyError("Server Went Unresponsive");
    }
  }, []);

  useEffect(() => {
    getAllUrls();
    getAllApplications();
    setIsLoading(false);
  }, []);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const handleSelectChange = (value: any, label: any) => {
    setFormData({
      ...formData,
      application_id: value,
      application_name: label,
    });
  };

  const handleCheck = (e: React.ChangeEvent<HTMLInputElement>, data: any) => {
    const { checked } = e.target;

    setFormData((prevFormData) => {
      const updatedUrls = checked
        ? [...prevFormData.urls, data]
        : prevFormData.urls.filter((url) => url.id !== data.id);

      return { ...prevFormData, urls: updatedUrls };
    });
  };

  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { checked } = e.target;

    if (checked) {
      setFormData((prev) => {
        return {
          ...prev,
          urls: allUrls,
        };
      });
    } else {
      setFormData((prev) => {
        return {
          ...prev,
          urls: [],
        };
      });
    }
  };

  const handleSubmit = async (e: any) => {
    e.preventDefault();
    try {
      const response = await fetch(
        `${process.env.REACT_APP_API_HOST}api/user/edit-role/`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(formData),
        }
      );
      if (response.status !== 200) notifyError("Server Went Unresponsive");
      else notifySuccess("Updated Role Successfully");
      cb();
    } catch (error) {
      console.error(error);
      notifyError("Server Went Unresponsive");
    }
  };

  const applicationsFormattedData = useMemo(() => {
    return [
      { value: null, label: "Select Application" },
      ...allApplications.map((a) => ({
        value: a.application_id,
        label: a.application_name,
      })),
    ];
  }, [allApplications]);

  const isFormValid = useMemo((): boolean => {
    return Object.keys(formData).every((k) => {
      const key = k as keyof FormDataType;
      const value = formData[key];
      if (key === "features") return true; 
      return (
        value !== null &&
        value !== undefined &&
        value !== "" &&
        (!Array.isArray(value) || value.length > 0)
      );
    });
  }, [formData]);

  const debounce = (fn: (...args: any[]) => void, delay: number) => {
    let timeout: NodeJS.Timeout | null = null;

    return (...args: any[]) => {
        if (timeout) {
            clearTimeout(timeout);
        }

        timeout = setTimeout(() => {
            fn(...args);
        }, delay);
    };
};

    const handleSearchURLs = (e:any)=>{
        setUrlSearchQuery(e.target.value.toLowerCase())
    }

    const debouncedSearch = debounce(handleSearchURLs,0)

  const isChecked = useCallback(
    (url: any) => {
      return formData.urls.some((u) => u.code === url.code);
    },
    [formData]
  );


  // const highlightText = (text: string, query: string) => {
  //   if (!query) return text

  //   const parts = text.split(new RegExp(`(${urlSearchQuery})`, 'gi'))
  //   return parts.map((part, index) => 
  //     part.toLowerCase() === query.toLowerCase() 
  //       ? <span style={{backgroundColor:"#BC3D81",color:'white',borderRadius:'4px',padding:'0px 2px'}}>{part}</span>
  //       : <span style={{padding:'0px 2px'}}>{part}</span>
  //   )
  // }

  const queriedURLs = useMemo(()=>{
    if(!urlSearchQuery || urlSearchQuery.length === 0)return allUrls
    return allUrls.filter((url)=>url.name.toLowerCase().includes(urlSearchQuery))
  },[urlSearchQuery,allUrls])

  if (isLoading) {
    return (
      <URLsForm>
        <div style={{ display: "flex", height: 30, gap: 20 }}>
          <Skeleton style={{ height: "100%", flex: 1, width: "100%" }} />
          <Skeleton style={{ height: "100%", flex: 1, width: "100%" }} />
        </div>
        <Skeleton style={{ height: 30, width: "100%", marginTop: 20 }} />
        <Skeleton style={{ height: 30, width: "100%", marginTop: 20 }} />

        <Skeleton style={{ height: 80, width: "100%", marginTop: 20 }} />
        <ButtonsWrapper
          style={{
            alignItems: "flex-end",
            justifyContent: "flex-end",
            flex: 10,
          }}
        >
          <Skeleton style={{ height: 30, width: "100px" }} />
        </ButtonsWrapper>
      </URLsForm>
    );
  }

  return (
    <URLsForm onSubmit={handleSubmit}>
      <div style={{ display: "flex" }}>
        <InputWrapper>
          <Label htmlFor="name"> Name</Label>
          <Input
            type={"text"}
            required
            name="name"
            value={formData.name}
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
            placeholder="Role code"
            themeUi={themeUi}
            value={formData.code}
            onChange={handleChange}
          />
        </InputWrapper>
      </div>
      <InputWrapper>
        <Label htmlFor="application_name">Applications </Label>
        <Select
          // defaultValue={{value:data.application_id,label:data.application_name}}
          options={applicationsFormattedData}
          value={{
            value: formData.application_id,
            label: formData.application_name,
          }}
          placeholder={"Select Application"}
          onChange={(data: any) => handleSelectChange(data.value, data.label)}
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
        />
      </InputWrapper>
      <InputWrapper>
        <Label htmlFor="description"> Description</Label>
        <TextArea
          name="description"
          value={formData.description}
          style={{ minHeight: 50 }}
          required
          placeholder="Example : BPR Manager"
          themeUi={themeUi}
          onChange={handleChange}
        />
      </InputWrapper>
      <CheckBoxesWrapper>
        <CheckBoxesHeaderContainer>
          <CheckBoxesHeader>Select URLS</CheckBoxesHeader>
          <SearchWrapper>
            <URLSearch
              // style={{ padding: "2px 5px", height: "25px" }}
              // themeUi={themeUi}
              type={"search"}
              placeholder="Search..."
              onChange={debouncedSearch}
            />
            <img src="/assets/img/search-icon.svg"height={15} width={15}/>
          </SearchWrapper>
        </CheckBoxesHeaderContainer>
        <CheckBoxesContainer
            className="custom-scrollbar"
          style={{
            display: "flex",
            flexDirection: "column",
            maxHeight: "150px",
            overflowY: "auto",
          }}
        >
         
          {queriedURLs.length?(
            <React.Fragment>
                 <CheckBoxWrapper style={{position:'sticky',top:0,backgroundColor:'white'}}>
                    <input
                    style={{ width: 10 }}
                    type={"checkbox"}
                    name={"all"}
                    onChange={handleSelectAll}
                    />
                    <Label htmlFor={"all"}>
                        <b> Select All</b>
                    </Label>
                </CheckBoxWrapper>
                {queriedURLs.map((r) => {
                return (
                  <CheckBoxWrapper key={r.code}>
                    <input
                      style={{ width: 10 }}
                      checked={isChecked(r)}
                      type={"checkbox"}
                      name={r.name}
                      onChange={(e) => handleCheck(e, r)}
                    />
                    <Label htmlFor={r.name}>
                    <CheckBoxLabel>
                        {/* {highlightText(r.name,urlSearchQuery)} */}
                        {r.name.split("").map((letter:string)=>{
                          if(urlSearchQuery.includes(letter.toLowerCase())){
                           return  <p style={{color:"#BC3D81"}}>{letter}</p>
                          }
                          return (
                            <p>{letter}</p>
                          )
                        })}
                    </CheckBoxLabel>
                    </Label>
                  </CheckBoxWrapper>
                );
              })}
            </React.Fragment>
            
          ):(
            <CheckBoxWrapper>
                <p style={{fontSize:'14px',textAlign:'center',width:'100%'}}>No result</p>
            </CheckBoxWrapper>
          )}
        </CheckBoxesContainer>
      </CheckBoxesWrapper>
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
        <PrimaryButton disabled={!isFormValid} themeUi={themeUi}>
          Update Role
        </PrimaryButton>
      </div>
    </URLsForm>
  );
};

export default EditRole;
