import { useState } from "react";
import {
  SCProfileOverView,
  SCSubTitleBox,
  SCSubTitlePad,
  SCSubTitleSpan,
  SCOverviewInfo,
  SCOverviewItem,
  SCOverviewItemTitle,
  SCOverViewSignItem,
  SCButtonSignIn,
  SCBoxChangePassword,
  SCChangePasswordLabel,
  SCChangePasswordInput,
  SCChangePasswordBox,
  SCChangePasswordFlex,
  SCChangePasswordSubmit,
  SCChangePasswordCancel,
} from "./styles";
import { useForm } from "react-hook-form";
import { useChangePassword } from "../../../services/profile";
import { useUserData } from "../../../../src/context";
import { notifyError, notifySuccess } from "../../../helpers/notify";
import { Errors } from "../../../components";
import { useTranslation } from "react-i18next";

const Overview = ({ themeUi }: any) => {
  const { t } = useTranslation();
  const { user } = useUserData();
  const [show, setShow] = useState(true);

  const form = useForm({
    mode:"onChange",
    defaultValues: {
      old_password: "",
      new_password: "",
      confirm_password: "",
    },
  });

  const {
    register,
    handleSubmit,
    getValues,
    reset,
    formState: { errors },
  } = form;
  const { mutate: mutateChangePassword } = useChangePassword();

  const onSave = () => {
    const formData = getValues();
    mutateChangePassword(formData, {
      onSuccess: (data: any) => {
        if (data?.status === 200) {
          notifySuccess(
            t("profile.tabContent.overview.notify.changePswSuccess")
          );
          reset();
          setShow(true);
        } else {
          notifyError(data?.response?.msg || data?.response?.detail);
        }
      },
      onError: (errors: any) => {
        console.log("errors", errors);
        notifyError(errors.response.msg);
      },
    });
  };

  return (
    <>
      <SCProfileOverView>
        <SCSubTitleBox>
          <SCSubTitlePad>
            <SCSubTitleSpan>
              {t("profile.tabContent.overview.title")}
            </SCSubTitleSpan>
          </SCSubTitlePad>
        </SCSubTitleBox>
        <SCOverviewInfo>
          <SCOverviewItem>
            <SCOverviewItemTitle>
              {t("profile.tabContent.overview.fullName")}
            </SCOverviewItemTitle>
            <SCSubTitleSpan>{user?.user?.name}</SCSubTitleSpan>
          </SCOverviewItem>
          {/* <SCOverviewItem>
            <SCOverviewItemTitle>
              {t("profile.tabContent.overview.contactNo")}
            </SCOverviewItemTitle>
            <SCSubTitleSpan></SCSubTitleSpan>
          </SCOverviewItem> */}
          <SCOverviewItem>
            <SCOverviewItemTitle>
              {t("profile.tabContent.overview.role")}
            </SCOverviewItemTitle>
            <SCSubTitleSpan>
              {user?.roles?.permission.toString().replace(/,/g, " | ")}
            </SCSubTitleSpan>
          </SCOverviewItem>
        </SCOverviewInfo>
      </SCProfileOverView>
      <SCProfileOverView>
        <SCSubTitleBox>
          <SCSubTitlePad>
            <SCSubTitleSpan>
              {t("profile.tabContent.overview.signInDetails")}
            </SCSubTitleSpan>
          </SCSubTitlePad>
        </SCSubTitleBox>
        <SCOverviewInfo>
          <SCOverViewSignItem>
            <div>
              <SCSubTitleSpan>
                {t("profile.tabContent.overview.email")}
              </SCSubTitleSpan>
              <SCOverviewItemTitle>{user.user.email}</SCOverviewItemTitle>
            </div>
            <SCButtonSignIn>
              {t("profile.tabContent.overview.button.notEditable")}
            </SCButtonSignIn>
          </SCOverViewSignItem>
          {show ? (
            <SCOverViewSignItem>
              <div>
                <SCSubTitleSpan>
                  {t("profile.tabContent.overview.password")}
                </SCSubTitleSpan>
                <SCOverviewItemTitle>
                  {t("profile.tabContent.overview.passwordPlaceholder")}
                </SCOverviewItemTitle>
              </div>
              <SCButtonSignIn
                onClick={() => {
                  setShow(false);
                }}
              >
                {t("profile.tabContent.overview.button.resetPsw")}
              </SCButtonSignIn>
            </SCOverViewSignItem>
          ) : (
            <form onSubmit={handleSubmit(onSave)}>
              <SCBoxChangePassword>
                <SCChangePasswordBox>
                  <SCChangePasswordLabel>
                    {t("profile.tabContent.overview.currentPsw")}
                  </SCChangePasswordLabel>
                  <SCChangePasswordInput
                    type="password"
                    {...register("old_password", { required: true })}
                  />
                </SCChangePasswordBox>
                <SCChangePasswordBox>
                  <SCChangePasswordLabel>
                    {t("profile.tabContent.overview.newPsw")}
                  </SCChangePasswordLabel>
                  <SCChangePasswordInput
                    type="password"
                    {...register("new_password", {
                      required: true,
                      minLength: {
                        value: 8,
                        message: t("loginPage.validate.password"),
                      },
                      maxLength: {
                        value: 15,
                        message: t("loginPage.validate.passwordMaxLength"),
                      },
                      pattern: {
                        value:
                          // eslint-disable-next-line no-useless-escape
                          /^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*()\-_=+{}[\]|;:'",.<>/?])(?=.*[a-zA-Z]).{8,}$/,
                        message: t(
                          "profile.tabContent.manageUsers.validate.formatPassword"
                        ),
                      },
                      validate: (value) => {
                        if (value.includes(" ")) {
                          return t("loginPage.validate.includeSpace" ) || "Password mush not contain spaces.";
                        }
                        return true;
                      }
                    })}
                  />
                </SCChangePasswordBox>
                <SCChangePasswordBox>
                  <SCChangePasswordLabel>
                    {t("profile.tabContent.overview.confirmPsw")}
                  </SCChangePasswordLabel>
                  <SCChangePasswordInput
                    type="password"
                    {...register("confirm_password", { 
                      required: true,
                      validate: (value)=>{
                        if(value !== getValues("new_password")){
                          return t("changePasswordPage.validate.confirmPassword") || "Passwords must match";
                        }
                        return true;
                      }
                    }
                     
                    )}
                  />
                </SCChangePasswordBox>
              </SCBoxChangePassword>

              <SCBoxChangePassword style={{ paddingTop: 0 }}>
                <SCChangePasswordBox>
                  <Errors errors={errors} name="old_password" />
                </SCChangePasswordBox>
                <SCChangePasswordBox>
                  <Errors errors={errors} name="new_password" />
                </SCChangePasswordBox>
                <SCChangePasswordBox>
                  <Errors errors={errors} name="confirm_password" />
                </SCChangePasswordBox>
              </SCBoxChangePassword>

              <SCChangePasswordFlex>
                <SCChangePasswordSubmit type="submit" disabled={Object.keys(errors).length > 0} themeUi={themeUi}>
                  {t("profile.tabContent.overview.button.updatePsw")}
                </SCChangePasswordSubmit>
                <SCChangePasswordCancel
                  onClick={() => {
                    setShow(true);
                  }}
                >
                  {t("profile.tabContent.overview.button.cancel")}
                </SCChangePasswordCancel>
              </SCChangePasswordFlex>
            </form>
          )}
        </SCOverviewInfo>
      </SCProfileOverView>
    </>
  );
};

export default Overview;
