export const gridColumnConfig = [
    {
        cc: "tag",
        cp: 0,
        hd: "Tags",
        v: true,
        cla: "center",
        scc: "tag"
    },
    {
        cc: "bpp",
        cp: 1,
        hd: "BPP",
        v: true,
        cla: "center",
        scc: "bpp",
      },
      {
        cc: "plnt",
        cp: 2,
        hd: "Plant",
        v: true,
        cla: "center",
        scc: "plnt",
      },
      {
        cc: "oid",
        cp: 3,
        hd: "Order Id",
        v: true,
        cla: "center",
        scc: "oid",
      },
      {
        cc: "ot",
        cp: 4,
        hd: "Order Type",
        v: true,
        cla: "center",
        scc: "ot",
      },
      {
        cc: "lid",
        cp: 5,
        hd: "Line Item Id",
        v: true,
        cla: "center",
        scc: "lid",
      },
      {
        cc: "ic",
        cp: 6,
        hd: "Item Code",
        v: true,
        cla: "center",
        scc: "ic",
      },
      {
        cc: "id",
        cp: 7,
        hd: "Item Description",
        v: true,
        cla: "center",
        scc: "id",
      },
      {
        cc: "oqty",
        cp: 8,
        hd: "Order Quantity",
        v: true,
        cla: "center",
        scc: "oqty",
      },
      {
        cc: "dd",
        cp: 9,
        hd: "Due Date",
        v: true,
        cla: "center",
        scc: "dd",
      },
      {
        cc: "cdt",
        cp: 10,
        hd: "Order Closing Date",
        v: true,
        cla: "center",
        scc: "cdt",
      },
      {
        cc: "mjr_r",
        cp: 20,
        hd: "Major Reason",
        v: true,
        cla: "center",
        scc: "mjr_r",
      },
      {
        cc: "min_r",
        cp: 21,
        hd: "Minor Reason",
        v: true,
        cla: "center",
        scc: "min_r",
      },
      {
        cc: "cc",
        cp: 13,
        hd: "Customer Code",
        v: true,
        cla: "center",
        scc: "cc",
      },
      {
        cc: "cn",
        cp: 14,
        hd: "Customer Name",
        v: true,
        cla: "center",
        scc: "cn",
      },
  
  ];

export const MockGridData = [
    {
        tag: 1,
        bpp: 100,
        plnt: "A",
        oid: "123",
        ot: "abc",
        lid: "321",
        ic: "a",
        id: "desc",
        oqty: 120,
        dd: "2024-04-24",
        cdt: "2024-04-24",
        cc: 101,
        cn: "Zara", 
        mjr_r: "packing",
        min_r: "ABC"
    },
    {
        tag: 2,
        bpp: 100,
        plnt: "A",
        oid: "123",
        ot: "abc",
        lid: "321",
        ic: "a",
        id: "desc",
        oqty: 120,
        dd: "2024-04-24",
        cdt: "2024-04-24",
        cc: 101,
        cn: "Zara", 
        mjr_r: "packing",
        min_r: "ABC"
    },
    {
        tag: 0,
        bpp: 100,
        plnt: "A",
        oid: "123",
        ot: "abc",
        lid: "321",
        ic: "a",
        id: "desc",
        oqty: 120,
        dd: "2024-04-24",
        cdt: "2024-04-24",
        cc: 101,
        cn: "Zara", 
        mjr_r: "packing",
        min_r: "ABC"
    },
    {
        tag: 3,
        bpp: 100,
        plnt: "A",
        oid: "123",
        ot: "abc",
        lid: "321",
        ic: "a",
        id: "desc",
        oqty: 120,
        dd: "2024-04-24",
        cdt: "2024-04-24",
        cc: 101,
        cn: "Zara", 
        mjr_r: "packing",
        min_r: "ABC"
    },
    {
        tag: 3,
        bpp: 100,
        plnt: "A",
        oid: "123",
        ot: "abc",
        lid: "321",
        ic: "a",
        id: "desc",
        oqty: 120,
        dd: "2024-04-24",
        cdt: "2024-04-24",
        cc: 101,
        cn: "Zara", 
        mjr_r: "packing",
        min_r: "ABC"
    },
    {
        tag: 3,
        bpp: 100,
        plnt: "A",
        oid: "123",
        ot: "abc",
        lid: "321",
        ic: "a",
        id: "desc",
        oqty: 120,
        dd: "2024-04-24",
        cdt: "2024-04-24",
        cc: 101,
        cn: "Zara", 
        mjr_r: "packing",
        min_r: "ABC"
    },
]

export const reasonColConfig =  [
    { 
        "cc": "r",
        "cp": 1,
        "hd": "Major | Minor Reasons",
        "v": true,
        "cla": "left",
        "scc": "r"
    },
    { 
        "cc": "co",
        "cp": 2,
        "hd": "Count Of Orders",
        "v": true,
        "cla": "left",
        "scc": "co"
    },
]

export const MockGraphData =  {
    previous: {
    start: '17 June 2024',
    end: '16 July 2024',
    data: [
    {
        co: 50,
        r: 'Dept 1 | Annealing - Rolling'

    },
    {
        co: 60,
        r: 'Dept 1 | Sales'

    },
    {
        co: 42,
        r: 'Dept 1 | Release Delay - com...'
    },
    {
        co: 42,
        r: 'Dept 1 | Quality'
    },
    {
        co: 42,
        r: 'Dept 1 | Man Absenteeism'
    },
    {
        co: 42,
        r: 'Dept 2 | Planning ( delay in )'
    },
    {
        co: 42,
        r: 'Dept 1 | Material Batch Quality'
    },
    {
        co: 42,
        r: 'Dept 2 | Incorrect Communication'
    },
    {
        co: 42,
        r: 'Dept 1 | Packing'
    },
    {
        co: 42,
        r: 'Dept 2 | Tempering'
    },
    {
        co: 42,
        r: 'Dept 2 | Man - Maintenance'
    },
]},
    current: {
    start: '17 July 2024',
    end: '16 Aug 2024',
    data: [
    {
        co: 50,
        r: 'Dept 1 | Annealing - Rolling'

    },
    {
        co: 60,
        r: 'Dept 1 | Sales'

    },
    {
        co: 42,
        r: 'Dept 1 | Release Delay - com...'
    },
    {
        co: 42,
        r: 'Dept 1 | Quality'
    },
    {
        co: 42,
        r: 'Dept 1 | Man Absenteeism'
    },
    {
        co: 42,
        r: 'Dept 2 | Planning ( delay in )'
    },
    {
        co: 42,
        r: 'Dept 1 | Material Batch Quality'
    },
    {
        co: 42,
        r: 'Dept 2 | Incorrect Communication'
    },
    {
        co: 42,
        r: 'Dept 1 | Packing'
    },
    {
        co: 42,
        r: 'Dept 2 | Tempering'
    },
    {
        co: 42,
        r: 'Dept 2 | Man - Maintenance'
    },
]}
}