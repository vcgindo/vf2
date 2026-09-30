import { BufferTrendData } from "../../../../../src/types/MTO/types";

export const  convertToPercentage = (data: BufferTrendData[]): BufferTrendData[] => {
    return data.map(entry => {
        let total = 0;
        if (entry?.b) {
            total += entry?.b;
        }
        if (entry?.r) {
            total += entry?.r;
        }
        if (entry?.g) {
            total += entry?.g;
        }
        if (entry?.y) {
            total += entry?.y;
        }
        if (entry?.w) {
            total += entry?.w;
        }
        if (entry?.bl) {
            total += entry?.bl;
        }

        if (total === 0) {
            return entry
        }

        return {
            dt: entry?.dt,
            b: entry?.b ? ((entry?.b / total) * 100) : 0,
            r: entry?.r ? ((entry?.r / total) * 100) : 0,
            g: entry?.g ? ((entry?.g / total) * 100) : 0,
            y: entry?.y ? ((entry?.y / total) * 100) : 0,
            bl: entry?.bl ? ((entry?.bl / total) * 100) : 0,
            w: entry?.w ? ((entry?.w / total) * 100) : 0,
        };
    });

}

export const filterDataByDaysGap = (buffData: BufferTrendData[], numberOfDaysGap: number, horizonDays: number, isPer: boolean): BufferTrendData[] => {
    const filteredData: (BufferTrendData[]) = [];
    const data = (isPer) ? convertToPercentage(buffData) : buffData;
    let currentDate = new Date(data[0]?.dt?.split('-')?.reverse()?.join('-')); // Convert dd-mm-yyyy to yyyy-mm-dd

    filteredData.push(data[0]);

    for (let i = 1; i < ((horizonDays < data.length) ? horizonDays : data.length); i++) {
        const prevDate = new Date(data[i]?.dt?.split('-')?.reverse()?.join('-'));

        const diffInDays = (prevDate.getTime() + currentDate.getTime()) / (1000 * 60 * 60 * 24);

        if (diffInDays >= numberOfDaysGap) {
            filteredData.push(data[i]);
            currentDate = prevDate;
        }
    }

    return filteredData?.reverse();
}

export const formatDate = (date: Date): string => {
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${day}-${month}-${year}`;
}

export const convertToGraphData = (lastRunDate: Date ,apiData: any) => {
    const startDate = formatDate(new Date(lastRunDate));
    const numDays = 90;
    const updatedData: BufferTrendData[] = [];
    const dateParts = startDate?.split('-');
    const date = new Date(`${dateParts[2]}-${dateParts[1]}-${dateParts[0]}`); // Convert to YYYY-MM-DD

    for (let i = 0; i < numDays; i++) {
        const day = formatDate(date);
        let entry: any = {
            'dt': day,
            'b': 0,
            'r': 0,
            'g': 0,
            'y': 0,
            'bl': 0,
            'w': 0,
        };
        const newDate = day?.split('-')?.reverse()?.join('-');
        if (apiData[newDate]) {
            if (apiData[newDate]?.B) {
                entry = { ...entry, b: apiData[newDate]?.B || 0 }
            }
            if (apiData[newDate]?.R) {
                entry = { ...entry, r: apiData[newDate]?.R || 0 }
            }
            if (apiData[newDate]?.G) {
                entry = { ...entry, g: apiData[newDate]?.G || 0 }
            }
            if (apiData[newDate]?.Y) {
                entry = { ...entry, y: apiData[newDate]?.Y || 0 }
            }
            if (apiData[newDate]?.W) {
                entry = { ...entry, w: apiData[newDate]?.W || 0 }
            }
            if (apiData[newDate]?.Bl) {
                entry = { ...entry, bl: apiData[newDate]?.Bl || 0 }
            }
        }

        updatedData.push(entry);
        date.setDate(date.getDate() - 1);
    }
    return updatedData;
}
