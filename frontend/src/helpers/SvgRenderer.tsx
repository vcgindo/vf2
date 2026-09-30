import React from 'react';
import { Theme } from '../styles/global';
interface SvgRendererProps {
  theme: Theme
  alt?: string;
  view?:boolean

}

export const ExportExcelSVG: React.FC<SvgRendererProps> = ({ theme }) => {
  const fillColor = theme === 'REGALBLAZE' ? "#FCA311" : "#BC3D81";

  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="23.001" viewBox="0 0 24 23.001">
    <g id="_12d36a3d034577c8172e565b9d8c82eb" data-name="12d36a3d034577c8172e565b9d8c82eb" transform="translate(0 -0.5)">
      <path
        id="Path_11318"
        data-name="Path 11318"
        d="M13.5,23.5a.487.487,0,0,1-.076-.006l-13-2A.5.5,0,0,1,0,21V4a.5.5,0,0,1,.388-.487l13-3A.5.5,0,0,1,14,1V23a.5.5,0,0,1-.5.5ZM1,20.571l12,1.846V1.628L1,4.4Z"
        fill={fillColor}
      />
      <path
        id="Path_11319"
        data-name="Path 11319"
        d="M23.5,21.5h-10a.5.5,0,0,1,0-1H23V3.5H13.5a.5.5,0,0,1,0-1h10A.5.5,0,0,1,24,3V21A.5.5,0,0,1,23.5,21.5Zm-14-5a.5.5,0,0,1-.424-.235l-5-8a.5.5,0,1,1,.848-.53l5,8A.5.5,0,0,1,9.5,16.5Z"
        fill={fillColor}
      />
      <path
        id="Path_11320"
        data-name="Path 11320"
        d="M4.5,16.5a.5.5,0,0,1-.424-.765l5-8a.5.5,0,1,1,.848.53l-5,8A.5.5,0,0,1,4.5,16.5Zm13,5A.5.5,0,0,1,17,21V3a.5.5,0,0,1,1,0V21A.5.5,0,0,1,17.5,21.5Z"
        fill={fillColor}
      />
      <path
        id="Path_11321"
        data-name="Path 11321"
        d="M23.5,18.5h-10a.5.5,0,0,1,0-1h10a.5.5,0,0,1,0,1Zm0-3h-10a.5.5,0,0,1,0-1h10a.5.5,0,0,1,0,1Zm0-3h-10a.5.5,0,0,1,0-1h10a.5.5,0,0,1,0,1Zm0-3h-10a.5.5,0,0,1,0-1h10a.5.5,0,0,1,0,1Zm0-3h-10a.5.5,0,0,1,0-1h10a.5.5,0,0,1,0,1Z"
        fill={fillColor}
      />
    </g>
  </svg>
  );
};



export const SaveSVG: React.FC<SvgRendererProps> = ({theme }) => {

  const fillColor = theme === 'REGALBLAZE' ? "#FCA311" : "#BC3D81";

  return (
    <svg xmlns="http://www.w3.org/2000/svg"  width="24" height="23.001" viewBox="0 0 28.633 28.633">
  <path id="diskette" d="M29.356,7,23.629,1.277A.954.954,0,0,0,22.952,1H3.863A2.863,2.863,0,0,0,1,3.863V26.77a2.863,2.863,0,0,0,2.863,2.863H26.77a2.863,2.863,0,0,0,2.863-2.863V7.681A.954.954,0,0,0,29.356,7ZM19.134,2.909V8.635H11.5V2.909ZM7.681,27.724V21.043a.954.954,0,0,1,.954-.954H22a.954.954,0,0,1,.954.954v6.681Zm20.043-.954a.954.954,0,0,1-.954.954H24.861V21.043A2.863,2.863,0,0,0,22,18.18H8.635a2.863,2.863,0,0,0-2.863,2.863v6.681H3.863a.954.954,0,0,1-.954-.954V3.863a.954.954,0,0,1,.954-.954H9.59V8.635A1.909,1.909,0,0,0,11.5,10.544h7.635a1.909,1.909,0,0,0,1.909-1.909V2.909H22.56l5.163,5.163Z" transform="translate(-1 -1)" fill={fillColor}/>
</svg>

  );
};


