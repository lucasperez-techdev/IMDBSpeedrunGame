// MovieCardDeck.js

import React, { useState } from 'react';

function MovieCardDeck({ movies, startMovieId, endMovieId }) {
    const [currentIndex, setCurrentIndex] = useState(0);
    const totalMovies = movies.length;

    const handleNext = () => {
        setCurrentIndex((prevIndex) => (prevIndex + 1) % totalMovies);
    };

    const handlePrev = () => {
        setCurrentIndex((prevIndex) => (prevIndex - 1 + totalMovies) % totalMovies);
    };

    const handleCardClick = (movieId) => {
        const tmdbUrl = `https://www.themoviedb.org/movie/${movieId}`;
        window.open(tmdbUrl, '_blank');
    };

    if (movies.length === 0) return null;

    return (
        <div className="movie-card-deck">
            <button className="nav-arrow left-arrow" onClick={handlePrev}>
                &#10094;
            </button>
            <div className="movie-card-container">
                {movies.map((movie, index) => (
                    <div
                        key={movie.id}
                        className={`movie-card ${index === currentIndex ? 'active' : 'inactive'
                            } ${movie.id === startMovieId
                                ? 'start-movie'
                                : movie.id === endMovieId
                                    ? 'end-movie'
                                    : ''
                            }`}
                        style={{
                            backgroundImage: movie.poster_path
                                ? `url(https://image.tmdb.org/t/p/w500${movie.poster_path})`
                                : 'url(/default-poster.jpg)',
                        }}
                        onClick={() => handleCardClick(movie.id)}
                    >
                        <div className="movie-info">
                            <h3>{movie.title}</h3>
                            <p>{movie.year}</p>
                            {movie.connection && (
                                <p className="connection-info">
                                    Connected via: {movie.connection.type} -{' '}
                                    {movie.connection.name}
                                </p>
                            )}
                        </div>
                    </div>
                ))}
            </div>
            <button className="nav-arrow right-arrow" onClick={handleNext}>
                &#10095;
            </button>
        </div>
    );
}

export default MovieCardDeck;