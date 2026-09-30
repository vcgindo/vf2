import React, { useState } from "react";
import Checkbox from "../../../components/VectorFLOW/commons/MTO/Checkbox";
import { useUserData } from "../../../context";
import VFButton from "../../../components/VectorFLOW/commons/VFButton";
import VFButtonOutline from "../../../components/VectorFLOW/commons/VFButtonOutline";
import { ModalContainer, ModalContent, Section, SectionHeader, RolesGrid, CheckboxLabel, ButtonSection } from "./style";

interface Role {
  id: number;
  name: string;
  application_name: string;
}

interface RoleSelectionModalProps {
  listRoles: Role[];
  updateRoles: (roles: Set<Role>) => void;
  closeModal: () => void;
  activeApplications: string[];
}



const RoleSelectionModal: React.FC<RoleSelectionModalProps> = ({
  listRoles,
  updateRoles,
  closeModal,
  activeApplications
}) => {

  const user = useUserData();
  const themeUi = user.user.user.theme_ui;
  const [selectedRoles, setSelectedRoles] = useState<Set<Role>>(new Set());
  const addRole = (item: Role) => {
    setSelectedRoles((prev) => new Set(prev).add(item));
  };
  const removeRole = (item: Role) => {
    setSelectedRoles((prev) => {
      const newSet = new Set(prev);
      newSet.delete(item);
      return newSet;
    });
  };
  const applicationGroups = Array.from(
    new Set(listRoles.map((role) => role.application_name).filter(app => activeApplications.includes(app)))
  );

  const [expandedApps, setExpandedApps] = useState<Record<string, boolean>>(
    Object.fromEntries(applicationGroups.map((app) => [app, true]))
  );

  const toggleSection = (appName: string) => {
    setExpandedApps((prev) => ({ ...prev, [appName]: !prev[appName] }));
  };

  return (
    <ModalContainer>
      <ModalContent>
        {applicationGroups.map((appName) => (
          <Section key={appName}>
            <SectionHeader
              onClick={() => toggleSection(appName)}
              style={{
                borderBottom: expandedApps[appName]
                  ? "1px solid #e0e0e0 "
                  : "none",
              }}
            >
              {appName}
              <span style={{ marginLeft: 8 }}>
                {expandedApps[appName] ? "▲" : "▼"}
              </span>
            </SectionHeader>
            {expandedApps[appName] && (
              <RolesGrid>
                {listRoles
                  .filter((role) => role.application_name === appName)
                  .map((role) => (
                    <CheckboxLabel
                      key={role.id}
                      style={{
                        userSelect: 'none',
                        display: "flex",
                        alignContent: "center",
                        alignItems: "center",
                        cursor: 'pointer'
                      }}
                      onClick={() => {
                        selectedRoles.has(role)
                          ? removeRole(role)
                          : addRole(role);
                      }}
                    >
                      <Checkbox
                        style={{ zoom: 0.5 }}
                        key={role.id}
                        theme={themeUi}
                        checked={selectedRoles.has(role)}
                        value={"true"}
                        onClick={(e) => e.stopPropagation()} // prevent double trigger
                        onChange={(e) =>
                          e.target.checked ? addRole(role) : removeRole(role)
                        }
                      />
                      <p
                        style={{ paddingTop: "1px", cursor: 'pointer' }}
                        onClick={(e) => {
                          e.stopPropagation();
                        }}
                      >
                        {role.name}
                      </p>
                    </CheckboxLabel>
                  ))}
              </RolesGrid>
            )}
          </Section>
        ))}
      </ModalContent>
      <ButtonSection>
        <VFButtonOutline
          disabled={false}
          style={{ width: "100px", height: "35px", fontSize: "1rem" }}
          themeUi={themeUi}
          onClick={() => {
            closeModal();
          }}
        >
          {"Cancel"}
        </VFButtonOutline>

        <VFButton
          disabled={false}
          style={{ width: "100px", height: "35px", fontSize: "1rem" }}
          themeUi={themeUi}
          onClick={()=>{updateRoles(selectedRoles); closeModal();}}
        >
          {"Update Roles"}
        </VFButton>
      </ButtonSection>
    </ModalContainer>
  );
};

export default RoleSelectionModal;
