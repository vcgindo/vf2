export const APIMock = {
    utilization: [
        {
            ccr: 'M1',
            limit: 100
        },
        {
            ccr: 'M2',
            limit: 90
        },
        {
            ccr: 'M3',
            limit: 80
        },
        {
            ccr: 'M4',
            limit: 75
        },
        {
            ccr: 'M5',
            limit: 70
        },
        {
            ccr: 'M6',
            limit: 65
        },
        {
            ccr: 'M7',
            limit: 60
        },
        {
            ccr: 'M8',
            limit: 50
        },
        {
            ccr: 'M9',
            limit: 40
        },
        {
            ccr: 'M10',
            limit: 30
        },
    ],
    wipLimit: [
        {
            overLimit: 110,
            underLimit: 80,
            ccr: 'M1',
            limit: 100
        },
        {
            overLimit: 110,
            underLimit: 80,
            ccr: 'M2',
            limit: 90
        },
        {
            overLimit: 100,
            underLimit: 60,
            ccr: 'M3',
            limit: 80
        },
        {
            overLimit: 90,
            underLimit: 60,
            ccr: 'M4',
            limit: 75
        },
        {
            overLimit: 90,
            underLimit: 50,
            ccr: 'M5',
            limit: 70
        },
        {
            overLimit: 80,
            underLimit: 50,
            ccr: 'M6',
            limit: 65
        },
        {
            overLimit: 80,
            underLimit: 40,
            ccr: 'M7',
            limit: 60
        },
        {
            overLimit: 60,
            underLimit: 40,
            ccr: 'M8',
            limit: 50
        },
        {
            overLimit: 60,
            underLimit: 30,
            ccr: 'M9',
            limit: 40
        },
        {
            overLimit: 40,
            underLimit: 20,
            ccr: 'M10',
            limit: 30
        },
    ]

    // calenderRequest: {
    //     ccr: "M1",
    //     calender: [
    //         {
    //             type: 'Utilization',
    //             month: 'July',
    //             year: 2024
    //         },
    //         {
    //             type: 'Wip Control',
    //             month: 'July',
    //             year: 2024
    //         }
    //     ]
    // }

    // response: {
    //     wip:{
    //         overLimit: ['15-07-2024', '01-07-2024'],
    //         underLimit: ['05-07-2024', '10-07-2024']
    //     },
    //     utilization:{
    //         low: ['15-07-2024', '01-07-2024'],
    //         medium: ['05-07-2024', '10-07-2024'],
    //         high: ['12-07-2024', '29-07-2024']
    //     }
    // }
}