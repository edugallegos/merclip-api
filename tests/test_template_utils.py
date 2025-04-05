import pytest
import sys
import os
from typing import Dict, Any
from unittest.mock import MagicMock

# Add the project root to sys.path if not already
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the functions to test
from app.routers.template_clip import deep_merge, get_property_with_defaults
from app.models.template_clip import Element, ElementType, Timeline

class TestDeepMerge:
    """Tests for the deep_merge function."""
    
    def test_merge_simple_dicts(self):
        """Test merging simple dictionaries without nested structures."""
        template = {"a": 1, "b": 2, "c": 3}
        user_values = {"b": 5, "d": 4}
        
        result = deep_merge(template, user_values)
        
        assert result == {"a": 1, "b": 5, "c": 3, "d": 4}
        
    def test_merge_nested_dicts(self):
        """Test merging dictionaries with nested structures."""
        template = {
            "a": 1,
            "nested": {
                "x": 10,
                "y": 20,
                "deep": {
                    "value": 100
                }
            }
        }
        
        user_values = {
            "a": 5,
            "nested": {
                "y": 30,
                "z": 40,
                "deep": {
                    "value": 200,
                    "extra": 300
                }
            }
        }
        
        result = deep_merge(template, user_values)
        
        assert result == {
            "a": 5,
            "nested": {
                "x": 10,
                "y": 30,
                "z": 40,
                "deep": {
                    "value": 200,
                    "extra": 300
                }
            }
        }
        
    def test_merge_with_none_values(self):
        """Test that None values in user_values are skipped."""
        template = {"a": 1, "b": 2, "c": 3}
        user_values = {"a": None, "b": 5, "d": None}
        
        result = deep_merge(template, user_values)
        
        assert result == {"a": 1, "b": 5, "c": 3}
        
    def test_merge_with_empty_dicts(self):
        """Test merging with empty dictionaries."""
        template = {"a": 1, "b": 2}
        empty_dict = {}
        
        result1 = deep_merge(template, empty_dict)
        result2 = deep_merge(empty_dict, template)
        
        assert result1 == {"a": 1, "b": 2}
        assert result2 == {"a": 1, "b": 2}
        
    def test_merge_with_lists(self):
        """Test handling of lists in dictionaries."""
        template = {"list": [1, 2, 3], "other": "value"}
        user_values = {"list": [4, 5, 6]}
        
        # Lists should be replaced, not merged
        result = deep_merge(template, user_values)
        
        assert result == {"list": [4, 5, 6], "other": "value"}
        
    def test_template_not_modified(self):
        """Test that the original template is not modified."""
        template = {"a": 1, "nested": {"x": 10}}
        user_values = {"a": 2, "nested": {"y": 20}}
        
        original_template = template.copy()
        deep_merge(template, user_values)
        
        assert template == original_template
        
    def test_user_values_not_modified(self):
        """Test that the original user_values is not modified."""
        template = {"a": 1, "nested": {"x": 10}}
        user_values = {"a": 2, "nested": {"y": 20}}
        
        original_user_values = user_values.copy()
        deep_merge(template, user_values)
        
        assert user_values == original_user_values


