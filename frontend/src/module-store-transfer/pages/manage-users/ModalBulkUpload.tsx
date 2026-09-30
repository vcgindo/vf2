import React from 'react';
import { ReactFlow, Handle, Position } from '@xyflow/react';
 
import '@xyflow/react/dist/style.css';
 
const CustomNode = ({ data }: { data: { label: string, value: boolean } }) => {

    const [checked, setChecked] = React.useState(data.value);
    return (
        <div style={{ padding: '10px', border: '1px solid #ddd', borderRadius: '5px',color: '#cecece', background: '#000000' }}>
            <input type="checkbox" onChange={(e)=>{setChecked(e.target.checked)}}  checked={checked} style={{ marginRight: '10px' }} />
            <span>{data.label}</span>
            <Handle type="target" position={Position.Left} style={{ background: '#555' }} />
            <Handle type="source" position={Position.Right} style={{ background: '#555' }} />
        </div>
    );
};

const nodeTypes = {
    customNode: CustomNode,
};

export default function PermissionHeirarchyCanvas(heirarchyData: any) {

    const [nodes, setNodes] = React.useState<any>([]);
    const [edges, setEdges] = React.useState<any>([]);
    React.useEffect(()=>{
        setNodes(heirarchyData.nodes);
        setEdges(heirarchyData.edges);
    },[heirarchyData])
    // const nodes = [
    //     { id: '1', type: 'customNode', position: { x: 0, y: 0 }, data: { label: 'Parent Node', value: true } },
    //     { id: '2', type: 'customNode', position: { x: 200, y: 100 }, data: { label: 'Child Node 1', value: true } },
    //     { id: '3', type: 'customNode', position: { x: 400, y: 0 }, data: { label: 'Child Node 2', value: false} },
    // ];

    // const edges = [
    //     { id: 'e1-2', source: '1', target: '2' },
    //     { id: 'e1-3', source: '2', target: '3' },
    // ];

    return (
        <div style={{ width: '80vw', height: '80vh' }}>
            <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} />
        </div>
    );
}