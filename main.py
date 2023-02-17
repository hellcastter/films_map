""" Films map """
import os
import ssl
import argparse
import webbrowser
from functools import lru_cache
from math import sin, cos, pi, asin, sqrt

import folium
import certifi
import geopy.geocoders
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

NUMBER_OF_FILMS = 10

@lru_cache(maxsize=None)
def get_coordinates(place: str) -> tuple[float, float]:
    """get coordinates of place

    Args:
        place (str): name of place

    Returns:
        tuple[float, float]: latitude and longitude

    >>> get_coordinates("Lviv, Ukraine")
    (49.841952, 24.0315921)
    >>> get_coordinates("Ukrainian Catholic University")
    (49.815884499999996, 24.02549565)
    """
    try:
        location = geolocator.geocode(place)
    except:
        return None

    return (location.latitude, location.longitude) if location else None


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """calculate distance between 2 points by its longitude and latitude

    Args:
        lat1 (float): latitude of first
        lon1 (float): longitude of first
        lat2 (float): latitude of second
        lon2 (float): longitude of second

    Returns:
        float: distance between 2 points

    >>> calculate_distance(50, 23, 50, 24)
    71.47418874347893
    """
    earth_radius = 6371

    angle1 = lat1 * pi / 180
    angle2 = lat2 * pi / 180
    delta_lat = (lat2 - lat1) * pi / 180
    delta_lon = (lon2 - lon1) * pi / 180

    hav = sin(delta_lat / 2) ** 2 + cos(angle1) * cos(angle2) * (sin(delta_lon / 2) ** 2)
    return 2 * earth_radius * asin(sqrt(hav))


def parse_file(
        path: str,
        year: int,
        latitude: float,
        longitude: float
    ) -> list[str, float, float, str, float]:
    """get nearest films from db

    Args:
        path (str): path to db file
        year (int): year in which films where created
        latitude (float): lat of nearest
        longitude (float): lon of nearest

    Returns:
        list[str, float, float, str, float]: [(name, lat, lon, location, distance)]
    """
    nearest_films = []

    with open(path, 'r', encoding="utf-8") as file:
        for row in file.readlines():
            if f"({year})" not in row:
                continue

            row = row[:-1].split('\t')
            name = row[0]
            location = row[-2 if '(' in row[-1] and ')' in row[-1] else -1]

            coordinates = get_coordinates(location)

            if not coordinates:
                continue

            place_latitude, place_longitude = coordinates
            distance = calculate_distance(place_latitude, place_longitude, latitude, longitude)
            result = (name, place_latitude, place_longitude, location, distance)

            # get only 10 films (not more)
            i = 0
            while i < min(len(nearest_films), NUMBER_OF_FILMS):
                if distance <= nearest_films[i][-1]:
                    nearest_films.insert(i, result)
                    break

                i += 1
            else:
                nearest_films.append(result)

            if len(nearest_films) > NUMBER_OF_FILMS:
                nearest_films.pop()

    return nearest_films


def generate_map(latitude: float, longitude: float, nearest_films: list, path: str) -> None:
    """Generate result map

    Args:
        latitude (float): start latitude
        longitude (float): start longitude
        nearest_films (list): list of nearest films to display
        path (str): file where to save
    """
    folium_map = folium.Map(location=[latitude, longitude], zoom_start=3)

    films_group = folium.FeatureGroup(name="Films")
    lines_group = folium.FeatureGroup(name="Lines")

    # get only unique locations
    unique_locations = {}
    for film in nearest_films:
        location = film[3]

        if location in unique_locations:
            unique_locations[location].append(film)
        else:
            unique_locations[location] = [film]

    # display them
    for films in unique_locations.values():
        # basic info
        _, lat, lon, location, distance = films[0]
        info = f"""
        <h3>{location}</h3>
        <b>Films filmed here:</b>
        <ul>
        """

        # all films in list
        for film in films:
            info += f"<li>{film[0]}</li>"

        info += '</ul>'
        info += f'<p><b>Distance:</b> {round(distance, 2)} km</p>'

        iframe = folium.IFrame(html=info, width="300", height="100%")
        films_group.add_child(
            folium.Marker(
                location=[lat, lon],
                icon=folium.Icon(color="blue"),
                popup=folium.Popup(iframe)
            )
        )

        lines_group.add_child(
            folium.PolyLine([[lat, lon], [latitude, longitude]],
            tooltip=f"<b>Distance:</b> {round(distance, 2)} km")
        )

    folium_map.add_child(films_group)
    folium_map.add_child(lines_group)

    folium_map.add_child(folium.Marker(
        location=[latitude, longitude],
        icon=folium.Icon(color="red"),
        tooltip="<h4>Selected location</h4>"
    ))
    folium_map.save(path)


def main():
    """ get info from argparse """
    parser = argparse.ArgumentParser(
            prog = 'Films Map',
            description = 'Generates map of 10 closest films')

    parser.add_argument('year', type=int, help="Year of the film")
    parser.add_argument('latitude', type=float, help="latitude of the film")
    parser.add_argument('longitude', type=float, help='longitude of the film')
    parser.add_argument('path', type=str, help='path to dataset')

    args = parser.parse_args()

    year = args.year
    latitude = args.latitude
    longitude = args.longitude
    path = args.path

    nearest_films = parse_file(path, year, latitude, longitude)
    generate_map(latitude, longitude, nearest_films, "index.html")

    webbrowser.open(f"file://{os.path.realpath('./index.html')}")

if __name__ == "__main__":
    # add certificates (it's not working without it)
    ctx = ssl.create_default_context(cafile=certifi.where())
    geopy.geocoders.options.default_ssl_context = ctx

    # initialize geolocator
    geolocator = Nominatim(user_agent="films_app")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    main()
