import {
  prettyLineageEdgeLabel,
  truncateLineageEdgeLabel,
} from '@/components/lineage/lineage-edge-label'
import { LineageToolbar } from '@/components/lineage/lineage-toolbar'
import { shouldRestorePersistedViewport } from '@/components/lineage/viewport-guard'
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
  BaseEdge,
  type Connection,
  Controls,
  type Edge,
  EdgeLabelRenderer,
  type EdgeProps,
  MarkerType,
  type Node,
  Position,
  ReactFlow,
  type ReactFlowInstance,
  type Viewport,
  addEdge,
  getSmoothStepPath,
  useEdgesState,
  useNodesState,
} from '@xyflow/react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

type FlowNode = Node<LineageNodeData, 'dataset'>
type FlowEdgeData = LineageEdgeData & {
  fullLabel?: string
  hideLabel?: boolean
  labelOffsetX?: number
  labelOffsetY?: number
}
type FlowEdge = Edge<FlowEdgeData>

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
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
    style: {
      width: 220,
      borderRadius: 12,
      border: '1px solid var(--border)',
      background: 'var(--card)',
      color: 'var(--foreground)',
      fontSize: 14,
      fontWeight: 500,
      boxShadow: '0 1px 2px rgba(15, 23, 42, 0.06)',
      padding: '10px 12px',
      textAlign: 'center',
      lineHeight: 1.25,
    },
  }))
}

function spreadIndex(index: number): number {
  if (index === 0) {
    return 0
  }

  const magnitude = Math.ceil(index / 2)
  return index % 2 === 1 ? magnitude : -magnitude
}

function toFlowEdges(edges: LineageEdge[]): FlowEdge[] {
  const totalByPair = new Map<string, number>()
  const indexByPair = new Map<string, number>()
  const totalBySource = new Map<string, number>()
  const indexBySource = new Map<string, number>()
  const sourceLabelSeen = new Set<string>()

  for (const edge of edges) {
    const pair = `${edge.source}->${edge.target}`
    totalByPair.set(pair, (totalByPair.get(pair) ?? 0) + 1)
    totalBySource.set(edge.source, (totalBySource.get(edge.source) ?? 0) + 1)
  }

  return edges.map((edge) => {
    const rawLabel = edge.label ?? edge.data?.step ?? ''
    const pair = `${edge.source}->${edge.target}`
    const pairIndex = indexByPair.get(pair) ?? 0
    indexByPair.set(pair, pairIndex + 1)
    const total = totalByPair.get(pair) ?? 1
    const sourceIndex = indexBySource.get(edge.source) ?? 0
    indexBySource.set(edge.source, sourceIndex + 1)
    const sourceTotal = totalBySource.get(edge.source) ?? 1

    const parallelSpread = total > 1 ? spreadIndex(pairIndex) * 14 : 0
    const fanoutSpread = sourceTotal > 1 ? spreadIndex(sourceIndex) * 10 : 0

    const dedupeKey = `${edge.source}|${rawLabel}`
    const hideLabel = rawLabel.length > 0 && sourceLabelSeen.has(dedupeKey)
    sourceLabelSeen.add(dedupeKey)

    return {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: 'lineage',
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 16,
        height: 16,
        color: 'var(--muted-foreground)',
      },
      style: {
        stroke: 'var(--muted-foreground)',
        strokeWidth: 1.4,
      },
      data: {
        ...edge.data,
        fullLabel: rawLabel,
        hideLabel,
        labelOffsetX: 14,
        labelOffsetY: parallelSpread + fanoutSpread,
      },
      label: rawLabel,
    }
  })
}

