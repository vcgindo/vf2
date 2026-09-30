import React from "react";
import VFRangeSlider from "../VFRangeSlider";
import { useUserData } from "../../../../context/UserDataContext";

const VFHorizon = ({ setHorizon, OnHorizonChange, horizon,styles }: any) => {
  const { user } = useUserData();
  const themeUi = user?.user?.theme_ui;

  return (
    <div
      className="horiozn one"
      style={{
        ...styles,
        // width: "100%",
        height: "50px",
        display: "flex",
        justifyContent: "space-evenly",
        alignItems: "center",
        zoom: "0.9",
      }}
    >
      <label
        style={{
          fontStyle: "normal",
          fontVariant: "normal",
          fontWeight: 300,
          fontSize: 15,
          fontFamily: "Roboto",
        }}
      >
        {" "}
        <b>Select Horizon: </b>
      </label>
      <VFRangeSlider
        showTriangle={false}
        min={1}
        max={90}
        milestones={[-1, 0, 30, 60, 90]}
        strictMode={false}
        width={250}
        defaultValue={horizon || 9}  
        handleChange={(e: any) => setHorizon(e)}
        labelValueFormatter={(value: number) =>
          value > 1 ? `${value} Days` : `${value} Day`
        }
        style={{ margin: "0px" }}
      />
      <img
        style={{ cursor: "pointer", marginLeft: "-15px" }}
        src={
          themeUi === "REGALBLAZE"
            ? "/assets/img/Group 627-regal.svg"
            : "/assets/img/Group 627.svg"
        }
        height={40}
        width={50}
        onClick={() => OnHorizonChange(horizon)}
      />
    </div>
  );
};

export default VFHorizon;
