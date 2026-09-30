export interface TooltipValuesProps {
    countArr: number[];
    perArr: number[];
    actBtn: ActBtn;
}

export type ActBtn = {
    label: string;
    value: string;
};

export type BufferTrendData = {
    dt: string;
    b?: number;
    r?: number;
    g?: number;
    y?: number;
    bl?: number;
    w?: number;
};

export type ReasonOrderAtRiskType = {
    r: string;
    bo: number;
    ro: number;
}