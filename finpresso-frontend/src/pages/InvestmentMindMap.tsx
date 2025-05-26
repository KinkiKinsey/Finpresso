import React, { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import type { HierarchyPointNode, HierarchyPointLink } from "d3";
import { useParams ,useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Loader2, AlertTriangle, ZoomIn, ZoomOut } from "lucide-react";
import { Button } from "@mui/material";
import SchemaIcon from "@mui/icons-material/Schema";

// ── Types ───────────────────────────────────────────
export interface MindmapNode {
  id: string;
  label: string;
  group?: "Macro" | "Company" | "Price" | "Strategy" | "Catalyst" | "Conclusion";
  parent?: string;
  extra?: any;
}
export interface MindmapEdge {
  source: string;
  target: string;
  relation: "supports" | "contradicts" | "drives" | "monitors" | "hedges";
}
export interface MindmapData {
  nodes: MindmapNode[];
  edges: MindmapEdge[];
}
type HierNode = MindmapNode & { children?: HierNode[] };

// ── Color Palettes ──────────────────────────────────
const GROUP_COLORS: Record<string, string> = {
  Macro: "#3b82f6",
  Company: "#16a34a",
  Price: "#f59e0b",
  Strategy: "#8b5cf6",
  Catalyst: "#ef4444",
  Conclusion: "#0ea5e9",
};
const EDGE_COLORS: Record<string, string> = {
  supports: "#10b981",
  contradicts: "#ef4444",
  drives: "#3b82f6",
  monitors: "#f59e0b",
  hedges: "#8b5cf6",
};

// ── CrossLink Type ─────────────────────────────────
type CrossLink = {
  source: HierarchyPointNode<HierNode>;
  target: HierarchyPointNode<HierNode>;
  relation: MindmapEdge["relation"];
};

// ── D3Mindmap Component ────────────────────────────
const D3Mindmap: React.FC<{ data: MindmapData }> = ({ data }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [dim, setDim] = useState({ width: 1200, height: 800 });
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [hovered, setHovered] = useState<string | null>(null);

  // Resize listener
  useEffect(() => {
    const onResize = () => {
      const p = svgRef.current?.parentElement;
      if (p) {
        const { width, height } = p.getBoundingClientRect();
        setDim({ width, height });
      }
    };
    onResize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  // Draw/update
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const { width, height } = dim;
    const margin = { top: 40, right: 100, bottom: 40, left: 100 };
    const innerW = width - margin.left - margin.right;
    const innerH = height - margin.top - margin.bottom;

    // ─ Defs: grid, glow, gradients
    const defs = svg.append("defs");
    defs
      .append("pattern")
      .attr("id", "grid")
      .attr("width", 40)
      .attr("height", 40)
      .attr("patternUnits", "userSpaceOnUse")
      .append("path")
      .attr("d", "M40 0 L0 0 0 40")
      .attr("fill", "none")
      .attr("stroke", "#1e293b")
      .attr("stroke-width", 0.5);

    const glow = defs.append("filter").attr("id", "glow");
    glow.append("feGaussianBlur").attr("stdDeviation", 4).attr("result", "coloredBlur");
    const mg = glow.append("feMerge");
    mg.append("feMergeNode").attr("in", "coloredBlur");
    mg.append("feMergeNode").attr("in", "SourceGraphic");

    Object.entries(EDGE_COLORS).forEach(([k, c]) => {
      const lg = defs
        .append("linearGradient")
        .attr("id", `grad-${k}`)
        .attr("gradientUnits", "userSpaceOnUse");
      lg.append("stop").attr("offset", "0%").attr("stop-color", "#fff");
      lg.append("stop").attr("offset", "100%").attr("stop-color", c);
    });

    // ─ Background grid
    svg
      .append("rect")
      .attr("x", margin.left)
      .attr("y", margin.top)
      .attr("width", innerW)
      .attr("height", innerH)
      .attr("fill", "url(#grid)");

    // ─ Main group + zoom
    const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on("zoom", (e) => g.attr("transform", e.transform));
    svg.call(zoom as any);

    // ─ Build hierarchy (with expand/collapse)
    const build = (n: MindmapNode): HierNode => {
      const kids = data.nodes.filter((c) => c.parent === n.id);
      return { ...n, children: kids.length && expanded.has(n.id) ? kids.map(build) : [] };
    };
    const rootHier = d3.hierarchy<HierNode>({
      id: "__root__",
      label: "__root__",
      children: data.nodes.filter((n) => !n.parent).map(build),
    });
    const rootPoint = (d3.tree<HierNode>().nodeSize([40, 220])(rootHier) as any) as HierarchyPointNode<
      HierNode
    >;
    rootPoint.each((d) => {
      const t = d.x;
      d.x = d.y;
      d.y = t;
    });

    // ─ id → node map
    const idToNode = new Map<string, HierarchyPointNode<HierNode>>();
    rootPoint.descendants().forEach((d) => {
      if (d.data.id !== "__root__") idToNode.set(d.data.id, d);
    });

    // ─ Tree links
    const treeLinks = (rootPoint.links() as HierarchyPointLink<HierNode>[]).filter(
      (l) => l.source.data.id !== "__root__"
    );
    g.append("g")
      .selectAll<SVGPathElement, HierarchyPointLink<HierNode>>("path.tree-link")
      .data(treeLinks, (d) => `${d.source.data.id}-${d.target.data.id}`)
      .enter()
      .append("path")
      .attr("class", "tree-link")
      .attr("d", d3.linkHorizontal<any, any>().x((d) => d.x).y((d) => d.y) as any)
      .attr("fill", "none")
      .attr("stroke", "#64748b")
      .attr("stroke-width", 1.5)
      .attr("stroke-opacity", 0.4);

    // ─ Cross-links from JSON edges
    const crossLinks: CrossLink[] = [];
    data.edges.forEach((e) => {
      const s = idToNode.get(e.source);
      const t = idToNode.get(e.target);
      if (s && t) crossLinks.push({ source: s, target: t, relation: e.relation });
    });
    g.append("g")
      .selectAll<SVGPathElement, CrossLink>("path.cross-link")
      .data(crossLinks)
      .enter()
      .append("path")
      .attr("class", "cross-link")
      .attr(
        "d",
        d3
          .linkHorizontal<{ x: number; y: number }, { x: number; y: number }>()
          .x((p) => p.x)
          .y((p) => p.y) as any
      )
      .attr("fill", "none")
      .attr("stroke-width", 2)
      .attr("stroke-opacity", 0.6)
      .attr("stroke", (d) => `url(#grad-${d.relation})`)
      .attr("marker-end", (d) => `url(#arrow-${d.relation})`);

    // ─ Cross-link labels
    g.append("g")
      .selectAll<SVGTextElement, CrossLink>("text.cross-label")
      .data(crossLinks)
      .enter()
      .append("text")
      .attr("class", "cross-label")
      .attr("x", (d) => (d.source.x + d.target.x) / 2)
      .attr("y", (d) => (d.source.y + d.target.y) / 2)
      .attr("dy", -4)
      .attr("text-anchor", "middle")
      .attr("font-size", 10)
      .attr("fill", "#f8fafc")
      .text((d) => d.relation);

    // ─ Arrow markers
    svg
      .append("defs")
      .selectAll<SVGMarkerElement, [string, string]>("marker")
      .data(Object.entries(EDGE_COLORS))
      .enter()
      .append("marker")
      .attr("id", ([k]) => `arrow-${k}`)
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 8)
      .attr("refY", 0)
      .attr("markerWidth", 8)
      .attr("markerHeight", 8)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", ([, c]) => c);

    // ─ Hover neighbors highlight
    const neighbors = new Set<string>();
    if (hovered) {
      treeLinks.forEach((l) => {
        if (l.source.data.id === hovered) neighbors.add(l.target.data.id);
        if (l.target.data.id === hovered) neighbors.add(l.source.data.id);
      });
      crossLinks.forEach((l) => {
        if (l.source.data.id === hovered) neighbors.add(l.target.data.id);
        if (l.target.data.id === hovered) neighbors.add(l.source.data.id);
      });
    }

    // ─ Nodes
    const nodesG = g
      .append("g")
      .selectAll<SVGGElement, HierarchyPointNode<HierNode>>("g.node")
      .data(rootPoint.descendants().filter((d) => d.data.id !== "__root__"))
      .enter()
      .append("g")
      .attr("class", "node")
      .attr("transform", (d) => `translate(${d.x},${d.y})`)
      .style("cursor", (d) => (data.nodes.some((c) => c.parent === d.data.id) ? "pointer" : "default"))
      .on("click", (_, d) => {
        const id = d.data.id;
        setExpanded((prev) => {
          const next = new Set(prev);
          next.has(id) ? next.delete(id) : next.add(id);
          return next;
        });
      })
      .on("mouseover", (_, d) => setHovered(d.data.id))
      .on("mouseout", () => setHovered(null))
      .style("opacity", (d) =>
        !hovered || d.data.id === hovered || neighbors.has(d.data.id) ? 1 : 0.2
      );

    nodesG
      .append("circle")
      .attr("r", (d) => {
        const hasKids = data.nodes.some((c) => c.parent === d.data.id);
        return hasKids ? (d.depth === 1 ? 14 : 12) : d.depth === 1 ? 12 : 8;
      })
      .attr("fill", (d) => GROUP_COLORS[d.data.group ?? ""]!)
      .attr("stroke", "#fff")
      .attr("stroke-width", 2)
      .style("filter", "url(#glow)");

    nodesG
      .filter((d) => data.nodes.some((c) => c.parent === d.data.id))
      .append("text")
      .attr("text-anchor", "middle")
      .attr("alignment-baseline", "middle")
      .attr("font-size", 12)
      .attr("fill", "#fff")
      .text((d) => (expanded.has(d.data.id) ? "−" : "+"));

    nodesG.each(function (d) {
      const r = data.nodes.some((c) => c.parent === d.data.id)
        ? d.depth === 1
          ? 14
          : 12
        : d.depth === 1
        ? 12
        : 8;
      const side = d.x < innerW / 2 ? -1 : 1;
      const parentY = (d.parent as HierarchyPointNode<HierNode>)?.y ?? d.y;
      const dy = d.y < parentY ? -(r + 12) : r + 12;
      const lblG = d3.select(this).append("g").attr("transform", `translate(${side * (r + 10)}, ${dy})`);
      const txt = lblG
        .append("text")
        .attr("x", 0)
        .attr("y", 0)
        .attr("text-anchor", side === -1 ? "end" : "start")
        .attr("alignment-baseline", "middle")
        .attr("font-size", d.depth === 1 ? 14 : 12)
        .attr("fill", "#fff")
        .text(d.data.label);
      // non-null assertion on getBBox
      const bb = (txt.node()! as SVGTextElement).getBBox();
      lblG.insert("rect", "text")
        .attr("x", bb.x - 4)
        .attr("y", bb.y - 2)
        .attr("width", bb.width + 8)
        .attr("height", bb.height + 4)
        .attr("rx", 4)
        .attr("ry", 4)
        .attr("fill", "rgba(15,23,42,0.9)")
        .attr("stroke", GROUP_COLORS[d.data.group ?? ""]!)
        .attr("stroke-width", 1.5);
    });

    // ─ Initial fit
    const bb = g.node()!.getBBox();
    const sc = 0.9 * Math.min(innerW / bb.width, innerH / bb.height);
    const init = d3.zoomIdentity
      .translate(width / 2 - (bb.x + bb.width / 2) * sc, height / 2 - (bb.y + bb.height / 2) * sc)
      .scale(sc);
    svg.call((zoom as any).transform, init);
  }, [data, dim, expanded, hovered]);

  // Zoom controls
  const zoomBy = (k: number) => {
    d3.select(svgRef.current!)
      .transition()
      .duration(600)
      .call((d3.zoom() as any).scaleBy, k);
  };

  return (
    <div className="relative w-full h-full bg-slate-950 rounded-2xl overflow-hidden">
      <svg ref={svgRef} width="100%" height="100%" />
      <div className="absolute top-4 right-4 flex flex-col gap-2">
        <button onClick={() => zoomBy(1.3)} className="p-2 bg-slate-800 rounded-lg hover:bg-slate-700">
          <ZoomIn className="w-5 h-5 text-white" />
        </button>
        <button onClick={() => zoomBy(0.7)} className="p-2 bg-slate-800 rounded-lg hover:bg-slate-700">
          <ZoomOut className="w-5 h-5 text-white" />
        </button>
      </div>
    </div>
  );
};

