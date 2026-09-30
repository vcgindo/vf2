import React, { useState, useEffect, useMemo, useCallback } from "react";

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
  CheckBoxLabel,
  CheckBoxesHeaderContainer,
  SearchWrapper,
  URLSearch,
} from "../UserURLsDrawer/styles";
import { Input, PrimaryButton, Skeleton, TextArea } from "../../commons/styled";
import { useUserData } from "../../../context";
import axios from "axios";
import { notifyError, notifySuccess } from "../../../helpers/notify";

interface FormDataType {
  name: string;
  code: string;
  description: string;
  application_id: string;
  urls: Array<any>;
}

const AddRole = (props: { cb: () => void }) => {
  const { cb } = props;

  const { user } = useUserData();

  const themeUi = user.user.theme_ui;

  const [isLoading, setIsLoading] = useState<boolean>(true);

  const [allUrls, setAllUrls] = useState<Array<any>>([]);

  const [allApplications, setAllApplications] = useState<Array<any>>([]);

  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const [urlSearchQuery, setUrlSearchQuery] = useState<string>("");

  const [formData, setFormData] = useState<FormDataType>({
    name: "",
    code: "",
    description: "",
    application_id: "",
    urls: [],
  });

  const getAllUrls = useCallback(async () => {
    try {
      const { data } = await axios.get(
        `${process.env.REACT_APP_API_HOST}api/user/get-all-functions/`
      );
      setAllUrls(data);
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

  const handleSelectChange = (value: any) => {
    setFormData({ ...formData, application_id: value });
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
    setIsSubmitting(true);
    try {
      await axios.post(
        `${process.env.REACT_APP_API_HOST}api/user/add-role/`,
        {
          data: [formData],
        },
        {
          headers: { "Content-Type": "application/json" },
        }
      );

      notifySuccess("Successfully Added " + formData.name);
      cb();
    } catch (error) {
      console.error(error);
      notifyError("Server Went Unresponsive");
    }
  };

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

  const handleSearchURLs = (e: any) => {
    setUrlSearchQuery(e.target.value.toLowerCase());
  };

  const debouncedSearch = debounce(handleSearchURLs, 0);

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
    return !Object.keys(formData).every((k) => {
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

  const isChecked = useCallback(
    (url: any) => {
      return formData.urls.some((u) => u.code === url.code);
    },
    [formData]
  );

  const queriedURLs = useMemo(() => {
    if (!urlSearchQuery || urlSearchQuery.length === 0) return allUrls;
    return allUrls.filter((url) =>
      url.name.toLowerCase().includes(urlSearchQuery)
    );
  }, [urlSearchQuery, allUrls]);

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
            onChange={handleChange}
          />
        </InputWrapper>
      </div>
      <InputWrapper>
        <Label htmlFor="application">Applications </Label>
        <Select
          options={applicationsFormattedData}
          placeholder={"Select Application"}
          onChange={(data: any) => handleSelectChange(data.value)}
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
          {queriedURLs.length ? (
            <React.Fragment>
              <CheckBoxWrapper
                style={{ position: "sticky", top: 0, backgroundColor: "white" }}
              >
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
          ) : (
            <CheckBoxWrapper>
              <p
                style={{ fontSize: "14px", textAlign: "center", width: "100%" }}
              >
                No result
              </p>
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
        }}
      >
        <PrimaryButton disabled={isFormValid || isSubmitting} themeUi={themeUi}>
          Add Role
        </PrimaryButton>
      </div>
    </URLsForm>
  );
};

export default AddRole;
