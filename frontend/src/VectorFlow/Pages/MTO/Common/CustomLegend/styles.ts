import styled from "styled-components";

export const CustomLegendWrapper = styled.div`
    display: flex;
    gap: 12px;
    justify-content: center;
    background: white;
    padding-top: 5px;
    height: 20px !important;
    max-height: 20px !important;
`;

export const LegendOptionsWrapper = styled.div<{opacity: number }>`
    display: flex;
    align-items: center;
    cursor: pointer;
    opacity: ${(props)=>props.opacity};
`;

export const LegendOptions = styled.span<{background:string}>`
    display: inline-block;
    width: 14px;
    height: 14px;
    margin-right: 6px;
    border-radius: 3px;
    background: ${(props) => props.background};
`;

export const LegendOptionsName = styled.span`
    font: 12px;
`;
