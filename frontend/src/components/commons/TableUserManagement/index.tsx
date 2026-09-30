import * as Tab from "./style";
import {  Modal } from "../../index";
import {
  UsePutDeleteUser,
  useResetPwd,
} from "../../../services/profile";
import { notifyError, notifySuccess } from "../../../helpers/notify";
import { useTranslation } from "react-i18next";
import {  useMemo, useRef, useState } from "react";
import VFTable from "../../../VectorFlow/Pages/MTO/Common/VFTable";
import LoadingSpinner from "../LoadingSpinner";
import { GridFilterWrapper, TextBtn } from "../../../VectorFlow/Pages/MTO/Common/VFPagination/styles";
import { useUserData } from "../../../context";
import ToggleCell from "./ToggleCell"; 
import Tooltip from "../../../VectorFlow/Pages/MTO/Common/Tooltip";

interface TableUser {
  handleClickEdit: any;
  dataAllUsers: any;
  refetch: any;
  is_admin: boolean;
  permission: any;
}

const TableUserManagement = ({
  handleClickEdit,
  dataAllUsers,
  refetch,
  is_admin,
  permission,
}: TableUser) => {
  const { t } = useTranslation();
  const [isOpenDelete, setIsOpenDelete] = useState(false);
  const [idUser, setIdUser] = useState<string>("");
  const [isDisabled, setIsDisabled] = useState<boolean>(true);
  const gridRef = useRef<any>(null);
  const { user } = useUserData();
  const theme_ui = user.user.theme_ui;

  const { mutateAsync: usePutDeleteUser, isLoading: isDeleting } = UsePutDeleteUser();
  const { mutateAsync: mutateResetPwd, isLoading: isResettingPwd } = useResetPwd();

  const isLoading = isDeleting || isResettingPwd;

  const handleDeleteUser = () => {
    setTimeout(() => {
      usePutDeleteUser(idUser, {
        onSuccess: (data: any) => {
          if (data?.status === 400) {
            notifyError(data?.response?.msg);
          } else {
            notifySuccess(data?.data?.msg);
          }
          setIsOpenDelete(false);
          refetch();
        },
        onError: (error: any) => {
          notifyError(error.response.msg || error.message);
          setIsOpenDelete(false);
        },
      });
    }, 200);
  };

  const handleResetPwd = (id: string) => {
    mutateResetPwd(id, {
      onSuccess: (res: any) => {
        if (res?.status === 400) {
          notifyError(res?.response?.msg);
        } else {
          notifySuccess("Password reset email has been sent successfully");
        }
      },
      onError: (error: any) => {
        console.log("error", error);
        notifyError(error.msg);
      },
    });
  };

  const handleOpenDelete = (id: string) => {
    setIsOpenDelete(true);
    setIdUser(id);
  };

  const renderAction = (item: any, is_admin: any) => {
    const permissionUser = item.role_id.map((item: any) => item.name);

    if (is_admin) {
      if (item.is_admin) {
        return <NoAction rolesMap={permissionUser} />;
      } else {
        return <>{action({ item, permissionUser })}</>;
      }
    } else {
      if (permission?.includes("IST Admin") || permission?.includes("Admin")) {
        if (item.is_admin) {
          return <NoAction rolesMap={permissionUser} />;
        } else {
          if (
            permissionUser?.includes("IST Admin") ||
            permissionUser?.includes("Admin")
          ) {
            return <NoAction rolesMap={permissionUser} />;
          } else {
            return <>{action({ item, permissionUser })}</>;
          }
        }
      } else {
        return <NoAction rolesMap={permissionUser} />;
      }
    }
  };

  const clearGridFilter = () => {
    gridRef?.current?.api.setFilterModel(null);
    setIsDisabled(true);
  };

  const CustomStatusPanel = () => {
    return (
      <GridFilterWrapper style={{ marginTop: '15px' }}>
        <TextBtn onClick={clearGridFilter} disabled={isDisabled} themeUi={theme_ui}>
          Clear All Grid Filters
        </TextBtn>
      </GridFilterWrapper>
    );
  };

  const ListAction = ({ item }: any) => {
    return (
      <>
        <Tab.SCTableTd>
          <Tab.SCIconWrapper>
            <Tooltip
              id="edit"
              content={<p style={{ fontSize: '1rem', padding: '4px' }}>Edit User</p>}
              place="top"
              className="user-manage-tooltip"
            >
              <Tab.SCIcon
                data-tooltip-id="edit"
                src="/assets/img/profile/icon_edit.svg"
                onClick={() => handleClickEdit(item)}
              />
            </Tooltip>
          </Tab.SCIconWrapper>

          <Tab.SCIconWrapper>
            <Tooltip
              id="delete"
              content={<p style={{ fontSize: '1rem', padding: '4px' }}>Delete User</p>}
              place="top"
              className="user-manage-tooltip"
            >
              <Tab.SCIcon
                data-tooltip-id="delete"
                src="/assets/img/profile/icon_delete.svg"
                onClick={() => {
                  handleOpenDelete(item.id);
                }}
              />
            </Tooltip>
          </Tab.SCIconWrapper>

          <Tab.SCIconWrapper>
            <Tooltip
              id="reset"
              content={<p style={{ fontSize: '1rem', padding: '4px' }}>Reset Password</p>}
              place="top"
              className="user-manage-tooltip"
            >
              <Tab.SCIcon
                data-tooltip-id="reset"
                src="/assets/img/profile/icon_lock.svg"
                onClick={() => {
                  handleResetPwd(item.id);
                }}
              />
            </Tooltip>
          </Tab.SCIconWrapper>
        </Tab.SCTableTd>
      </>
    );
  };

  const action = ({ item, permissionUser }: any) => {
    return (
      <>
        <ListAction item={item} />
      </>
    );
  };

  const NoAction = ({ rolesMap }: any) => {
    return <></>;
  };

  const columnDefs = useMemo(
    () => [
      {
        headerName: "User ID",
        field: "name",
        flex: 1,
      },
      {
        headerName: "Email ID",
        field: "email",
        flex: 1,
      },
      {
        headerName: "Roles",
        flex: 1.5,
        valueGetter: (params: any) =>
          params.data.role_id?.map((r: any) => r.name).join(" | ") || "",
        filter: "agTextColumnFilter",
        cellRenderer: (params: any) => {
          const value = params.value || "";
          const tooltipId = `roles-tooltip-${params.node.id}`;

          return (
            <>
              <span
                data-tooltip-id={tooltipId}
                style={{
                  display: "inline-block",
                  maxWidth: "50%",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {value}
              </span>
              <Tooltip
                id={tooltipId}
                content={value}
                place="top"
                delayShow={0}
                positionStrategy="fixed"
                className="user-manage-tooltip"
              />
            </>
          );
        },
      },
      {
        headerName: "Actions",
        field: "actions",
        flex: 1,
        filter: false,
        suppressTooltips: true,
        tooltipValueGetter: () => '',
        cellRenderer: (params: any) => {
          return renderAction(params.data, is_admin);
        },
      },
      {
        headerName: "Active",
        field: "active",
        flex: 1,
        filter: false,
        suppressTooltips: true,
        cellRenderer: (params: any) => {
          return <ToggleCell data={params.data} permission={permission} is_admin={is_admin} />;
        },
      },
    ],
    [is_admin, permission]
  );

 

  return (
    <>
      {isLoading && <LoadingSpinner />}
      <VFTable
        ref={gridRef}
        rowData={dataAllUsers}
        columnDefs={columnDefs}
        domLayout="normal"
        rowHeight={55}
        pagination={false}
        height="450px"
        sideBar={false}
        getRowStyle={(params: any) => {
          if (params.node.rowIndex % 2 === 0) {
            return { background: "#F4F4F4" };
          }
          return { background: "#ffffff" };
        }}
        statusBar={{
          statusPanels: [
            { statusPanel: CustomStatusPanel, align: "left" },
            { statusPanel: 'agTotalAndFilteredRowCountComponent', align: 'right' },
            { statusPanel: 'agTotalRowCountComponent', align: 'right' },
            { statusPanel: 'agFilteredRowCountComponent', align: 'right' },
            { statusPanel: 'agSelectedRowCountComponent', align: 'right' },
            { statusPanel: 'agAggregationComponent', align: 'right' },
          ],
        }}
        onGridReady={(params: any) => {
          params.api.addEventListener('filterChanged', () => {
            const filterModel = params.api.getFilterModel();
            if (Object.keys(filterModel).length > 0) {
              setIsDisabled(false);
            } else {
              setIsDisabled(true);
            }
          });
        }}
      />
      {isOpenDelete && (
        <Modal
          fileJson=""
          modalTitle="Do you want to delete this user?"
          modalContent="This user will not be able to log back into the system after being deleted"
          openModal={isOpenDelete}
          closeModal={() => setIsOpenDelete(false)}
          onClickModal={handleDeleteUser}
          text="Delete"
        />
      )}
    </>
  );
};

export default TableUserManagement;