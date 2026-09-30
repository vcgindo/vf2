import axios from "axios";
import { EnquiryResponseService } from "./api";

jest.mock("axios");

describe("EnquiryResponseService", () => {
  const mockResponse = {
    msg: "Enquiry response data fetched successfully",
    data: {
      links: { next: null, previous: null },
      count: 4,
      nop: 1,
      results: [
        {
          cid: 1,
          plid: 2,
          plnm: "plant name 2",
          dpid: 1,
          dpnm: "dept 01",
          gid: 1,
          gnm: "CCR Group 1",
          cnm: "ccr_01_Name",
          fol: null,
          it: { ItemType1: { id: 1, proc_size: 30, prod_size: 10 } },
        },
        {
          cid: 2,
          plid: 3,
          plnm: "plant name 3",
          dpid: 2,
          dpnm: "dept 02",
          gid: 2,
          gnm: "CCR Group 2",
          cnm: "ccr_02_Name",
          fol: null,
          it: { ItemType2: { id: 2, proc_size: 12, prod_size: 12 } },
        },
        {
          cid: 3,
          plid: 3,
          plnm: "plant name 3",
          dpid: 3,
          dpnm: "dept 03",
          gid: 3,
          gnm: "CCR Group 3",
          cnm: "ccr_03_Name",
          fol: null,
          it: { ItemType3: { id: 3, proc_size: 13, prod_size: 13 } },
        },
        {
          cid: 4,
          plid: 4,
          plnm: "plant name 4",
          dpid: 4,
          dpnm: "dept 04",
          gid: 4,
          gnm: "CCR Group 4",
          cnm: "ccr_04_Name",
          fol: null,
          it: {
            ItemType4: {
              id: 4,
              proc_size: 9,
              prod_size: 8,
            },
          },
        },
      ],
    },
  };

  beforeEach(() => {
    jest.spyOn(axios, "get").mockResolvedValueOnce(mockResponse);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("should fetch Enquiry response data correctly", async () => {
    const response = await EnquiryResponseService.getEnquiryData();

    expect(axios.get).toHaveBeenCalledWith(
      `${process.env.REACT_APP_VF_API_HOST_MTO}/getEnquiryResponseData/`,
      {
        headers: { "Content-Type": "application/json" },
      }
    );

    expect(response).toEqual(mockResponse);
  });
});
