import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './styles.css';
import MovieCardDeck from './MovieCardDeck';
import GraphPage from './GraphPage';

function App() {
  const [currentPage, setCurrentPage] = useState('home');
  const [startMovie, setStartMovie] = useState('');
  const [endMovie, setEndMovie] = useState('');
  const [algorithm, setAlgorithm] = useState('dijkstra');
  const [startMovieSuggestions, setStartMovieSuggestions] = useState([]);
  const [endMovieSuggestions, setEndMovieSuggestions] = useState([]);
  const [path, setPath] = useState(null);
  const [fullPath, setFullPath] = useState([]);
  const [processedMovies, setProcessedMovies] = useState([]);
  const [topProcessedMovies, setTopProcessedMovies] = useState([]);
  const [startMovieId, setStartMovieId] = useState(null);
  const [endMovieId, setEndMovieId] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [executionTime, setExecutionTime] = useState(null);
  const [totalMovies, setTotalMovies] = useState(null);
  const [lastExecutedAlgorithm, setLastExecutedAlgorithm] = useState('');
  const [error, setError] = useState(null);

  // Fetch movie suggestions
  const fetchMovieSuggestions = async (query, setSuggestions) => {
    if (query.length > 2) {
      try {
        const res = await axios.get(`/search_movie?movie_name=${encodeURIComponent(query)}`);
        setSuggestions(res.data.results || []);
      } catch (err) {
        console.error('Error fetching movie suggestions:', err);
        setSuggestions([]);
      }
    } else {
      setSuggestions([]);
    }
  };

  const handleSelectSuggestion = (movie, setMovie, setSuggestions, setMovieId) => {
  setMovie(movie.title);
  setMovieId(movie.id); // Set the selected movie ID
  setSuggestions([]);
};

  // Search for the path using the selected algorithm
  const searchMovies = async () => {
    if (!startMovie || !endMovie) {
      setError('Please select both start and end movies.');
      return;
    }

    if (!startMovieId || !endMovieId) {
      setError('Invalid movie selections. Please try again.');
      return;
    }

    setIsProcessing(true);
    setProcessedMovies([]);
    setTopProcessedMovies([]);
    setPath(null);
    setError(null);

    try {
        // Fetch the path using movie IDs
        const pathResponse = await axios.get(
          `/find_path?start_id=${startMovieId}&end_id=${endMovieId}&algorithm=${algorithm}`
        );

        console.log('API Response:', pathResponse.data); // Debugging
        const algorithmPath = pathResponse.data.path;
        const timeTaken = pathResponse.data.execution_time;
        const totalMovies = pathResponse.data.total_movies;

        if (algorithmPath) {
          setPath(algorithmPath);
          setFullPath(algorithmPath.movies);
          fetchProcessedMoviesProgressively(); // Start fetching processed movies dynamically
          setExecutionTime(timeTaken);
          setTotalMovies(totalMovies);
          setLastExecutedAlgorithm(algorithm);
          fetchAllProcessedMovies();
        }
      } catch (err) {
        console.error('Error finding path:', err);
        setError('Unable to find a path between the selected movies.');
      } finally {
        setIsProcessing(false);
      }
  };

  // Fetch all processed movies progressively
  const fetchAllProcessedMovies = async () => {
    try {
      let offset = 0;
      const batchSize = 250;

      const fetchBatch = async () => {
        setIsLoadingMore(true); // Show loading indicator
        const res = await axios.get(`/get_processed_movies?offset=${offset}&limit=${batchSize}`);
        const newMovies = res.data.processed_movies;

        if (newMovies && newMovies.length > 0) {
          setProcessedMovies((prevMovies) => [...prevMovies, ...newMovies]);
          offset += newMovies.length;

          if (offset < res.data.total_count) {
            setTimeout(fetchBatch, 100); // Fetch next batch
          } else {
            setIsLoadingMore(false); // Stop loading once all movies are fetched
          }
        } else {
          setIsLoadingMore(false); // Stop loading if no more movies
        }
      };

      await fetchBatch();
    } catch (err) {
      console.error('Error fetching all processed movies:', err);
      setIsLoadingMore(false);
    }
  };

  // Fetch processed movies progressively
  const fetchProcessedMoviesProgressively = async () => {
    try {
      let offset = 0;
      const batchSize = 250;
      const maxMovies = 500;

      const fetchBatch = async () => {
        setIsLoadingMore(true);
        const res = await axios.get(`/get_processed_movies?offset=${offset}&limit=${batchSize}`);
        const newMovies = res.data.processed_movies;

        if (newMovies && newMovies.length > 0) {
          setProcessedMovies((prevMovies) => [...prevMovies, ...newMovies]);
          setTopProcessedMovies((prevMovies) => {
            const updatedMovies = [...prevMovies, ...newMovies];
            return updatedMovies.slice(0, 250); // Keep the top 250 movies
          });
          offset += newMovies.length;

          if (offset < Math.min(res.data.total_count, maxMovies)) {
            setTimeout(fetchBatch, 100); // Continue fetching next batch
          } else {
            setIsLoadingMore(false);
          }
        } else {
          setIsLoadingMore(false);
        }
      };

      await fetchBatch();
    } catch (err) {
      console.error('Error fetching processed movies:', err);
      setIsLoadingMore(false);
    }
  };

  // Render the home page
  const renderHomePage = () => (
    <div>
      <h1>🎬 Movie Path Finder</h1>

      {/* Start Movie Input */}
      <div className="autocomplete">
        <input
          type="text"
          value={startMovie}
          onChange={(e) => {
            setStartMovie(e.target.value);
            fetchMovieSuggestions(e.target.value, setStartMovieSuggestions);
          }}
          placeholder="Start Movie"
        />
        {startMovieSuggestions.length > 0 && (
          <ul className="suggestions">
            {startMovieSuggestions.map((movie) => (
              <li
                key={movie.id}
                onClick={() =>
                  handleSelectSuggestion(
                    movie,
                    setStartMovie,
                    setStartMovieSuggestions,
                    setStartMovieId
                  )
                }
              >
                <strong>{movie.title}</strong> ({movie.year}) - Directed by{' '}
                {movie.director || 'N/A'}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* End Movie Input */}
      <div className="autocomplete">
        <input
          type="text"
          value={endMovie}
          onChange={(e) => {
            setEndMovie(e.target.value);
            fetchMovieSuggestions(e.target.value, setEndMovieSuggestions);
          }}
          placeholder="End Movie"
        />
        {endMovieSuggestions.length > 0 && (
          <ul className="suggestions">
            {endMovieSuggestions.map((movie) => (
              <li
                key={movie.id}
                onClick={() =>
                  handleSelectSuggestion(
                    movie,
                    setEndMovie,
                    setEndMovieSuggestions,
                    setEndMovieId
                  )
                }
              >
                <strong>{movie.title}</strong> ({movie.year}) - Directed by{' '}
                {movie.director || 'N/A'}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Algorithm Selection */}
      <div className="algorithm-selection">
        <label>Select Algorithm:</label>
        <select value={algorithm} onChange={(e) => setAlgorithm(e.target.value)}>
          <option value="dijkstra">Bidirectional Dijkstra's Algorithm</option>
          <option value="bfs">Bidirectional BFS</option>
        </select>
      </div>

      {/* Search Button */}
      <button onClick={searchMovies} disabled={isProcessing}>
        {isProcessing ? 'Searching...' : 'Find Path'}
      </button>

      {/* Error Message */}
      {error && <p className="error">{error}</p>}

      {/* Loading Indicator */}
      {isProcessing ? (
        <div className="loading">
          <p>Processing movies... Please wait.</p>
        </div>
      ) : (
        executionTime && (
            <div className="loading">
              <p>
                {lastExecutedAlgorithm === 'dijkstra'
                    ? "Dijkstra's Execution Time"
                    : 'Bidirectional BFS Execution Time'}
                : {executionTime.toFixed(2)} seconds
                <p>Total Unique Movies Explored: {totalMovies}</p>
              </p>
            </div>
        )
      )}

      {/* Display Path */}
      {path && (
          <div className="path-result">
          <h2>
            {lastExecutedAlgorithm === 'dijkstra'
              ? "Dijkstra's"
              : 'Bidirectional BFS'}{' '}
            Path:
          </h2>
          <ul>
            {path.movies.map((movie, index) => (
              <li key={movie.id}>
                <p>
                  <strong>{movie.title}</strong> ({movie.year})
                </p>
                {index < path.connections.length && (
                  <p>
                    Connected via: <em>{path.connections[index]}</em>
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Processed Movies */}
      {topProcessedMovies.length > 0 && (
        <>
          <h2>Processed Movies:</h2>
          <MovieCardDeck movies={topProcessedMovies} startMovieId={startMovieId} endMovieId={endMovieId} />
          <button onClick={() => setCurrentPage('graph')}>View Interactive Graph</button>
        </>
      )}

      {isLoadingMore && <p>Loading more processed movies...</p>}
    </div>
  );

  return (
    <div className="container">
      {currentPage === 'home' ? (
        renderHomePage()
      ) : (
        <GraphPage
          navigateHome={() => setCurrentPage('home')}
          fullPath={fullPath}
          processedMovies={processedMovies}
        />
      )}
    </div>
  );
}

export default App;