function LineageEdgePath({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  label,
  data,
}: EdgeProps<FlowEdge>) {
  const [path, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    borderRadius: 18,
    offset: 24,
  })

  const fullLabel = data?.fullLabel ?? (typeof label === 'string' ? label : String(label ?? ''))
  const prettyLabel = prettyLineageEdgeLabel(fullLabel)
  const edgeLength = Math.hypot(targetX - sourceX, targetY - sourceY)
  const maxLabelChars = edgeLength < 250 ? 14 : edgeLength < 420 ? 22 : 30
  const labelText = truncateLineageEdgeLabel(prettyLabel, maxLabelChars)
  const directionalOffsetX = (targetX >= sourceX ? 1 : -1) * (data?.labelOffsetX ?? 14)

  const showLabel = !data?.hideLabel && labelText.length > 0 && edgeLength >= 140

  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        markerEnd={markerEnd}
        style={{
          stroke: 'var(--muted-foreground)',
          strokeWidth: 1.4,
        }}
      />
      {showLabel ? (
        <EdgeLabelRenderer>
          <div
            title={fullLabel}
            className="pointer-events-auto nodrag nopan absolute rounded-md border border-[var(--border)] bg-[var(--card)] px-2 py-0.5 text-[11px] font-medium text-[var(--muted-foreground)] shadow-sm"
            style={{
              transform: `translate(-50%, -50%) translate(${labelX + directionalOffsetX}px, ${labelY + (data?.labelOffsetY ?? 0)}px)`,
            }}
          >
            {labelText}
          </div>
        </EdgeLabelRenderer>
      ) : null}
    </>
  )
}

