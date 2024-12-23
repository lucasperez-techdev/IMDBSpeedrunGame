# app.py

from flask import Flask, request, jsonify
import requests
import heapq
import logging
import time
from functools import lru_cache

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = '9f981a4c4394f62d994979dbb6ee0230'
BASE_URL = 'https://api.themoviedb.org/3/'

last_processed_movies = []

#API functions
def get_movie_credits(movie_id):
    url = f"{BASE_URL}movie/{movie_id}/credits"
    response = requests.get(url, params={'api_key': API_KEY})
    return response.json() if response.status_code == 200 else None

def get_person_movies(person_id):
    url = f"{BASE_URL}person/{person_id}/movie_credits"
    response = requests.get(url, params={'api_key': API_KEY})
    return response.json() if response.status_code == 200 else None

def get_movie_details(movie_id):
    url = f"{BASE_URL}movie/{movie_id}"
    response = requests.get(url, params={'api_key': API_KEY})
    return response.json() if response.status_code == 200 else None

def search_movie_list(title, limit=10):
    url = f"{BASE_URL}search/movie"
    response = requests.get(url, params={'api_key': API_KEY, 'query': title})
    results = response.json().get('results', [])
    movies = []
    for movie in results[:limit]:
        credits = get_movie_credits(movie['id'])
        if credits:
            director = next((crew['name'] for crew in credits.get('crew', []) if crew['job'] == 'Director'), 'N/A')
        else:
            director = 'N/A'
        movies.append({
            'id': movie['id'],
            'title': movie['title'],
            'year': movie['release_date'][:4] if movie.get('release_date') else 'N/A',
            'poster_path': movie.get('poster_path'),
            'director': director
        })
    return movies

def get_commonalities(current_movie_id, goal_movie_id):
    movie1 = get_movie_details(current_movie_id)
    movie2 = get_movie_details(goal_movie_id)

    credits1 = get_movie_credits(current_movie_id)
    credits2 = get_movie_credits(goal_movie_id)
    cast1 = set(person['id'] for person in credits1.get('cast', []))
    cast2 = set(person['id'] for person in credits2.get('cast', []))
    common_cast = len(cast1.intersection(cast2))

    crew1 = set(person['id'] for person in credits1.get('crew', []))
    crew2 = set(person['id'] for person in credits2.get('crew', []))
    common_crew = len(crew1.intersection(crew2))

    genres1 = set(genre['id'] for genre in movie1.get('genres', []))
    genres2 = set(genre['id'] for genre in movie2.get('genres', []))
    common_genres = len(genres1.intersection(genres2))

    return 3 * common_cast + 2 * common_crew + common_genres

# API calls
@lru_cache(maxsize=10000)
def get_movie_details_cached(movie_id):
    return get_movie_details(movie_id)

@lru_cache(maxsize=10000)
def get_movie_credits_cached(movie_id):
    return get_movie_credits(movie_id)

@lru_cache(maxsize=10000)
def get_person_movies_cached(person_id):
    return get_person_movies(person_id)

def heuristic(current_movie_id, goal_movie_id):
    credits_current = get_movie_credits_cached(current_movie_id)
    credits_goal = get_movie_credits_cached(goal_movie_id)

    if not credits_current or not credits_goal:
        return 10  # Arbitrary high value if credits are missing

    cast_current = set(person['id'] for person in credits_current.get('cast', []))
    cast_goal = set(person['id'] for person in credits_goal.get('cast', []))

    if cast_current.intersection(cast_goal):
        return 0  # Direct connection

    return 1  # Minimal heuristic value

