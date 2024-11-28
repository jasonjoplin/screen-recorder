# Screen Recorder

A feature-rich screen recording application built with Python, offering high-quality screen capture with audio recording capabilities and a modern user interface.

## Features

- **Screen Recording**
  - Full screen capture with cursor overlay
  - Audio recording from selected microphone
  - Pause/Resume functionality
  - Custom recording names
  - Live preview during recording

- **User Interface**
  - Modern CustomTkinter-based GUI
  - Dark/Light theme toggle
  - Real-time volume meter
  - Recording timer
  - Quick access to recent recordings

- **Customization**
  - Custom cursor support
  - Microphone selection
  - Recording name customization

## Requirements

- Python 3.8 or higher
- Dependencies listed in `requirements.txt`

## Installation

1. Clone the repository:
```bash
git clone [your-repository-url]
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
python screen_recorder.py
```

2. Select your preferred microphone from the dropdown menu
3. (Optional) Customize the cursor or upload your own
4. (Optional) Enter a custom name for your recording
5. Click "Start Recording" to begin
6. Use the Pause/Resume button to temporarily halt recording
7. Click "Stop Recording" to finish

## Controls

- **Start/Stop**: Main recording control
- **Pause/Resume**: Temporarily halt recording without stopping
- **Monitor**: Test microphone input
- **Toggle Theme**: Switch between light and dark modes
- **Upload Custom Cursor**: Add your own cursor image (PNG format)

## File Locations

- Recordings are saved in the `recordings` folder
- Custom cursors are stored in the `cursors` folder

## Version History

### Current Version: 1.0.0
- Initial release with core functionality

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
