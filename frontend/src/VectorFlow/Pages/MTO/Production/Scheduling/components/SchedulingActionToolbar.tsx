import React, { CSSProperties, useEffect, useRef, useState } from "react";
import styled from "styled-components";
import VFButtonOutline from "../../../../../../components/VectorFLOW/commons/VFButtonOutline";
import { useUserData } from "../../../../../../context";
import Portal from "../../../../../../components/VectorFLOW/layouts/Portal";
import {
  SCFilterVerticalDivider,
  VFFilterScrollBar,
  VFSelectedFiltersChip,
  VFSelectedFiltersFilterCloseIcon,
  VFSelectedFiltersFilterContent,
  VFSelectedFiltersFilterLabel,
  VFSelectedFiltersFilterValue,
  VFSelectedFiltersPlaceHolder,
  VFSelectedFiltersWrapper,
} from "../../../../../../components/VectorFLOW/commons/MTO/ActionToolBar/styles";
import { useSearchParams } from "react-router-dom";
import _ from "lodash";
import { format } from "date-fns";
import { start } from "repl";

const ToolbarWrapper = styled.div`
  width: calc(100% + 24px);
  position: sticky;
  top: 61px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 20px;
  background: #ffffff;
  z-index: 2;
  box-shadow: 0px 1px 4px rgba(0, 0, 0, 0.1);
`;

const ToolbarLeftSection = styled.span`
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  font-size: 1.2rem;
`;

const ToolbarRightSection = styled.span`
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 11px;
  font-size: 1.2rem;
`;
const GoBackButton = styled.button`
  display: flex;
  background: transparent;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 6px 12px;
  cursor: pointer;

  &:hover {
    transform: scale(1.05);
    transition: all 0.3s ease-in-out;
  }
`;

const ToggleButtonWrapper = styled.div`
  display: flex;
  position: relative;
  width: fit-content;
  padding: 4px;
  border: 0.5px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0px 1px 4px rgba(0, 0, 0, 0.1);
  background: #ffffff;
`;

const ToggleButton = styled.button`
  background: transparent;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  &:hover {
    transform: scale(1.05);
    transition: all 0.3s ease-in-out;
  }
`;

const ButtonLabel = styled.span<{ isSelected: boolean }>`
  font-size: 0.8rem;
  color: ${(props) => (props.isSelected ? "rgb(188, 61, 129)" : "#3e3e3e")};
  font-weight: ${(props) => (props.isSelected ? "600" : "400")};
  user-select: none;
`;

const ToggleDivider = styled.div`
  width: 1px;
  height: 35px;
  background: #e0e0e0;
  margin: 0 6px;
`;

const DropdownWrapper = styled.div<{ topPos: any; leftPos: any }>`
  position: absolute;
  top: ${(props) => props.topPos};
  left: ${(props) => props.leftPos};
  background-color: transparent;
  z-index: 9999;
  max-height: 300px;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
`;

const DropDownArrow = styled.span`
  width: 0;
  height: 0;
  margin-right: 20px;
  border-left: 8px solid transparent;
  border-right: 8px solid transparent;
  border-bottom: 8px solid rgba(229, 228, 228, 0.55);
  filter: drop-shadow(0px 1px 1px rgba(0, 0, 0, 0.1));
`;

// Small bulge container for date filter
const DateBulge = styled.div`
  background: white;
  border: 1px solid rgb(188, 61, 129);
  height: 30px;
  border-radius: 8px;
  padding: 4px 8px;
  z-index: 4;
  width: 150px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
  font-size: 0.9rem;
`;