def dijkstra_tmdb_by_id(start_movie_id, end_movie_id):
    global last_processed_movies
    start_time = time.perf_counter()

    # Fetch movie details directly using movie IDs
    start_movie = get_movie_details_cached(start_movie_id)
    end_movie = get_movie_details_cached(end_movie_id)

    if not start_movie or not end_movie:
        logger.error("Start or end movie not found.")
        return None, None

    logger.info(f"Starting Dijkstra's algorithm from '{start_movie['title']}' (ID: {start_movie_id}) to '{end_movie['title']}' (ID: {end_movie_id})")

    # Initialize forward search structures
    forward_heap = [(0, start_movie_id)]
    forward_visited = {start_movie_id: 0}
    forward_predecessors = {}

    # Initialize backward search structures
    backward_heap = [(0, end_movie_id)]
    backward_visited = {end_movie_id: 0}
    backward_predecessors = {}

    # Keeps track of all processed movies
    processed_movies = set([start_movie_id, end_movie_id])

    # Variable to store the meeting point
    meeting_movie = None
    minimal_total_cost = float('inf')

    while forward_heap and backward_heap:
        # Expand forward search
        if forward_heap:
            forward_cost, forward_current = heapq.heappop(forward_heap)
            forward_movie_details = get_movie_details_cached(forward_current)
            if not forward_movie_details:
                continue
            logger.info(f"Forward Exploring movie: '{forward_movie_details['title']}' (ID: {forward_current}) with cost {forward_cost}")

            credits = get_movie_credits_cached(forward_current)
            if credits:
                all_people = credits.get('cast', []) + credits.get('crew', [])
                sorted_people = sorted(all_people, key=lambda x: x.get('popularity', 0), reverse=True)[:50]

                for person in sorted_people:
                    person_id = int(person['id'])
                    person_name = person['name']
                    logger.info(f"Forward Exploring connections through: {person_name} (ID: {person_id})")

                    person_movies = get_person_movies_cached(person_id)
                    if not person_movies:
                        continue

                    all_movies = person_movies.get('cast', []) + person_movies.get('crew', [])
                    sorted_movies = sorted(all_movies, key=lambda x: (x.get('release_date', ''), x.get('popularity', 0)), reverse=True)[:50]

                    for movie in sorted_movies:
                        next_movie_id = int(movie['id'])
                        processed_movies.add(next_movie_id)  # Add to processed_movies set

                        if next_movie_id in forward_visited:
                            continue

                        tentative_forward_cost = forward_cost + 1
                        if next_movie_id not in forward_visited or tentative_forward_cost < forward_visited[next_movie_id]:
                            forward_visited[next_movie_id] = tentative_forward_cost
                            forward_predecessors[next_movie_id] = forward_current
                            logger.info(f"Forward Adding movie to heap: '{movie['title']}' (ID: {next_movie_id}) with cost {tentative_forward_cost}")
                            heapq.heappush(forward_heap, (tentative_forward_cost, next_movie_id))

                            # Checks if this node has been visited by backward search
                            if next_movie_id in backward_visited:
                                total_cost = tentative_forward_cost + backward_visited[next_movie_id]
                                if total_cost < minimal_total_cost:
                                    minimal_total_cost = total_cost
                                    meeting_movie = next_movie_id

        # Expand backward search
        if backward_heap:
            backward_cost, backward_current = heapq.heappop(backward_heap)
            backward_movie_details = get_movie_details_cached(backward_current)
            if not backward_movie_details:
                continue
            logger.info(f"Backward Exploring movie: '{backward_movie_details['title']}' (ID: {backward_current}) with cost {backward_cost}")

            credits = get_movie_credits_cached(backward_current)
            if credits:
                all_people = credits.get('cast', []) + credits.get('crew', [])
                sorted_people = sorted(all_people, key=lambda x: x.get('popularity', 0), reverse=True)[:50]

                for person in sorted_people:
                    person_id = int(person['id'])
                    person_name = person['name']
                    logger.info(f"Backward Exploring connections through: {person_name} (ID: {person_id})")

                    person_movies = get_person_movies_cached(person_id)
                    if not person_movies:
                        continue

                    all_movies = person_movies.get('cast', []) + person_movies.get('crew', [])
                    sorted_movies = sorted(all_movies, key=lambda x: (x.get('release_date', ''), x.get('popularity', 0)), reverse=True)[:50]

                    for movie in sorted_movies:
                        next_movie_id = int(movie['id'])
                        processed_movies.add(next_movie_id)  # Add to processed_movies set

                        if next_movie_id in backward_visited:
                            continue

                        tentative_backward_cost = backward_cost + 1
                        if next_movie_id not in backward_visited or tentative_backward_cost < backward_visited[next_movie_id]:
                            backward_visited[next_movie_id] = tentative_backward_cost
                            backward_predecessors[next_movie_id] = backward_current
                            logger.info(f"Backward Adding movie to heap: '{movie['title']}' (ID: {next_movie_id}) with cost {tentative_backward_cost}")
                            heapq.heappush(backward_heap, (tentative_backward_cost, next_movie_id))

                            # Checks if this node has been visited by forward search
                            if next_movie_id in forward_visited:
                                total_cost = tentative_backward_cost + forward_visited[next_movie_id]
                                if total_cost < minimal_total_cost:
                                    minimal_total_cost = total_cost
                                    meeting_movie = next_movie_id

        # Error condition
        if meeting_movie is not None:
            # Reconstruct the path
            path_forward = []
            current = meeting_movie
            while current != start_movie_id:
                path_forward.append(current)
                current = forward_predecessors.get(current)
                if current is None:
                    break
            path_forward.append(start_movie_id)
            path_forward.reverse()

            path_backward = []
            current = meeting_movie
            while current != end_movie_id:
                current = backward_predecessors.get(current)
                if current is None:
                    break
                path_backward.append(current)

            full_path = path_forward + path_backward

            end_time = time.perf_counter()
            logger.info(f"Dijkstra's execution time: {end_time - start_time:.2f} seconds")
            logger.info(f"Dijkstra's Path found! Total movies in path: {len(full_path)}")
            logger.info(f"Total unique movies explored: {len(processed_movies)}")

            execution_time = end_time - start_time
            total_movies = len(processed_movies)

            # Store the processed movies globally
            last_processed_movies = list(processed_movies)

            return full_path, list(processed_movies), execution_time, total_movies

    logger.info("No path found")
    logger.info(f"Total unique movies explored: {len(processed_movies)}")
    last_processed_movies = list(processed_movies)
    execution_time = time.perf_counter() - start_time
    total_movies = len(processed_movies)
    return None, list(processed_movies), execution_time, total_movies


