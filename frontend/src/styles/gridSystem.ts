import styled from "styled-components";
import * as globalStyles from "./global";
import * as gridSystem from "./gridSystem";

const customTransition = "all 0.3s ease";

export const size = {
  mobileS: "320px",
  mobileM: "375px",
  mobileL: "425px",
  tablet: "768px",
  laptop: "1024px",
  laptopL: "1440px",
  desktop: "1688px",
};

export const SCGrid = styled.div`
  // margin: 0 auto;
  // padding: 0 ${globalStyles.pd};
  @media (min-width: ${size.laptopL}) {
    // max-width: 1850px;
  }
`;

export const SCRow = styled.div`
  margin-left: calc(var(--pd) * -1);
  margin-right: calc(var(--pd) * -1);
  display: flex;
  flex-wrap: wrap;
  min-height: 90vh;
`;

export const SCFull = styled.div`
  max-width: 1260px;
  padding-left: ${globalStyles.pd};
  padding-right: ${globalStyles.pd};
  display: flex;
  flex-wrap: wrap;
`;
export const SCCol = styled.div`
  padding-left: ${globalStyles.pd};
  padding-right: ${globalStyles.pd};
`;

export const SCCol1 = styled.div<{colorTheme: string}>`
  flex: 0 0 3%;
  background-color: ${props => globalStyles.chooseThemeColor[props.colorTheme]?.color1};
  z-index: 4;
`;

export const SCCol2 = styled.div<{ width: any, colorTheme: string }>`
  flex: 0 0 ${(props) => props.width.widthLeft};
  max-width: ${(props) => props.width.widthLeft};
  transition: ${customTransition};
  background-color:  ${props => globalStyles.chooseThemeColor[props.colorTheme]?.color2};
`;

export const SCCol4 = styled.div`
  flex: 0 0 33.33%;
  max-width: 33.33%;
`;
export const SCCol5 = styled.div`
  flex: 0 0 66.66%;
  max-width: 66.66%;
`;

export const SCCol6 = styled.div`
  flex: 0 0 50%;
  max-width: 50%;
`;

export const SCCol8 = styled.div<{ width: any, hidePadding:boolean,disableZoomScaling?:boolean }>`
  flex: 0 0 ${(props) => props.width.widthRight};
  max-width: ${(props) => props.width.widthRight};
  padding-left: ${(props)=> props.hidePadding ? 0 : 50}px;
  transition: ${customTransition};
  zoom:${props=>props.disableZoomScaling ? 1 : 0.75};
  // overflow:scroll;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
      .size.desktop}) {
    padding-left: ${(props)=> props.hidePadding ? 0 : 50}px;
    zoom:${props=>props.disableZoomScaling ? 1 : 0.75};
  }

  @media (min-width: ${gridSystem.size.desktop}) {
    padding-left: ${(props)=> props.hidePadding ? 0 : 50}px;
    zoom:1;
}
`;
export const SCFullScreen = styled.div`
  height: 10vh;
  position: sticky;
  top: 0px;
  z-index: 9990;
`;
