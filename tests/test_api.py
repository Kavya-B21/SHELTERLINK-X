import pytest


def test_health_check_endpoint(client):
    """Test /health cloud check endpoint."""
    res = client.get('/health')
    assert res.status_code == 200
    data = res.get_json()
    assert data['status'] == 'healthy'
    assert data['application'] == 'SHELTERLINK X'
    assert data['database'] == 'healthy'


def test_geojson_endpoint(client):
    """Test GeoJSON endpoint for interactive Leaflet map."""
    res = client.get('/api/shelters/geojson')
    assert res.status_code == 200
    data = res.get_json()
    assert data['type'] == 'FeatureCollection'
    assert len(data['features']) > 0
    first = data['features'][0]
    assert 'geometry' in first
    assert 'properties' in first
    assert 'available_capacity' in first['properties']


def test_charts_data_endpoint(client):
    """Test Chart.js data endpoint."""
    res = client.get('/api/analytics/charts')
    assert res.status_code == 200
    data = res.get_json()
    assert 'occupancy_chart' in data
    assert 'requests_chart' in data
    assert 'forecast_chart' in data
