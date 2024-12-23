import React from 'react';
import GraphVisualizer from './GraphVisualizer';

function GraphPage({ navigateHome, fullPath, processedMovies }) {
    return (
        <div>
            <h1>Interactive Movie Graph</h1>
            <button onClick={navigateHome}>Back to Home</button>
            <GraphVisualizer fullPath={fullPath} processedMovies={processedMovies} />
        </div>
    );
}

export default GraphPage;