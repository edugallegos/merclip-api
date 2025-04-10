# Merclip API

A FastAPI-based service for creating dynamic video clips with text overlays, image overlays, and background videos.

<a href="https://cloud.digitalocean.com/apps/new?repo=https://github.com/edugallegos/merclip-api/tree/main&refcode=b2da9090ff66" target="_blank">
  <img src="https://www.deploytodo.com/do-btn-blue.svg" alt="Deploy to DO">
</a>
<a href="https://render.com/deploy?repo=https://github.com/edugallegos/merclip-api/tree/main" target="_blank">
  <img src="https://render.com/images/deploy-to-render-button.svg" alt="Deploy to Render">
</a>

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)


## Features

- Create video clips with multiple elements:
  - Background videos
  - Image overlays (logos, watermarks, etc.)
  - Text overlays with customizable styling
  - Audio support
- Template-based clip creation with predefined styles and defaults
- Customizable output settings:
  - Resolution
  - Frame rate
  - Duration
  - Background color
- Asynchronous job processing
- Job status tracking
- Static file serving for video downloads

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/merclip-api.git
cd merclip-api
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install FFmpeg:
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt-get install ffmpeg`
- Windows: Download from [FFmpeg website](https://ffmpeg.org/download.html)

## Usage

### API Endpoints

#### POST /clip
Creates a new video clip with the specified elements.

**Request Body:**
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
      "type": "image",
      "id": "logo",
      "source": "https://example.com/logo.png",
      "timeline": {
        "start": 10,
        "duration": 5
      },
      "transform": {
        "scale": 0.5,
        "position": {
          "x": 100,
          "y": 100
        }
      }
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

#### POST /template-clip
Creates a new video clip using a predefined template.

**Request Body:**
```json
{
  "template_id": "multi_element_reel",
  "elements": [
    {
      "type": "video",
      "source": "https://cdn.example.com/video1.mp4",
      "timeline": {
        "start": 0,
        "duration": 5
      }
    },
    {
      "type": "image",
      "source": "https://cdn.example.com/image1.png",
      "timeline": {
        "start": 5,
        "duration": 3
      }
    },
    {
      "type": "text",
      "text": "🔥 Sale Starts Now",
      "timeline": {
        "start": 8,
        "duration": 4
      }
    },
    {
      "type": "audio",
      "source": "https://cdn.example.com/music.mp3",
      "timeline": {
        "start": 0,
        "duration": 12
      }
    }
  ]
}
```

**Response:**
```json
{
  "job_id": "unique-job-id",
  "status": "processing"
}
```

#### GET /clip/{job_id}
Get the status of a video clip job.

**Response:**
```json
{
  "job_id": "unique-job-id",
  "status": "completed",
  "created_at": "2024-03-20T10:00:00Z",
  "completed_at": "2024-03-20T10:01:00Z",
  "output_url": "/jobs/unique-job-id/output.mp4"
}
```

### Element Types and Properties

#### Video Element
```json
{
  "type": "video",
  "id": "unique-id",
  "source": "https://example.com/video.mp4",
  "timeline": {
    "start": 0,        // When to start showing the video
    "duration": 15,    // How long to show the video
    "in": 0           // Optional: where to start in the source video
  },
  "transform": {
    "scale": 1.5,     // Scale factor (1.0 = original size)
    "position": {
      "x": 0,         // X position (can be number or "center")
      "y": 0          // Y position
    },
    "opacity": 1.0    // Opacity (0.0 to 1.0)
  },
  "audio": true       // Whether to include audio
}
```

#### Image Element
```json
{
  "type": "image",
  "id": "unique-id",
  "source": "https://example.com/image.png",
  "timeline": {
    "start": 0,        // When to start showing the image
    "duration": 15     // How long to show the image
  },
  "transform": {
    "scale": 0.5,     // Scale factor (1.0 = original size)
    "position": {
      "x": 100,       // X position (can be number or "center")
      "y": 100        // Y position
    }
  }
}
```

#### Text Element
```json
{
  "type": "text",
  "id": "unique-id",
  "text": "Your text here",
  "timeline": {
    "start": 0,        // When to start showing the text
    "duration": 15     // How long to show the text
  },
  "transform": {
    "position": {
      "x": "center",  // X position (can be number or "center")
      "y": 200        // Y position
    }
  },
  "style": {
    "font_family": "Arial",
    "font_size": 92,
    "color": "white",
    "background_color": "rgba(0,0,0,0.3)",  // Optional: can be rgba or hex
    "alignment": "center"
  }
}
```

### Output Settings
```json
{
  "output": {
    "resolution": {
      "width": 1080,    // Output video width
      "height": 1920    // Output video height
    },
    "frame_rate": 30,   // Frames per second
    "format": "mp4",    // Output format
    "duration": 15,     // Total duration in seconds
    "background_color": "#000000"  // Background color (hex format)
  }
}
```

### Templates

Templates are stored in the `templates` directory as JSON files. Each template defines:
- Output settings (resolution, frame rate, format, background color)
- Default styles and transformations for each element type
- Base structure for common video layouts

Example template structure:
```json
{
  "template_id": "multi_element_reel",
  "name": "Flexible Multi-Element Reel",
  "description": "Base structure with dynamic element injection",
  "output": {
    "resolution": {
      "width": 1080,
      "height": 1920
    },
    "frame_rate": 30,
    "format": "mp4",
    "background_color": "#000000"
  },
  "defaults": {
    "video": {
      "transform": {
        "scale": 1.5,
        "position": { "x": 0, "y": 0 },
        "opacity": 1.0
      },
      "audio": true
    },
    "image": {
      "transform": {
        "scale": 0.5,
        "position": { "x": 100, "y": 100 }
      }
    },
    "text": {
      "transform": {
        "position": { "x": "center", "y": 200 }
      },
      "style": {
        "font_family": "Arial",
        "font_size": 92,
        "color": "white",
        "background_color": "rgba(0,0,0,0.3)",
        "alignment": "center"
      }
    }
  }
}
```

## Template System

### How Templates Work

Templates provide a way to define default styles, layouts, and behaviors for video elements. When you use the `/template-clip` endpoint, your elements are merged with the template defaults, giving you a consistent look without having to specify every property.

### Template Structure

A template includes:
- **Output settings**: Resolution, frame rate, background color, etc.
- **Element defaults**: Default properties for each element type (video, image, text, audio)

### Merging Logic

When you submit elements via the `/template-clip` endpoint:

1. Each element is merged with the corresponding template defaults
2. Properties you specify override the template defaults
3. Properties you omit will use the template defaults

### Special Properties

The template system supports special shorthand properties that make it easier to create videos. These properties are processed automatically and converted to their standard format.

#### Available Special Properties

##### Position Shorthand

Instead of specifying the full transform with x and y coordinates, you can use the `position` shorthand:

```json
{
  "type": "text",
  "text": "Hello World",
  "timeline": { "start": 0, "duration": 5 },
  "position": "center"  // Special property that sets both x and y to "center"
}
```

This is equivalent to:

```json
{
  "type": "text",
  "text": "Hello World",
  "timeline": { "start": 0, "duration": 5 },
  "transform": {
    "position": {
      "x": "center",
      "y": "center"
    }
  }
}
```

Available position presets:
- Basic positions: `"center"`, `"top"`, `"bottom"`, `"left"`, `"right"`
- Corner positions: `"top-left"`, `"top-right"`, `"bottom-left"`, `"bottom-right"`
- Mid positions: `"mid-top"`, `"mid-bottom"`

##### Size Shorthand

Instead of specifying a scale transform, you can use the `size` shorthand:

```json
{
  "type": "image",
  "source": "https://example.com/logo.png",
  "timeline": { "start": 0, "duration": 5 },
  "size": "small"  // Special property that sets transform.scale to 0.5
}
```

This is equivalent to:

```json
{
  "type": "image",
  "source": "https://example.com/logo.png",
  "timeline": { "start": 0, "duration": 5 },
  "transform": {
    "scale": 0.5
  }
}
```

Available size presets:
- `"tiny"`: scale = 0.25
- `"small"`: scale = 0.5
- `"medium"`: scale = 1.0 (original size)
- `"large"`: scale = 1.5
- `"huge"`: scale = 2.0

You can also specify a numeric value directly:

```json
{
  "type": "image",
  "source": "https://example.com/logo.png",
  "timeline": { "start": 0, "duration": 5 },
  "size": 0.75  // Sets transform.scale to 0.75
}
```

#### Extending Special Properties

The special properties system is designed to be extensible. New special properties can be added by:

1. Adding the property to the `Element` model in `app/models/template_clip.py`
2. Creating a handler function in the `SpecialProperties` class
3. Registering the handler in the `HANDLERS` dictionary

This allows for easy addition of new shorthand properties without changing the core logic of the template system.

### Example: Using Template with Special Properties

When using a template, you can combine multiple special properties for concise element definitions:

```json
{
  "template_id": "multi_element_reel",
  "elements": [
    {
      "type": "video",
      "source": "https://example.com/video.mp4",
      "timeline": {
        "start": 0,
        "duration": 5
      }
    },
    {
      "type": "image",
      "source": "https://example.com/logo.png",
      "timeline": {
        "start": 0,
        "duration": 5
      },
      "position": "top-right",
      "size": "small"
    },
    {
      "type": "text",
      "text": "Amazing Views",
      "timeline": {
        "start": 0,
        "duration": 5
      },
      "position": "bottom"
    }
  ]
}
```

## Development

### Project Structure
```
merclip-api/
├── app/
│   ├── models/
│   │   ├── video.py      # Pydantic models for request/response
│   │   └── template_clip.py  # Models for template-based requests
│   ├── services/
│   │   └── ffmpeg.py     # FFmpeg command generation and job management
│   ├── routers/
│   │   ├── clips.py      # Regular clip endpoints
│   │   └── template_clip.py  # Template-based clip endpoints
│   ├── static/
│   │   └── jobs/         # Output directory for rendered videos
│   └── main.py           # FastAPI application
├── templates/            # Template definitions
├── jobs/                # Temporary storage for job files
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

### Running the Development Server
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### API Documentation
Once the server is running, you can access:
- Interactive API docs: `http://localhost:8000/docs`
- Alternative API docs: `http://localhost:8000/redoc`

## License

MIT License 