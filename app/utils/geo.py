import math

# Centroid approximate coordinates for fictional disaster operational zones
AREA_CENTROIDS = {
    'North Coastal Sector': (13.0827, 80.2707),
    'East River Basin': (13.0500, 80.2500),
    'South Hillside Zone': (13.0000, 80.2000),
    'Central Metro Sector': (13.0600, 80.2300),
    'West Industrial District': (13.0400, 80.1700),
    'Harbor Port District': (13.1000, 80.2900),
    'Suburban Highland Area': (12.9800, 80.1500)
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees) using Haversine formula.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    
    # Radius of earth in kilometers
    R = 6371.0
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2.0) ** 2)
    
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    distance = R * c
    return round(distance, 2)


def get_area_coordinates(area_name: str) -> tuple[float, float] | tuple[None, None]:
    """Retrieve approximate coordinates for an affected area name."""
    if not area_name:
        return None, None
    for name, coords in AREA_CENTROIDS.items():
        if area_name.strip().lower() in name.lower() or name.lower() in area_name.strip().lower():
            return coords
    return 13.0500, 80.2400  # Default regional center fallback
