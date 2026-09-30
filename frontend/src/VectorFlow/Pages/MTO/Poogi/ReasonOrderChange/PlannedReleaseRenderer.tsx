
const PlannedReleaseRenderer = (params: any) => {

    if (!params.data) {
        return params.value || null;
    }

    return (
        params.colDef.colId === "PlannedReleaseDate" ?
            <div style={{ display: 'flex', width: '100%', alignItems: 'center' }
            }>
                <div style={{ width: '60%' }}>
                    <span>{params.data.prd} </span>
                </div>

                <div style={{ width: '10%' }}>
                    <span style={{ color: '#cfcbcb' }}>{params.data.prd === null ? '' : '|'}</span>
                </div>

                <div style={{ width: '15%' }}>
                    [ <span style={{ color: 'red' }}>{Math.sign(params.data.rdd) == 1 ? '+' + params.data.rdd : params.data.rdd}</span> ]
                </div>
            </div>
            :
            <div style={{ display: 'flex', width: '100%', alignItems: 'center' }
            }>
                <div style={{ width: '60%' }}>
                    <span>{params.data.dd} </span>
                </div>

                <div style={{ width: '10%' }}>
                    <span style={{ color: '#cfcbcb' }}>{params.data.dd === null ? '' : '|'}</span>
                </div>

                <div style={{ width: '15%' }}>
                    [ <span style={{ color: 'red' }}>{Math.sign(params.data.qdd) == 1 ? '+' + params.data.qdd : params.data.qdd}</span> ]
                </div>
            </div>
    )
}

export default PlannedReleaseRenderer