def bidirectional_bfs_tmdb_by_id(start_movie_id, end_movie_id):
    global last_processed_movies
    start_time = time.perf_counter()

    start_movie = get_movie_details_cached(start_movie_id)
    end_movie = get_movie_details_cached(end_movie_id)

    if not start_movie or not end_movie:
        logger.error("Start or end movie not found.")
        return None, None

    logger.info(f"Starting Bidirectional BFS from '{start_movie['title']}' (ID: {start_movie_id}) to '{end_movie['title']}' (ID: {end_movie_id})")

    # Initialize forward search structures
    forward_queue = [start_movie_id]
    forward_visited = {start_movie_id: None}

    # Initialize backward search structures
    backward_queue = [end_movie_id]
    backward_visited = {end_movie_id: None}

    # To keep track of all processed movies
    processed_movies = set([start_movie_id, end_movie_id])

    # Variable to store the meeting point
    meeting_movie = None

    while forward_queue and backward_queue:
        # Expand forward search
        current_forward = forward_queue.pop(0)
        forward_movie_details = get_movie_details_cached(current_forward)
        if not forward_movie_details:
            continue
        logger.info(f"Forward Exploring movie: '{forward_movie_details['title']}' (ID: {current_forward})")

        credits = get_movie_credits_cached(current_forward)
        if credits:
            all_people = credits.get('cast', []) + credits.get('crew', [])
            sorted_people = sorted(all_people, key=lambda x: x.get('popularity', 0), reverse=True)[:50]

            for person in sorted_people:
                person_id = int(person['id'])
                person_name = person['name']
                logger.info(f"Forward Exploring connections through: {person_name} (ID: {person_id})")

                person_movies = get_person_movies_cached(person_id)
                if not person_movies:
                    continue

                all_movies = person_movies.get('cast', []) + person_movies.get('crew', [])
                sorted_movies = sorted(all_movies, key=lambda x: (x.get('release_date', ''), x.get('popularity', 0)), reverse=True)[:50]

                for movie in sorted_movies:
                    next_movie_id = int(movie['id'])
                    processed_movies.add(next_movie_id)  # Add to processed_movies set

                    if next_movie_id in forward_visited:
                        continue

                    forward_visited[next_movie_id] = current_forward
                    forward_queue.append(next_movie_id)
                    logger.info(f"Forward Adding movie to queue: '{movie['title']}' (ID: {next_movie_id})")

                    # Check if this node has been visited by backward search
                    if next_movie_id in backward_visited:
                        meeting_movie = next_movie_id
                        logger.info(f"Meeting point found at movie ID: {meeting_movie}")
                        break
                if meeting_movie:
                    break
        if meeting_movie:
            break

        # Expand backward search
        current_backward = backward_queue.pop(0)
        backward_movie_details = get_movie_details_cached(current_backward)
        if not backward_movie_details:
            continue
        logger.info(f"Backward Exploring movie: '{backward_movie_details['title']}' (ID: {current_backward})")

        credits = get_movie_credits_cached(current_backward)
        if credits:
            all_people = credits.get('cast', []) + credits.get('crew', [])
            sorted_people = sorted(all_people, key=lambda x: x.get('popularity', 0), reverse=True)[:50]

            for person in sorted_people:
                person_id = int(person['id'])
                person_name = person['name']
                logger.info(f"Backward Exploring connections through: {person_name} (ID: {person_id})")

                person_movies = get_person_movies_cached(person_id)
                if not person_movies:
                    continue

                all_movies = person_movies.get('cast', []) + person_movies.get('crew', [])
                sorted_movies = sorted(all_movies, key=lambda x: (x.get('release_date', ''), x.get('popularity', 0)), reverse=True)[:50]

                for movie in sorted_movies:
                    next_movie_id = int(movie['id'])
                    processed_movies.add(next_movie_id)  # Add to processed_movies set

                    if next_movie_id in backward_visited:
                        continue

                    backward_visited[next_movie_id] = current_backward
                    backward_queue.append(next_movie_id)
                    logger.info(f"Backward Adding movie to queue: '{movie['title']}' (ID: {next_movie_id})")

                    # Checks if this node has been visited by forward search
                    if next_movie_id in forward_visited:
                        meeting_movie = next_movie_id
                        logger.info(f"Meeting point found at movie ID: {meeting_movie}")
                        break
                if meeting_movie:
                    break
        if meeting_movie:
            break

    if meeting_movie is None:
        logger.info("No path found")
        logger.info(f"Total unique movies explored: {len(processed_movies)}")
        last_processed_movies = list(processed_movies)
        execution_time = time.perf_counter() - start_time
        total_movies = len(processed_movies)
        return None, list(processed_movies), execution_time, total_movies

    # Reconstruct the path
    path_forward = []
    current = meeting_movie
    while current != start_movie_id:
        path_forward.append(current)
        current = forward_visited.get(current)
        if current is None:
            break
    path_forward.append(start_movie_id)
    path_forward.reverse()

    path_backward = []
    current = meeting_movie
    while current != end_movie_id:
        current = backward_visited.get(current)
        if current is None:
            break
        path_backward.append(current)

    full_path = path_forward + path_backward

    end_time = time.perf_counter()
    logger.info(f"Bidirectional BFS execution time: {end_time - start_time:.2f} seconds")
    logger.info(f"Bidirectional BFS Path found! Total movies in path: {len(full_path)}")

    # Store the processed movies globally
    last_processed_movies = list(processed_movies)
    execution_time = time.perf_counter() - start_time
    total_movies = len(processed_movies)

    return full_path, list(processed_movies), execution_time, total_movies

