import { useTranslation } from "react-i18next";

import { ContainerRight, CircleForgotPassword, IputLogin, SCButtonLogin, SignInArea, SignInContainer, Tittle, FormArea, ButtonSubmit, ButtonSubmitText, ArrowArea, InputArea, InputGroup, LogoAreaForgotPsw, ContainerLeft, SuccessArea, SuccessIcon, SuccessText,CaptchaContainer,CaptchaReload,RecaptchaInput, } from "./styles";

import { Errors } from "../../../components";
import { useForm } from "react-hook-form";
import { useChangePassword } from "../../services";
import { useNavigate } from "react-router";
import { notifyError, notifySuccess } from "../../../helpers/notify";
import WelcomeBoard from "./welcome-board";
import { useEffect, useState } from "react";
import LoadingSpinner from "../../../components/commons/LoadingSpinner";
import {
  loadCaptchaEnginge,
  LoadCanvasTemplateNoReload,
  validateCaptcha,
} from "react-simple-captcha";
import VFLoader from "../../../components/VectorFLOW/commons/VFLoader";

function ChangePasswordContainer() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token");
  const userId = params.get("userId");

  const [requestSend, setRequestSend] = useState(false);
  const [loading, setLoading] = useState(false);
  const [captchaInput, setCaptchaInput] = useState("");

  useEffect(() => {
    if (!token || !userId) {
      navigate("/login", { replace: true });
    }
    loadCaptchaEnginge(6);
    const interval = setInterval(() => {
      loadCaptchaEnginge(6);
    }, 120000);
    return () => clearInterval(interval);
  }, [token, userId, navigate]);

  const form = useForm<{
    new_password: string;
    confirm_password: string;
    token: string;
    uid: string;
  }>({
    mode: "onTouched",
    defaultValues: {
      new_password: "",
      confirm_password: "",
    },
  });
  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors },
  } = form;

  const { mutateAsync: mutateForgotPassword } = useChangePassword();

  const onSave = () => {
    if (!captchaInput || !validateCaptcha(captchaInput)) {
      notifyError("Invalid Captcha. Please try again.");
      setCaptchaInput("");
      return;
    }

    setLoading(true);
    let formData = getValues();
    formData = {
      ...formData,
      token: token || "",
      uid: userId || "",
    };
    mutateForgotPassword(formData, {
      onSuccess: (data: any) => {
        if (data?.status === 400) {
          notifyError(data?.response?.msg);
          loadCaptchaEnginge(6);
          setCaptchaInput("");
          setLoading(false);
          return;
        }
        notifySuccess(data?.data?.msg || "Password changed successfully");
        setRequestSend(true);
        setLoading(false);
      },
      onError: () => {
        notifyError("Something went wrong!");
        loadCaptchaEnginge(6);
        setCaptchaInput("");
        setLoading(false);
      },
    });
  };

  return (
    <SignInArea>
      {loading && <LoadingSpinner />}
      <SignInContainer>
        <ContainerRight>
          {requestSend ? (
            <SuccessArea>
              <SuccessIcon src="/assets/img/auth/tick-circle.svg" />
              <SuccessText>Password changed successfully.</SuccessText>
              <SuccessText>
                Please login again with the new password.
              </SuccessText>
              <SCButtonLogin
                onClick={() => navigate("/login", { replace: true })}
              >
                <ButtonSubmit>
                  <ButtonSubmitText>
                    {t("changePasswordPage.loginBtn")}
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
            </SuccessArea>
          ) : (
            <>
              <Tittle>{t("changePasswordPage.title")}</Tittle>
              <FormArea onSubmit={handleSubmit(onSave)}>
                <InputArea error={errors.new_password}>
                  <InputGroup>
                    <img src="/assets/img/auth/password.svg" />
                    <IputLogin
                      type="password"
                      {...register("new_password", {
                        required: true,
                        pattern: {
                          value:
                            /^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*()\-_=+{}[\]|;:'",.<>/?]).{8,}$/,
                          message: t("changePasswordPage.validate.password"),
                        },
                        validate: (value) =>
                          value.includes(" ")
                            ? (t("loginPage.validate.includeSpace") as string)
                            : true,
                      })}
                      placeholder={t("changePasswordPage.placeholder.password")}
                    />
                  </InputGroup>
                  <Errors errors={errors} name="new_password" />
                </InputArea>

                <InputArea error={errors.confirm_password}>
                  <InputGroup>
                    <img src="/assets/img/auth/password.svg" />
                    <IputLogin
                      type="password"
                      {...register("confirm_password", {
                        required: true,
                        validate: (value) =>
                          value !== getValues("new_password")
                            ? (t(
                                "changePasswordPage.validate.confirmPassword"
                              ) as string)
                            : true,
                      })}
                      placeholder={t(
                        "changePasswordPage.placeholder.confirmPassword"
                      )}
                    />
                  </InputGroup>
                  <Errors errors={errors} name="confirm_password" />
                </InputArea>

                <CaptchaContainer>
                  <LoadCanvasTemplateNoReload />
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

                <SCButtonLogin
                  disabled={loading || Object.keys(errors).length > 0}
                >
                  <ButtonSubmit>
                    {loading ? (
                      <>
                        <ButtonSubmitText>Submitting...</ButtonSubmitText>
                        <div
                          style={{
                            width: "30px",
                            height: "20px",
                            display: "flex",
                            justifyContent: "center",
                            alignItems: "center",
                          }}
                        >
                          <VFLoader
                            styles={{ width: "50px", height: "50px" }}
                          />
                        </div>
                      </>
                    ) : (
                      <>
                        <ButtonSubmitText>
                          {t("changePasswordPage.submitBtn")}
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
                      </>
                    )}
                  </ButtonSubmit>
                </SCButtonLogin>
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

export default ChangePasswordContainer;
