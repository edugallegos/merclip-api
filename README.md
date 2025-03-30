# Merclip API

A powerful API for creating dynamic video clips with customizable elements, including text overlays, video insertions, and more.

## Features

- Create video clips with text overlays
- Add video elements with custom positioning and scaling
- Timeline-based element rendering
- Support for vertical video (perfect for Instagram Reels, TikTok)
- Background color customization
- Custom text styles and positioning

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/merclip-api.git
cd merclip-api
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Make sure FFmpeg is installed on your system:
```bash
# For macOS
brew install ffmpeg

# For Ubuntu/Debian
sudo apt-get update
sudo apt-get install ffmpeg
```

## Running the API

```bash
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

## API Endpoints

### Create a Clip

`POST /clip`

Create a new video clip with custom elements.

**Request Body Example:**

```json
{
  "output": {
    "resolution": {
      "width": 1080,
      "height": 1920
    },
    "frame_rate": 30,
    "format": "mp4",
    "duration": 15,
    "background_color": "#000000"
  },
  "elements": [
    {
      "type": "video",
      "id": "background-video",
      "source": "https://example.com/video.mp4",
      "timeline": {
        "start": 0,
        "duration": 15,
        "in": 0
      },
      "transform": {
        "scale": 1.5,
        "position": {
          "x": 0,
          "y": 0
        },
        "opacity": 1.0
      },
      "audio": true
    },
    {
      "type": "text",
      "id": "headline",
      "text": "STUNNING VIEWS",
      "timeline": {
        "start": 0,
        "duration": 15
      },
      "transform": {
        "position": {
          "x": "center",
          "y": 200
        }
      },
      "style": {
        "font_family": "Arial",
        "font_size": 92,
        "color": "white",
        "background_color": "rgba(0,0,0,0.3)",
        "alignment": "center"
      }
    }
  ]
}
```

**Response:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "created_at": "2023-03-29T12:00:00",
  "completed_at": null,
  "error": null,
  "output_url": null
}
```

### Check Job Status

`GET /clip/{job_id}`

Check the status of a video rendering job.

**Response:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "created_at": "2023-03-29T12:00:00",
  "completed_at": "2023-03-29T12:01:30",
  "error": null,
  "output_url": "/jobs/550e8400-e29b-41d4-a716-446655440000/output.mp4"
}
```

### Download Rendered Video

`GET /clip/{job_id}/download`

Download the rendered video file.

## Templates

### Create a Template

`POST /template`

Create a new template for reusable video elements.

### Get Templates

`GET /template`

List all available templates.

### Get Template by ID

`GET /template/{template_id}`

Get a specific template by ID.

## License

MIT 