function autoLayoutNodes(nodes: FlowNode[], edges: FlowEdge[], centerNodeId: string): FlowNode[] {
  const incomingByTarget = new Map<string, string[]>()
  const outgoingBySource = new Map<string, string[]>()
  const levelByNode = new Map<string, number>()

  for (const node of nodes) {
    incomingByTarget.set(node.id, [])
    outgoingBySource.set(node.id, [])
  }

  for (const edge of edges) {
    const incoming = incomingByTarget.get(edge.target)
    if (incoming) {
      incoming.push(edge.source)
    }
    const outgoing = outgoingBySource.get(edge.source)
    if (outgoing) {
      outgoing.push(edge.target)
    }
  }

  levelByNode.set(centerNodeId, 0)

  const upstreamQueue = [centerNodeId]
  while (upstreamQueue.length > 0) {
    const currentId = upstreamQueue.shift()
    if (!currentId) {
      continue
    }

    const currentLevel = levelByNode.get(currentId) ?? 0
    for (const upstreamId of incomingByTarget.get(currentId) ?? []) {
      if (!levelByNode.has(upstreamId)) {
        levelByNode.set(upstreamId, currentLevel - 1)
        upstreamQueue.push(upstreamId)
      }
    }
  }

  const downstreamQueue = [centerNodeId]
  while (downstreamQueue.length > 0) {
    const currentId = downstreamQueue.shift()
    if (!currentId) {
      continue
    }

    const currentLevel = levelByNode.get(currentId) ?? 0
    for (const downstreamId of outgoingBySource.get(currentId) ?? []) {
      const nextLevel = currentLevel + 1
      const knownLevel = levelByNode.get(downstreamId)
      if (knownLevel === undefined || nextLevel > knownLevel) {
        levelByNode.set(downstreamId, nextLevel)
        downstreamQueue.push(downstreamId)
      }
    }
  }

  const groupedByLevel = new Map<number, FlowNode[]>()
  for (const node of nodes) {
    const level = levelByNode.get(node.id) ?? 0
    const group = groupedByLevel.get(level)
    if (group) {
      group.push(node)
    } else {
      groupedByLevel.set(level, [node])
    }
  }

  const nextNodes: FlowNode[] = []
  const sortedLevels = [...groupedByLevel.keys()].sort((left, right) => left - right)
  for (const level of sortedLevels) {
    const group = groupedByLevel.get(level)
    if (!group) {
      continue
    }

    const sortedGroup = [...group].sort((left, right) => left.id.localeCompare(right.id))
    const centerOffset = (sortedGroup.length - 1) / 2
    for (let index = 0; index < sortedGroup.length; index += 1) {
      const node = sortedGroup[index]
      if (!node) {
        continue
      }
      nextNodes.push({
        ...node,
        position: {
          x: level * 380,
          y: (index - centerOffset) * 180,
        },
      })
    }
  }

  return nextNodes
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
      data: edge.data?.step ? { step: edge.data.step } : undefined,
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
  const initialEdges = toFlowEdges(graph.edges)
  const initialNodes = autoLayoutNodes(toFlowNodes(graph.nodes), initialEdges, datasetId)
  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNode>(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState<FlowEdge>(initialEdges)
  const [isEditMode, setIsEditMode] = useState(false)
  const [selectedDatasetId, setSelectedDatasetId] = useState('')
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null)
  const snapshotRef = useRef<{ nodes: FlowNode[]; edges: FlowEdge[] } | null>(null)
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance<
    FlowNode,
    FlowEdge
  > | null>(null)
  const edgeTypes = useMemo(
    () => ({
      lineage: LineageEdgePath,
    }),
    [],
  )
  const containerRef = useRef<HTMLDivElement | null>(null)
  const lastCameraInitKeyRef = useRef<string | null>(null)
  const isProgrammaticMoveRef = useRef(false)
  const { viewport, saveViewport } = useLineageViewport(datasetId)
  const datasetsQuery = useDatasets({ page: 1, pageSize: 100 })

  const runProgrammaticCameraMove = useCallback((action: () => void, holdMs = 360) => {
    isProgrammaticMoveRef.current = true
    action()
    window.setTimeout(() => {
      isProgrammaticMoveRef.current = false
    }, holdMs)
  }, [])

  useEffect(() => {
    if (!isEditMode) {
      const nextEdges = toFlowEdges(graph.edges)
      const nextNodes = autoLayoutNodes(toFlowNodes(graph.nodes), nextEdges, datasetId)
      setNodes(nextNodes)
      setEdges(nextEdges)
    }
  }, [datasetId, graph, isEditMode, setEdges, setNodes])

  useEffect(() => {
    if (!reactFlowInstance) {
      return
    }

    const nodeSignature = nodes
      .map((node) => node.id)
      .sort()
      .join(',')
    const edgeSignature = edges
      .map((edge) => edge.id)
      .sort()
      .join(',')
    const cameraInitKey = `${datasetId}|${nodeSignature}|${edgeSignature}`

    if (lastCameraInitKeyRef.current === cameraInitKey) {
      return
    }

    const applyInitialCamera = () => {
      const container = containerRef.current
      if (!container) {
        return
      }

      const width = container.clientWidth
      const height = container.clientHeight
      if (width <= 0 || height <= 0) {
        window.requestAnimationFrame(applyInitialCamera)
        return
      }

      const lineageNodes = toLineageGraph(nodes, edges).nodes
      const canRestore = shouldRestorePersistedViewport(lineageNodes, viewport, width, height)

      if (canRestore) {
        runProgrammaticCameraMove(() => {
          reactFlowInstance.setViewport(viewport)
        }, 120)
      } else {
        runProgrammaticCameraMove(() => {
          reactFlowInstance.fitView({ duration: 240, padding: 0.24 })
        })
      }

      lastCameraInitKeyRef.current = cameraInitKey
    }

    applyInitialCamera()
  }, [datasetId, edges, nodes, reactFlowInstance, runProgrammaticCameraMove, viewport])

  const displayedNodes = useMemo(
    () =>
      nodes.map((node) => ({
        ...node,
        style:
          node.id === focusedNodeId
            ? {
                ...(node.style ?? {}),
                border: '2px solid var(--primary)',
                borderRadius: 10,
                padding: 2,
                background: 'white',
              }
            : node.style,
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
    runProgrammaticCameraMove(() => {
      reactFlowInstance?.fitView({ duration: 250, padding: 0.24 })
    })
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
      runProgrammaticCameraMove(() => {
        reactFlowInstance?.fitView({ nodes: [existing], duration: 250, padding: 0.5 })
      })
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

      <div
        ref={containerRef}
        className="h-[60vh] min-h-[60vh] w-full min-w-0 rounded-md border border-[var(--border)]"
      >
        <ReactFlow<FlowNode, FlowEdge>
          nodes={displayedNodes}
          edges={edges}
          edgeTypes={edgeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={handleConnect}
          onInit={setReactFlowInstance}
          onMoveEnd={(_event, nextViewport: Viewport) => {
            if (isProgrammaticMoveRef.current) {
              return
            }
            saveViewport(nextViewport)
          }}
          onNodeClick={(_event, node) => {
            const nodeDatasetId = node.data.datasetId
            if (!nodeDatasetId) {
              return
            }

            if (nodeDatasetId === datasetId) {
              setFocusedNodeId(node.id)
              runProgrammaticCameraMove(() => {
                reactFlowInstance?.fitView({ nodes: [node], duration: 250, padding: 0.55 })
              })
              return
            }

            onNavigateDataset(nodeDatasetId)
          }}
          nodesConnectable={isEditMode}
          nodesDraggable={isEditMode}
          elementsSelectable
          deleteKeyCode={['Backspace', 'Delete']}
        >
          <Background gap={24} size={1.2} color="rgba(107, 114, 128, 0.22)" />
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
