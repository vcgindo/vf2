import { useTranslation } from "react-i18next";
import { ContainerRight, ChangePassText, CircleLogin, IputLogin, KeepSingIn, KeepMe, LinkRouter, SCButtonLogin, SignInArea, SignInContainer, Tittle, FormArea, ButtonSubmit, ButtonSubmitText, ArrowArea, InputArea, CheckboxButton, InputGroup, LogoAreaLogin, ContainerLeft, RecaptchaInput, CaptchaContainer, CaptchaReload } from "./styles";
import { Errors } from "../../../components";
import { useForm } from "react-hook-form";
import { LoginRequest } from "../../../module-main/types";
import { useLoginAccount } from "../../../module-main/services";
import {  useNavigate } from "react-router";
import { notifyError, notifySuccess, notifyWarningWithoutAutoClose } from "../../../helpers/notify";
import { useEffect, useRef, useState } from "react";
import WelcomeBoard from "./welcome-board";
import { hashPassword } from '../../../helpers/utils'
import VFLoader from "../../../components/VectorFLOW/commons/VFLoader";
import { loadCaptchaEnginge, LoadCanvasTemplateNoReload, validateCaptcha } from 'react-simple-captcha';
import { useGetAllEnvironmentConfiguration } from "../../../VectorFlow/Services/MTA/MDM";
import { useDispatch } from "react-redux";
import { UPDATE_ENV_CONFIG } from "../../../redux/actions/MTA";

