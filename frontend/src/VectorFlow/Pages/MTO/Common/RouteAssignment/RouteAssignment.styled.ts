import styled from "styled-components";

export const StepperWrapper = styled.div<{ ccrMasterLength?: number }>`
  flex-wrap: wrap;
  display: flex;
  justify-content: start;
  font-size: 12px;
  padding: 2rem 2rem;
  margin: 1.5rem 0;
  gap: 32px;
  border: 1px dashed #707070;
  border-radius: 10px;
  position: relative;
  &.route-assignment > .step-group > div{
    flex: 1;
  }
  &.buffer-assignment > .step-group > div:nth-of-type(2){
    flex: 1.5;
  }
    
    /* Adjust justify-content based on window width */
  @media (max-width: 1200px) {
    justify-content: start;
  }

  @media only screen and (min-width: 1201px) {
    justify-content : ${props => {
      if (props.ccrMasterLength) {
        if (props.ccrMasterLength <= 3) {
          return "start";
        } else if (props.ccrMasterLength <= 6) {
          return "end";
        } else if (props.ccrMasterLength <= 9) {
          return "start";
        } else {
          return "end";
        }
      } else {
        return "start";
      }
    }};
  }
`;

StepperWrapper.defaultProps = {
  className: "stepper-container",
};

export const StepGroup = styled.div<{$step:boolean}>`
  width: 30%;
  text-align: center;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0;
  background: #eae8e8;
  border-radius: 4px;
  position: relative;
 
 
  ${props => {
    return (props.$step &&
    `&[data-order="asc"]:not(:first-of-type):before {
        content: "";
        position: absolute;
        width: 5px;
        height: 5px;
        border: 1px solid #82104c;
        right: 100%;
        background: #82104c;
        border-radius: 50%;
      }
      &[data-order="asc"]#inactive:before {
        content: "";
        position: absolute;
        width: 5px;
        height: 5px;
        border: 1px solid #82104c;
        right: calc(100% + 5px);
        background: transparent;
        border-radius: 50%;
      }
      &[data-order="asc"]:not(:last-of-type):after {
        content: "";
        position: absolute;
        width: 5px;
        height: 5px;
        border: 1px solid #82104c;
        left: 100%;
        background: #82104c;
        border-radius: 50%;
      }
      &[data-order="asc"]#inactive:after {
        content: "";
        position: absolute;
        width: 5px;
        height: 5px;
        border: 1px solid #82104c;
        left: calc(100% + 5px);
        border-radius: 50%;
      }
      
      

      &[data-order="dsc"]:not(:last-of-type):before {
        content: "";
        position: absolute;
        width: 5px;
        height: 5px;
        border: 1px solid #82104c;
        background: #82104c;
        right: 100%;
        border-radius: 50%;
      }
      &[data-order="dsc"]#inactive:before {
        content: "";
        position: absolute;
        width: 5px;
        height: 5px;
        border: 1px solid #82104c;
        right: calc(100% + 5px);
        background: transparent;
        border-radius: 50%;
      }
      &[data-order="dsc"]:not(:first-of-type):after {
        content: "";
        position: absolute;
        width: 5px;
        height: 5px;
        border: 1px solid #82104c;
        background: #82104c;
        left: 100%;
        border-radius: 50%;
      }
      &[data-order="dsc"]#inactive:after {
        content: "";
        position: absolute;
        width: 5px;
        height: 5px;
        border: 1px solid #82104c;
        left: calc(100% + 5px);
        border-radius: 50%;
      }
      `)}
    }
`;

StepGroup.defaultProps = {
  className: "step-group",
};

export const StepLabel = styled.div`
  margin: 0 1rem;
  width: max-content;
`;

export const FOLIcon = styled.div<{width:number, color: string}>`
  width: 40px;
  height: 10px;
  background: lightgrey;
  margin-left: 5px;
  position:relative;
  &:before{
    content:"";
    position:absolute;
    width: ${props => props.width}%;
    height: 100%;
    background: ${props => props.color};
    left: 0;
    top:0;
  }
`