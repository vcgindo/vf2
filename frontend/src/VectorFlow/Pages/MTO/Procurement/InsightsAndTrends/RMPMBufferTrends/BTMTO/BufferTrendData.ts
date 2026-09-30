type BufferTrendData = {
    'dt': string;
    'b': number;
    'r': number;
    'g': number;
    'y': number;
    'w': number;
};

function generateDummyData(startDate: string, numDays: number): BufferTrendData[] {
    const data: BufferTrendData[] = [];
    const dateParts = startDate.split('-');
    const date = new Date(`${dateParts[2]}-${dateParts[1]}-${dateParts[0]}`); // Convert to YYYY-MM-DD

    for (let i = 0; i < numDays; i++) {
        const entry: BufferTrendData = {
            'dt': formatDate(date),
            'b': getRandomValue('b'),
            'r': getRandomValue('r'),
            'g': getRandomValue('g'),
            'y': getRandomValue('y'),
            'w': getRandomValue('w'),
        };
        data.push(entry);
        date.setDate(date.getDate() + 1);
    }

    return data;
}

function formatDate(date: Date): string {
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${day}-${month}-${year}`;
}

function getRandomValue(str: string): number {

    if (str === 'b') {

        return Math.floor(Math.random() * 4) + 1; // Random value between 1 and 20
    }
    if (str === 'r') {

        return Math.floor(Math.random() * 8) + 1; // Random value between 1 and 20
    }
    if (str === 'y') {

        return Math.floor(Math.random() * 12) + 1; // Random value between 1 and 20
    }
    if (str === 'g') {

        return Math.floor(Math.random() * 16) + 1; // Random value between 1 and 20
    }
    if (str === 'w') {

        return Math.floor(Math.random() * 20) + 1; // Random value between 1 and 20
    }
    else {
        return Math.floor(Math.random() * 20) + 1; // Random value between 1 and 20

    }
}

// Usage example
const startDate = '26-06-2024';
const numDays = 90;
const dummyData = generateDummyData(startDate, numDays);

export default dummyData;