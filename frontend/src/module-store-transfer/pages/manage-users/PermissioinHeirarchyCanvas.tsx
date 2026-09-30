import React, { createContext, useContext, useEffect, useState } from "react";
import { ReactFlow, Handle, Position } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import Checkbox from "../../../components/VectorFLOW/commons/MTO/Checkbox";
import { useUserData } from "../../../context";
import { ToggleContainer, ToggleButton, ChartWrapper } from "./PermissionHeirarchyStyles";

const NodeDataContext = createContext<any>(undefined);

function useNodeDataContext() {
  const context = useContext(NodeDataContext);
  if (!context) {
    throw new Error(
      "useNodeDataContext must be used within a NodeDataProvider"
    );
  }
  return context;
}

const ViewToggle = ({
  allApplications,
  selectedApplication,
  setSelectedApplication,
}: any) => {
  return (
    <ToggleContainer>
      {allApplications.map((app: string) => (
        <ToggleButton
          key={app}
          active={selectedApplication === app}
          onClick={() => setSelectedApplication(app)}
        >
          {app === "location_permission" ? "Location" : "Product"}
        </ToggleButton>
      ))}
    </ToggleContainer>
  );
};

const CustomNode = ({
  data,
}: {
  data: {
    label: string;
    key: string;
    isOpen: boolean;
    index: number;
    level?: number;
  };
}) => {
  const {
    nodes,
    opened,
    setOpened,
    checked,
    setChecked,
    selectedPermissions,
    setSelectedPermissions,
    selectedApplication,
    permissionType,
  } = useNodeDataContext();

  const { user } = useUserData();

  const getPathArray = (key: string) =>
    key.split(">").map((part) => part.split("_")[1]);

  const pathArray = getPathArray(data.key);

  const getPermissionList = () =>
    (selectedPermissions?.[selectedApplication]?.[permissionType] ??
      []) as string[][];

  const isPermissionChecked = (key: string) => {
    const path = getPathArray(key); // e.g., ['Vendor', 'P001']
    const permissionList = getPermissionList(); // e.g., [['Vendor', 'P001', 'WSO'], ...]

    return permissionList.some((perm) =>
      path.every((val, idx) => perm[idx] === val)
    );
  };

  const getAllChildrenPaths = (pathArray: string[]) => {
    const currentPath = pathArray.join("/");
    return nodes
      .map((node: any) => ({
        path: getPathArray(node.data.key).join("/"),
        index: node.data.index,
        arrPath: getPathArray(node.data.key),
      }))
      .filter(
        ({ path }: { path: any }) =>
          path.startsWith(currentPath) && path !== currentPath
      );
  };

  const getAllParentPaths = (pathArray: string[]) => {
    const parents: string[][] = [];
    for (let i = 1; i < pathArray.length; i++) {
      parents.push(pathArray.slice(0, i));
    }
    return parents;
  };

  function getUpdatedPermissionsOnDeselect(
    currentPath: string[],
    existingPermissions: string[][]
  ): string[][] {
    // Remove all permissions that are same as or deeper than currentPath
    const updatedPermissions = existingPermissions.filter(
      (perm) => !currentPath.every((val, idx) => perm[idx] === val)
    );

    const parentPath = currentPath.slice(0, -1); // e.g. ['A','B']

    // Count how many remaining permissions still share the same parent path
    const stillHasChildren = updatedPermissions.some(
      (perm) =>
        parentPath.every((val, idx) => perm[idx] === val) &&
        perm.length > parentPath.length
    );

    const parentExists = updatedPermissions.some(
      (perm) => JSON.stringify(perm) === JSON.stringify(parentPath)
    );

    // Only add back the parentPath if it has no children left
    if (!stillHasChildren && parentPath.length > 0 && !parentExists) {
      updatedPermissions.push(parentPath);
    }

    return updatedPermissions;
  }

  const setTheChecked = () => {
    const newChecked = [...checked];
    const isCurrentlyChecked = isPermissionChecked(data.key);
    const currentPath = pathArray;
    const currentPathStr = JSON.stringify(currentPath);

    // Get all children
    const children = getAllChildrenPaths(pathArray);
    const childrenPaths = children.map((c: any) => c.arrPath);

    const allPathsToToggle = [currentPath, ...childrenPaths];
    const allPathsStr = allPathsToToggle.map((p) => JSON.stringify(p));

    // Get existing permissions
    const existingPermissions = getPermissionList();

    if (isCurrentlyChecked) {
      //  Uncheck: remove this path and all children

      const updatedPermissions = getUpdatedPermissionsOnDeselect(
        currentPath,
        existingPermissions
      );

      // Update visual check state
      newChecked[data.index] = 0;
      children.forEach(({ index }: any) => {
        newChecked[index] = 0;
      });

      setChecked(newChecked);
      setSelectedPermissions((prev: any) => ({
        ...prev,
        [selectedApplication]: {
          ...(prev[selectedApplication] || {}),
          [permissionType]: updatedPermissions,
        },
      }));
    } else {
      // ✅ Check: add current and parent paths if not present
      const parentPaths = getAllParentPaths(pathArray);
      const pathsToAdd = [currentPath];

      const updatedPermissions = existingPermissions.filter((existingPath) => {
        // Remove if existing path is a prefix of any new path
        return !pathsToAdd.some((newPath) =>
          existingPath.every((val, idx) => newPath[idx] === val)
        );
      });

      const finalPermissions = [...updatedPermissions, ...pathsToAdd];

      pathsToAdd.forEach((p) => {
        const pStr = JSON.stringify(p);
        if (!finalPermissions.some((perm) => JSON.stringify(perm) === pStr)) {
          finalPermissions.push(p);
        }
      });

      // Update visual check state
      newChecked[data.index] = 1;

      setChecked(newChecked);
      setSelectedPermissions((prev: any) => ({
        ...prev,
        [selectedApplication]: {
          ...(prev[selectedApplication] || {}),
          [permissionType]: finalPermissions,
        },
      }));
    }
  };

  const setTheIndex = () => {
    const newArr = [...opened];
    newArr[data.index] = opened[data.index] === 1 ? 0 : 1;
    setOpened(newArr);
  };

  return (
    <div
      style={{
        padding: "8px",
        border: "1px solid #ddd",
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        borderRadius: "5px",
        color: "black",
        background: "#cecece",
      }}
    >
      <label
        style={{ display: "flex", alignItems: "center", cursor: "pointer" }}
      >
        <Checkbox
          checked={isPermissionChecked(data.key)}
          onChange={setTheChecked}
          theme={user.user.theme_ui}
          style={{ zoom: 0.5 }}
        />
        <span
          style={{ padding: "10px", fontSize: "11px", fontFamily: "roboto" }}
        >
          {data.label}
        </span>
      </label>
      {!(data?.level === 2) && (
        <div
          onClick={setTheIndex}
          style={{
            margin: "2px",
            font: "bold",
            fontSize: "14px",
            cursor: "pointer",
          }}
        >
          {opened?.[data?.index] !== 1 ? (
            <img
              alt="arrow-right"
              src="\assets\img\mto\dayWiseCoverage\arrow_right.svg"
            ></img>
          ) : (
            <img
              style={{ rotate: "90deg" }}
              alt="arrow-left"
              src="\assets\img\nav\arrow_down.svg"
            ></img>
          )}
        </div>
      )}
      {data.level !== 0 && (
        <Handle
          type="target"
          position={Position.Left}
          style={{ background: "#555" }}
        />
      )}
      {data.level !== 2 && (
        <Handle
          type="source"
          position={Position.Right}
          style={{ background: "#555" }}
        />
      )}
    </div>
  );
};