const gridViewIcon = (isSelected: boolean) => {
  const activeColor = "rgb(188, 61, 129)";
  const inactiveColor = "#3e3e3e";

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="25"
      height="25"
      viewBox="0 0 30 30"
    >
      <g
        id="Grid_View"
        data-name="Grid View"
        transform="translate(-11056 -3258)"
      >
        <rect
          id="Rectangle_16195"
          data-name="Rectangle 16195"
          width="30"
          height="30"
          transform="translate(11056 3258)"
          fill="none"
        />
        <g id="note_15834685" transform="translate(11054.9 3250.127)">
          <path
            d="M10.738,30.3H3.409A.387.387,0,0,0,3,30.709v9.458a.387.387,0,0,0,.409.409h7.329a.387.387,0,0,0,.409-.409V30.709A.44.44,0,0,0,10.738,30.3Zm-.409,9.458H3.819V31.119h6.51Z"
            transform="translate(-0.005 -9.331)"
            fill={isSelected ? activeColor : inactiveColor}
          />
          <path
            d="M3.036,19.413a.471.471,0,0,0,.368.246H9.1a.372.372,0,0,0,.328-.164l1.638-2.17a.373.373,0,0,0,0-.491l-1.638-2.17A.505.505,0,0,0,9.1,14.5H3.4a.393.393,0,0,0-.368.246.377.377,0,0,0,.041.409L4.51,17.039,3.077,18.922c-.082.2-.123.368-.041.491Zm2.334-2.088a.373.373,0,0,0,0-.491L4.223,15.36H8.891L10.2,17.12l-1.31,1.761H4.223Z"
            transform="translate(0)"
            fill={isSelected ? activeColor : inactiveColor}
          />
          <path
            d="M32.8,30.3H25.509a.387.387,0,0,0-.409.409v9.458a.387.387,0,0,0,.409.409h7.329a.387.387,0,0,0,.409-.409V30.709A.481.481,0,0,0,32.8,30.3Zm-.409,9.458H25.919V31.119h6.51v8.639Z"
            transform="translate(-13.057 -9.331)"
            fill={isSelected ? activeColor : inactiveColor}
          />
          <path
            d="M25.118,19.413a.471.471,0,0,0,.368.246h5.691A.372.372,0,0,0,31.5,19.5l1.638-2.17a.373.373,0,0,0,0-.491L31.5,14.664a.505.505,0,0,0-.328-.164H25.486a.393.393,0,0,0-.368.246.377.377,0,0,0,.041.409l1.433,1.883-1.433,1.883a.44.44,0,0,0-.041.491Zm2.293-2.088a.373.373,0,0,0,0-.491L26.264,15.36h4.668l1.31,1.761-1.31,1.761H26.305Z"
            transform="translate(-13.033)"
            fill={isSelected ? activeColor : inactiveColor}
          />
          <path
            d="M54.838,30.3H47.509a.387.387,0,0,0-.409.409v9.458a.387.387,0,0,0,.409.409h7.329a.387.387,0,0,0,.409-.409V30.709A.41.41,0,0,0,54.838,30.3Zm-.409,9.458h-6.51V31.119h6.51Z"
            transform="translate(-26.049 -9.331)"
            fill={isSelected ? activeColor : inactiveColor}
          />
          <path
            d="M47.136,19.413a.471.471,0,0,0,.368.246H53.2a.372.372,0,0,0,.328-.164l1.638-2.17a.373.373,0,0,0,0-.491l-1.638-2.17A.505.505,0,0,0,53.2,14.5H47.5a.393.393,0,0,0-.368.246.377.377,0,0,0,.041.409l1.433,1.883-1.433,1.883a.71.71,0,0,0-.041.491Zm2.334-2.088a.373.373,0,0,0,0-.491L48.323,15.36h4.668L54.3,17.12l-1.31,1.761H48.323Z"
            transform="translate(-26.044)"
            fill={isSelected ? activeColor : inactiveColor}
          />
          {/* repeat same cleanup for remaining <path> elements */}
        </g>
      </g>
    </svg>
  );
};

const JobViewIcon = (isSelected: boolean) => {
  const fillColor = isSelected ? "rgb(188, 61, 129)" : "#3e3e3e";

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 30 30"
    >
      <g id="Job_View" data-name="Job View" transform="translate(-11017 -3258)">
        <path
          id="Path_17445"
          d="M0,0H30V30H0Z"
          transform="translate(11017 3258)"
          fill="none"
        />
        <path
          id="Path_17444"
          d="M25.537,76.579a.519.519,0,0,0,.519-.519V56.894a.519.519,0,0,0-.519-.519H.519A.519.519,0,0,0,0,56.894V76.06a.519.519,0,0,0,.519.519Zm-.519-8.709H19.8v-2.8h5.216Zm-23.98-2.8H6.255v2.8H1.038Zm17.725-3.824v2.785H13.547V61.249Zm-6.255,0v2.785H7.293V61.249ZM7.293,65.072h5.216v2.8H7.293Zm6.255,0h5.216v2.8H13.547ZM19.8,64.034V61.249h5.216v2.785ZM6.255,61.249v2.785H1.038V61.249ZM1.038,68.908H6.255v2.8H1.038Zm6.255,0h5.216v2.8H7.293Zm6.255,0h5.216v2.8H13.547Zm6.255,0h5.216v2.8H19.8ZM1.038,60.2V57.413h23.98V60.2Zm0,12.545H6.255v2.8H1.038Zm6.255,0h5.216v2.8H7.293Zm6.255,0h5.216v2.8H13.547Zm11.471,2.8H19.8v-2.8h5.216Z"
          transform="translate(11018.972 3206.523)"
          fill={fillColor}
        />
      </g>
    </svg>
  );
};