export const ResetSVG: React.FC<SvgRendererProps> = ({theme }) => {

  const fillColor = theme === 'REGALBLAZE' ? "#FCA311" : "#BC3D81";

  return (
    <svg id="refresh" xmlns="http://www.w3.org/2000/svg"  width="24" height="23.001" viewBox="0 0 22.546 25.123">
    <path id="Path_11029" data-name="Path 11029" d="M16.69,9.249a10.946,10.946,0,0,0-3.162.462.966.966,0,1,1-.555-1.851,12.878,12.878,0,0,1,3.718-.543A11.183,11.183,0,1,1,5.417,18.5a11.1,11.1,0,0,1,1.9-6.222.966.966,0,0,1,1.6,1.081A9.171,9.171,0,0,0,7.349,18.5a9.341,9.341,0,1,0,9.34-9.25Z" transform="translate(-5.417 -4.56)" fill={fillColor} fillRule="evenodd"/>
    <path id="Path_11030" data-name="Path 11030" d="M17.523,3.906a.966.966,0,0,1,.285,1.336L16.171,7.765,18.718,9.4a.966.966,0,0,1-1.046,1.625L14.31,8.865a.966.966,0,0,1-.288-1.338L16.187,4.19a.966.966,0,0,1,1.337-.285Z" transform="translate(-7.335 -3.75)" fill={fillColor} fillRule="evenodd"/>
  </svg>
  

  );
};

export const GridView: React.FC<SvgRendererProps> = ({theme,view }) => {

  const activeFillColor = theme === 'REGALBLAZE' ? "#FCA311" : "#BC3D81";
  const inactiveFillColor = "#a8a8a8";
  const fillColor = view ? activeFillColor : inactiveFillColor;

  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="37" height="22" viewBox="0 0 37 22">
      <g id="Group_4112" data-name="Group 4112" transform="translate(-0.348 0.002)">
        <rect id="Rectangle_11420" data-name="Rectangle 11420" width="37" height="5" rx="1" transform="translate(0.348 -0.002)" fill={fillColor} />
        <rect id="Rectangle_11421" data-name="Rectangle 11421" width="37" height="5" rx="1" transform="translate(0.348 7.998)" fill={fillColor} />
        <rect id="Rectangle_11422" data-name="Rectangle 11422" width="37" height="5" rx="1" transform="translate(0.348 16.998)" fill={fillColor} />
      </g>
    </svg>
  );
};




export const ChartView: React.FC<SvgRendererProps> = ({theme,view }) => {

  const activeFillColor = theme === 'REGALBLAZE' ? "#FCA311" : "#BC3D81";
  const inactiveFillColor = "#a8a8a8";
  const fillColor = view ? activeFillColor : inactiveFillColor;


  return (
    
    <svg xmlns="http://www.w3.org/2000/svg" width="26.2" height="26.792" viewBox="0 0 26.2 26.792">
  <g id="_8a4e174b3b44e8626dd24d036a35900f" data-name="8a4e174b3b44e8626dd24d036a35900f" transform="translate(0.244 0.223)">
    <path id="Path_11013" data-name="Path 11013" d="M22.042,9.771A10.715,10.715,0,0,0,11.775.778a.92.92,0,0,0-.956.885h0v.083L11.4,10.4a1.062,1.062,0,0,0,1.121.991l8.674-.578a.92.92,0,0,0,.85-.991Z" transform="translate(2.911)" fill='none' stroke={fillColor} strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" fillRule="evenodd"/>
    <path id="Path_11014" data-name="Path 11014" d="M8.679,4.776a1.18,1.18,0,0,1,1.345.673,1.062,1.062,0,0,1,.106.389c.118,1.676.366,5.346.507,7.328a1.345,1.345,0,0,0,1.44,1.251h0l7.281-.448a1.18,1.18,0,0,1,1.251,1.18h0a9.925,9.925,0,0,1-18.6,4.119,9.441,9.441,0,0,1-1.18-3.611,6.089,6.089,0,0,1-.071-1.18,9.936,9.936,0,0,1,7.907-9.7" transform="translate(0 1.148)" fill="none" stroke={fillColor} strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" fillRule="evenodd"/>
  </g>
</svg>
      
  );
};


