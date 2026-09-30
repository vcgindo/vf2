import styled from "styled-components";
interface ColorValues {
    B?: number;
    R?: number;
    Y?: number;
    G?: number;
    W?: number;
    Bl?: number;
}

export const ColorPriorityCellRenderer = styled.div<ColorValues>`
    position: relative;
    height: 70%;
    width: 90%;
    max-width: 150px;
    background: #000000 0% 0% no-repeat padding-box;
    &::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        bottom: 0;
        width: 100%;
        background: ${(props) => {
        const { B = 0, R = 0, Y = 0, G = 0, W = 0, Bl = 0 } = props;

        const colorStops: string[] = [];
        if (B > 0) colorStops.push(`#000000 0% ${B}%`);
        if (R > 0) colorStops.push(`#E53F3F ${B}% ${B + R}%`);
        if (Y > 0) colorStops.push(`#EBBF2C ${B + R}% ${B + R + Y}%`);
        if (G > 0) colorStops.push(`#4CAF50 ${B + R + Y}% ${B + R + Y + G}%`);
        if (W > 0) colorStops.push(`#cecece ${B + R + Y + G}% ${B + R + Y + G + W}%`);
        if (Bl > 0) colorStops.push(`#0000FF ${B + R + Y + G + W}% 100%`);

        if (colorStops.length === 0) {
            // If no colors are provided, default to white
            colorStops.push('#FFFFFF 0% 100%');
        }

        return `linear-gradient(to right, ${colorStops.join(', ')})`;
    }};
    }
`;

export const ColorPriorityCellRendererWrapper = styled.div`
    height:100%;
    width:100%;
    display:flex;
    align-items:center;
    justify-content:center;
`