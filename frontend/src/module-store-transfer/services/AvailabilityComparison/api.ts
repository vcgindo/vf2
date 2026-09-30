/* eslint-disable @typescript-eslint/no-namespace */
import axios from "axios";

export namespace AvailabilityComparisonService {
  export const getListProductFilter = async () => {
    return await axios.get("/api/availability-comparison/list/product");
  };

  export const getListLocationFilter = async () => {
    return await axios.get("/api/availability-comparison/list/location");
  };

  export const getViewData = async (
    productFilter: any,
    locationFilter: any,
    activeTab: string,
    filterStyle: boolean
  ) => {
    const url = `/api/availability-comparison/filter/${activeTab}`;
    const bodyData = {
      product_hierarchy_1: productFilter.brand.map((item: any) => item.value),
      product_hierarchy_2: productFilter.subBrand.map((item: any) => item.value),
      product_hierarchy_3: productFilter.category.map((item: any) => item.value),
      wh_location_group: locationFilter.ISTLocGrp.map((item: any) => item.value),
      wh_region: locationFilter.region.map((item: any) => item.value),
      wh_state: locationFilter.cluster.map((item: any) => item.value),
      performance_group: locationFilter.locPerfGrp.map(
        (item: any) => item.value
      ),
      pcs_style: filterStyle,
    };
    return await axios.post(url, bodyData);
  };

  export const exportViewData = async (
    productFilter: any,
    locationFilter: any,
    activeTab: string,
    filterStyle: boolean,
    listStatus: any = []
  ) => {
    const url = "/api/availability-comparison/export";

    let pageLevel: any = "wh_code";
    if (activeTab === "store") {
      pageLevel = "wh_code";
    } else if (activeTab === "sub-brand") {
      pageLevel = "product_hierarchy_2";
    } else if (activeTab === "category") {
      pageLevel = "product_hierarchy_3";
    }

    const bodyData = {
      product_hierarchy_1: productFilter.brand.map((item: any) => item.value),
      product_hierarchy_2: productFilter.subBrand.map(
        (item: any) => item.value
      ),
      product_hierarchy_3: productFilter.category.map(
        (item: any) => item.value
      ),
      wh_location_group: locationFilter.ISTLocGrp.map(
        (item: any) => item.value
      ),
      wh_region: locationFilter.region.map((item: any) => item.value),
      wh_state: locationFilter.cluster.map((item: any) => item.value),
      performance_group: locationFilter.locPerfGrp.map(
        (item: any) => item.value
      ),
      pcs_style: filterStyle,
      page_level: pageLevel,
      list_status: listStatus,
    };
    return await axios.post(url, bodyData, { responseType: "blob" });
  };

  export const getTotalParticulars = async ( body: any ) => {    
    return await axios.post("/api/availability-comparison/total-particulars", body);
  }
}
