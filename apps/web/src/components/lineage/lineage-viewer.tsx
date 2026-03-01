import { LineageToolbar } from '@/components/lineage/lineage-toolbar'
import { Button } from '@/components/ui/button'
import { useDatasets } from '@/hooks/use-catalog'
import { useLineageViewport } from '@/hooks/use-lineage-viewport'
import type {
  LineageEdge,
  LineageEdgeData,
  LineageGraph,
  LineageNode,
  LineageNodeData,
} from '@pseudolab/shared-types'
import {
  Background,
  type Connection,
  Controls,
  type Edge,
  type Node,
  ReactFlow,
  type ReactFlowInstance,
  type Viewport,
  addEdge,
  useEdgesState,
  useNodesState,
} from '@xyflow/react'
import { useEffect, useMemo, useRef, useState } from 'react'

type FlowNode = Node<LineageNodeData, 'dataset'>
type FlowEdge = Edge<LineageEdgeData>

type LineageViewerProps = {
  datasetId: string
  graph: LineageGraph
  isSaving: boolean
  onSave: (graph: LineageGraph) => Promise<void>
  onNavigateDataset: (datasetId: string) => void
}

function toFlowNodes(nodes: LineageNode[]): FlowNode[] {
  return nodes.map((node) => ({
    id: node.id,
    type: 'dataset',
    position: node.position,
    data: node.data,
  }))
}

function toFlowEdges(edges: LineageEdge[]): FlowEdge[] {
  return edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    data: edge.data,
    label: edge.label ?? edge.data?.step,
  }))
}

function toLineageGraph(nodes: FlowNode[], edges: FlowEdge[]): LineageGraph {
  return {
    version: 1,
    nodes: nodes.map((node) => ({
      id: node.id,
      type: 'dataset',
      position: node.position,
      data: node.data,
    })),
    edges: edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      data: edge.data,
      label: edge.label ? String(edge.label) : edge.data?.step,
    })),
  }
}

export function LineageViewer({
  datasetId,
  graph,
  isSaving,
  onSave,
  onNavigateDataset,
}: LineageViewerProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNode>(toFlowNodes(graph.nodes))
  const [edges, setEdges, onEdgesChange] = useEdgesState<FlowEdge>(toFlowEdges(graph.edges))
  const [isEditMode, setIsEditMode] = useState(false)
  const [selectedDatasetId, setSelectedDatasetId] = useState('')
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null)
  const snapshotRef = useRef<{ nodes: FlowNode[]; edges: FlowEdge[] } | null>(null)
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance<
    FlowNode,
    FlowEdge
  > | null>(null)
  const { viewport, saveViewport } = useLineageViewport(datasetId)
  const datasetsQuery = useDatasets({ page: 1, pageSize: 200 })

  useEffect(() => {
    if (!isEditMode) {
      setNodes(toFlowNodes(graph.nodes))
      setEdges(toFlowEdges(graph.edges))
    }
  }, [graph, isEditMode, setEdges, setNodes])

  useEffect(() => {
    if (!reactFlowInstance) {
      return
    }
    reactFlowInstance.setViewport(viewport)
  }, [reactFlowInstance, viewport])

  const displayedNodes = useMemo(
    () =>
      nodes.map((node) => ({
        ...node,
        style:
          node.id === focusedNodeId
            ? {
                border: '2px solid var(--primary)',
                borderRadius: 10,
                padding: 2,
                background: 'white',
              }
            : undefined,
      })),
    [focusedNodeId, nodes],
  )

  const handleToggleEdit = () => {
    snapshotRef.current = { nodes: structuredClone(nodes), edges: structuredClone(edges) }
    setIsEditMode(true)
  }

  const handleCancel = () => {
    if (snapshotRef.current) {
      setNodes(snapshotRef.current.nodes)
      setEdges(snapshotRef.current.edges)
    }
    setIsEditMode(false)
    setFocusedNodeId(null)
  }

  const handleSave = async () => {
    await onSave(toLineageGraph(nodes, edges))
    snapshotRef.current = null
    setIsEditMode(false)
  }

  const handleFitView = () => {
    reactFlowInstance?.fitView({ duration: 250, padding: 0.24 })
  }

  const handleConnect = (connection: Connection) => {
    if (!isEditMode) {
      return
    }

    setEdges((current) =>
      addEdge(
        {
          ...connection,
          id: crypto.randomUUID(),
        },
        current,
      ),
    )
  }

  const handleAddNode = () => {
    if (!selectedDatasetId) {
      return
    }

    const targetDataset = datasetsQuery.data?.data.find(
      (dataset) => dataset.id === selectedDatasetId,
    )
    if (!targetDataset) {
      return
    }

    const existing = nodes.find((node) => node.id === targetDataset.id)
    if (existing) {
      setFocusedNodeId(existing.id)
      reactFlowInstance?.fitView({ nodes: [existing], duration: 250, padding: 0.5 })
      return
    }

    const newNode: FlowNode = {
      id: targetDataset.id,
      type: 'dataset',
      position: { x: 80 + nodes.length * 70, y: 80 + nodes.length * 25 },
      data: {
        datasetId: targetDataset.id,
        label: targetDataset.name,
        domain: targetDataset.domain,
      },
    }

    setNodes((current) => [...current, newNode])
    setFocusedNodeId(targetDataset.id)
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <LineageToolbar
          isEditMode={isEditMode}
          isSaving={isSaving}
          onToggleEdit={handleToggleEdit}
          onSave={() => {
            void handleSave()
          }}
          onCancel={handleCancel}
          onFitView={handleFitView}
        />
        {isEditMode && (
          <div className="flex items-center gap-2">
            <select
              className="h-8 rounded-md border border-[var(--border)] bg-white px-2 text-xs"
              value={selectedDatasetId}
              onChange={(event) => setSelectedDatasetId(event.target.value)}
            >
              <option value="">Select dataset</option>
              {(datasetsQuery.data?.data ?? []).map((dataset) => (
                <option key={dataset.id} value={dataset.id}>
                  {dataset.name}
                </option>
              ))}
            </select>
            <Button size="sm" variant="outline" onClick={handleAddNode}>
              Add node
            </Button>
          </div>
        )}
      </div>

      <div className="min-h-[60vh] w-full min-w-0 rounded-md border border-[var(--border)]">
        <ReactFlow<FlowNode, FlowEdge>
          nodes={displayedNodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={handleConnect}
          onInit={setReactFlowInstance}
          onMoveEnd={(_event, nextViewport: Viewport) => saveViewport(nextViewport)}
          onNodeClick={(_event, node) => {
            const nodeDatasetId = node.data.datasetId
            if (!nodeDatasetId) {
              return
            }

            if (nodeDatasetId === datasetId) {
              setFocusedNodeId(node.id)
              reactFlowInstance?.fitView({ nodes: [node], duration: 250, padding: 0.55 })
              return
            }

            onNavigateDataset(nodeDatasetId)
          }}
          nodesConnectable={isEditMode}
          nodesDraggable={isEditMode}
          elementsSelectable
          fitView
          deleteKeyCode={['Backspace', 'Delete']}
        >
          <Background />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>

      <p className="text-xs text-[var(--muted-foreground)]">
        {isEditMode
          ? 'Edit mode: drag nodes, connect edges, and press Delete to remove selected items.'
          : 'Click a node to navigate. Clicking current dataset recenters and highlights it.'}
      </p>
    </div>
  )
}