const gridViewJobIcon = (isSelected: boolean) => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="20.603"
      height="20.604"
      viewBox="0 0 24.603 24.604"
    >
      <path
        id="job-description"
        d="M10.024,20.062h7.2a1.136,1.136,0,0,0,1-1.255V14.16a1.129,1.129,0,0,0-1.143-1.143H15.8a1.19,1.19,0,0,0-1.173-1.34H12.621a1.224,1.224,0,0,0-1.2,1.34H10.163A1.132,1.132,0,0,0,9.018,14.16v4.647C9.018,19.532,9.439,20.062,10.024,20.062ZM17.7,22.1H15.718a.489.489,0,0,0,0,.976H17.7a.489.489,0,0,0,0-.976ZM12.38,9.073h5.377a.489.489,0,0,0,0-.976H12.38a.489.489,0,1,0,0,.976ZM13.608,22.1H9.521a.489.489,0,0,0,0,.976H13.6a.489.489,0,0,0,0-.976Zm14.784-12.05-6.17-2.428V6.913A1.96,1.96,0,0,0,20.24,5h-9.8c-.306,0-.5.224-.724.446L5.166,9.8A.451.451,0,0,0,5,10.161l.027,14.672a1.966,1.966,0,0,0,2.009,1.914h6.588l6.812,2.706a2.056,2.056,0,0,0,.692.15,1.889,1.889,0,0,0,1.788-1.173L29.477,12.5a1.914,1.914,0,0,0-1.093-2.46ZM9.718,8.709a.968.968,0,0,1-1.006.921L6.73,9.658,9.718,6.785ZM7.036,25.776a1.014,1.014,0,0,1-1.031-.949l-.03-14.193,2.764-.027a1.93,1.93,0,0,0,1.955-1.9l-.027-2.734h9.568a.97.97,0,0,1,1.011.938l.027,17.881a.981.981,0,0,1-.965.96ZM28.561,12.135,22,28.064a.935.935,0,0,1-1.227.473l-4.552-1.78,4.087-.027a1.974,1.974,0,0,0,1.955-1.914V16.771l1.115.446a.394.394,0,0,0,.2.03.478.478,0,0,0,.446-.309.514.514,0,0,0-.273-.64l-1.479-.588-.046-2.843,2.906,1.154a.413.413,0,0,0,.194.027.478.478,0,0,0,.454-.317.517.517,0,0,0-.273-.642l-3.28-1.282V8.682l5.806,2.288a.888.888,0,0,1,.53,1.17Zm-15.94.519H14.63c.224,0,.194.224.194.364H12.4C12.4,12.878,12.4,12.654,12.621,12.654ZM10,14.16a.148.148,0,0,1,.167-.167h6.924a.161.161,0,0,1,.167.167V15.5l-3.155.686a.492.492,0,0,0-.476-.476.514.514,0,0,0-.5.476L10,15.462Zm0,2.315,3.127.724v.2a.489.489,0,0,0,.976,0v-.2l3.155-.719V18.8c0,.167-.057.273-.027.273l-7.146.027A.478.478,0,0,1,10,18.791Z"
        transform="translate(-4.999 -5)"
        fill={isSelected ? "rgb(188, 61, 129)" : "#3e3e3e"}
      />
    </svg>
  );
};

