import { useState } from "react";
import { notifyError } from "../../../../helpers/notify";

import { PrimaryButton } from "../../../../components/commons/styled";

import {
  FormLogo,
  LoginForm,
  LoginWrapper,
  InputArea,
  PasswordInput,
  FormSection,
} from "./styles";
import { useNavigate } from "react-router";
import { useGetAllEnvironmentConfiguration } from "../../../../VectorFlow/Services/MTA/MDM";
import { useDispatch } from "react-redux";
import { UPDATE_ENV_CONFIG } from "../../../../redux/actions/MTA";

const Login = () => {
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const [password, setPassword] = useState<string>("");

  const navigate = useNavigate();
  const dispatch = useDispatch();
  const {mutateAsync : getAllEnvConfiguration} = useGetAllEnvironmentConfiguration();
  const manageEnvConfig = async () => {
        const response = await getAllEnvConfiguration();
        const configMap = response?.data?.data.reduce((map:any, item:any) => {
          map[item.ConfigKey] = item.ConfigValue;
          return map;
        }, {});
        dispatch(UPDATE_ENV_CONFIG(configMap))
  }

  const handleLogin = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);
    setTimeout(() => {
      if (password === "password") {
        localStorage.setItem("isAdmin", "1");
        navigate("/vector-admin/");
        manageEnvConfig();
      } else {
        notifyError("Invalid Password");
      }
      setIsLoading(false);
    }, 1000);
  };

  return (
    <LoginWrapper>
      <LoginForm onSubmit={handleLogin}>
        <FormSection style={{ flex: 4, alignItems: "start" }}>
          <FormLogo src="/assets/VectorFlow_black.svg" />
        </FormSection>
        <FormSection style={{ flex: 3 }}>
          <InputArea themeUi="NOIRFUSION">
            <img
              src="/assets/img/auth/password.svg"
              style={{ height: "20px" }}
            />
            <PasswordInput
              type="password"
              required
              autoFocus
              disabled={isLoading}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={"Password"}
            />
          </InputArea>
        </FormSection>
        <FormSection style={{ flex: 1 }}>
          <PrimaryButton
            disabled={isLoading}
            type="submit"
            themeUi="NOIRFUSION"
            style={{ width: "100%", height: "40px", borderRadius: "32px" }}
          >
            Continue
          </PrimaryButton>
        </FormSection>
      </LoginForm>
    </LoginWrapper>
  );
};

export default Login;