def format_path(path):
    formatted_path = {
        'movies': [],
        'connections': []
    }
    for i, movie_id in enumerate(path):
        movie_details = get_movie_details_cached(movie_id)
        if movie_details:
            formatted_path['movies'].append({
                'id': movie_id,
                'title': movie_details.get('title'),
                'year': movie_details.get('release_date', '')[:4],
                'poster_path': movie_details.get('poster_path')
            })
        if i < len(path) - 1:
            movie1_credits = get_movie_credits_cached(path[i])
            movie2_credits = get_movie_credits_cached(path[i + 1])
            common_people = set(p['id'] for p in movie1_credits.get('cast', []) + movie1_credits.get('crew', [])) & \
                            set(p['id'] for p in movie2_credits.get('cast', []) + movie2_credits.get('crew', []))
            if common_people:
                person_id = list(common_people)[0]
                person_details = next((p for p in movie1_credits.get('cast', []) + movie1_credits.get('crew', []) if
                                       p['id'] == person_id), None)
                if person_details:
                    formatted_path['connections'].append(person_details.get('name'))
                else:
                    formatted_path['connections'].append('Unknown')
            else:
                formatted_path['connections'].append('Unknown')
    return formatted_path

@app.route('/find_path', methods=['GET'])
def find_path():
    """
    Endpoint to find the path between two movies using their TMDB IDs.
    Returns the path immediately once found.
    """
    start_movie_id = request.args.get('start_id')
    end_movie_id = request.args.get('end_id')
    algorithm = request.args.get('algorithm', 'bfs').lower()  # Default to BFS

    logger.info(f"Received request to find path from ID '{start_movie_id}' to ID '{end_movie_id}' using {algorithm}")

    if not start_movie_id or not end_movie_id:
        return jsonify({'error': 'Please provide both start_id and end_id'}), 400

    # Validate that start_movie_id and end_movie_id are integers
    try:
        start_movie_id = int(start_movie_id)
        end_movie_id = int(end_movie_id)
    except ValueError:
        return jsonify({'error': 'Invalid movie IDs provided'}), 400

    if algorithm == 'bfs':
        path, processed_movies, execution_time, total_movies = bidirectional_bfs_tmdb_by_id(start_movie_id, end_movie_id)
    elif algorithm == 'dijkstra':
        path, processed_movies, execution_time, total_movies = dijkstra_tmdb_by_id(start_movie_id, end_movie_id)
    else:
        return jsonify({'error': 'Invalid algorithm specified'}), 400

    if path is None:
        logger.info("No path found between the movies")
        return jsonify({'error': 'No path found between the movies'}), 404

    formatted_path = format_path(path)
    logger.info(f"Path found and formatted. Number of steps: {len(formatted_path['movies']) + len(formatted_path['connections'])}")

    return jsonify({
        'path': formatted_path,
        'execution_time': execution_time,
        'total_movies': total_movies
    })