const gridViewResourceIcon = (isSelected: boolean) => {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="20.603"
      height="20.604"
      viewBox="0 0 24.603 24.604"
    >
      <g transform="translate(8832.302 -5257.771)">
        <path
          d="M17.7,22.1H15.718a.489.489,0,0,0,0,.976H17.7a.489.489,0,0,0,0-.976ZM12.38,9.073h5.377a.489.489,0,0,0,0-.976H12.38a.489.489,0,1,0,0,.976ZM13.608,22.1H9.521a.489.489,0,0,0,0,.976H13.6a.489.489,0,0,0,0-.976Zm14.784-12.05-6.17-2.428V6.913A1.96,1.96,0,0,0,20.24,5h-9.8c-.306,0-.5.224-.724.446L5.166,9.8A.451.451,0,0,0,5,10.161l.027,14.672a1.966,1.966,0,0,0,2.009,1.914h6.588l6.812,2.706a2.056,2.056,0,0,0,.692.15,1.889,1.889,0,0,0,1.788-1.173L29.477,12.5a1.914,1.914,0,0,0-1.093-2.46ZM9.718,8.709a.968.968,0,0,1-1.006.921L6.73,9.658,9.718,6.785ZM7.036,25.776a1.014,1.014,0,0,1-1.031-.949l-.03-14.193,2.764-.027a1.93,1.93,0,0,0,1.955-1.9l-.027-2.734h9.568a.97.97,0,0,1,1.011.938l.027,17.881a.981.981,0,0,1-.965.96ZM28.561,12.135,22,28.064a.935.935,0,0,1-1.227.473l-4.552-1.78,4.087-.027a1.974,1.974,0,0,0,1.955-1.914V16.771l1.115.446a.394.394,0,0,0,.2.03.478.478,0,0,0,.446-.309.514.514,0,0,0-.273-.64l-1.479-.588-.046-2.843,2.906,1.154a.413.413,0,0,0,.194.027.478.478,0,0,0,.454-.317.517.517,0,0,0-.273-.642l-3.28-1.282V8.682l5.806,2.288a.888.888,0,0,1,.53,1.17Z"
          transform="translate(-8837.301 5252.771)"
          fill={isSelected ? "rgb(188, 61, 129)" : "#3e3e3e"}
        />
        <path d="M14.626,5.043l-.76-.595a2.994,2.994,0,0,0,.018-.312,2.9,2.9,0,0,0-.018-.312l.761-.595a.373.373,0,0,0,.09-.475l-.791-1.368a.367.367,0,0,0-.457-.164l-.9.36a3.076,3.076,0,0,0-.539-.313L11.9.317A.366.366,0,0,0,11.531,0H9.946a.365.365,0,0,0-.365.314l-.137.955a3.171,3.171,0,0,0-.538.313l-.9-.361a.374.374,0,0,0-.454.162l-.792,1.37a.371.371,0,0,0,.09.477l.76.595a2.727,2.727,0,0,0,0,.624l-.761.595a.373.373,0,0,0-.09.475l.791,1.368a.366.366,0,0,0,.457.164l.9" />
      </g>
    </svg>
  );
};

