import pytest
from app.models.video import VideoRequest, ElementType, Resolution, Output, Element, Timeline, Transform, Style, Position
from app.services.ffmpeg import FFmpegService

@pytest.fixture
def basic_video_request():
    """Fixture for a basic video request with minimal elements."""
    return VideoRequest(
        output=Output(
            resolution=Resolution(width=1080, height=1920),
            frame_rate=30,
            format="mp4",
            duration=15,
            background_color="#000000"
        ),
        elements=[]
    )

@pytest.fixture
def video_element():
    """Fixture for a video element."""
    return Element(
        type=ElementType.VIDEO,
        id="test-video",
        source="https://example.com/video.mp4",
        timeline=Timeline(start=0, duration=5, in_=0),
        transform=Transform(
            scale=1.5,
            position=Position(x=0, y=0),
            opacity=1.0
        ),
        audio=True
    )

@pytest.fixture
def image_element():
    """Fixture for an image element."""
    return Element(
        type=ElementType.IMAGE,
        id="test-image",
        source="https://example.com/image.png",
        timeline=Timeline(start=5, duration=3),
        transform=Transform(
            scale=0.5,
            position=Position(x=100, y=100)
        )
    )

@pytest.fixture
def text_element():
    """Fixture for a text element."""
    return Element(
        type=ElementType.TEXT,
        id="test-text",
        text="Test Text",
        timeline=Timeline(start=0, duration=15),
        transform=Transform(
            position=Position(x="center", y=200)
        ),
        style=Style(
            font_family="Arial",
            font_size=92,
            color="white",
            background_color="rgba(0,0,0,0.3)",
            alignment="center"
        )
    )

def test_basic_command_generation(basic_video_request):
    """Test basic command generation with no elements."""
    command = FFmpegService.generate_command(basic_video_request, "output.mp4")
    
    # Check basic command structure
    assert command[0] == "ffmpeg"
    assert "-y" in command
    assert "-f" in command
    assert "lavfi" in command[command.index("-f") + 1]
    
    # Check output parameters
    assert "-t" in command
    assert str(basic_video_request.output.duration) in command[command.index("-t") + 1]
    assert "-c:v" in command
    assert "libx264" in command[command.index("-c:v") + 1]
    assert "-preset" in command
    assert "medium" in command[command.index("-preset") + 1]
    assert "-pix_fmt" in command
    assert "yuv420p" in command[command.index("-pix_fmt") + 1]

def test_video_element_command(basic_video_request, video_element):
    """Test command generation with a video element."""
    basic_video_request.elements.append(video_element)
    command = FFmpegService.generate_command(basic_video_request, "output.mp4")
    
    # Check video input
    assert command.count("-i") == 2  # One for background, one for video
    # Find the second -i (after the background input)
    first_i_index = command.index("-i")
    second_i_index = command.index("-i", first_i_index + 1)
    assert video_element.source in command[second_i_index + 1]
    
    # Check filter complex for video
    filter_complex = command[command.index("-filter_complex") + 1]
    assert f"scale=iw*{video_element.transform.scale}:ih*{video_element.transform.scale}" in filter_complex
    assert f"overlay=x={video_element.transform.position.x}:y={video_element.transform.position.y}" in filter_complex

def test_image_element_command(basic_video_request, image_element):
    """Test command generation with an image element."""
    basic_video_request.elements.append(image_element)
    command = FFmpegService.generate_command(basic_video_request, "output.mp4")
    
    # Check image input
    assert command.count("-i") == 2  # One for background, one for image
    # Find the second -i (after the background input)
    first_i_index = command.index("-i")
    second_i_index = command.index("-i", first_i_index + 1)
    assert image_element.source in command[second_i_index + 1]
    
    # Check filter complex for image
    filter_complex = command[command.index("-filter_complex") + 1]
    assert f"scale=iw*{image_element.transform.scale}:ih*{image_element.transform.scale}" in filter_complex
    assert f"overlay=x={image_element.transform.position.x}:y={image_element.transform.position.y}" in filter_complex

def test_text_element_command(basic_video_request, text_element):
    """Test command generation with a text element."""
    basic_video_request.elements.append(text_element)
    command = FFmpegService.generate_command(basic_video_request, "output.mp4")
    
    # Check text overlay
    filter_complex = command[command.index("-filter_complex") + 1]
    assert f"drawtext=text='{text_element.text}'" in filter_complex
    assert f"fontsize={text_element.style.font_size}" in filter_complex
    assert f"fontcolor={text_element.style.color}" in filter_complex
    assert f"x=(w-text_w)/2" in filter_complex  # Center position
    assert f"y={text_element.transform.position.y}" in filter_complex

def test_complex_command(basic_video_request, video_element, image_element, text_element):
    """Test command generation with multiple elements."""
    basic_video_request.elements.extend([video_element, image_element, text_element])
    command = FFmpegService.generate_command(basic_video_request, "output.mp4")
    
    # Check all inputs are present
    assert command.count("-i") == 3  # One for background, one for video, one for image
    
    # Check filter complex contains all elements
    filter_complex = command[command.index("-filter_complex") + 1]
    assert "scale=iw*1.5:ih*1.5" in filter_complex  # Video scale
    assert "scale=iw*0.5:ih*0.5" in filter_complex  # Image scale
    assert f"drawtext=text='{text_element.text}'" in filter_complex

def test_rgba_to_hex_conversion():
    """Test RGBA to hex color conversion."""
    assert FFmpegService.rgba_to_hex("rgba(0,0,0,0.3)") == "#000000"
    assert FFmpegService.rgba_to_hex("rgba(255,255,255,1)") == "#ffffff"
    assert FFmpegService.rgba_to_hex("rgba(128,128,128,0.5)") == "#808080"

def test_center_position_handling(basic_video_request, text_element):
    """Test handling of center position for text elements."""
    text_element.transform.position = Position(x="center", y=200)
    basic_video_request.elements.append(text_element)
    command = FFmpegService.generate_command(basic_video_request, "output.mp4")
    
    filter_complex = command[command.index("-filter_complex") + 1]
    assert "x=(w-text_w)/2" in filter_complex

def test_audio_handling(basic_video_request, video_element):
    """Test audio handling in command generation."""
    video_element.audio = True
    basic_video_request.elements.append(video_element)
    command = FFmpegService.generate_command(basic_video_request, "output.mp4")
    
    # Check audio codec is included
    assert "-c:a" in command
    assert "aac" in command[command.index("-c:a") + 1]
    assert "-b:a" in command
    assert "128k" in command[command.index("-b:a") + 1]
    
    # Check audio mapping
    # First find the video mapping
    filter_complex_index = command.index("-filter_complex")
    video_map_index = command.index("-map", filter_complex_index + 1)
    # Then find the audio mapping after the video mapping
    audio_map_index = command.index("-map", video_map_index + 1)
    assert "1:a?" in command[audio_map_index + 1]

def test_duration_handling(basic_video_request, video_element):
    """Test duration handling in command generation."""
    video_element.timeline.duration = 10
    basic_video_request.elements.append(video_element)
    command = FFmpegService.generate_command(basic_video_request, "output.mp4")
    
    filter_complex = command[command.index("-filter_complex") + 1]
    assert f"enable='between(t,{video_element.timeline.start},{video_element.timeline.start + video_element.timeline.duration})'" in filter_complex 