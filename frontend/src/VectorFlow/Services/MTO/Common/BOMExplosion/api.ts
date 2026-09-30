import axios from 'axios';

// eslint-disable-next-line @typescript-eslint/no-namespace
export namespace BOMService {

    export const getBOMExplosionData = async (orderId: string, lineId: string) => {
        return await axios.get(process.env.REACT_APP_VF_API_HOST_MTO + `/getBomExplosionData/`, {
            headers: {
                'Content-Type': 'application/json',
            },
            params: {
                oid: orderId,
                lid: lineId
            }
        })
    }

}