@app.route('/get_processed_movies', methods=['GET'])
def get_processed_movies():
    global last_processed_movies

    if not last_processed_movies:
        logger.error("No processed movies found. Please find a path first.")
        return jsonify({'error': 'No processed movies found. Please find a path first.'}), 400

    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 250))  # Changed default to 100

    total_count = len(last_processed_movies)
    paginated_movies = last_processed_movies[offset:offset+limit]

    formatted_processed = []
    for movie_id in paginated_movies:
        details = get_movie_details_cached(movie_id)
        if details:
            formatted_processed.append({
                'id': movie_id,
                'title': details.get('title'),
                'year': details.get('release_date', '')[:4],
                'poster_path': details.get('poster_path')
            })

    logger.info(f"Returning {len(formatted_processed)} processed movies. Offset: {offset}, Limit: {limit}, Total: {total_count}")
    return jsonify({
        'processed_movies': formatted_processed,
        'total_count': total_count
    })
@app.route('/search_movie', methods=['GET'])
def search_movie_route():
    """
    Endpoint to search for movies by name.
    """
    movie_name = request.args.get('movie_name')
    logger.info(f"Searching for movie: '{movie_name}'")
    movies = search_movie_list(movie_name)
    if movies:
        logger.info(f"Found {len(movies)} movies matching '{movie_name}'")
        return jsonify({
            'results': movies
        })
    else:
        logger.info(f"Movie not found: '{movie_name}'")
        return jsonify({'error': 'Movie not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
