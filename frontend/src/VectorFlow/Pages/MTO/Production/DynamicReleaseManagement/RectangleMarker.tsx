import { Marker } from "ag-charts-community";

export class Rectangle extends Marker {
    updatePath() {
        const { x, y, path, size } = this;
        const width = size * 4;
        const height = size / 2;

        path.clear();
        path.rect(x - width / 2, y - height / 2, width, height);
    }
}
