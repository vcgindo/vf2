import styled from "styled-components";
import * as globalStyles from "../../../../../styles/global";

export const MTOCheckBox = styled.input<{theme:string}>`
    width: 2.5rem !important;
    height: 2.5rem !important;
    border-radius: 2px;
    border: 2px solid rgb(148, 154, 171);
    background-color: white;
    appearance: none;
    cursor: pointer;
    &:checked {
        background-color: ${props => globalStyles.chooseThemeColor[props.theme]?.color4};
        border-color: ${props => globalStyles.chooseThemeColor[props.theme]?.color4};
        background-repeat: no-repeat;
        background-position: center;
        background-size: contain;
        background-image: url(/assets/img/mto/dueDateQuotation/checked.svg);
    }
`

MTOCheckBox.defaultProps = {
    type: "checkbox"
}

// input[type="checkbox"]:checked {
//     background-color: rgb(80, 158, 227);
//     border-color: rgb(80, 158, 227);
//     background-repeat: no-repeat;
//     background-position: center;
//     background-size: contain;
//     background-image: url("data:image/svg+xml,%3csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 20 20%27%3e%3cpath fill=%27none%27 stroke=%27%23fff%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27 stroke-width=%273%27 d=%27m6 10 3 3 6-6%27/%3e%3c/svg%3e")
//   }