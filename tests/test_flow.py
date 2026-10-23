import re
import pytest
from app import create_app


def test_full_browser_login_workflow():
    """Test standard browser workflow with CSRF token extraction and submission."""
    app = create_app('development')
    client = app.test_client()

    # 1. GET login page to obtain CSRF token
    get_res = client.get('/auth/login')
    assert get_res.status_code == 200
    html = get_res.get_data(as_text=True)

    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    assert match is not None, "CSRF token must be present in login form"
    csrf_token = match.group(1)

    # 2. POST login with credentials and CSRF token
    post_res = client.post('/auth/login', data={
        'username': 'coordinator',
        'password': 'Coord@12345',
        'csrf_token': csrf_token
    }, follow_redirects=True)

    assert post_res.status_code == 200
    dash_html = post_res.get_data(as_text=True)
    assert "Disaster Operations Intelligence" in dash_html
    assert "coordinator" in dash_html

    # 3. GET shelter map
    map_res = client.get('/shelters/map')
    assert map_res.status_code == 200
    assert "Interactive Disaster Shelter Geospatial Map" in map_res.get_data(as_text=True)

    # 4. GET forecasting evaluation page
    eval_res = client.get('/forecasting/evaluate')
    assert eval_res.status_code == 200
    assert "Machine Learning Model Evaluation" in eval_res.get_data(as_text=True)