export const NewChartView: React.FC<SvgRendererProps> = ({ theme, view }) => {
  const activeFillColor = theme === "REGALBLAZE" ? "#FCA311" : "#BC3D81";
  const inactiveFillColor = "#a8a8a8";
  const fillColor = view ? activeFillColor : inactiveFillColor;

  return (
    <svg
      width="34"
      height="34"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M13 19.5H12C9.17157 19.5 7.75736 19.5 6.87868 18.6213C6 17.7426 6 16.3284 6 13.5V11.5M6 8V11.5M6 11.5H11.5"
        stroke={fillColor}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M13 19.5C13 18.3215 13 17.7322 13.3515 17.3661C13.7029 17 14.2686 17 15.4 17H16.6C17.7314 17 18.2971 17 18.6485 17.3661C19 17.7322 19 18.3215 19 19.5C19 20.6785 19 21.2678 18.6485 21.6339C18.2971 22 17.7314 22 16.6 22H15.4C14.2686 22 13.7029 22 13.3515 21.6339C13 21.2678 13 20.6785 13 19.5Z"
        stroke={fillColor}
        strokeWidth="1.5"
      />
      <path
        d="M4.28571 2H7.71429C9.7888 2 10 3.10993 10 5C10 6.89007 9.7888 8 7.71429 8H4.28571C2.2112 8 2 6.89007 2 5C2 3.10993 2.2112 2 4.28571 2Z"
        stroke={fillColor}
        strokeWidth="1.5"
      />
      <path
        d="M16.1793 11.8738L16.0224 11.1403H16.0224L16.1793 11.8738ZM15.1262 10.8207L15.8597 10.9776L15.1262 10.8207ZM15.8931 8.59775L15.3628 8.06742H15.3628L15.8931 8.59775ZM21.8217 6.29263L22.4712 5.91763L21.8217 6.29263ZM21.8217 7.62331L22.4712 7.99831L21.8217 7.62331ZM20.7074 5.17828L21.0824 4.52876V4.52876L20.7074 5.17828ZM18.7874 5.70339L19.3178 6.23372L18.7874 5.70339ZM19.3767 5.17828L19.0017 4.52876V4.52876L19.3767 5.17828ZM20.7663 7.68222L17.8719 10.5766L18.9326 11.6372L21.8269 8.74288L20.7663 7.68222ZM16.4234 9.12808L19.3178 6.23372L18.2571 5.17306L15.3628 8.06742L16.4234 9.12808ZM16.0224 11.1403C15.8685 11.1732 15.7472 11.1991 15.6433 11.2184C15.5383 11.238 15.4729 11.2465 15.4312 11.2492C15.388 11.2519 15.4022 11.2459 15.4456 11.2571C15.5015 11.2715 15.5728 11.3058 15.6335 11.3665L14.5728 12.4272C14.8844 12.7388 15.272 12.7623 15.5264 12.7461C15.7673 12.7308 16.0586 12.6665 16.3361 12.6072L16.0224 11.1403ZM14.3928 10.6639C14.3335 10.9414 14.2692 11.2327 14.2539 11.4736C14.2377 11.728 14.2612 12.1156 14.5728 12.4272L15.6335 11.3665C15.6942 11.4272 15.7285 11.4985 15.7429 11.5544C15.7541 11.5978 15.7481 11.612 15.7508 11.5688C15.7535 11.5271 15.762 11.4617 15.7816 11.3567C15.8009 11.2528 15.8268 11.1315 15.8597 10.9776L14.3928 10.6639ZM20.7663 6.23372C21.0921 6.55955 21.1464 6.62298 21.1722 6.66763L22.4712 5.91763C22.3218 5.65885 22.0845 5.4306 21.8269 5.17306L20.7663 6.23372ZM21.8269 8.74288C22.0845 8.48535 22.3218 8.2571 22.4712 7.99831L21.1722 7.24831C21.1464 7.29297 21.0921 7.3564 20.7663 7.68222L21.8269 8.74288ZM21.1722 6.66763C21.2759 6.8473 21.2759 7.06865 21.1722 7.24831L22.4712 7.99831C22.8429 7.35455 22.8429 6.5614 22.4712 5.91763L21.1722 6.66763ZM21.8269 5.17306C21.5694 4.91553 21.3412 4.67817 21.0824 4.52876L20.3324 5.8278C20.377 5.85358 20.4405 5.9079 20.7663 6.23372L21.8269 5.17306ZM19.3178 6.23372C19.6436 5.9079 19.707 5.85358 19.7517 5.8278L19.0017 4.52876C18.7429 4.67817 18.5147 4.91553 18.2571 5.17306L19.3178 6.23372ZM21.0824 4.52876C20.4386 4.15708 19.6455 4.15708 19.0017 4.52876L19.7517 5.8278C19.9313 5.72407 20.1527 5.72407 20.3324 5.8278L21.0824 4.52876ZM17.8719 10.5766C17.7177 10.7308 17.5023 10.8357 17.1779 10.9186C17.0153 10.9601 16.8409 10.9924 16.6433 11.0266C16.4545 11.0592 16.2342 11.095 16.0224 11.1403L16.3361 12.6072C16.5103 12.5699 16.6886 12.5409 16.8987 12.5047C17.0999 12.4699 17.3246 12.4292 17.549 12.372C17.9985 12.2572 18.5086 12.0613 18.9326 11.6372L17.8719 10.5766ZM15.8597 10.9776C15.905 10.7658 15.9408 10.5455 15.9734 10.3567C16.0076 10.1591 16.0399 9.98467 16.0814 9.8221C16.1643 9.49768 16.2692 9.28231 16.4234 9.12808L15.3628 8.06742C14.9387 8.49143 14.7428 9.00154 14.628 9.45104C14.5708 9.67544 14.5301 9.90012 14.4953 10.1013C14.4591 10.3114 14.4301 10.4897 14.3928 10.6639L15.8597 10.9776Z"
        fill={fillColor}
      />
    </svg>
  );
}; 

