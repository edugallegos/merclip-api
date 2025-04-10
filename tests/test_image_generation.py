import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from datetime import datetime

client = TestClient(app)

@pytest.fixture
def mock_env_api_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake_api_key")

@pytest.fixture
def mock_date_dir():
    date_str = datetime.now().strftime("%Y-%m-%d")
    return os.path.join("generated_images", date_str)

@patch("app.services.image_generator.generate_multiple_images")
@patch("app.services.image_generator.get_output_directory")
def test_generate_images_endpoint(mock_get_dir, mock_generate, mock_env_api_key, mock_date_dir):
    # Mock the output directory
    mock_get_dir.return_value = mock_date_dir
    
    # Mock the service response
    mock_generate.return_value = [
        {
            "prompt": "A test prompt",
            "success": True,
            "image_path": os.path.join(mock_date_dir, "image_001.png")
        }
    ]
    
    # Test data
    test_data = {
        "prompts": ["A test prompt"]
    }
    
    # Make request to the endpoint
    response = client.post("/images/generate", json=test_data)
    
    # Assert response
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["prompt"] == "A test prompt"
    assert response.json()[0]["success"] is True
    assert response.json()[0]["image_path"] == os.path.join(mock_date_dir, "image_001.png")
    
    # Verify service was called with correct arguments
    mock_generate.assert_called_once_with(
        prompts=["A test prompt"],
        output_dir=None
    )

@patch("app.services.image_generator.generate_multiple_images")
def test_generate_images_with_custom_dir(mock_generate, mock_env_api_key):
    # Mock the service response
    mock_generate.return_value = [
        {
            "prompt": "A test prompt",
            "success": True,
            "image_path": "custom_dir/image_001.png"
        }
    ]
    
    # Test data with custom directory
    test_data = {
        "prompts": ["A test prompt"],
        "output_dir": "custom_dir"
    }
    
    # Make request to the endpoint
    response = client.post("/images/generate", json=test_data)
    
    # Assert response
    assert response.status_code == 200
    assert response.json()[0]["image_path"] == "custom_dir/image_001.png"
    
    # Verify service was called with correct arguments
    mock_generate.assert_called_once_with(
        prompts=["A test prompt"],
        output_dir="custom_dir"
    )

@patch("app.services.image_generator.generate_multiple_images")
def test_generate_images_empty_prompts(mock_generate, mock_env_api_key):
    # Test data with empty prompts
    test_data = {
        "prompts": []
    }
    
    # Make request to the endpoint
    response = client.post("/images/generate", json=test_data)
    
    # Assert response
    assert response.status_code == 400
    assert "No prompts provided" in response.json()["detail"]
    
    # Verify service was not called
    mock_generate.assert_not_called()

def test_generate_images_missing_api_key(monkeypatch):
    # Ensure API key is not set
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    
    # Test data
    test_data = {
        "prompts": ["A test prompt"]
    }
    
    # Make request to the endpoint
    response = client.post("/images/generate", json=test_data)
    
    # Assert response
    assert response.status_code == 500
    assert "GEMINI_API_KEY environment variable not set" in response.json()["detail"]

@pytest.mark.parametrize("error_message", [
    "API key invalid",
    "Service unavailable"
])
@patch("app.services.image_generator.generate_multiple_images")
def test_generate_images_service_error(mock_generate, mock_env_api_key, error_message):
    # Mock the service to raise an exception
    mock_generate.side_effect = Exception(error_message)
    
    # Test data
    test_data = {
        "prompts": ["A test prompt"]
    }
    
    # Make request to the endpoint
    response = client.post("/images/generate", json=test_data)
    
    # Assert response
    assert response.status_code == 500
    assert error_message in response.json()["detail"] 