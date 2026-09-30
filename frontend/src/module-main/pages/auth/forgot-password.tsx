import { useEffect, useRef,useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ContainerRight,
  CircleForgotPassword,
  IputLogin,
  SCButtonLogin,
  SignInArea,
  SignInContainer,
  Tittle,
  FormArea,
  ButtonSubmit,
  ButtonSubmitText,
  ArrowArea,
  InputArea,
  InputGroup,
  LogoAreaForgotPsw,
  ContainerLeft,
  GoBackButton,
  SuccessIcon,
  SuccessText,
  SuccessArea,
  CaptchaContainer,
  CaptchaReload,
  RecaptchaInput,
} from "./styles";
import { Errors } from "../../../components";
import { useForm } from "react-hook-form";
import { LoginRequest } from "../../types";
import { useForgotPassword } from "../../services";
import { notifyError, notifySuccess } from "../../../helpers/notify";
import WelcomeBoard from "./welcome-board";
import LoadingSpinner from "../../../components/commons/LoadingSpinner";
// eslint-disable-next-line import/no-named-as-default
import { loadCaptchaEnginge, LoadCanvasTemplateNoReload, validateCaptcha } from 'react-simple-captcha';
import { SITE_KEY } from "../../../helpers/constants";

function ForgotPasswordContainer() {
  const { t } = useTranslation();
  localStorage.clear();
  const [requestSend, setRequestSend] = useState(false);
  const [loading, setLoading] = useState(false);

  const form = useForm<LoginRequest>({
    mode : "onChange",
    defaultValues: {
      email: "",
    },
  });
  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors },
  } = form;

  const { mutateAsync: mutateForgotPassword } = useForgotPassword();

  const [message, setMessage] = useState("");
  const [captchaInput, setCaptchaInput] = useState("");

 const onSave = () => {
    if (!captchaInput || !validateCaptcha(captchaInput)) {
      notifyError("Invalid Captcha. Please try again.");
      setCaptchaInput("");
      return;
    }
      

    setLoading(true);
    const formData = getValues();
    const data = { email: formData.email.trim() };

    mutateForgotPassword(data, {
      onSuccess: (data: any) => {
        setMessage(data?.data?.msg);
        if (data?.status === 400) {
          notifyError(data?.response?.msg[0]);
          loadCaptchaEnginge(6);
          setCaptchaInput("");
        } else {
          setRequestSend(true);
          notifySuccess("Password reset link sent to your email.");
        }
        setLoading(false);
      },
      onError: (error: any) => {
        setMessage(error?.data?.msg);
        notifyError(error?.error || "Something went wrong");
        setLoading(false);
        loadCaptchaEnginge(6);
        setCaptchaInput("");
      },
    });
  };


  useEffect(() => {
    loadCaptchaEnginge(6);
    const interval = setInterval(() => {
      loadCaptchaEnginge(6);
    }, 120000);

    return () => clearInterval(interval);
  }, []);

  
  return (
    <SignInArea>
      {loading && <LoadingSpinner />}
      <SignInContainer>
        <ContainerRight>
          {requestSend ? (
            <SuccessArea>
              <SuccessIcon src="/assets/img/auth/tick-circle.svg" />
              <SuccessText>{message}</SuccessText>
            </SuccessArea>
          ) : (
            <>
              <Tittle>{t("forgotPasswordPage.title")}</Tittle>
              <FormArea onSubmit={handleSubmit(onSave)}>
                <InputArea error={errors.email}>
                  <InputGroup>
                    <img src="/assets/img/auth/user.svg" />
                    <IputLogin
                      inputType="email"
                      type="text"
                      {...register("email", {
                        required: true,
                        maxLength: {
                          value: 255,
                          message: t("loginPage.validate.emailMaxLength"),
                        },
                      })}
                      placeholder={t("forgotPasswordPage.placeholder.email")}
                    />
                  </InputGroup>
                  <Errors errors={errors} name="email" />
                </InputArea>

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
                  onKeyDown={(e: any) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      handleSubmit(onSave)();
                    }
                  }}
                />

                <SCButtonLogin disabled={loading}>
                  <ButtonSubmit>
                    <ButtonSubmitText>
                      {t("forgotPasswordPage.submitBtn")}
                    </ButtonSubmitText>
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
                  </ButtonSubmit>
                </SCButtonLogin>

                <GoBackButton onClick={() => window.location.replace("/login")}>
                  {t("forgotPasswordPage.goBackBtn")}
                </GoBackButton>
              </FormArea>
            </>
          )}
        </ContainerRight>
      </SignInContainer>
      <SignInContainer>
        <ContainerLeft>
          <CircleForgotPassword />
          <LogoAreaForgotPsw>
            <img
              src="/assets/img/auth/forgot-left.png"
              className="icon-head left-icon"
            />
            <img
              src="/assets/img/auth/forgot-right.png"
              className="icon-head right-icon"
            />
            <WelcomeBoard />
          </LogoAreaForgotPsw>
        </ContainerLeft>
      </SignInContainer>
    </SignInArea>
  );
}

export default ForgotPasswordContainer;
