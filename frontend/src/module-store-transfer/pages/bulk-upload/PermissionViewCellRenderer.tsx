import { CustomCellRendererProps } from "ag-grid-react";
import React, { useEffect, useState } from "react";
import VFButton from "../../../components/VectorFLOW/commons/VFButton";
import { useUserData } from "../../../context";
import { notifyWarning } from "../../../helpers/notify";
import { Container, ImageSpan } from "./style";

interface MyCellRendererProps extends CustomCellRendererProps {
  allPermissions?: any[];
  setIsPermissionModalOpen?: (open: boolean) => void;
  setRowIndex: (index: number) => void;
  enabledPermissionsRow?: any[];
}

const PermissionViewCellRenderer = (params: MyCellRendererProps) => {
  const PermissionCount =
    params.data.permissions &&
    typeof params.data.permissions === "object" &&
    !Array.isArray(params.data.permissions)
      ? Object.keys(params.data.permissions).length
      : 0;

  const user = useUserData();
  const themeUi = user.user.user.theme_ui;

  return (
    <>
      {PermissionCount > 0 ? (
        <Container>
          {
            params.data.errorPermission ?
              <ImageSpan>
                <img
                  style={{ width: "20px", height: "20px" }}
                  src="\assets\img\error_icon.svg" alt="" />
              </ImageSpan>
              :
              <ImageSpan>
                <img
                  style={{ width: "20px", height: "20px" }}
                  src="\assets\img\check_list_icon.svg" alt="" />
              </ImageSpan>
          }
          
          <VFButton
            style={{ width: "80%", height: "25px", fontSize: "1rem" }}
            themeUi={themeUi}
            onClick={() => {
              if (params?.data?.roles?.size && params?.data?.roles?.size > 0) {

                params.setRowIndex(params.node.rowIndex || 0);
                params.setIsPermissionModalOpen?.(true);
              }
              else {
                notifyWarning("select a role before editing permissions");
              }
            }}
          >
            {"View / Edit Permissions"}
          </VFButton>
        </Container>
      ) : (
        <Container> 
            {
              params.data.errorPermission &&
              <ImageSpan>
                <img
                  style={{ width: "20px", height: "20px" }}
                  src="\assets\img\error_icon.svg" alt="" />
              </ImageSpan>
            }
          <VFButton
            style={{ width: "80%", height: "25px", fontSize: "1rem" }}
            themeUi={themeUi}
            onClick={() => {
              if (params?.data?.roles?.size && params?.data?.roles?.size > 0) {
                params.setRowIndex(params.node.rowIndex || 0);
                params.setIsPermissionModalOpen?.(true);
              }
              else {
                notifyWarning("select a role before selecting permissions");
              }
            }}
          >
            {"Select Permissions"}
          </VFButton>
        </Container>   
      )}
    </>
  );
};

export default PermissionViewCellRenderer;