function LoginContainer() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  useEffect(() => {
   
    loadCaptchaEnginge(6);

    const interval = setInterval(() => {
      loadCaptchaEnginge(6);
    }, 120000);
  
    return () => clearInterval(interval);
  },[])

  const form = useForm<LoginRequest>({
    mode:"onTouched",
    defaultValues: {
      email: "",
      password: "",
    },
  });
  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors },
  } = form;

  const { mutate: mutateLogin,isLoading } = useLoginAccount();
  // const [remember, setRemember] = useState(true);
  const recaptchaRef: any = useRef();
  const [captchaInput, setCaptchaInput] = useState("");
  const dispatch = useDispatch();
  const {mutateAsync : getAllEnvConfiguration} = useGetAllEnvironmentConfiguration();
  const getAllEnvironmentConfiguration = async () => {
    try {
      const response = await getAllEnvConfiguration();
      const configMap = response?.data?.data.reduce((map:any, item:any) => {
        map[item.ConfigKey] = item.ConfigValue;
        return map;
      }, {});
      dispatch(UPDATE_ENV_CONFIG(configMap))
    }
    catch (err) {
      console.error("Unexpected error in get Environment configuration:", err);
    }
  };

  const onSave = async () => {
    if (!captchaInput || !validateCaptcha(captchaInput)) {
      notifyError("Invalid Captcha. Please try again.");
      setCaptchaInput("");
      return;
    }
  
    const formData = getValues();  
    formData.password = await hashPassword(formData.password);
  
    mutateLogin(formData, {
      onSuccess: (data: any) => {
        if (data?.status !== 200) {
          if (data.response.msg === 'User is inactive please contact admin') {
            notifyError("User is inactive please contact admin");
          } else if (data?.status === 400) {
            notifyError(data?.error?.non_field_errors[0]);
          } else {
            notifyError("Something went wrong");
          }
          // Reload captcha
          loadCaptchaEnginge(6);
        } else {
          const url = "/landing-page";
          navigate(url, { replace: true });
          getAllEnvironmentConfiguration();
          notifySuccess(data.data?.data?.msg);
          if(data.data?.data?.wrng != null){
           notifyWarningWithoutAutoClose(data.data.data.wrng)
          }
        }
      },
      onError(error: any) {
        if (error?.code === "ERR_NETWORK") {
          notifyError(t("loginPage.notify.networkError"));
        } else {
          notifyError(error?.error?.non_field_errors[0]);
        }
        loadCaptchaEnginge(6);
        setCaptchaInput("");
      },
    }); 
  };
  

  return (
    <SignInArea>
      <SignInContainer>
        <ContainerLeft>
          <CircleLogin />
          <LogoAreaLogin>
            <img
              src="/assets/img/auth/login-left.png"
              className="icon-head left-icon"
            />
            <img
              src="/assets/img/auth/login-right.png"
              className="icon-head right-icon"
            />
            <WelcomeBoard />
          </LogoAreaLogin>
        </ContainerLeft>
      </SignInContainer>
      <SignInContainer>
        <ContainerRight>
          {/* <LogoArvind
            style={{ opacity: 0, visibility: "hidden" }}
            src=""
            alt="logo"
          /> */}
          <Tittle>{t("loginPage.title")}</Tittle>
          <FormArea onSubmit={handleSubmit(onSave)}>
            <InputArea error={errors.email}>
              <InputGroup>
                <img src="/assets/img/auth/user.svg" />
                <IputLogin
                  type="text"
                  {...register("email", {
                    required: true,
                    maxLength: {
                      value: 255,
                      message: t("loginPage.validate.emailMaxLength"),
                    },
                  })}
                  placeholder={t("loginPage.placeholder.email")}
                />
              </InputGroup>
              <Errors errors={errors} name="email" />
            </InputArea>
            <InputArea error={errors.password}>
              <InputGroup>
                <img src="/assets/img/auth/password.svg" />
                <IputLogin
                  type="password"
                  {...register("password", {
                    required: true
                  })}
                  placeholder={t("loginPage.placeholder.password")}
                />
              </InputGroup>
              <Errors style={{ marginLeft: "30px" }} errors={errors} name="password" />
            </InputArea>
            <ChangePassText>
              <LinkRouter style={{textAlign:'center'}} to={"/forgot-password"}>
                {t("loginPage.forgotPassword")}
              </LinkRouter>
            </ChangePassText>
            

            <CaptchaContainer>
  <LoadCanvasTemplateNoReload/>
  <CaptchaReload
  type="button"
  onClick={() => {
    loadCaptchaEnginge(6);
    setCaptchaInput("");   
  }}
>
  <img src="/assets/img/reload.svg" alt="Reload" />
</CaptchaReload>
</CaptchaContainer>

<RecaptchaInput
  type="text"
  placeholder="Enter the text here"
  value={captchaInput}
  onChange={(e: any) => setCaptchaInput(e.target.value)}
  onKeyDown={(e:any) => {
    if (e.key === "Enter") {
      e.preventDefault(); 
      handleSubmit(onSave)();
    }
  }}
/>



            {/* <KeepSingIn>
              <div>
                <CheckboxButton
                  type="checkbox"
                  onChange={() => {
                    setRemember(!remember);
                  }}
                  defaultChecked={true}
                />
                <KeepMe>{t("loginPage.keepMeSignedIn")}</KeepMe>
              </div>
              <ChangePassText>
                <LinkRouter to={"/forgot-password"}>
                  {t("loginPage.forgotPassword")}
                </LinkRouter>
              </ChangePassText>
            </KeepSingIn> */}

            <SCButtonLogin disabled={isLoading}>
              <ButtonSubmit>
                <ButtonSubmitText isLoading={isLoading}>
                  {isLoading ? "Logging in" : t("loginPage.submitBtn")}
                </ButtonSubmitText>
                {isLoading ? (
                  <div
                    style={{
                      width: "30px",
                      height: "20px",
                      display: "flex",
                      justifyContent: "center",
                      alignItems: "center",
                    }}
                  >
                    <VFLoader styles={{ width: "50px", height: "50px" }} />
                  </div>
                ) : (
                  <ArrowArea>
                    <img
                      src="/assets/img/auth/arrow.svg"
                      className="arrow arrow-in"
                    />
                    <img
                      src="/assets/img/auth/arrow-hover.svg"
                      className="arrow arrow-out"
                    />
                  </ArrowArea>
                )}
              </ButtonSubmit>
            </SCButtonLogin>
          </FormArea>
        </ContainerRight>
      </SignInContainer>
    </SignInArea>
  );
}

export default LoginContainer;