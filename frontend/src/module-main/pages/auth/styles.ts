import { Link } from "react-router-dom";
import styled from "styled-components";
import * as gridSystem from "../../../styles/gridSystem";

export const SignInArea = styled.div`
  display: flex;
  flex-direction: row;
  height: 100vh;
  background: transparent linear-gradient(126deg, #f8f8fc 0%, #e1e2e8 100%) 0%
    0% no-repeat padding-box;
  opacity: 1;
  overflow: hidden;

  @media (max-width: 768px) {
    flex-direction: column;
  }

  .spinner--dotted {
    border: 5px dotted #fff;
  }
`;

export const SignInContainer = styled.div`
  flex: 1;
  position: relative;
`;

export const ContainerLeft: any = styled.div`
  display: flex;
  height: 100%;
  width: 100%;
`;

export const CircleLogin = styled.div`
  position: absolute;
  width: 170%;
  height: 170%;
  background: transparent linear-gradient(135deg, #000000 0%, #333333 100%) 0%
    0% no-repeat padding-box;
  border-top-right-radius: 50%;
  border-bottom-right-radius: 50%;
  top: -65%;
  right: 0;
`;

export const CircleForgotPassword = styled.div`
  position: absolute;
  width: 170%;
  height: 170%;
  background: transparent linear-gradient(45deg, #333333 0%, #000000 100%) 0% 0%
    no-repeat padding-box;
  border-top-left-radius: 50%;
  border-bottom-left-radius: 50%;
  top: -65%;
  left: 0;
`;
export const CaptchaContainer = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #ccc;
  width: fit-content;
  margin-top: 20px;
`;

export const CaptchaReload = styled.button`
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ac3072;   /* your brand pink/purple */
  border: none;
  border-radius: 6px;
  padding: 6px;
  cursor: pointer;
  transition: 0.3s ease;

  &:hover {
    background: #820f4c;
  }

  img {
    width: 20px;
    height: 20px;
    filter: brightness(0) invert(1); /* makes icon white */
  }
`;





export const ContainerRight: any = styled.div`
  display: flex;
  flex-direction: column;
  height: 100%;
  place-content: center;
  align-items: center;
`;
export const Tittle: any = styled.h1`
  color: #575f6b;
  font-size: 1.8vw;
  margin: -52px 0 0 0;

  @media (min-width: ${gridSystem.size.laptop}) and (max-width: ${gridSystem
    .size.laptopL}) {
    margin: -40px 0 0 0;
  }
`;

export const IputLogin: any = styled.input`
  border: none;
  font-weight: 500;
  font-size: 1.2vw;
  font-family: "Roboto", sans-serif;
  opacity: 1;
  position: relative;
  width: 100%;
  background: transparent;
  color: #707070;

  &::placeholder {
    color: #707070;
    font-size: 1.2vw;
  }

  &:focus {
    outline: none;
  }

  &:-webkit-autofill,
  &:-webkit-autofill:hover,
  &:-webkit-autofill:focus,
  &:-webkit-autofill:active {
    transition: background-color 9999s ease-in-out 0s;
    -webkit-text-fill-color: #707070 !important;
  }
`;
 
export const RecaptchaInput: any = styled.input`
  margin-top: 12px;
  padding: 10px;
  width: 50%;
  border-radius: 6px;
  border: 1px solid #ccc;
  font-size: 1rem;
  font-family: "Roboto", sans-serif;
  color: #707070;

  &::placeholder {
    color: #aaa;
  }

  &:focus {
    outline: none;
    border-color: #ac3072;
  }
`;



export const KeepSingIn: any = styled.div`
  display: flex;
  width: 100%;
  justify-content: space-between;
  margin: 4vh 0 0 0;
  padding: 0 0.5rem;
`;

export const KeepMe: any = styled.label`
  font-size: 0.8vw;
  font-weight: 500;
  font-family: "Roboto", sans-serif;
  letter-spacing: 0px;
  color: #707070;
`;

export const ChangePassText: any = styled.div`
  padding-top: 30px;
  width: 28vw;
  margin-left:65px;
`;

export const SCButtonLogin = styled.button<{ disabled?: boolean }>`
  cursor: ${({ disabled }) => (disabled ? "not-allowed" : "pointer")};
  font-size: 1vw;
  font-weight: bold;
  padding: 10px 0;
  display:flex;
  justify-content:center;
  align-items:center;
  text-align: center;
  transition: all 0.2s ease;
  background: ${({ disabled }) => (disabled ? "#E3DFDF" : "#ffffff")};
  box-shadow: 6px 6px 12px #c5c5c5, -6px -6px 12px #ffffff;
  border-radius: 40px;
  width: 17vw;
  height: 7vh;
  margin: 4vh 0 0 0;
  color: #575f6b;

  .arrow {
    height: 1.8vh;
  }

  .arrow-out {
    visibility: hidden;
  }

  &:hover {
    ${({ disabled }) =>
      !disabled &&
      `
      background: #ac3072;
      color: #ffffff !important;
      position: relative;
      transition: all 0.9s ease;

      span {
        color: #ffffff;
      }

      .arrow-in {
        display: none;
      }

      .arrow {
        transform: translate(30px, 0px);
        transition: all 0.5s ease-in;
      }

      .arrow-out {
        visibility: visible;
      }
    `}
  }