const resourceViewIcon = (isSelected: boolean) => {
  const fillColor = isSelected ? "rgb(188, 61, 129)" : "#3e3e3e";

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="25"
      height="25"
      viewBox="0 0 30 30"
    >
      <g
        id="Resources_View"
        data-name="Resources View"
        transform="translate(-10977 -3258)"
      >
        <rect
          id="Rectangle_16193"
          data-name="Rectangle 16193"
          width="30"
          height="30"
          transform="translate(10977 3258)"
          fill="none"
        />
        <g id="Layer_x0020_1" transform="translate(10832 3035.204)">
          <path
            id="Path_17015"
            data-name="Path 17015"
            d="M167.483,246.59a1.753,1.753,0,1,1,1.753-1.753A1.763,1.763,0,0,1,167.483,246.59Zm-13.122-7.574h-1.707a.515.515,0,0,1-.518-.472L152,237.308a4.739,4.739,0,0,1-.808-.335l-.991.777a.5.5,0,0,1-.686-.046l-1.219-1.2a.514.514,0,0,1-.031-.686l.777-.991a4.74,4.74,0,0,1-.335-.808l-1.234-.137a.526.526,0,0,1-.472-.518v-1.707a.525.525,0,0,1,.457-.518l1.25-.137a5.316,5.316,0,0,1,.335-.808l-.777-.975a.533.533,0,0,1,.031-.7l1.219-1.2a.5.5,0,0,1,.686-.046l.975.777a5.312,5.312,0,0,1,.808-.335l.152-1.234a.515.515,0,0,1,.518-.472h1.707a.526.526,0,0,1,.518.472l.137,1.234a5.313,5.313,0,0,1,.808.335l.975-.777a.518.518,0,0,1,.7.046l1.2,1.2a.513.513,0,0,1,.031.686l-.777.991a4.74,4.74,0,0,1,.335.808l1.25.137a.514.514,0,0,1,.457.518v1.707a.526.526,0,0,1-.457.518l-1.25.137a5.311,5.311,0,0,1-.335.808l.777.975a.533.533,0,0,1-.031.7l-1.2,1.2a.518.518,0,0,1-.7.046l-.975-.777a5.236,5.236,0,0,1-.808.32l-.137,1.25A.526.526,0,0,1,154.361,239.015Zm-1.631-.61h1.555c.244-2.256-.061-1.219,1.417-2.057a.325.325,0,0,1,.351.015l1.067.869,1.1-1.1c-1.433-1.814-.884-.823-.442-2.469a.31.31,0,0,1,.259-.229l1.372-.152V231.73c-2.271-.259-1.219.061-2.073-1.417a.325.325,0,0,1,.031-.35l.853-1.082-1.1-1.1c-1.8,1.433-.808.9-2.469.457a.316.316,0,0,1-.213-.259l-.152-1.372H152.73c-.259,2.256.061,1.219-1.433,2.057a.3.3,0,0,1-.335-.015l-1.082-.869-1.1,1.1c1.433,1.8.884.823.457,2.469a.31.31,0,0,1-.259.229l-1.372.152v1.555c2.256.259,1.219-.061,2.057,1.417a.3.3,0,0,1-.03.351l-.853,1.082,1.1,1.1c1.8-1.448.808-.9,2.469-.457a.31.31,0,0,1,.229.259Zm.777-2.819a3.079,3.079,0,1,1,3.079-3.079A3.07,3.07,0,0,1,153.508,235.586Zm0-5.547a2.469,2.469,0,1,0,2.469,2.469A2.459,2.459,0,0,0,153.508,230.039Zm18.166,8.977h-9.632a1.327,1.327,0,0,1-1.326-1.326v-7.315a1.34,1.34,0,0,1,1.341-1.326h9.617A1.327,1.327,0,0,1,173,230.374v7.315A1.327,1.327,0,0,1,171.674,239.015Zm-10.348-7.3v5.974a.715.715,0,0,0,.716.716h9.632a.715.715,0,0,0,.716-.716v-5.974Zm0-.61H172.39v-.732a.715.715,0,0,0-.716-.716h-9.617a.729.729,0,0,0-.732.716Zm9.921,5.106h-2.256a.3.3,0,1,1,0-.61h2.256A.3.3,0,0,1,171.247,236.211Zm0,1.189H167.6a.3.3,0,1,1,0-.61h3.642A.3.3,0,0,1,171.247,237.4Zm-5.212-.823h-3.246a.3.3,0,0,1-.3-.3v-3.231a.306.306,0,0,1,.3-.3h3.246a.306.306,0,0,1,.3.3v3.231A.306.306,0,0,1,166.035,236.577Zm-2.941-.61h2.637v-2.621h-2.637Zm5.151,13.625h-16.49a4.747,4.747,0,1,1,0-9.495h16.49a4.747,4.747,0,1,1,0,9.495Zm-16.49-8.885a4.138,4.138,0,1,0,0,8.275h16.49a4.138,4.138,0,1,0,0-8.275Zm16.49,7.361h-16.49a3.223,3.223,0,1,1,0-6.447h16.49a3.223,3.223,0,1,1,0,6.447Zm-16.49-5.852a2.621,2.621,0,1,0,0,5.243h16.49a2.621,2.621,0,1,0,0-5.243Zm.762,4.374a1.753,1.753,0,1,1,1.753-1.753A1.753,1.753,0,0,1,152.517,246.59Zm0-2.9a1.143,1.143,0,1,0,1.143,1.143A1.141,1.141,0,0,0,152.517,243.694Zm4.984,2.9a1.753,1.753,0,1,1,1.753-1.753A1.763,1.763,0,0,1,157.5,246.59Zm0-2.9a1.143,1.143,0,1,0,1.143,1.143A1.151,1.151,0,0,0,157.5,243.694Zm5,2.9a1.753,1.753,0,1,1,1.753-1.753A1.753,1.753,0,0,1,162.5,246.59Zm0-2.9a1.143,1.143,0,1,0,1.143,1.143A1.141,1.141,0,0,0,162.5,243.694Zm4.984,0a1.143,1.143,0,1,0,1.143,1.143A1.151,1.151,0,0,0,167.483,243.694Z"
            fill={fillColor}
            stroke={fillColor}
            strokeWidth="0.4"
            fillRule="evenodd"
          />
        </g>
      </g>
    </svg>
  );
};

