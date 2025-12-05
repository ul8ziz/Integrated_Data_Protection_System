"""
Tests for Presidio service
"""
import pytest
from app.services.presidio_service import PresidioService


def test_presidio_initialization():
    """Test Presidio service initialization"""
    service = PresidioService()
    assert service is not None
    assert service.analyzer is not None


def test_analyze_text():
    """Test text analysis"""
    service = PresidioService()
    text = "My name is John Doe and my phone is 123-456-7890"
    results = service.analyze(text)
    assert isinstance(results, list)


def test_get_supported_entities():
    """Test getting supported entities"""
    service = PresidioService()
    entities = service.get_supported_entities()
    assert isinstance(entities, list)
    assert len(entities) > 0


def test_is_sensitive():
    """Test sensitive data detection"""
    service = PresidioService()
    # Text with phone number
    text_with_sensitive = "Call me at 123-456-7890"
    assert service.is_sensitive(text_with_sensitive) is True
    
    # Text without sensitive data
    text_without_sensitive = "Hello world"
    assert service.is_sensitive(text_without_sensitive) is False

