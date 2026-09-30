import React from "react";
import {
  HeaderSection,
  HeaderText,
  LeftCommonComUploadWrapper,
  LeftCommonComWrapper,
  LeftStep,
  SubText,
} from "./style";
import ButtonFloat from "../../../../src/components/commons/ButtonFloat";

interface LeftCommonComProps {
  step: number;
  img: string;
  headerText: string;
  subText: string;
  btnText: string;
  btnImg: string;
  btnStyles?: React.CSSProperties;
  imgStyles?: React.CSSProperties;
  handleClick: (e:any)=>void;
}

function LeftCommonCom({
  step,
  img,
  headerText,
  subText,
  btnText,
  btnImg,
  btnStyles,
  imgStyles,
  handleClick
}: LeftCommonComProps) {

  
  return (
    <LeftCommonComWrapper>
      <LeftStep>Step {step}</LeftStep>
      <LeftCommonComUploadWrapper>
        <div
          style={{
            display: "flex",
            gap: "1rem",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <img src={img} alt="" style={imgStyles} />
          <HeaderSection>
            <HeaderText>{headerText}</HeaderText>
            <SubText fontSize="1.15rem" >{subText}</SubText>
          </HeaderSection>
        </div>
        <ButtonFloat
          onClick={(e:any)=>{handleClick(e)}}
          text={btnText}
          icon={btnImg}
          styles={btnStyles}
        ></ButtonFloat>
      </LeftCommonComUploadWrapper>
    </LeftCommonComWrapper>
  );
}

export default LeftCommonCom;