`;

export const LinkRouter: any = styled(Link)`
  font-size: 0.8vw;
  font-weight: 500;
  font-family: "Roboto", sans-serif;
  letter-spacing: 0px;
  color: #707070;
  text-decoration: none;
`;

export const FormArea: any = styled.form`
  display: flex;
  flex-direction: column;
  align-items: center;
  .recaptcha {
    padding-top: 0.4vh;
    margin: 4vh 0 0 0;
  }
`;

export const ButtonSubmit: any = styled.div`
  display: flex;
  justify-content:center;
  align-items:center;
  // width: 100%;
  // transform: translate(40%, 0);
`;

export const ButtonSubmitText: any = styled.span<{ isLoading?: boolean }>`
  margin-right: 1rem;
  color: ${({ isLoading }) => (isLoading ? "#808080" : "#575f6b")};
  font-size: 1vw;
  font-weight: bold;
  font-family: "Roboto", sans-serif;
  &:hover {
    ${({ isLoading }) => !isLoading && `color: #ffffff ;`}
  }
`;

export const ArrowArea: any = styled.div`
  display: flex;
  align-items: center;
`;

export const InputArea: any = styled.div<{ error: true | false , errorLength: number }>`
  border: ${(props) => (props.error ? "2px solid red" : "none")}; 
  margin-top: 6vh;
  background: transparent linear-gradient(278deg, #f2f3f6 0%, #e5e6ec 100%) 0%
    0% no-repeat padding-box;
  box-shadow: 6px 6px 20px #c5c5c5, -6px -6px 20px #ffffff;
  border-radius: 40px;
  width: 28vw;
  height: 8vh;
  margin-bottom: ${({error,errorLength})=> ( (error && errorLength > 50)? "2.5vh" : error ?  "0.3vh" : '0px')};
  
`;

export const InputGroup: any = styled.div`
  display: flex;
  height: 100%;
  width: 100%;
  padding: 0 2vw;
  align-items: center;
  gap: 1.2vw;

  img {
    width: 1.5vw;
  }
`;

export const CheckboxButton: any = styled.input`
  -webkit-appearance: none;
  background: white;
  padding: 0.5vw;
  border-radius: 2px;
  display: inline-block;
  position: relative;
  top: 0.7vh;
  right: 0.3vw;
  background: transparent linear-gradient(278deg, #f2f3f6 0%, #e5e6ec 100%) 0%
    0% no-repeat padding-box;
  box-shadow: 6px 6px 20px #c5c5c5, -6px -6px 20px #ffffff;

  &:checked {
    background-image: url("../../../assets/img/check/checkmark.svg");
    background-repeat: no-repeat;
    background-size: 1.2vw;
  }

  &:focus {
    outline: none;
  }
`;

export const LogoVector: any = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  position: relative;
  bottom: 7.5vh;
`;

export const LogoAreaLogin: any = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  color: #fff;
  height: 100%;
  width: 100%;
  flex-direction: column;
  position: relative;

  .icon-head {
    position: absolute;
  }

  .left-icon {
    width: 28vw;
    left: 0;
    bottom: 0;
    opacity: 0.7;
  }

  .right-icon {
    width: 10vw;
    right: -10px;
    top: 32%;
    transform: matrix(0.33, -0.95, 0.95, 0.33, 0, 0);
    opacity: 0.9;
  }
`;

export const LogoAreaForgotPsw: any = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  color: #fff;
  height: 100%;
  width: 100%;
  flex-direction: column;
  position: relative;

  .icon-head {
    position: absolute;
  }

  .left-icon {
    width: 8vw;
    left: 0;
    top: 25%;
    opacity: 0.9;
  }

  .right-icon {
    width: 28vw;
    right: 0;
    bottom: 0;
    opacity: 0.7;
  }
`;

export const LogoIcon: any = styled.img`
  width: 20vw;
`;

export const WelcomeText: any = styled.h2`
  font-size: 1vw;
  font-weight: 300;
  font-family: "Roboto", sans-serif;
  letter-spacing: 0px;
  color: #fff;
`;

export const GoBackButton: any = styled.div`
  font-size: 0.8vw;
  font-weight: 500;
  font-family: "Roboto", sans-serif;
  letter-spacing: 0px;
  color: #820f4c;
  text-decoration: none;
  margin: 4vh 0 0 0;
  cursor: pointer;
`;

export const LogoArvind = styled.img`
  margin-top: -4vh;
  height: 35vh;
`;

export const SuccessArea = styled.div`
  margin-bottom: 10vh;
  display: flex;
  flex-direction: column;
  align-items: center;
`;

export const SuccessIcon = styled.img`
  height: 10vh;
  margin-bottom: 2vh;
`;

export const SuccessText = styled.p`
  font-size: 1vw;
`;
