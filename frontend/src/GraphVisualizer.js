import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

function GraphVisualizer({ fullPath, processedMovies }) {
    const svgRef = useRef();

    useEffect(() => {
        const svg = d3.select(svgRef.current);
        svg.selectAll('*').remove(); // Clear previous content

        const width = 800;
        const height = 600;

        // Create a map of movie IDs to movie data for quick lookup
        const movieMap = {};
        processedMovies.forEach((movie) => {
            movieMap[movie.id] = movie;
        });

        // Mark nodes and links that are part of the shortest path
        const pathNodeIds = fullPath.map((movie) => movie.id);
        const pathLinkIds = [];

        // Generate nodes with a flag indicating if they're part of the shortest path
        const nodes = processedMovies.map((movie) => ({
            id: movie.id,
            title: movie.title,
            isPathNode: pathNodeIds.includes(movie.id),
        }));

        // Generate all possible links between movies based on shared connections
        // For simplicity, we'll assume that each movie is connected to the next one in the processedMovies array
        // In a real scenario, you should generate links based on actual connections between movies

        // Create a set of processed movie IDs for quick lookup
        const processedMovieIds = new Set(processedMovies.map((movie) => movie.id));

        // Generate links
        const links = [];

        processedMovies.forEach((movie) => {
            const movieId = movie.id;

            // Couldn't figure out true connection logic - assume each movie is connected to the next one
            const nextMovieIndex = processedMovies.findIndex((m) => m.id === movieId) + 1;
            if (nextMovieIndex < processedMovies.length) {
                const targetMovie = processedMovies[nextMovieIndex];
                const link = {
                    source: movieId,
                    target: targetMovie.id,
                    isPathLink:
                        pathNodeIds.includes(movieId) && pathNodeIds.includes(targetMovie.id),
                };
                links.push(link);

                // If link is part of the path, add it to pathLinkIds
                if (link.isPathLink) {
                    pathLinkIds.push(`${movieId}-${targetMovie.id}`);
                }
            }
        });

        // Create a zoomable group
        const zoomGroup = svg.append('g');

        // Add zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 5]) // Set zoom scale limits
            .on('zoom', (event) => {
                zoomGroup.attr('transform', event.transform);
            });

        svg.call(zoom);

        // Simulation setup
        const simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links).id((d) => d.id).distance(150))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2));

        // Define arrow markers for links
        svg.append('defs').selectAll('marker')
            .data(['pathLink', 'normalLink'])
            .enter()
            .append('marker')
            .attr('id', (d) => d)
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 15)
            .attr('refY', 0)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('fill', (d) => (d === 'pathLink' ? '#ffeb3b' : '#999'));

        // Draw links
        const link = zoomGroup.append('g')
            .attr('stroke-width', 2)
            .selectAll('line')
            .data(links)
            .join('line')
            .attr('stroke', (d) => (d.isPathLink ? '#ffeb3b' : '#999'))
            .attr('marker-end', (d) => `url(#${d.isPathLink ? 'pathLink' : 'normalLink'})`);

        // Draw nodes
        const node = zoomGroup.append('g')
            .selectAll('circle')
            .data(nodes)
            .join('circle')
            .attr('r', 15)
            .attr('fill', (d) => (d.isPathNode ? '#ffeb3b' : '#69b3a2'))
            .attr('stroke', (d) => (d.isPathNode ? '#f57f17' : '#555'))
            .attr('stroke-width', 2)
            .call(
                d3.drag()
                    .on('start', (event, d) => {
                        if (!event.active) simulation.alphaTarget(0.3).restart();
                        d.fx = d.x;
                        d.fy = d.y;
                    })
                    .on('drag', (event, d) => {
                        d.fx = event.x;
                        d.fy = event.y;
                    })
                    .on('end', (event, d) => {
                        if (!event.active) simulation.alphaTarget(0);
                        d.fx = null;
                        d.fy = null;
                    })
            );

        // Add glow effect to path nodes
        node.filter((d) => d.isPathNode)
            .style('filter', 'url(#glow)');

        // Define glow filter
        const defs = svg.append('defs');

        const filter = defs.append('filter')
            .attr('id', 'glow');

        filter.append('feGaussianBlur')
            .attr('stdDeviation', '4')
            .attr('result', 'coloredBlur');

        const feMerge = filter.append('feMerge');
        feMerge.append('feMergeNode')
            .attr('in', 'coloredBlur');
        feMerge.append('feMergeNode')
            .attr('in', 'SourceGraphic');

        // Add titles to nodes
        const text = zoomGroup.append('g')
            .selectAll('text')
            .data(nodes)
            .join('text')
            .attr('dx', 20)
            .attr('dy', 4)
            .text((d) => d.title)
            .attr('font-size', '12px')
            .attr('fill', '#fff');

        // Update positions on each tick
        simulation.on('tick', () => {
            link
                .attr('x1', (d) => d.source.x)
                .attr('y1', (d) => d.source.y)
                .attr('x2', (d) => d.target.x)
                .attr('y2', (d) => d.target.y);

            node.attr('cx', (d) => d.x).attr('cy', (d) => d.y);

            text.attr('x', (d) => d.x).attr('y', (d) => d.y);
        });

        // Adjust view to fit all nodes
        const adjustZoomToFit = () => {
            const bounds = zoomGroup.node().getBBox();
            const fullWidth = bounds.width;
            const fullHeight = bounds.height;

            const midX = bounds.x + fullWidth / 2;
            const midY = bounds.y + fullHeight / 2;

            const scale = Math.min(width / fullWidth, height / fullHeight) * 0.9; // Add padding
            const transform = d3.zoomIdentity
                .translate(width / 2, height / 2)
                .scale(scale)
                .translate(-midX, -midY);

            svg.transition().duration(750).call(zoom.transform, transform);
        };

        // Run adjustment after simulation stabilizes
        setTimeout(adjustZoomToFit, 1000);

        // Cleanup on unmount
        return () => {
            simulation.stop();
        };
    }, [processedMovies, fullPath]);

    return <svg ref={svgRef} width={800} height={600} style={{ border: '1px solid black' }}></svg>;
}

export default GraphVisualizer;