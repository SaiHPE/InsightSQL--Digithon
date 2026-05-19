import { useEffect, useRef } from 'react';
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3-force';
import { select } from 'd3-selection';

// Map resource types to HPE Categorical Palette
const TYPE_COLORS = { sap_sid: '#7630EA', host: '#00739D', storage_array: '#01A982', volume: '#00C8FF', service: '#FF8300' };
const TYPE_SIZES = { sap_sid: 22, host: 16, storage_array: 18, volume: 12, service: 10 };
const STATUS_STROKE = { ok: null, warning: '#FFBC44', critical: '#FC6161' };

export default function TopologyGraph({ topology }) {
  const svgRef = useRef(null);
  const simRef = useRef(null);

  useEffect(() => {
    if (!topology.nodes.length || !svgRef.current) return;

    const el = svgRef.current;
    const width = 320;
    const height = 360;
    const svg = select(el);
    svg.selectAll('*').remove();

    const nodes = topology.nodes.map(n => ({ ...n, id: n.resource_id }));
    const links = topology.edges.map(e => ({ source: e.src_resource_id, target: e.dst_resource_id, type: e.edge_type }));

    const sim = forceSimulation(nodes)
      .force('link', forceLink(links).id(d => d.id).distance(65))
      .force('charge', forceManyBody().strength(-180))
      .force('center', forceCenter(width / 2, height / 2))
      .force('collide', forceCollide(26));

    simRef.current = sim;

    const link = svg.append('g')
      .selectAll('line').data(links).join('line')
      .attr('stroke', 'var(--border-default)')
      .attr('stroke-width', 1.5);

    const node = svg.append('g')
      .selectAll('g').data(nodes).join('g');

    // Add backdrop for label readability (HPE Accessibility)
    node.append('rect')
      .attr('x', -30)
      .attr('y', d => (TYPE_SIZES[d.resource_type] || 12) + 4)
      .attr('width', 60)
      .attr('height', 14)
      .attr('fill', 'var(--bg-back)')
      .attr('fill-opacity', 0.6)
      .attr('rx', 2);

    node.append('circle')
      .attr('r', d => TYPE_SIZES[d.resource_type] || 12)
      .attr('fill', d => TYPE_COLORS[d.resource_type] || 'var(--status-unknown)')
      .attr('fill-opacity', 0.2)
      .attr('stroke', d => STATUS_STROKE[d.status] || TYPE_COLORS[d.resource_type] || 'var(--status-unknown)')
      .attr('stroke-width', d => d.status === 'critical' ? 3 : 2);

    node.append('text')
      .text(d => { const n = d.display_name || d.resource_id; return n.length > 14 ? n.slice(0, 12) + '…' : n; })
      .attr('text-anchor', 'middle')
      .attr('dy', d => (TYPE_SIZES[d.resource_type] || 12) + 14)
      .attr('fill', 'var(--text-strong)')
      .attr('font-size', '10px')
      .attr('font-weight', '500')
      .attr('font-family', 'HPE Graphik');

    node.append('title')
      .text(d => `${d.display_name}\n${d.vendor} ${d.product}\nStatus: ${d.status}`);

    sim.on('tick', () => {
      link.attr('x1', d => d.source.x).attr('y1', d => d.source.y).attr('x2', d => d.target.x).attr('y2', d => d.target.y);
      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    return () => sim.stop();
  }, [topology.nodes, topology.edges]);

  useEffect(() => {
    if (!svgRef.current) return;
    const svg = select(svgRef.current);
    for (const n of topology.nodes) {
      svg.selectAll('circle')
        .filter(d => d && d.resource_id === n.resource_id)
        .attr('stroke', STATUS_STROKE[n.status] || TYPE_COLORS[n.resource_type] || 'var(--status-unknown)')
        .attr('stroke-width', n.status === 'critical' ? 3 : 2)
        .attr('fill-opacity', n.status === 'critical' ? 0.4 : 0.2);
    }
  }, [topology.nodes]);

  return (
    <div className="section">
      <div className="section-head">
        <span className="section-title">Infrastructure Topology</span>
      </div>
      <div style={{ padding: 'var(--space-xxs)', display: 'flex', justifyContent: 'center' }}>
        <svg ref={svgRef} className="topo-svg" viewBox="0 0 320 360" style={{ height: 340, maxWidth: '100%' }} />
      </div>
    </div>
  );
}