const nodeTypes = {
  customNode: CustomNode,
};

export default function PermissionHeirarchyCanvas({
  dataAllPermissions,
  selectedApplication,
  selectedPermissions,
  setSelectedPermissions,
}: any) {
  const [permissionType, setPermissionType] = useState<
    "location_permission" | "product_permission"
  >("location_permission");

  const [selectedAppAllPermissions, setSelectedApplication] = useState<any>(
    dataAllPermissions?.find(
      (ele: any) => ele.application_name === selectedApplication
    )
  );

  useEffect(() => {
    setSelectedApplication(
      dataAllPermissions?.find(
        (ele: any) => ele.application_name === selectedApplication
      )
    );
  }, [selectedApplication,dataAllPermissions]);

  const [opened, setOpened] = useState<any>([]);

  const [checked, setChecked] = useState<any>([]);
  function createEdge(sourceId: string, targetId: string) {
    return {
      id: `${sourceId}-${targetId}`,
      source: sourceId,
      target: targetId,
      selectable: false,
      style: {
        stroke: "#676565",
        strokeDasharray: "5 5",
        PointerEvents: "none",
        cursor: "grab",
      },
    };
  }
const generateTreeNodesAndEdges = (
  allNodes: any,
  permissionType: string,
  opened: number[]
) => {
  if (!allNodes) {
    return { nodes: [], edges: [] };
  }
  const level1Keys = Object.keys(allNodes);
  const level1: { id: string; key: string; index: number }[] = [];
  const level2: { id: string; key: string; index: number }[] = [];
  const level3: { id: string; key: string; index: number }[] = [];
  const childrenMap = new Map<string, string[]>(); // <ParentID, ChildID[]>

  let l1Index = 0;
  let l2Index = level1Keys.length;
  let l3BaseIndex = -1; // Will be set after L2
  
  level1Keys.forEach((key, index) => {
    const l1Id = `${index}_${key}`;
    level1.push({ id: l1Id, key: key, index: index });
    childrenMap.set(l1Id, []);
    l1Index++;
  });

  level1.forEach((l1Node) => {
    const arr = Object.keys(allNodes[l1Node.key]);
    arr.forEach((item) => {
      const l2Id = `${l1Node.id}>${l2Index}_${item}`;
      level2.push({ id: l2Id, key: item, index: l2Index });
      childrenMap.get(l1Node.id)!.push(l2Id);
      childrenMap.set(l2Id, []);
      l2Index++;
    });
  });
  l3BaseIndex = l1Index + level2.length;
  let l3RelativeIndex = 0;
  level1.forEach((l1Node) => {
    childrenMap.get(l1Node.id)!.forEach((l2Id) => {
      const l2Node = level2.find(n => n.id === l2Id)!;
      const l3Items = allNodes[l1Node.key][l2Node.key];
      
      l3Items.forEach((ele: any) => {
        const l3Prop =
          permissionType === "location_permission"
            ? "location_heirarchy_3"
            : "product_hierarchy_3";
        const l3Key = ele[l3Prop];
        
        const l3Index = l3BaseIndex + l3RelativeIndex;
        
        const l3Id = `${l2Id}>${l3Index}_${l3Key}`; 
        
        level3.push({ id: l3Id, key: l3Key, index: l3Index });
        childrenMap.get(l2Id)!.push(l3Id);
        l3RelativeIndex++;
      });
    });
  });
  
  
  const finalNodes: any[] = [];
  const finalEdges: any[] = [];
  
  const START_X = 100;
  const START_Y = 100;
  const HORIZONTAL_GAP = 400;
  const NODE_VERTICAL_SPACING = 100; // Vertical gap between nodes
  const GROUP_VERTICAL_SPACING = 50;  // Extra gap between L1 groups

  let currentY = START_Y;

  const positionCache = new Map<string, { y: number; yStart: number; yEnd: number }>();

  function calculateNodePosition(nodeId: string, level: number) {
    if (positionCache.has(nodeId)) {
      return positionCache.get(nodeId)!;
    }

    const nodeInfo = 
        level === 0 ? level1.find(n => n.id === nodeId) :
        level === 1 ? level2.find(n => n.id === nodeId) :
        level3.find(n => n.id === nodeId);
        
    if (!nodeInfo) return { y: 0, yStart: 0, yEnd: 0 };

    const children = childrenMap.get(nodeId) || [];
    const isOpened = opened[nodeInfo.index] === 1;

    let yPosition: number;
    let yStartSpan: number;
    let yEndSpan: number;

    if (children.length === 0 || !isOpened) {
      yPosition = currentY;
      yStartSpan = currentY;
      yEndSpan = currentY;
      
      currentY += NODE_VERTICAL_SPACING;
    } else {
      const firstChildSpan = calculateNodePosition(children[0], level + 1);
      yStartSpan = firstChildSpan.yStart;
      yEndSpan = firstChildSpan.yEnd;
      for (let i = 1; i < children.length; i++) {
        const childSpan = calculateNodePosition(children[i], level + 1);
        yEndSpan = childSpan.yEnd; // Update the end of the span
      }
      
      yPosition = yStartSpan + (yEndSpan - yStartSpan) / 2;
    }

    finalNodes.push({
      id: nodeInfo.id,
      type: "customNode",
      position: { x: START_X + level * HORIZONTAL_GAP, y: yPosition },
      data: {
        label: nodeInfo.key,
        key: nodeInfo.id,
        isOpen: isOpened, // You can use this prop inside CustomNode
        index: nodeInfo.index,
        level: level,
      },
    });

    // Add edges for all visible children
    if (isOpened) {
      children.forEach(childId => {
        finalEdges.push(createEdge(nodeId, childId));
      });
    }

    const position = { y: yPosition, yStart: yStartSpan, yEnd: yEndSpan };
    positionCache.set(nodeId, position);
    return position;
  }

  level1.forEach(l1Node => {
    calculateNodePosition(l1Node.id, 0);
    currentY += GROUP_VERTICAL_SPACING;
  });
  
  return { nodes: finalNodes, edges: finalEdges };
};

  const { user } = useUserData();

  const [nodes, setNodes] = React.useState<any>([]);
  const [edges, setEdges] = React.useState<any>([]);

  useEffect(() => {
     if (checked && checked.length && opened && opened.length&& selectedAppAllPermissions ) {
     const { nodes: generatedNodes, edges: generatedEdges } =
     generateTreeNodesAndEdges( 
     selectedAppAllPermissions[permissionType],
     permissionType,
     opened 
     );
     setNodes(generatedNodes);
     setEdges(generatedEdges);
     }
     }, [opened, checked, selectedAppAllPermissions, permissionType]);

  useEffect(() => {
    if (
      selectedAppAllPermissions &&
      selectedAppAllPermissions[permissionType]
    ) {
      const allNodes = selectedAppAllPermissions[permissionType];
      const level1 = Object.keys(allNodes);
      let level2: string[] = [];
      let inIndex = level1.length;
      level1.forEach((key, index) => {
        const arr = Object.keys(allNodes[key]);
        const newArr: string[] = [];
        arr.forEach((item) => {
          const val = `${index}_${key}>${inIndex}_${item}`;
          newArr.push(val);
          inIndex++;
        });
        level2 = [...level2, ...newArr];
      });

      const level3: string[] = [];
      inIndex = level1.length;
      let inIndex2 = level1.length + level2.length - 1;
      level1.forEach((key, index) => {
        const arr = Object.keys(allNodes[key]);

        arr.forEach((item) => {
          allNodes[key][item].forEach((ele: any) => {
            if (permissionType === "location_permission") {
              level3.push(
                `${index}_${key}>${inIndex}_${item}>${inIndex2}_${
                  ele[permissionType.split("_")[0] + "_heirarchy_3"]
                }`
              );
            } else {
              level3.push(
                `${index}_${key}>${inIndex}_${item}>${inIndex2}_${
                  ele[permissionType.split("_")[0] + "_hierarchy_3"]
                }`
              );
            }
            inIndex2++;
          });
          inIndex++;
        });
      });

      setOpened(Array(level1.length + level2.length + level3.length).fill(0));
      setChecked(Array(level1.length + level2.length + level3.length).fill(0));
    }
  }, [selectedAppAllPermissions, permissionType]);

  return (
    <NodeDataContext.Provider
      value={{
        nodes,
        edges,
        opened,
        setOpened,
        checked,
        setChecked,
        selectedPermissions,
        selectedApplication,
        permissionType,
        setSelectedPermissions,
      }}
    >
      <div
        style={{
          width: "100%",
          height: "94%",
          margin: "8px auto 0 auto",
          border: "1.5px dashed #cecece",
          borderRadius: "10px",
          padding: "8px",
        }}
      >
        <ViewToggle
          allApplications={["location_permission", "product_permission"]}
          selectedApplication={permissionType}
          setSelectedApplication={setPermissionType}
        />
        <ChartWrapper
          style={{
            position: "relative",
            width: "100%",
            height: "90%",
            borderRadius: "10px",
          }}
        >
          <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} />
        </ChartWrapper>
      </div>
    </NodeDataContext.Provider>
  );
}
