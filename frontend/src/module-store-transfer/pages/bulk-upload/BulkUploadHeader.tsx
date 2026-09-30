import React, { useEffect, useRef, useState } from "react";
import VFButton from "../../../components/VectorFLOW/commons/VFButton";
import { CSSProperties } from "styled-components";
import Portal from "../../../components/VectorFLOW/layouts/Portal";
import { DropdownWrapper } from "../../../components/commons/CustomDropdown/style";
import { SCGoBackContainer, SCGoBackText } from "../../../components/VectorFLOW/commons/MTO/ActionToolBar/styles";
import { GridRef } from "../../../VectorFlow/types/MDM";
import { ActionButton } from "./style";
import { notifyWarning } from "../../../helpers/notify";
import _ from "lodash";

/**
 * Props for the BulkUploadHeader component.
 * @typedef {Object} BulkUploadHeaderParams
 * @property {any} themeUi - The theme configuration for the UI.
 * @property {function(boolean): void} setIsPermissionModalOpen - Function to toggle the permission modal.
 * @property {function(boolean): void} setIsRoleModalOpen - Function to toggle the role modal.
 * @property {boolean | undefined} isBulkActionEnabled - Indicates if the bulk action button is enabled.
 * @property {function(): void} resetState - Function to reset the state.
 * @property {GridRef | any} gridRef - Reference to the grid for exporting data.
 */
type BulkUploadHeaderParams = {
  themeUi: any;
  setIsPermissionModalOpen: (e: boolean) => void;
  setIsRoleModalOpen: (e: boolean) => void;
  isBulkActionEnabled: any;
  resetState: () => void;
  gridRef?: GridRef | any;
  removeSelectedUser: () => void,
};

/**
 * BulkUploadHeader component for managing bulk upload actions.
 * 
 * @param {BulkUploadHeaderParams} props - The props for the component.
 * @returns {JSX.Element} The rendered BulkUploadHeader component.
 */
const BulkUploadHeader = ({
  themeUi,
  setIsPermissionModalOpen,
  setIsRoleModalOpen,
  isBulkActionEnabled,
  resetState,
  gridRef,
  removeSelectedUser
}: BulkUploadHeaderParams): JSX.Element => {
  const [open, setOpen] = useState(false);
  const [dropdownPosition, setDropdownPosition] = useState<CSSProperties>({});
  const buttonRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  /**
   * Handles clicks outside the dropdown to close it.
   * 
   * @param {MouseEvent} e - The mouse event.
   */
  const handleClickOutside = (e: MouseEvent) => {
    if (
      dropdownRef.current &&
      !dropdownRef.current.contains(e.target as Node) &&
      !buttonRef.current?.contains(e.target as Node)
    ) {
      setOpen(false);
    } else {
      console.log("no ref found");
    }
  };

  // Add or remove event listener for handling clicks outside the dropdown
  useEffect(() => {
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
    } else {
      document.removeEventListener("mousedown", handleClickOutside);
    }

    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  /**
   * Handles the click event for the "Bulk Action" button.
   * 
   * @param {React.MouseEvent<HTMLElement>} e - The mouse event.
   */
  const onSelectClick = (e: React.MouseEvent<HTMLElement>) => {
    const { bottom, left } = e.currentTarget.getBoundingClientRect();
    setDropdownPosition({
      top: bottom + window.scrollY,
      bottom: bottom,
      left: left + window.scrollX,
    });
    setOpen(!open);
  };


  const areValidRoles = () => {
    let isValid = true;
    const applicationNameSet = new Set<string>();
  
    gridRef.current.api.forEachNode((node: any) => {
      if (node.isSelected()) {
        const roles = node.data.roles || [];
        if (roles.size > 0) {
          const roleArr:any = [];
          roles.forEach((role: any) => {
            if (role.application_name) {
              roleArr.push(role.application_name);
            }
          });
          const uniqueApps = _.uniq(roleArr).sort();
          applicationNameSet.add(uniqueApps.join(","));
        }
        else{
          isValid = false;
        }
      }
    });
    if(applicationNameSet?.size===0){
      notifyWarning("First select the roles for the users before assigning permissions.");
      return false;
    }
  
    if (!isValid) {
      notifyWarning("All the users must have roles of the same applications.");
      return false;
    }
  
    if (applicationNameSet.size > 1) {
      notifyWarning("All selected users must have roles with the same application name.");
      return false;
    }
  
    return true;
  };

  return (
    <div
      style={{
        display: "flex",
        width: "100%",
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "20px",
        marginBottom: "20px",
      }}
    >
      {/* Go Back Section */}
      <div>
        <SCGoBackContainer style={{ paddingLeft: "10px" }} onClick={resetState}>
          <img
            src="/assets/img/VectorFLOW/BPR/goback.svg"
            alt=""
            style={{ height: "20px" }}
          />
          <SCGoBackText style={{ fontSize: "1.5rem" }}>
            <b>Go Back</b>
          </SCGoBackText>
        </SCGoBackContainer>
      </div>

      {/* Action Buttons */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        {/*Remove user Button*/}
        <VFButton
          disabled={!isBulkActionEnabled?.removeUserEnable}
          style={{ width: "120px", height: "35px", fontSize: "1rem" }}
          themeUi={themeUi}
          onClick={removeSelectedUser}
        >
          {"Remove Selected User"}
        </VFButton>

        {/* Bulk Action Button */}
        <VFButton
          disabled={!isBulkActionEnabled.bulkActionEnable}
          style={{ width: "150px", height: "35px", fontSize: "1rem" }}
          themeUi={themeUi}
          onClick={onSelectClick}
        >
          {"Bulk Action For Selected User"}
        </VFButton>

      </div>

      {/* Dropdown Menu */}
      {open && (
        <Portal wrapperId="checkbox-dropdown">
          <DropdownWrapper
            ref={dropdownRef}
            topPos={dropdownPosition.top + "px"}
            leftPos={dropdownPosition.left + "px"}
          >
            <div
              style={{
                width: "100px",
                height: "54px",
                display: "flex",
                flexDirection: "column",
              }}
            >
              {/* Roles Action */}
              <ActionButton
                onClick={() => {
                  
                  setIsRoleModalOpen(true);
                  setOpen(false);
                }}
              >
                Roles
              </ActionButton>

              {/* Permissions Action */}
              <ActionButton
                onClick={() => {
                  if(!areValidRoles()){
                    return;
                  }
                  setIsPermissionModalOpen(true);
                  setOpen(false);
                }}
              >
                Permissions
              </ActionButton>
            </div>
          </DropdownWrapper>
        </Portal>
      )}
    </div>
  );
};

export default BulkUploadHeader;
