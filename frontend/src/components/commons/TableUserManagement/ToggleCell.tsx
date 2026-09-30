import * as Tab from "./style";
import { ButtonOutlineStoreStatus } from "../../index";
import { useChangeStatus } from "../../../services/profile";
import { notifyError, notifySuccess } from "../../../helpers/notify";
import { useTranslation } from "react-i18next";
import { useState } from "react";

const ToggleCell = ({ data, permission, is_admin }:any) => {
  const { t } = useTranslation();
  const { mutateAsync: mutateChangeStatus } = useChangeStatus();
  const [isActive, setIsActive] = useState(data.is_active);

  const changeStatus = (status:any) => {
    setIsActive(status);
    const payload = {
      user_id: data.id,
      is_active: status,
    };

    mutateChangeStatus(payload, {
      onSuccess: (res:any) => {
        if (res?.status === 400) {
          notifyError(res?.response?.msg);
          setIsActive(!status);
        } else {
          notifySuccess(res?.data?.msg);
        }
      },
      onError: (error:any) => {
        console.error("error", error);
        notifyError(error.msg);
        setIsActive(!status);
      },
    });
  };

  const permissionUser = data.role_id.map((item:any) => item.name);

  if (is_admin) {
    if (data.is_admin) {
      return null; // Or return a component indicating no action
    }
  } else {
    if (
      (permission?.includes("IST Admin") || permission?.includes("Admin")) &&
      (permissionUser?.includes("IST Admin") || permissionUser?.includes("Admin"))
    ) {
      return null;
    }
  }

  return (
    <Tab.SCTableTdCenter>
      <ButtonOutlineStoreStatus
        labelOn={t("profile.tabContent.manageUsers.button.active")}
        labelOff={t("profile.tabContent.manageUsers.button.inactive")}
        toggled={isActive}
        onClick={changeStatus}
      />
    </Tab.SCTableTdCenter>
  );
};

export default ToggleCell;