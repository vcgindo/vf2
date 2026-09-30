import { useTranslation } from "react-i18next";
import {
  SCProfileOverView,
  SCSubTitleBox,
  SCSubTitlePad,
  SCSubTitleSpan,
  SCOverviewInfo,
  SCOverviewItem,
  SCOverviewItemTitle,
  SCOverViewSignItem,
  SCIconChecked,
  SCOverviewWrap,
  SCOverviewFlex,
  SCProfileOverViewCol,
  SCSubTitleSpanItem,
  SCOverviewItemContent,
  SCOverviewInfoPermis,
  SCOverviewItemPerTitle,
  // SCOverviewItemPerTitleLoca,
  SCOverviewWrapTitle,
  SCOverviewWrapItem,
} from "./styles";
import { useSelector } from "react-redux";
import { RootState } from "../../../redux/store/store";

const Permissions = ({ roles }: any) => {
  console.log(roles);
  const { t } = useTranslation();

  const generateProductPermissionsList = (roles:any) => {
    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const PRODUCT_PERMISSION_L1 = EnvConfig['PRODUCT_PERMISSION_L1'];   
    const PRODUCT_PERMISSION_L2 = EnvConfig['PRODUCT_PERMISSION_L2'];   
    const PRODUCT_PERMISSION_L3 = EnvConfig['PRODUCT_PERMISSION_L3']; 

    return roles?.product_permission.map((application:any)=>{
      const listBrand = application.product_hierarchy_1;
      const listSubBrand = application.product_hierarchy_2;
      const listCategories = application.product_hierarchy_3;
      return {
        'application_name':application['application_name'],
        'permissions':[
          {
            title: t("profile.tabContent.permissions.L1"),
            name: PRODUCT_PERMISSION_L1,
            data: listBrand,
          },
          {
            title: t("profile.tabContent.permissions.L2"),
            name: PRODUCT_PERMISSION_L2,
            data: listSubBrand,
          },
          {
            title: t("profile.tabContent.permissions.L3"),
            name: PRODUCT_PERMISSION_L3,
            data: listCategories,
          },
        ]
      }
    })
  }

  const generateLocationPermissionsList = (roles:any) => {
    const EnvConfig = useSelector((state:RootState) =>state.mta.EnvConfig);
    const LOCATION_PERMISSION_L1 = EnvConfig['LOCATION_PERMISSION_L1']; 
    const LOCATION_PERMISSION_L2 = EnvConfig['LOCATION_PERMISSION_L2']; 
    const LOCATION_PERMISSION_L3 = EnvConfig['LOCATION_PERMISSION_L3']; 
    return roles?.location_permission.map((application:any)=>{
      const listLCRegion = application.location_heirarchy_1;
      const listLCType = application.location_heirarchy_2;
      const listLCCluster = application.location_heirarchy_3;
      return {
        'application_name':application['application_name'],
        'permissions':[
          {
            title: t("profile.tabContent.permissions.L1"),
            name: LOCATION_PERMISSION_L1,
            data: listLCRegion,
          },
          {
            title: t("profile.tabContent.permissions.L2"),
            name: LOCATION_PERMISSION_L2,
            data: listLCType,
          },
          {
            title: t("profile.tabContent.permissions.L3"),
            name:LOCATION_PERMISSION_L3,
            data: listLCCluster,
          },
        ]
      }
    })
  }
  
  return (
    <>
      <SCProfileOverView>
        <SCSubTitleBox>
          <SCSubTitlePad>
            <SCSubTitleSpan>
              {t("profile.tabContent.permissions.title")}
            </SCSubTitleSpan>
          </SCSubTitlePad>
        </SCSubTitleBox>
        <SCOverviewInfo>
          <SCOverviewWrap>
            {/* <SCOverviewWrapTitle>
              {t(
                "profile.tabContent.permissions.roleAndPermissions.interStoreTransfer"
              )}
            </SCOverviewWrapTitle> */}
            <SCOverviewWrapItem checkBackGround={roles?.permission?.length === 3}>
              {roles?.permission?.map((item: any, index: number) => (
                <SCOverviewItem
                  key={index}
                  checkBorderBottom={roles?.permission?.length > 2}
                >
                  <SCIconChecked src="/assets/img/check/checked_black.svg" />
                  <SCOverviewItemTitle>{item}</SCOverviewItemTitle>
                </SCOverviewItem>
              ))}
            </SCOverviewWrapItem>
          </SCOverviewWrap>
        </SCOverviewInfo>
      </SCProfileOverView>

      <SCOverviewFlex>
        <SCProfileOverViewCol>
          <SCSubTitleBox>
            <SCSubTitlePad>
              <SCSubTitleSpan>
                {t("profile.tabContent.permissions.productPermission.title")}
              </SCSubTitleSpan>
            </SCSubTitlePad>
          </SCSubTitleBox>

          <SCOverviewInfoPermis>
            {generateProductPermissionsList(roles)?.map((application:any)=>(
              <div style={{margin:'5px'}}>
                <SCOverviewWrapTitle>
                  {application?.application_name}
                </SCOverviewWrapTitle>
                {
                  application?.permissions?.map((dataPrd: any) => (
                    <SCOverViewSignItem>
                      <SCSubTitleSpan>{dataPrd?.title}</SCSubTitleSpan>
                      <SCSubTitleSpanItem>
                        <SCOverviewItemPerTitle>
                          {dataPrd?.name}
                        </SCOverviewItemPerTitle>
                        <SCOverviewItemContent>-</SCOverviewItemContent>
                        <SCOverviewItemContent>
                          {dataPrd?.data?.toString()?.replace(/,/g, " | ")}
                        </SCOverviewItemContent>
                      </SCSubTitleSpanItem>
                    </SCOverViewSignItem>
                  ))
                }
              </div>
            ))}
          </SCOverviewInfoPermis>
        </SCProfileOverViewCol>

        <SCProfileOverViewCol>
          <SCSubTitleBox>
            <SCSubTitlePad>
              <SCSubTitleSpan>
                {t("profile.tabContent.permissions.locationPermission.title")}
              </SCSubTitleSpan>
            </SCSubTitlePad>
          </SCSubTitleBox>
          <SCOverviewInfoPermis>
            {generateLocationPermissionsList(roles)?.map((application:any)=>(
              <div style={{margin:'10px 5px'}}>
                <SCOverviewWrapTitle>
                  {application?.application_name}
                </SCOverviewWrapTitle>
                {
                  application?.permissions?.map((dataPrd: any) => (
                    <SCOverViewSignItem>
                      <SCSubTitleSpan>{dataPrd.title}</SCSubTitleSpan>
                      <SCSubTitleSpanItem>
                        <SCOverviewItemPerTitle>
                          {dataPrd.name}
                        </SCOverviewItemPerTitle>
                        <SCOverviewItemContent>-</SCOverviewItemContent>
                        <SCOverviewItemContent>
                          {dataPrd?.data?.toString()?.replace(/,/g, " | ")}
                        </SCOverviewItemContent>
                      </SCSubTitleSpanItem>
                    </SCOverViewSignItem>
                  ))
                }
              </div>
            ))}
          </SCOverviewInfoPermis>
        </SCProfileOverViewCol>
      </SCOverviewFlex>
    </>
  );
};

export default Permissions;
