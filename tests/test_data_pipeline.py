import io
import pytest
from app.services.data_processor import DataProcessor
from app.models.shelter import Shelter


def test_import_shelters_csv_valid_and_invalid(app):
    """Test data pipeline validation with both valid and invalid records."""
    csv_content = (
        "shelter_code,name,location_name,total_capacity,current_occupancy,status\n"
        "SHELTER-VALID-1,Test Valid Shelter 1,East Sector,100,20,Active\n"
        "SHELTER-BAD-1,Bad Shelter Negative Capacity,East Sector,-50,10,Active\n"
        "SHELTER-BAD-2,Bad Shelter Overbooked,East Sector,50,80,Active\n"
    )
    stream = io.BytesIO(csv_content.encode('utf-8'))
    report = DataProcessor.import_shelters_csv(stream)

    assert report['total_rows'] == 3
    assert report['success_count'] == 1
    assert report['rejected_count'] == 2
    assert len(report['rejections']) == 2
    assert Shelter.query.filter_by(shelter_code='SHELTER-VALID-1').first() is not None


def test_data_quality_summary(app):
    """Test data quality health metrics calculation."""
    summary = DataProcessor.get_data_quality_summary()
    assert 'total_shelters' in summary
    assert 'overall_quality_score' in summary
    assert summary['overall_quality_score'] >= 0


def test_export_csv(app):
    """Test CSV report generation."""
    csv_out = DataProcessor.export_csv('shelters')
    assert 'shelter_code,name,location_name' in csv_out
    assert 'SHELTER-001' in csv_out