class TestGetPropertyWithDefaults:
    """Tests for the get_property_with_defaults function."""
    
    def test_property_from_processed_element(self):
        """Test retrieving a property from processed_element."""
        # Create test data
        element = MagicMock(spec=Element)
        template_defaults = {"transform": {"scale": 1.0, "position": {"x": 0, "y": 0}}}
        processed_element = {"transform": {"scale": 2.0}}
        property_name = "transform"
        
        # Call the function
        result = get_property_with_defaults(
            element, template_defaults, processed_element, property_name
        )
        
        # Check the result
        assert result == {"scale": 2.0, "position": {"x": 0, "y": 0}}
        
    def test_property_from_element_attribute(self):
        """Test retrieving a property from element attribute when not in processed_element."""
        # Create mock style object
        mock_style = MagicMock()
        mock_style.dict.return_value = {"font_size": 24, "color": "red"}
        
        # Create element with style attribute
        element = MagicMock(spec=["style"])
        element.style = mock_style
        
        processed_element = {}
        template_defaults = {}
        
        result = get_property_with_defaults(element, template_defaults, processed_element, "style")
        
        assert result == {"font_size": 24, "color": "red"}
        mock_style.dict.assert_called_once_with(exclude_unset=True)
        
    def test_property_from_template_defaults(self):
        """Test retrieving a property from template_defaults when not found elsewhere."""
        # Create mock without transform attribute
        element = MagicMock(spec=[])  # No attributes
        
        processed_element = {}
        template_defaults = {"transform": {"position": {"x": 0, "y": 0}, "opacity": 1.0}}
        
        result = get_property_with_defaults(element, template_defaults, processed_element, "transform")
        
        assert result == {"position": {"x": 0, "y": 0}, "opacity": 1.0}
        
    def test_property_empty_when_not_found(self):
        """Test that an empty dict is returned when property not found anywhere."""
        # Create a mock Element without the property
        element = MagicMock(spec=Element)
        
        template_defaults = {}  # Empty template defaults
        processed_element = {}  # Empty processed element
        property_name = "transform"
        
        # Call the function
        result = get_property_with_defaults(
            element, template_defaults, processed_element, property_name
        )
        
        # Check the result
        assert result == {}
        
    def test_complex_nested_property_merge(self):
        """Test merging a complex nested property."""
        # Create mock transform object
        mock_transform = MagicMock()
        mock_transform.dict.return_value = {
            "position": {"x": 100},
            "opacity": 0.5
        }
        
        # Create element with transform attribute
        element = MagicMock(spec=["transform"])
        element.transform = mock_transform
        
        processed_element = {
            "transform": {
                "position": {"y": 200},
                "scale": 1.5
            }
        }
        
        template_defaults = {
            "transform": {
                "position": {"x": 0, "y": 0},
                "opacity": 1.0,
                "scale": 1.0
            }
        }
        
        result = get_property_with_defaults(element, template_defaults, processed_element, "transform")
        
        # With the updated priority, element attributes have highest priority
        expected = {
            "position": {"x": 100, "y": 200},  # x from element.transform, y from processed_element
            "opacity": 0.5,    # From element.transform
            "scale": 1.5      # From processed_element
        }
        
        assert result == expected
        
    def test_priority_order(self):
        """Test that element attributes take priority over processed_element."""
        # Create mock style object
        mock_style = MagicMock()
        mock_style.dict.return_value = {"font_size": 24, "color": "red"}
        
        # Create element with style attribute
        element = MagicMock(spec=["style"])
        element.style = mock_style
        
        processed_element = {
            "style": {"font_size": 18, "background": "blue"}
        }
        
        template_defaults = {
            "style": {"font_size": 16, "color": "black", "background": "white"}
        }
        
        result = get_property_with_defaults(element, template_defaults, processed_element, "style")
        
        # Element attributes have highest priority with the updated implementation
        expected = {
            "font_size": 24,      # From element.style (overrides processed_element)
            "color": "red",       # From element.style
            "background": "blue"  # From processed_element
        }
        
        assert result == expected


# Integration tests with real Element objects
class TestWithRealElements:
    """Tests using real Element objects instead of mocks."""
    
    def test_with_real_element_transform(self):
        """Test using a real Element object with transform property."""
        # Create a real Element
        element = Element(
            type=ElementType.TEXT,
            text="Sample text",
            timeline=Timeline(start=0, duration=5),
            transform={"position": {"x": "center", "y": 100}, "scale": 1.5}
        )
        
        template_defaults = {
            "transform": {
                "scale": 1.0,
                "position": {"x": 0, "y": 0},
                "opacity": 1.0
            }
        }
        
        # Process special properties
        processed_element = {}  # No special properties here
        property_name = "transform"
        
        # Call the function
        result = get_property_with_defaults(
            element, template_defaults, processed_element, property_name
        )
        
        # Check the result
        expected = {
            "scale": 1.5,
            "position": {"x": "center", "y": 100},
            "opacity": 1.0
        }
        assert result == expected
        
    def test_with_special_properties(self):
        """Test the interaction between special properties and get_property_with_defaults."""
        # Create a real Element with a special property
        element = Element(
            type=ElementType.IMAGE,
            source="image.jpg",
            timeline=Timeline(start=0, duration=5),
            position="top-right"  # Special property
        )
        
        template_defaults = {
            "transform": {
                "scale": 1.0,
                "position": {"x": 0, "y": 0},
                "opacity": 1.0
            }
        }
        
        # Process special properties
        processed_element = element.process_special_properties()
        property_name = "transform"
        
        # Call the function
        result = get_property_with_defaults(
            element, template_defaults, processed_element, property_name
        )
        
        # Check if the special property position was properly processed
        assert "transform" in processed_element
        assert "position" in processed_element["transform"]
        
        # Check the result includes the properly merged position
        assert "position" in result
        assert result["position"]["x"] == "top-right"
        assert result["position"]["y"] == "top-right"
        
        # Other defaults should be preserved
        assert result["scale"] == 1.0
        assert result["opacity"] == 1.0
