/* eslint-disable @typescript-eslint/no-namespace */
import axios from 'axios';

// export namespace BMTrends {
//     export const getBMTrendsData = async () => {
//         return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getBMTrendData/`, {
//             headers: { 'Content-Type': 'application/json' }
//         });
//     }
// }

export const getBMTrendsData = async (plant: number) => {
  return await axios.get(
    process.env.REACT_APP_VF_API_HOST_MTO + `/getBMTrendData/`, {
      headers: {
        "Content-Type": "application/json",
      },
      params: {
        plantId: plant
      },
    }
  );
};