// ── Legend Component ───────────────────────────────
const Legend: React.FC = () => (
  <div className="flex flex-wrap gap-6 mb-4">
    {Object.entries(GROUP_COLORS).map(([grp, col]) => (
      <div key={grp} className="flex items-center gap-2">
        <span className="w-4 h-4 rounded-full" style={{ backgroundColor: col }} />
        <span className="text-white">{grp}</span>
      </div>
    ))}
  </div>
);



// ── Main Page ──────────────────────────────────────
const InvestmentMindMapPage: React.FC = () => {
  const navigate = useNavigate()
  const { job_id } = useParams<{ job_id?: string }>();
  const { data, isFetching, error, refetch } = useQuery(
    ["mindmap", job_id],
    async () => {
      if (!job_id) throw new Error("Missing id");
      const res = await fetch(`/api/v1/analysis/${job_id}/result`);
      if (res.status === 404) return null;
      if (!res.ok) throw new Error(`backend ${res.status}`);
      const j = await res.json();
      return (j as any).Investment_Mindmap_json as MindmapData;
    },
    { enabled: !!job_id, refetchInterval: (d) => (d ? false : 4000) }
  );

  if (isFetching && !data)
    return (
      <div className="h-screen flex items-center justify-center text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin" /> Loading…
      </div>
    );
  if (error)
    return (
      <div className="h-screen flex flex-col items-center justify-center gap-4">
        <AlertTriangle className="w-8 h-8 text-red-400" />
        {(error as Error).message}
+    <button onClick={() => refetch()} className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg">
        Retry
    </button>
      </div>
    );
  if (!data)
    return (
      <div className="h-screen flex items-center justify-center text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin" /> Waiting…
      </div>
    );

  return (
    <div className="fixed inset-0 bg-slate-950 p-6">
      <Legend />
        <Button
          variant="contained"
          startIcon={<SchemaIcon />}
          onClick={() => navigate(`/detail/${job_id}/macro`)}
          sx={{
            py: 0.5,
            px: 2.5,
            fontWeight: 700,
            background:
              "linear-gradient(135deg,#00e5ff 0%,#3b82f6 45%,#8b5cf6 100%)",
            color: "#fff",
            textTransform: "none",
            boxShadow: "0 0 14px rgba(0,229,255,.6)",
            transition: "all .2s",
            "&:hover": {
              transform: "translateY(-2px)",
              boxShadow: "0 0 22px rgba(0,229,255,.9)",
              background:
                "linear-gradient(135deg,#00e5ff 0%,#00b0ff 45%,#5e3bff 100%)",
            },
          }}
        >
          Detail Page
        </Button>
      <h1 className="text-3xl font-bold text-white mb-6">Investment Analysis Mind-map</h1>
      <div className="w-full h-[calc(100vh-200px)] rounded-2xl overflow-hidden shadow-2xl">
        <D3Mindmap data={data} />
      </div>
    </div>
  );
};

export default InvestmentMindMapPage;
