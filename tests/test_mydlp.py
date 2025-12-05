"""
Tests for MyDLP service
"""
import pytest
from app.services.mydlp_service import MyDLPService


def test_mydlp_initialization():
    """Test MyDLP service initialization"""
    service = MyDLPService()
    assert service is not None


def test_is_enabled():
    """Test MyDLP enabled status"""
    service = MyDLPService()
    assert isinstance(service.is_enabled(), bool)


def test_block_data_transfer():
    """Test blocking data transfer"""
    service = MyDLPService()
    # This will return True if disabled (simulated) or actual result if enabled
    result = service.block_data_transfer(
        source_ip="192.168.1.1",
        destination="external",
        detected_entities=[{"entity_type": "CREDIT_CARD", "value": "1234-5678-9012-3456"}]
    )
    assert isinstance(result, bool)