const SchedulingActionToolbar = ({
  currentView,
  setCurrentView,
  setIsFilterModalOpen,
  onGoBack,
  appliedFilters,
  setAppliedFilters,
  gridRef,
  startDate,
  endDate,
}: any) => {
  const themeUi = useUserData().user.user.themeUi;

  console.log("StartDate", startDate, endDate);

  const [open, setOpen] = useState(false);
  const [dropdownPosition, setDropdownPosition] = useState<CSSProperties>({});
  const buttonRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [searchParams, setSearchParams] = useSearchParams();

  const handleClickOutside = (e: MouseEvent) => {
    if (
      dropdownRef.current &&
      !dropdownRef.current.contains(e.target as Node) &&
      !buttonRef.current?.contains(e.target as Node)
    ) {
      setOpen(false);
    } else {
      console.log("no ref found");
    }
  };

  const isAnyFilterApplied = (appliedFilters: any) => {
    if (!appliedFilters) return false;
    const { timePreference, ...lengthCheckFilters } = appliedFilters;
    return (
      Object.values(lengthCheckFilters).some((filter) => {
        if (Array.isArray(filter)) {
          return filter.length > 0;
        }
        return filter !== null && filter !== undefined && filter !== "";
      }) ||
      !!timePreference?.startDate ||
      !!timePreference?.endDate
    );
  };


  useEffect(() => {
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
    } else {
      document.removeEventListener("mousedown", handleClickOutside);
    }

    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const onSelectClick = (e: React.MouseEvent<HTMLElement>) => {
    const { bottom, left } = e.currentTarget.getBoundingClientRect();
    setDropdownPosition({
      top: bottom + window.scrollY + 6,
      bottom: bottom,
      left: left + window.scrollX - 70,
    });
    setOpen(!open);
  };

  const handleRemoveFilter = (filterType: string, value: string) => {
    //logic to remove individual filter
    const updatedFilters = { ...appliedFilters };
    if (Array.isArray(updatedFilters[filterType])) {
      updatedFilters[filterType] = updatedFilters[filterType].filter(
        (item: string) => item !== value
      );
    } else {
      updatedFilters[filterType] = null; // or set to default value
    }
    setAppliedFilters(updatedFilters);
  };

  const allFilterTypes = Object.keys(appliedFilters);

  const handleRemoveTimeFilter = () => {
      setAppliedFilters({
       ...appliedFilters,
       timePreference: {
        startDate: null,
        endDate: null,
       },
      });
     };

  return (
    <ToolbarWrapper>
      <ToolbarLeftSection>
        <GoBackButton
          onClick={() => {
            onGoBack();
            setSearchParams(undefined);
          }}
        >
          <img
            style={{ marginBottom: "3.2px" }}
            src="/assets/img/VectorFLOW/BPR/goback.svg"
            alt="Go Back"
            width={16}
            height={16}
          />
          <p style={{ fontSize: "1.2rem" }}>Go Back</p>
        </GoBackButton>
        <DateBulge
          style={{
            border: (appliedFilters?.timePreference?.startDate || appliedFilters?.timePreference?.endDate) ? "1px solid #bc3d81" : "1px solid #cecece",
            background: (appliedFilters?.timePreference?.startDate || appliedFilters?.timePreference?.endDate) ? "rgba(240, 159, 202, 0.1)" : "#f5f5f5",
          }}
        >
          <img
            style={{ marginBottom: "3.2px" }}
            src="\assets\img\scheduling\calendar-date.svg"
            alt="Go Back"
            width={14}
            height={14}
          />
          {startDate && endDate && (
            <p style={{ fontSize: "1.1rem", marginLeft: "6px" }}>
              {format(
                new Date(
                  appliedFilters?.timePreference?.startDate || startDate
                ),
                "dd MMM"
              )}{" "}
              -{" "}
              {format(
                new Date(appliedFilters?.timePreference?.endDate || endDate),
                "dd MMM yyyy"
              )}
            </p>
          )}
        </DateBulge>
      </ToolbarLeftSection>

      <ToolbarRightSection>
      {isAnyFilterApplied(appliedFilters) && (
          <VFSelectedFiltersWrapper
            style={{
              width: "fit-content",
              overflowY: "hidden",
              maxWidth: "380px",
              padding: "2px",
              height: "36px",
              border: "0.8px solid #cecece",
            }}
          >
                 {" "}
            <VFSelectedFiltersPlaceHolder
              style={{ fontSize: "1.2rem", height: "20px" }}
            >
                     Selected Filters      {" "}
            </VFSelectedFiltersPlaceHolder>
                 {" "}
            <VFFilterScrollBar
              style={{ overflowY: "hidden", borderRadius: "10px" }}
            >
                    {" "}
              {/* // CHANGE 3: Update mapping logic to handle both array and object filter types */}
                    {" "}
              {allFilterTypes?.map((filterType: any) => {
                // Case for timePreference object
                if (
                  filterType === "timePreference" &&
                  (appliedFilters.timePreference?.startDate ||
                    appliedFilters.timePreference?.endDate)
                ) {
                  return (<VFSelectedFiltersChip
                  key={filterType}
                  style={{ padding: "2px 5px", height: "23px" }}
                >
                  <VFSelectedFiltersFilterLabel
                    style={{ fontSize: "1.2rem", padding: "3px" }}
                  >
                    Date Range:
                  </VFSelectedFiltersFilterLabel>
                  <VFSelectedFiltersFilterContent>
                    <VFSelectedFiltersFilterValue style={{ fontSize: "1.1rem" }}>
                      <p style={{ margin: "0px 5px", display: "flex", gap: "4px" }}>
                        {/* Render the start date if it exists in filters or as a prop */}
                        {(appliedFilters.timePreference?.startDate || startDate) && (
                          <span>
                            {format(
                              new Date(appliedFilters.timePreference.startDate || startDate),
                              "dd MMM"
                            )}
                          </span>
                        )}
                        {/* Render hyphen only if both start and end dates exist */}
                        {(appliedFilters.timePreference?.startDate || startDate) &&
                          (appliedFilters.timePreference?.endDate || endDate) && <span>-</span>}
                        {/* Render the end date if it exists in filters or as a prop */}
                        {(appliedFilters.timePreference?.endDate || endDate) && (
                          <span>
                            {format(
                              new Date(appliedFilters.timePreference.endDate || endDate),
                              "dd MMM yyyy"
                            )}
                          </span>
                        )}
                      </p>
                    </VFSelectedFiltersFilterValue>
                    <VFSelectedFiltersFilterCloseIcon
                      style={{
                        height: "1.2rem",
                        width: "1.2rem",
                      }}
                      onClick={handleRemoveTimeFilter}
                      src="/assets/img/VectorFLOW/BPR/close-circle.svg"
                      alt="close-icon"
                      data-testid={"closeIcon-time-filter"}
                    />
                  </VFSelectedFiltersFilterContent>
                </VFSelectedFiltersChip>);
                } // Case for array-based filters

                if (
                  Array.isArray(appliedFilters[filterType]) &&
                  appliedFilters[filterType]?.length > 0
                ) {
                  return (
                    <VFSelectedFiltersChip
                      key={filterType}
                      style={{ padding: "2px 5px", height: "23px" }}
                    >
                                {" "}
                      <VFSelectedFiltersFilterLabel
                        style={{ fontSize: "1.2rem", padding: "3px" }}
                      >
                                    {_.startCase(filterType) + " "}:
                                  {" "}
                      </VFSelectedFiltersFilterLabel>
                                {" "}
                      {appliedFilters[filterType].map(
                        (value: string, index: number) => (
                          <div key={value}>
                                         {" "}
                            <VFSelectedFiltersFilterContent>
                                            {" "}
                              <VFSelectedFiltersFilterValue
                                style={{ fontSize: "1.1rem" }}
                              >
                                               {" "}
                                <p style={{ margin: "0px 5px" }}>
                                                   {value}  
                                              {" "}
                                </p>
                                              {" "}
                              </VFSelectedFiltersFilterValue>
                                            {" "}
                              <VFSelectedFiltersFilterCloseIcon
                                style={{
                                  height: "1.2rem",
                                  width: "1.2rem",
                                }}
                                onClick={() =>
                                  handleRemoveFilter(filterType, value)
                                }
                                src="/assets/img/VectorFLOW/BPR/close-circle.svg"
                                alt="close-icon"
                                data-testid={"closeIcon-filter"}
                              />
                                            {" "}
                              {appliedFilters[filterType].length > 1 &&
                                index !==
                                  appliedFilters[filterType].length - 1 && (
                                  <SCFilterVerticalDivider
                                    style={{ height: "12px" }}
                                  />
                                )}
                                           {" "}
                            </VFSelectedFiltersFilterContent>
                                        {" "}
                          </div>
                        )
                      )}
                               {" "}
                    </VFSelectedFiltersChip>
                  );
                }
                return null; // Return null if filter type has no values to display
              })}
                   {" "}
            </VFFilterScrollBar>
                {" "}
          </VFSelectedFiltersWrapper>
        )}
        {currentView !== "JobView" && (
          <VFButtonOutline
            style={{
              border: "1px solid rgb(188, 61, 129)",
              color: "rgb(188, 61, 129)",
              fontSize: "1.1rem",
              height: "3.4rem",
            }}
            themeUi={themeUi}
            onClick={() => {
              console.log("gridRef", gridRef);
              gridRef.current?.api.exportDataAsExcel({
                fileName:
                  "Scheduling" +
                  (currentView === "ResourceView"
                    ? "_ResourceView_Summary"
                    : currentView === "JobView"
                    ? "_JobView"
                    : currentView === "GridViewR"
                    ? "_ResourceList"
                    : "_JobList"),
              });
            }}
          >
            Export Excel
          </VFButtonOutline>
        )}
        <VFButtonOutline
          style={{
            border: "1px solid rgb(188, 61, 129)",
            color: "rgb(188, 61, 129)",
            fontSize: "1.1rem",
            height: "3.4rem",
          }}
          themeUi={themeUi}
          onClick={() => {
            setIsFilterModalOpen(true);
          }}
        >
          {isAnyFilterApplied(appliedFilters) ? "Edit Filter" : "+ Add Filter"}
        </VFButtonOutline>
        <ToggleButtonWrapper>
          <ToggleButton
            onClick={() => {
              setCurrentView("ResourceView");
              setSearchParams({ page: "ResourceView" });
            }}
          >
            {resourceViewIcon(currentView === "ResourceView")}
            <ButtonLabel isSelected={currentView === "ResourceView"}>
              Resource View
            </ButtonLabel>
          </ToggleButton>

          <ToggleDivider />

          <ToggleButton
            onClick={() => {
              setCurrentView("JobView");
              setSearchParams({ page: "JobView" });
            }}
          >
            {JobViewIcon(currentView === "JobView")}
            <ButtonLabel isSelected={currentView === "JobView"}>
              Job View
            </ButtonLabel>
          </ToggleButton>
          <ToggleDivider />

          <ToggleButton onClick={onSelectClick}>
            {gridViewIcon(
              currentView === "GridViewR" || currentView === "GridViewJ"
            )}
            <ButtonLabel
              isSelected={
                currentView === "GridViewR" || currentView === "GridViewJ"
              }
            >
              Grid View
            </ButtonLabel>
          </ToggleButton>
        </ToggleButtonWrapper>
      </ToolbarRightSection>

      {open && (
        <Portal wrapperId="checkbox-dropdown">
          <DropdownWrapper
            ref={dropdownRef}
            topPos={dropdownPosition.top + "px"}
            leftPos={dropdownPosition.left + "px"}
          >
            <DropDownArrow></DropDownArrow>
            <ToggleButtonWrapper>
              <ToggleButton
                onClick={() => {
                  setCurrentView("GridViewR");
                  setSearchParams({ page: "GridViewR" });
                  setOpen(!open);
                }}
              >
                {gridViewResourceIcon(currentView === "GridViewR")}
                <ButtonLabel isSelected={currentView === "GridViewR"}>
                  Resource List
                </ButtonLabel>
              </ToggleButton>
              <ToggleDivider />
              <ToggleButton
                onClick={() => {
                  setCurrentView("GridViewJ");
                  setSearchParams({ page: "GridViewJ" });
                  setOpen(!open);
                }}
              >
                {gridViewJobIcon(currentView === "GridViewJ")}
                <ButtonLabel isSelected={currentView === "GridViewJ"}>
                  Job List
                </ButtonLabel>
              </ToggleButton>
            </ToggleButtonWrapper>
          </DropdownWrapper>
        </Portal>
      )}
    </ToolbarWrapper>
  );
};

export default SchedulingActionToolbar;
