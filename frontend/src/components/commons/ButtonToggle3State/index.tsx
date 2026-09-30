import { useState } from "react";
import { SCWrapper, SCInput, SCText } from "./style";
import { useUserData } from "../../../context";

const ButtonToggle3State = ({ onClick }: any) => {
  const { user } = useUserData();

  const [stateToggle, setStateToggle] = useState<any>({
    status: 2,
    text: "Ignore MOQ",
    moq: "All",
  });

  const handleChange = (e: any) => {
    const value = e.target.value;
    let formData: any = {};
    if (value == 1) {
      formData = { status: 1, text: "MOQ not met", moq: "False" };
    } else if (value == 2) {
      formData = { status: 2, text: "Ignore MOQ", moq: "All" };
    } else if (value == 3) {
      formData = { status: 3, text: "MOQ met", moq: "True" };
    }

    setStateToggle(formData);
    onClick(formData.moq);
  };

  return (
    <>
      <SCWrapper>
        <SCInput
          colorTheme={user?.user?.theme_ui}
          id="custom-toggle"
          type="range"
          name="points"
          onChange={(e) => handleChange(e)}
          min={1}
          step={1}
          max={3}
          value={stateToggle.status}
        />
        <SCText>{stateToggle.text}</SCText>
      </SCWrapper>
    </>
  );
};

export default ButtonToggle3State;
