import { RRRColorCellRendererWrapper } from "./styles"

const colorMapper = (color: string) => {

    switch (color) {
        case "White":
            return {
                "bg": "white",
                "text": "black"
            }
        case "Yellow":
            return {
                "bg": "#EBBF2B",
                "text": "white"
            }
        case "Green":
            return {
                "bg": "#418D18",
                "text": "white"
            }
        case "Red":
            return {
                "bg": "#F04D4D",
                "text": "white"
            }
        case "Black":
            return {
                "bg": "#000000",
                "text": "white"
            }
        case "Blue":
            return {
                "bg": "#355FD3",
                "text": "white"
            }
        default:
            return {
                "bg": "white",
                "text": "black"
            }
    }
}

export const RRRTechColorCellRenderer = (params: any) => {
    const techColor = params.data.cp != undefined ? params.data.cp : params.data.TCol

    const cellColor = colorMapper(techColor)


    if (!techColor || techColor.lenght < 1) {
        return (
            <RRRColorCellRendererWrapper style={{ backgroundColor: cellColor.bg, color: cellColor.text }}>
                NULL
            </RRRColorCellRendererWrapper>
        )
    }

    return (
        <RRRColorCellRendererWrapper style={{ backgroundColor: cellColor.bg, color: cellColor.text }}>
            {params.data.cp != undefined ? params.data.cp : params.data.TPen}%
        </RRRColorCellRendererWrapper>
    )
}


export const RRREcoColorCellRenderer = (params: any) => {


    const ecoColor = params.data.ECol

    const cellColor = colorMapper(ecoColor)

    if (!ecoColor || ecoColor.lenght < 1) {
        return (
            <RRRColorCellRendererWrapper style={{ backgroundColor: cellColor.bg, color: cellColor.text }}>
                NULL
            </RRRColorCellRendererWrapper>
        )
    }

    return (
        <RRRColorCellRendererWrapper style={{ backgroundColor: cellColor.bg, color: cellColor.text }}>
            {params.data.EPen}%
        </RRRColorCellRendererWrapper>
    )
}

export const RRRDispatchColorCellRenderer = (params: any) => {


    const ecoColor = params.data.DispatchColor

    const cellColor = colorMapper(ecoColor)

    if (!ecoColor || ecoColor.lenght < 1) {
        return (
            <RRRColorCellRendererWrapper style={{ backgroundColor: cellColor.bg, color: cellColor.text }}>
                NULL
            </RRRColorCellRendererWrapper>
        )
    }

    return (
        <RRRColorCellRendererWrapper style={{ backgroundColor: cellColor.bg, color: cellColor.text }}>
            {params.data.DispatchPen}%
        </RRRColorCellRendererWrapper>
    )
}



