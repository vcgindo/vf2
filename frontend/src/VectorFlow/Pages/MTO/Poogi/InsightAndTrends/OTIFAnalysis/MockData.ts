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
      cc: "ex_delay",
      cp: 11,
      hd: "Extend Of Delay (In Days)",
      v: true,
      cla: "center",
      scc: "ex_delay",
    },
    {
      cc: "ex_shortage",
      cp: 12,
      hd: "Extend Of Shortage",
      v: true,
      cla: "center",
      scc: "ex_shortage",
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
    {
      cc: "crdd",
      cp: 15,
      hd: "CRDD",
      v: true,
      cla: "center",
      scc: "crdd",
    },
    {
      cc: "rdt",
      cp: 16,
      hd: "Release Date",
      v: true,
      cla: "center",
      scc: "rdt",
    },
    {
      cc: "oattr",
      cp: 17,
      hd: "Order Attribute 1",
      v: true,
      cla: "center",
      scc: "oattr",
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

];

export const graphColumnConfig = {
  otif: [
      { 
          "cc": "m",
          "cp": 1,
          "hd": "Week",
          "v": true,
          "cla": "left",
          "scc": "m"
      },
      { 
          "cc": "otif_plus",
          "cp": 1,
          "hd": "Otif % Trends (+3 Days)",
          "v": true,
          "cla": "left",
          "scc": "otif_plus"
      },
      { 
          "cc": "otif",
          "cp": 2,
          "hd": "Otif % Trends",
          "v": true,
          "cla": "left",
          "scc": "otif"
      },
  ],
  ot_n_if: [
      { 
          "cc": "m",
          "cp": 0,
          "hd": "Week",
          "v": true,
          "cla": "left",
          "scc": "m"
      },
      { 
          "cc": "ot",
          "cp": 1,
          "hd": "On Time %",
          "v": true,
          "cla": "left",
          "scc": "ot"
      },
      { 
          "cc": "if",
          "cp": 2,
          "hd": "In Full %",
          "v": true,
          "cla": "left",
          "scc": "if"
      },
  ]
}

export const APIMock = {
  grid: [
      {
          tags: 1,
          bpp: 100,
          plnt: "A",
          order_id: "123",
          order_type: "abc",
          lineitmid: "321",
          item_code: "a",
          item_desc: "desc",
          oq: 120,
          due_dt: "2024-04-24",
          orclsdt: "2024-04-24",
          ex_delay: 16,
          ex_short: 19,
          cus_code: 101,
          cus_name: "Zara", 
          crdd: "2024-04-24",
          release_dt: "2024-04-24",
          or_Att1: "NA",
          or_Att2: "NA",
          or_Att3: "NA",
          mjr_r: "packing",
          min_r: "ABC"
      },
      {
          tags: 2,
          bpp: 100,
          plnt: "A",
          order_id: "123",
          order_type: "abc",
          lineitmid: "321",
          item_code: "a",
          item_desc: "desc",
          oq: 120,
          due_dt: "2024-04-24",
          orclsdt: "2024-04-24",
          ex_delay: 16,
          ex_short: 19,
          cus_code: 101,
          cus_name: "Zara", 
          crdd: "2024-04-24",
          release_dt: "2024-04-24",
          or_Att1: "NA",
          or_Att2: "NA",
          or_Att3: "NA",
          mjr_r: "packing",
          min_r: "ABC"
      },
      {
          tags: 0,
          bpp: 100,
          plnt: "A",
          order_id: "123",
          order_type: "abc",
          lineitmid: "321",
          item_code: "a",
          item_desc: "desc",
          oq: 120,
          due_dt: "2024-04-24",
          orclsdt: "2024-04-24",
          ex_delay: 16,
          ex_short: 19,

          cus_code: 101,
          cus_name: "Zara", 
          crdd: "2024-04-24",
          release_dt: "2024-04-24",
          or_Att1: "NA",
          or_Att2: "NA",
          or_Att3: "NA",
          mjr_r: "packing",
          min_r: "ABC"
      },
      {
          tags: 3,
          bpp: 100,
          plnt: "A",
          order_id: "123",
          order_type: "abc",
          lineitmid: "321",
          item_code: "a",
          item_desc: "desc",
          oq: 120,
          due_dt: "2024-04-24",
          orclsdt: "2024-04-24",
          ex_delay: 16,
          ex_short: 19,

          cus_code: 101,
          cus_name: "Zara", 
          crdd: "2024-04-24",
          release_dt: "2024-04-24",
          or_Att1: "NA",
          or_Att2: "NA",
          or_Att3: "NA",
          mjr_r: "packing",
          min_r: "ABC"
      },
      {
          tags: 3,
          bpp: 100,
          plnt: "A",
          order_id: "123",
          order_type: "abc",
          lineitmid: "321",
          item_code: "a",
          item_desc: "desc",
          oq: 120,
          due_dt: "2024-04-24",
          orclsdt: "2024-04-24",
          ex_delay: 16,
          ex_short: 19,

          cus_code: 101,
          cus_name: "Zara", 
          crdd: "2024-04-24",
          release_dt: "2024-04-24",
          or_Att1: "NA",
          or_Att2: "NA",
          or_Att3: "NA",
          mjr_r: "packing",
          min_r: "ABC"
      },
      {
          tags: 3,
          bpp: 100,
          plnt: "A",
          order_id: "123",
          order_type: "abc",
          lineitmid: "321",
          item_code: "a",
          item_desc: "desc",
          oq: 120,
          due_dt: "2024-04-24",
          orclsdt: "2024-04-24",
          ex_delay: 16,
          ex_short: 19,

          cus_code: 101,
          cus_name: "Zara", 
          crdd: "2024-04-24",
          release_dt: "2024-04-24",
          or_Att1: "NA",
          or_Att2: "NA",
          or_Att3: "NA",
          mjr_r: "packing",
          min_r: "ABC"
      },
  ],
  graph: {
      otif_graph: {
          start: '1 May 2024',
          end: '1 Aug 2024',
          data: [
          {
              otif_plus: 60,
              otif: 50,
              x_label: 'May 2024'

          },
          {
              otif_plus: 60,
              otif: 50,
              x_label: 'Jun 2024'

          },
          {
              otif_plus: 42,
              otif: 30,
              x_label: 'Jul 2024 - wk 1'
          },
          {
              otif_plus: 42,
              otif: 30,
              x_label: 'Jul 2024 - wk 2'
          },
          {
              otif_plus: 42,
              otif: 30,
              x_label: 'Jul 2024 - wk 3'
          },
          {
              otif_plus: 42,
              otif: 30,
              x_label: 'Jul 2024 - wk 4'
          }
      ]},
      ot_n_if_graph:{
          start: '1 Jun 2024',
          end: '4 Aug 2024',
          data: [
          {
              if: 60,
              ot: 50,
              x_label: 'Jun 2024'

          },
          {
              if: 115,
              ot: 45,
              x_label: 'Jul 2024'
          },
          {
              if: 42,
              ot: 30,
              x_label: 'Aug 2024 - wk 1'
          }
      ]},
  }
};