export const NewGridIcon: React.FC<SvgRendererProps> = ({ theme, view }) => {
  const activeFillColor = theme === "REGALBLAZE" ? "#FCA311" : "#BC3D81";
  const inactiveFillColor = "#a8a8a8";
  const fillColor = view ? activeFillColor : inactiveFillColor;

  return (
    <svg
      width="34"
      height="34"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      
    >
      <path
        d="M2 11.4C2 10.2417 2.24173 10 3.4 10H20.6C21.7583 10 22 10.2417 22 11.4V12.6C22 13.7583 21.7583 14 20.6 14H3.4C2.24173 14 2 13.7583 2 12.6V11.4Z"
        stroke={fillColor}
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path
        d="M2 3.4C2 2.24173 2.24173 2 3.4 2H20.6C21.7583 2 22 2.24173 22 3.4V4.6C22 5.75827 21.7583 6 20.6 6H3.4C2.24173 6 2 5.75827 2 4.6V3.4Z"
        stroke={fillColor}
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path
        d="M2 19.4C2 18.2417 2.24173 18 3.4 18H20.6C21.7583 18 22 18.2417 22 19.4V20.6C22 21.7583 21.7583 22 20.6 22H3.4C2.24173 22 2 21.7583 2 20.6V19.4Z"
        stroke={fillColor}
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
};

