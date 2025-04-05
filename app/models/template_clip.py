from typing import List, Optional, Dict, Any, Union, Type, Callable
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum

class ElementType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"
    TEXT = "text"
    AUDIO = "audio"

class Timeline(BaseModel):
    start: float = Field(..., ge=0)
    duration: float = Field(..., gt=0)

class Position(BaseModel):
    """Position model for element positioning.
    
    This class supports both numeric pixel values and string position presets.
    When used in templates, these values determine where elements appear in the video frame.
    
    String position presets include:
    - Basic positions: "center", "top", "bottom", "left", "right"
    - Corner positions: "top-left", "top-right", "bottom-left", "bottom-right"
    - Mid positions: "mid-top", "mid-bottom"
    
    These values are converted to pixel coordinates during rendering based on the video dimensions.
    
    Example:
        To position an element at the top center of the video:
        position = Position(x="center", y="top")
    """
    x: Union[int, str] = "center"
    y: Union[int, str] = "center"
    
    @validator('x', 'y')
    def validate_position(cls, v):
        """Validate that string position values are one of the allowed presets."""
        allowed_positions = [
            "center", "top", "bottom", "left", "right", 
            "top-left", "top-right", "bottom-left", "bottom-right", 
            "mid-top", "mid-bottom"
        ]
        if isinstance(v, str) and v not in allowed_positions:
            raise ValueError(f'String position must be one of: {", ".join(allowed_positions)}')
        return v

class Transform(BaseModel):
    position: Optional[Position] = None
    scale: Optional[float] = None

class Style(BaseModel):
    font_family: Optional[str] = None
    font_size: Optional[int] = None
    color: Optional[str] = None
    background_color: Optional[str] = None
    alignment: Optional[str] = None

class SpecialProperties:
    """Handler for special shorthand properties in elements.
    
    This class defines special shorthand properties that can be used in template-clip
    elements for easier video creation. Each special property has a registration and 
    a handler function that transforms it into standard element properties.
    
    New special properties can be easily added by creating a new handler method and
    registering it in the HANDLERS dictionary.
    """
    
    @staticmethod
    def handle_position(element_dict: Dict[str, Any], value: str) -> Dict[str, Any]:
        """Handle position shorthand property.
        
        Converts a simple string position value into a full transform.position object.
        
        Args:
            element_dict: The element dictionary to modify
            value: The position value as a string
            
        Returns:
            The modified element dictionary
        """
        if not value:
            return element_dict
            
        # Create transform if it doesn't exist
        if 'transform' not in element_dict:
            element_dict['transform'] = {}
            
        # Create position in transform
        element_dict['transform']['position'] = {
            'x': value,
            'y': value
        }
        
        return element_dict
    
    @staticmethod
    def handle_size(element_dict: Dict[str, Any], value: Union[int, str]) -> Dict[str, Any]:
        """Handle size shorthand property.
        
        Converts a simple size value into a scale transform property.
        
        Args:
            element_dict: The element dictionary to modify
            value: The size value as an int or a string like "small", "medium", "large"
            
        Returns:
            The modified element dictionary
        """
        if not value:
            return element_dict
            
        # Map string sizes to scale values
        size_map = {
            "tiny": 0.25,
            "small": 0.5,
            "medium": 1.0,
            "large": 1.5,
            "huge": 2.0
        }
        
        # Get the scale value
        scale = value if isinstance(value, (int, float)) else size_map.get(value, 1.0)
            
        # Create transform if it doesn't exist
        if 'transform' not in element_dict:
            element_dict['transform'] = {}
            
        # Set scale in transform
        element_dict['transform']['scale'] = scale
        
        return element_dict
    
    # Registry of special property handlers
    # This makes it easy to add new special properties in the future
    HANDLERS = {
        'position': handle_position,
        'size': handle_size,
        # Add more special properties here
    }
    
    @classmethod
    def process(cls, element_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Process all special properties in an element.
        
        This method looks for special properties in the element dictionary
        and applies the corresponding handlers to transform them into
        standard element properties.
        
        Args:
            element_dict: Raw element dictionary with potential special properties
            
        Returns:
            Processed element dictionary with special properties transformed
        """
        result = element_dict.copy()
        
        # Process each registered special property
        for prop_name, handler in cls.HANDLERS.items():
            if prop_name in result:
                # Apply the handler and remove the special property
                value = result.pop(prop_name)
                # Call the static method correctly without passing cls
                result = handler(result, value)
                
        return result

class Element(BaseModel):
    """Element model for template-based clip requests.
    
    This model includes both standard element properties and special shorthand properties
    that simplify element creation. When processed, these elements are merged with template
    defaults to create the final video elements.
    
    Special properties:
    - position: A string shorthand for positioning elements (e.g., "center", "top-left").
                This is converted to a full Transform.position object during processing.
    - size: A shorthand for scale. Can be a number or string like "small", "medium", "large".
    
    Standard properties follow the VideoRequest element structure, and all optional 
    properties will use template defaults if not specified.
    """
    type: ElementType
    source: Optional[str] = None
    text: Optional[str] = None
    timeline: Timeline
    # Optional fields for different element types
    transform: Optional[Transform] = None
    style: Optional[Style] = None
    # Audio properties
    volume: Optional[float] = None
    fade_in: Optional[float] = None
    fade_out: Optional[float] = None
    
    # Special shorthand properties
    position: Optional[str] = None  # Can be "center", "top", "bottom", "left", "right", etc.
    size: Optional[Union[float, str]] = None  # Can be a number or "small", "medium", "large"
    
    # Add more special properties here as needed
    
    @validator('source', 'text')
    def validate_source_text(cls, v, values):
        """Validate that source or text is provided based on element type."""
        if 'type' in values:
            if values['type'] == ElementType.TEXT and not v:
                raise ValueError('text is required for text elements')
            if values['type'] in [ElementType.VIDEO, ElementType.AUDIO, ElementType.IMAGE] and not v:
                raise ValueError('source is required for video, audio, and image elements')
        return v
    
    def process_special_properties(self) -> Dict[str, Any]:
        """Process all special properties and return a standard element dictionary.
        
        This method converts all special shorthand properties to their standard form.
        
        Returns:
            Dict with all special properties processed into standard format
        """
        # Convert to dict first
        element_dict = self.dict(exclude_unset=True)
        
        # Use the SpecialProperties processor to handle all special properties
        return SpecialProperties.process(element_dict)

class TemplateClipRequest(BaseModel):
    template_id: str
    elements: List[Element] 