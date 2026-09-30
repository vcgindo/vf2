import styled from "styled-components";
export const ProcPlanningChildrenColor = styled.div`
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
`
const determineColor = (value: any) => {
    if (value === "Red") return 'Red';
    if (value === "Yellow") return 'Yellow';
    if (value === "Black") return 'Black';
    if (value === "Green") return 'Green';
    if (value === "Orange") return 'Orange';
    if (value === "Blue") return 'Blue';
    if (value === "Purple") return '#BC3D81';
    if (value === "White") return '#A8A8A8';


};
export const ChildrenColorCellRenderer = styled.div<{ value: string }>`
display: flex;
align-items: center;
justify-content: center;
width: 10px;
height: 10px;
border-radius: 50%;
margin-top: 5px;
background-color: ${(props) => determineColor(props.value)};
`;

export const Tooltipcontainer = styled.div`
margin: 2px 4px;
font-size: 12px;
`;