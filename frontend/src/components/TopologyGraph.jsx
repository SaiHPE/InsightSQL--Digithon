import { useEffect, useRef } from 'react';
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3-force';
import { select } from 'd3-selection';

const TYPE_COLORS = { sap_sid: '#7764FC', host: '#0070F8', storage_array: '#01A982', volume: '#62E5F6', service: '#FFBC44' };
const TYPE_SIZES = { sap_sid: 20, host: 15, storage_array: 17, volume: 11, service: 9 };
const STATUS_STROKE = { ok: null, warning: '#FFBC44', critical: '#FC6161' };

export default function TopologyGraph({ topology }) {
  const svgRef = useRef(null);
  const simRef = useRef(null);

  useEffect(() => {
    if (!topology.nodes.length || !svgRef.current) return;

    const el = svgRef.current;
    const width = 280;
    const height = 360;
    const svg = select(el);
    svg.selectAll('*').remove();

    const nodes = topology.nodes.map(n => ({ ...n, id: n.resource_id }));
    const links = topology.edges.map(e => ({ source: e.src_resource_id, target: e.dst_resource_id, type: e.edge_type }));

    const sim = forceSimulation(nodes)
      .force('link', forceLink(links).id(d => d.id).distance(55))
      .force('charge', forceManyBody().strength(-140))
      .force('center', forceCenter(width / 2, height / 2))
      .force('collide', forceCollide(22));

    simRef.current = sim;

    const link = svg.append('g')
      .selectAll('line').data(links).join('line')
      .attr('stroke', 'rgba(255,255,255,0.06)')
      .attr('stroke-width', 1);

    const node = svg.append('g')
      .selectAll('g').data(nodes).join('g');

    node.append('circle')
      .attr('r', d => TYPE_SIZES[d.resource_type] || 11)
      .attr('fill', d => TYPE_COLORS[d.resource_type] || '#535C66')
      .attr('fill-opacity', 0.15)
      .attr('stroke', d => STATUS_STROKE[d.status] || TYPE_COLORS[d.resource_type] || '#535C66')
      .attr('stroke-width', d => d.status === 'critical' ? 2.5 : 1.5);

    node.append('text')
      .text(d => { const n = d.display_name || d.resource_id; return n.length > 14 ? n.slice(0, 14) + '…' : n; })
      .attr('text-anchor', 'middle')
      .attr('dy', d => (TYPE_SIZES[d.resource_type] || 11) + 13)
      .attr('fill', '#7d8a92')
      .attr('font-size', '8.5px')
      .attr('font-family', 'HPE Graphik');

    node.append('title')
      .text(d => `${d.display_name}\n${d.vendor} ${d.product}\nStatus: ${d.status}`);

    sim.on('tick', () => {
      link.attr('x1', d => d.source.x).attr('y1', d => d.source.y).attr('x2', d => d.target.x).attr('y2', d => d.target.y);
      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    return () => sim.stop();
  }, [topology.nodes.length, topology.edges.length]);

  // Live status updates
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = select(svgRef.current);
    for (const n of topology.nodes) {
      svg.selectAll('circle')
        .filter(d => d && d.resource_id === n.resource_id)
        .attr('stroke', STATUS_STROKE[n.status] || TYPE_COLORS[n.resource_type] || '#535C66')
        .attr('stroke-width', n.status === 'critical' ? 2.5 : 1.5)
        .attr('fill-opacity', n.status === 'critical' ? 0.3 : 0.15);
    }
  }, [topology.nodes]);

  return (
    <div className="section">
      <div className="section-head">
        <span className="section-title">Infrastructure Topology</span>
      </div>
      <div style={{ padding: 4 }}>
        <svg ref={svgRef} className="topo-svg" viewBox="0 0 280 360" style={{ height: 340 }} />
      </div>
    </div>
  );
}
