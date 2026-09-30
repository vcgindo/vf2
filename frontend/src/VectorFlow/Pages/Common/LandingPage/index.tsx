import React, { Fragment, useEffect, useRef, useState } from "react";
import { useUserData } from "../../../../context";
import { listMenuParent } from "../../../../../src/components/layouts/NavbarMenu/listMenu";
import {
  AppBox,
  ImageHolder,
  LandingContainer,
  LandingPageDivider,
  Rectangle,
  Image,
  AppBoxDivider,
  ClickBox,
  CardContainer,
  AppBoxDiv,
} from "./LandingPage.styled";
import { ApplicationName } from "../../MTO/Common/Enum";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";

const LandingPage = () => {
  const { user } = useUserData();
  const [listMenu] = useState(listMenuParent);
  const map = useRef(new Map());
  const { t } = useTranslation();
  const [renderMap, setRenderMap] = useState(new Map());
  const navigate = useNavigate();

  const themeUi = user?.user?.theme_ui;

  const findUrl = (item: any)=>{
    const checkUrl = user?.url_permission?.some((value : any)=>{
      return item.url == value;
    })
    if(checkUrl){
      return item.url;
    }else if(item?.child){
      item.child.forEach((child : any)=>{
        const foundUrl =  findUrl(child);
        if(foundUrl){
          return foundUrl;
        }
      })
    }
    return null;
  }

  const CreateMenuFunction = (app_id: any, item: any) => {
    if (item?.lp_attr) {
        const currentList = map.current.get(app_id) || [];
        if (
          !currentList.some(
            (existingItem: any) => existingItem.name === item.name
          )
        ) 
        {
          const checkUrl = user?.url_permission?.some((value : any)=>{
            return item.url == value;
          })
          let url = undefined;
          if(checkUrl){
              url = item.url
          }else{
            if(item?.child){
              for (const child of item.child) {
                url = findUrl(child);
                if (url != null && url != undefined) {
                  break;  // Exit the loop once URL is found
                }
              }
            }
          }
          if(url != null && url != undefined){
            currentList.push({
              name: item.name,
              img: themeUi === "REGALBLAZE" ? item.rp_img : item.lp_img,
              // img:item.lp_img,
              url: url,
            });
          }
          map.current.set(app_id, currentList);
        
      }
       else{
        const curr = currentList.find((existingItem: any) => existingItem.name == item.name)
        if(curr){
          curr.img = themeUi === "REGALBLAZE" ? item.rp_img : item.lp_img;
        }   
      }
    
    } else if (item?.child) {
      item?.child.forEach((child: any) => {
        CreateMenuFunction(app_id, child);
      });
    }
  };

  const createMenu = () => {
    listMenu?.forEach((item: any) => {

        CreateMenuFunction(item?.app_id, item);
      
    });
  };

  useEffect(() => {
    createMenu();
    setRenderMap(new Map(map.current));
  }, [themeUi]);


  const [myMap, setMyMap] = useState<any>(null);
  useEffect(()=>{
    setMyMap(map);
  },[map])


  const imageSrc = themeUi === "REGALBLAZE" 
  ? "/assets/img/Clicktoview1.svg" 
  : "/assets/img/Clicktoview.svg"; 
  return (
    <LandingContainer>
      <h1 style={{ fontSize: "2rem" }}>
        Welcome to{" "}
        <span style={{ color: themeUi === "REGALBLAZE" ? "rgb(199, 129, 14)" : "#BC3D81", marginBottom: 0 }}>VectorFlow</span>
      </h1>
      <h3 style={{ color: "#707070", top: 0, marginTop: "-2%" }}>
        A seamless, end to end supply chain management system
      </h3>
      <>
        {myMap && Array.from(myMap?.current?.entries()).map(
          (item: any, index: number, array: any[]) => {
            if (item[1]?.length > 0) {
              return (
                <Fragment key={index}>
                  <Rectangle  text={ApplicationName[item[0]]} theme={themeUi}>
                    <CardContainer>
                      {item[1].map((subItem: any, subIndex: number) => {
                        return (
                          <AppBox key={subIndex}>
                            <AppBoxDiv>
                              <ImageHolder theme={themeUi}>
                                <Image src={subItem.img} alt="Product" />
                              </ImageHolder>
                              <h3
                                style={{
                                  zIndex: 4,
                                  margin: "1.5rem 0 0.5rem 2.5rem",
                                }}
                              >
                                {t(subItem.name)}
                              </h3>
                              <AppBoxDivider />
                              <ClickBox onClick={()=>{
                                navigate(subItem?.url);
                              }}>
                                <p style={{ color: themeUi === "REGALBLAZE" ? "rgb(199, 129, 14)" : "#820F4C" }}>
                                  Click to view{" "}
                                </p>
                                <img
                                  style={{
                                    position: "relative",
                                    width: "7%",
                                    marginLeft: "1rem",
                                  }}
                                  src={imageSrc}
                                />
                              </ClickBox>
                            </AppBoxDiv>
                          </AppBox>
                        );
                      })}
                    </CardContainer>
                  </Rectangle>
                  {index < array.length - 1 && item.length > 0 && (
                    <LandingPageDivider />
                  )}
                </Fragment>
              );
            }
          }
        )}
      </>
    </LandingContainer>
  );
};

export default LandingPage;
