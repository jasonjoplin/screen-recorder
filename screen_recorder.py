import cv2
import numpy as np
import pyautogui
import threading
import time
import os
import sounddevice as sd
import soundfile as sf
from datetime import datetime
import customtkinter as ctk
from PIL import Image
import queue
import torch
import subprocess
import traceback
from version_control import VersionControl, get_version

class ScreenRecorder:
    def __init__(self):
        self.recording = False
        self.paused = False
        self.total_pause_duration = 0
        self.current_chunk = 0
        self.custom_filename = None
        self.preview_callback = None
        self.volume_callback = None
        self.screen_thread = None
        self.audio_stream = None
        self.audio_frames = []
        self.current_video_writer = None
        self.current_audio_file = None
        self.last_recording = None
        self.selected_mic_id = None
        self.use_gpu = False
        
        # Set up output directory
        self.output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recordings")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize cursor
        self.cursor_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cursors")
        os.makedirs(self.cursor_dir, exist_ok=True)
        self.cursor_image = None
        self.cursor_size = (32, 32)
        self.create_default_cursor()
        self.load_cursor("default")  # Load default cursor immediately
        
        # Set up output directory
        self.output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recordings")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize cursor
        self.cursor_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cursors")
        os.makedirs(self.cursor_dir, exist_ok=True)
        self.cursor_image = None
        self.cursor_size = (32, 32)
        self.create_default_cursor()

    def create_default_cursor(self):
        cursor_path = os.path.join(self.cursor_dir, "default.png")
        if not os.path.exists(cursor_path):
            # Create a simple arrow cursor
            cursor = np.zeros((32, 32, 4), dtype=np.uint8)
            # Draw white arrow with black border
            points = np.array([[0,0], [0,16], [12,12]], dtype=np.int32).reshape((-1,1,2))
            # Draw fill
            mask = np.zeros((32, 32), dtype=np.uint8)
            cv2.fillPoly(mask, [points], 255)
            cursor[mask > 0] = [255, 255, 255, 255]
            # Draw border
            cv2.polylines(cursor, [points], True, (0,0,0,255), 1)
            cv2.imwrite(cursor_path, cursor)

    def load_cursor(self, cursor_name):
        cursor_path = os.path.join(self.cursor_dir, f"{cursor_name}.png")
        if os.path.exists(cursor_path):
            cursor_img = cv2.imread(cursor_path, cv2.IMREAD_UNCHANGED)
            self.cursor_image = cv2.resize(cursor_img, self.cursor_size)
        else:
            print(f"Cursor {cursor_name} not found, using default")
            self.create_default_cursor()
            self.load_cursor("default")

    def get_available_cursors(self):
        cursors = []
        for file in os.listdir(self.cursor_dir):
            if file.endswith('.png'):
                cursors.append(os.path.splitext(file)[0])
        return cursors

    def set_preview_callback(self, callback):
        print("Setting preview callback")
        self.preview_callback = callback

    def set_volume_callback(self, callback):
        self.volume_callback = callback

    def start_recording(self):
        if self.recording:
            print("Recording already in progress")
            return
            
        try:
            print("Starting recording...")
            self.recording = True
            self.paused = False
            self.total_pause_duration = 0
            
            # Get screen size
            screen_size = pyautogui.size()
            print(f"Screen size: {screen_size.width}x{screen_size.height}")
            
            # Generate output filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = self.custom_filename if self.custom_filename else timestamp
            video_filename = os.path.join(self.output_dir, f"{base_filename}_chunk{self.current_chunk}.mp4")
            print(f"Video filename: {video_filename}")
            
            # Initialize video writer
            print("Initializing video writer...")
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.current_video_writer = cv2.VideoWriter(
                video_filename,
                fourcc,
                30.0,
                (screen_size.width, screen_size.height)
            )
            print("Video writer initialized successfully")
            
            # Initialize audio recording
            print("Initializing audio recording...")
            if self.selected_mic_id is not None:
                audio_filename = os.path.join(self.output_dir, f"{base_filename}_chunk{self.current_chunk}.wav")
                self.current_audio_file = audio_filename
                self.audio_frames = []
                self.audio_stream = sd.InputStream(
                    device=self.selected_mic_id,
                    channels=2,
                    callback=self._audio_callback,
                    samplerate=44100
                )
                self.audio_stream.start()
                print("Audio recording initialized")
            
            # Start recording thread
            print("Starting recording thread...")
            self.screen_thread = threading.Thread(target=self._record_screen)
            self.screen_thread.daemon = True  # Make thread daemon so it exits when main program exits
            self.screen_thread.start()
            print("Recording thread started")
            
        except Exception as e:
            print(f"Error starting recording: {str(e)}")
            traceback.print_exc()
            self.recording = False
            raise

    def _record_screen(self):
        frame_time = 1.0 / 30.0  # Target 30 FPS
        next_frame_time = time.time()
        
        try:
            while self.recording:
                if not self.paused:
                    current_time = time.time()
                    
                    if current_time >= next_frame_time:
                        # Capture screen
                        screenshot = pyautogui.screenshot()
                        frame = np.array(screenshot)
                        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                        
                        # Get cursor position and overlay cursor
                        x, y = pyautogui.position()
                        frame = self.overlay_cursor(frame, x, y)
                        
                        # Write frame
                        if self.current_video_writer is not None:
                            self.current_video_writer.write(frame)
                        
                        # Update preview if callback is set
                        if self.preview_callback:
                            try:
                                self.preview_callback(frame)
                            except Exception as e:
                                print(f"Preview callback error: {str(e)}")
                        
                        # Calculate next frame time
                        next_frame_time = current_time + frame_time
                    
                    time.sleep(max(0, next_frame_time - time.time()))  # Sleep only if needed
                else:
                    time.sleep(0.1)  # Longer sleep while paused
            
        except Exception as e:
            print(f"Error in screen recording: {str(e)}")
            traceback.print_exc()
        finally:
            self.recording = False

    def overlay_cursor(self, frame, x, y):
        if self.cursor_image is None or frame is None:
            return frame
            
        try:
            h, w = self.cursor_image.shape[:2]
            
            # Ensure coordinates are within frame bounds
            if x >= 0 and y >= 0 and x < frame.shape[1] and y < frame.shape[0]:
                # Calculate overlay boundaries
                y1, y2 = max(0, y), min(frame.shape[0], y + h)
                x1, x2 = max(0, x), min(frame.shape[1], x + w)
                
                if y2 > y1 and x2 > x1:  # Only proceed if we have valid dimensions
                    # Adjust cursor image crop coordinates
                    cursor_y1 = max(0, -y)
                    cursor_x1 = max(0, -x)
                    cursor_y2 = cursor_y1 + (y2 - y1)
                    cursor_x2 = cursor_x1 + (x2 - x1)
                    
                    # Create alpha mask
                    alpha = self.cursor_image[cursor_y1:cursor_y2, cursor_x1:cursor_x2, 3:4].astype(float) / 255.0
                    
                    # Get cursor RGB
                    cursor_rgb = self.cursor_image[cursor_y1:cursor_y2, cursor_x1:cursor_x2, :3]
                    
                    # Extract frame region
                    frame_region = frame[y1:y2, x1:x2]
                    
                    # Blend cursor with frame
                    blended = frame_region * (1 - alpha) + cursor_rgb * alpha
                    
                    # Update frame region
                    frame[y1:y2, x1:x2] = blended.astype(np.uint8)
            
        except Exception as e:
            print(f"Error overlaying cursor: {str(e)}")
            traceback.print_exc()
        
        return frame

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Audio status: {status}")
        if not self.paused:
            self.audio_frames.append(indata.copy())
            # Calculate volume for meter
            volume = np.linalg.norm(indata) * 10
            if self.volume_callback:
                self.volume_callback(min(1.0, volume))

    def stop_recording(self):
        try:
            print("Stopping recording...")
            self.recording = False
            
            if self.screen_thread and self.screen_thread.is_alive():
                print("Waiting for recording thread to finish...")
                self.screen_thread.join(timeout=2.0)  # Wait up to 2 seconds
            
            try:
                if self.current_video_writer:
                    self.current_video_writer.release()
                    print("Video writer released")
            except Exception as e:
                print(f"Error releasing video writer: {str(e)}")
                traceback.print_exc()
            
            try:
                if self.audio_stream:
                    self.audio_stream.stop()
                    self.audio_stream.close()
                    self._save_audio()
                    print("Audio stream closed and saved")
            except Exception as e:
                print(f"Error stopping audio stream: {str(e)}")
                traceback.print_exc()
            
            # Set last recording to video file first in case combining fails
            if hasattr(self, 'custom_filename'):
                video_path = os.path.join(self.output_dir, f"{self.custom_filename}_chunk{self.current_chunk}.mp4")
                if os.path.exists(video_path):
                    self.last_recording = video_path
            
            # Try to combine files if we have both audio and video
            try:
                self._combine_audio_video()
                print("Audio and video combined")
            except Exception as e:
                print(f"Error combining audio and video: {str(e)}")
                traceback.print_exc()
                # Keep the separate video and audio files if combining fails
            
            print("Recording stopped successfully")
            
        except Exception as e:
            print(f"Error in stop_recording: {str(e)}")
            traceback.print_exc()
        finally:
            # Clean up resources
            self.current_video_writer = None
            self.audio_stream = None
            self.audio_frames = []

    def _save_audio(self):
        try:
            if self.audio_frames and self.current_audio_file:
                print("Saving audio file...")
                audio_data = np.concatenate(self.audio_frames, axis=0)
                sf.write(self.current_audio_file, audio_data, 44100)
                print("Audio file saved successfully")
        except Exception as e:
            print(f"Error saving audio: {str(e)}")
            traceback.print_exc()
        finally:
            self.audio_frames = []

    def _combine_audio_video(self):
        try:
            if not hasattr(self, 'custom_filename') or not self.custom_filename:
                print("No filename set for combining files")
                return
            
            video_path = os.path.join(self.output_dir, f"{self.custom_filename}_chunk{self.current_chunk}.mp4")
            final_path = os.path.join(self.output_dir, f"{self.custom_filename}_final.mp4")
            
            if not os.path.exists(video_path):
                print(f"Video file not found: {video_path}")
                return
                
            # Check if ffmpeg is available
            try:
                subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            except FileNotFoundError:
                print("ffmpeg not found. Skipping audio-video combination.")
                self.last_recording = video_path
                return
            
            print(f"Combining files to: {final_path}")
            
            if self.current_audio_file and os.path.exists(self.current_audio_file):
                command = [
                    'ffmpeg', '-y',
                    '-i', video_path,
                    '-i', self.current_audio_file,
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    final_path
                ]
                print("Running ffmpeg with audio...")
            else:
                command = [
                    'ffmpeg', '-y',
                    '-i', video_path,
                    '-c:v', 'copy',
                    final_path
                ]
                print("Running ffmpeg without audio...")
            
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"FFmpeg error: {result.stderr}")
                self.last_recording = video_path  # Keep original video if ffmpeg fails
                return
            
            # Clean up temporary files only if combining was successful
            if os.path.exists(final_path):
                print("Cleaning up temporary files...")
                try:
                    if os.path.exists(video_path):
                        os.remove(video_path)
                    if self.current_audio_file and os.path.exists(self.current_audio_file):
                        os.remove(self.current_audio_file)
                except Exception as e:
                    print(f"Error cleaning up temporary files: {str(e)}")
                self.last_recording = final_path
                print("Cleanup completed")
            else:
                print("Final file not created, keeping temporary files")
                self.last_recording = video_path
            
        except Exception as e:
            print(f"Error combining audio and video: {str(e)}")
            traceback.print_exc()
            self.last_recording = video_path  # Use the video file if combining fails

    def get_available_mics(self):
        devices = sd.query_devices()
        mics = []
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                mics.append({
                    'id': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'default': device.get('default_input', False)
                })
        return mics

    def set_microphone(self, device_id):
        self.selected_mic_id = device_id

    def set_filename(self, filename):
        self.custom_filename = filename

class RecorderGUI:
    def __init__(self):
        self.recorder = ScreenRecorder()
        self.version_control = VersionControl()
        
        self.window = ctk.CTk()
        self.window.title(f"Screen Recorder v{get_version()}")
        self.window.geometry("1200x700")
        self.window.resizable(False, False)
        
        # Configure grid weights
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_columnconfigure(1, weight=0)  # Control panel
        self.window.grid_rowconfigure(0, weight=1)
        
        # Create main frame for preview
        self.preview_frame = ctk.CTkFrame(self.window)
        self.preview_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Create preview canvas with fixed size
        self.preview_canvas = ctk.CTkCanvas(
            self.preview_frame,
            width=640,
            height=360,
            bg='black'
        )
        self.preview_canvas.pack(expand=True, padx=10, pady=10)
        
        # Create control panel frame with fixed width
        self.control_panel = ctk.CTkFrame(self.window, width=300)
        self.control_panel.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.control_panel.grid_propagate(False)  # Prevent frame from shrinking
        
        # Theme toggle
        self.theme_button = ctk.CTkButton(
            self.control_panel,
            text="Toggle Theme",
            command=self.toggle_theme
        )
        self.theme_button.pack(pady=5)
        
        # Cursor selection
        self.cursor_frame = ctk.CTkFrame(self.control_panel)
        self.cursor_frame.pack(fill="x", padx=5, pady=5)
        
        self.cursor_label = ctk.CTkLabel(
            self.cursor_frame,
            text="Select Cursor:"
        )
        self.cursor_label.pack(pady=(5, 0))
        
        self.available_cursors = self.recorder.get_available_cursors()
        self.cursor_var = ctk.StringVar(value="default")
        self.cursor_menu = ctk.CTkOptionMenu(
            self.cursor_frame,
            values=self.available_cursors,
            variable=self.cursor_var,
            command=self.on_cursor_select,
            width=200
        )
        self.cursor_menu.pack(pady=5)
        
        # Custom cursor upload button
        self.upload_cursor_button = ctk.CTkButton(
            self.cursor_frame,
            text="Upload Custom Cursor",
            command=self.upload_custom_cursor
        )
        self.upload_cursor_button.pack(pady=5)
        
        # Microphone selection frame
        self.mic_frame = ctk.CTkFrame(self.control_panel)
        self.mic_frame.pack(fill="x", padx=5, pady=5)
        
        self.mic_label = ctk.CTkLabel(
            self.mic_frame,
            text="Select Microphone:"
        )
        self.mic_label.pack(pady=(5, 0))
        
        # Get available microphones
        self.available_mics = self.recorder.get_available_mics()
        self.mic_names = [f"{mic['name']}{' (Default)' if mic['default'] else ''}" for mic in self.available_mics]
        
        self.mic_var = ctk.StringVar(value=self.mic_names[0] if self.mic_names else "No microphones found")
        self.mic_menu = ctk.CTkOptionMenu(
            self.mic_frame,
            values=self.mic_names,
            variable=self.mic_var,
            command=self.on_mic_select,
            width=200
        )
        self.mic_menu.pack(pady=5)
        
        # Set initial microphone
        if self.available_mics:
            default_mic = next((mic for mic in self.available_mics if mic['default']), self.available_mics[0])
            self.recorder.set_microphone(default_mic['id'])
        
        # Filename input
        self.filename_label = ctk.CTkLabel(
            self.control_panel,
            text="Recording Name:"
        )
        self.filename_label.pack(pady=(10, 0))
        
        self.filename_entry = ctk.CTkEntry(
            self.control_panel,
            width=200
        )
        self.filename_entry.pack(pady=(5, 20))
        
        # Recording status frame
        self.status_frame = ctk.CTkFrame(self.control_panel)
        self.status_frame.pack(fill="x", padx=5, pady=5)
        
        # Recording indicator light
        self.indicator_canvas = ctk.CTkCanvas(
            self.status_frame,
            width=20,
            height=20,
            bg=self.window._apply_appearance_mode(ctk.ThemeManager.theme["CTkFrame"]["fg_color"]),
            highlightthickness=0
        )
        self.indicator_canvas.pack(side="left", padx=5)
        self.indicator_light = self.indicator_canvas.create_oval(5, 5, 15, 15, fill="gray")
        
        # Timer label
        self.timer_label = ctk.CTkLabel(
            self.status_frame,
            text="00:00:00",
            font=("Arial", 16)
        )
        self.timer_label.pack(side="left", padx=10)
        
        # Volume meter
        self.volume_frame = ctk.CTkFrame(self.control_panel)
        self.volume_frame.pack(fill="x", padx=5, pady=10)
        
        self.volume_label = ctk.CTkLabel(
            self.volume_frame,
            text="Volume Level"
        )
        self.volume_label.pack()
        
        self.volume_meter = ctk.CTkProgressBar(
            self.volume_frame,
            width=180,
            height=15,
            border_width=2,
            progress_color="green"
        )
        self.volume_meter.pack(pady=5)
        self.volume_meter.set(0)
        
        # Test Audio Button
        self.test_audio_button = ctk.CTkButton(
            self.volume_frame,
            text="Monitor",
            command=self.test_microphone,
            width=120
        )
        self.test_audio_button.pack(pady=5)
        
        # Start/Stop button
        self.start_button = ctk.CTkButton(
            self.control_panel,
            text="Start Recording",
            command=self.toggle_recording
        )
        self.start_button.pack(pady=20)
        
        # Pause/Resume button
        self.pause_button = ctk.CTkButton(
            self.control_panel,
            text="Pause",
            command=self.pause_resume_recording,
            state="disabled"
        )
        self.pause_button.pack(pady=5)
        
        self.status_label = ctk.CTkLabel(
            self.control_panel,
            text="Ready to record"
        )
        self.status_label.pack(pady=10)
        
        # Recordings frame (right side)
        self.list_frame = ctk.CTkFrame(self.window)
        self.list_frame.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        
        self.list_label = ctk.CTkLabel(
            self.list_frame,
            text="Last Recording:",
            font=("Arial", 14, "bold")
        )
        self.list_label.pack(pady=5)
        
        # Frame for the last recording
        self.last_recording_frame = ctk.CTkFrame(self.list_frame)
        self.last_recording_frame.pack(fill="x", padx=5, pady=5)
        
        # Label for the last recording (will be updated)
        self.last_recording_label = ctk.CTkLabel(
            self.last_recording_frame,
            text="No recordings yet",
            wraplength=200
        )
        self.last_recording_label.pack(pady=5)
        
        # Buttons frame
        self.buttons_frame = ctk.CTkFrame(self.list_frame)
        self.buttons_frame.pack(fill="x", padx=5, pady=5)
        
        # Open last recording button
        self.open_recording_button = ctk.CTkButton(
            self.buttons_frame,
            text="Open Recording",
            command=self.open_last_recording,
            state="disabled"
        )
        self.open_recording_button.pack(side="left", padx=2, pady=5)
        
        # Open folder button
        self.open_folder_button = ctk.CTkButton(
            self.buttons_frame,
            text="Open Folder",
            command=self.open_recordings_folder
        )
        self.open_folder_button.pack(side="right", padx=2, pady=5)
        
        # Add version control to the control panel
        self.version_frame = ctk.CTkFrame(self.control_panel)
        self.version_frame.pack(fill="x", padx=5, pady=5)
        
        self.version_label = ctk.CTkLabel(
            self.version_frame,
            text=f"Version: {get_version()}"
        )
        self.version_label.pack(side="left", padx=5)
        
        self.check_updates_button = ctk.CTkButton(
            self.version_frame,
            text="Check Updates",
            command=self.check_for_updates,
            width=100
        )
        self.check_updates_button.pack(side="right", padx=5)
        
        # Check for updates on startup
        self.window.after(1000, self.check_for_updates)
        
        self.recording_active = False
        self.start_time = None
        
        # Set up volume callback
        self.recorder.set_volume_callback(self.update_volume_meter)

    def update_timer(self):
        if self.recording_active and self.start_time:
            try:
                elapsed = time.time() - self.start_time - self.recorder.total_pause_duration
                hours = int(elapsed // 3600)
                minutes = int((elapsed % 3600) // 60)
                seconds = int(elapsed % 60)
                self.timer_label.configure(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                if self.recording_active:  # Only schedule next update if still recording
                    self.window.after(1000, self.update_timer)
            except Exception as e:
                print(f"Error updating timer: {str(e)}")

    def update_volume_meter(self, volume):
        self.volume_meter.set(volume / 100)

    def on_mic_select(self, choice):
        selected_index = self.mic_names.index(choice)
        selected_mic = self.available_mics[selected_index]
        self.recorder.set_microphone(selected_mic['id'])
        print(f"Selected microphone: {selected_mic['name']} (ID: {selected_mic['id']})")

    def on_cursor_select(self, choice):
        self.recorder.load_cursor(choice)

    def test_microphone(self):
        if not self.recording_active:
            self.test_audio_button.configure(text="Stop Monitoring")
            self.recording_active = True
            
            # Start a brief recording to test the microphone
            self.recorder.recording = True
            self.audio_test_thread = threading.Thread(target=self._run_audio_test)
            self.audio_test_thread.start()
        else:
            self.stop_mic_test()

    def stop_mic_test(self):
        self.recorder.recording = False
        self.recording_active = False
        self.test_audio_button.configure(text="Monitor")
        self.volume_meter.set(0)

    def _run_audio_test(self):
        try:
            with sd.InputStream(
                device=self.recorder.selected_mic_id,
                callback=self._test_audio_callback,
                channels=2,
                samplerate=44100,
                blocksize=1024  # Smaller blocksize for more frequent updates
            ):
                while self.recording_active:
                    time.sleep(0.1)
        except Exception as e:
            print(f"Audio test error: {e}")
        finally:
            self.stop_mic_test()

    def _test_audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        # Increase sensitivity and use RMS calculation
        volume_norm = np.sqrt(np.mean(indata**2)) * 100
        self.window.after(0, self.volume_meter.set, min(volume_norm, 1.0))

    def toggle_recording(self):
        try:
            if not self.recording_active:
                # Get filename from entry
                filename = self.filename_entry.get().strip()
                if filename:
                    self.recorder.custom_filename = filename
                
                # Start recording
                self.recorder.start_recording()
                self.recording_active = True  # Set recording active state
                
                # Update UI
                self.start_button.configure(text="Stop Recording")
                self.pause_button.configure(state="normal")
                self.status_label.configure(text="Recording...")
                self.indicator_canvas.itemconfig(self.indicator_light, fill="red")
                
                # Start timer
                self.start_time = time.time()
                self.window.after(0, self.update_timer)  # Start timer immediately
                
                # Update recording list
                self.update_last_recording()
                
            else:
                # Stop recording
                self.recording_active = False  # Set recording inactive first
                self.recorder.stop_recording()
                
                # Update UI
                self.start_button.configure(text="Start Recording")
                self.pause_button.configure(state="disabled")
                self.status_label.configure(text="Ready to record")
                self.indicator_canvas.itemconfig(self.indicator_light, fill="gray")
                
                # Reset timer
                self.timer_label.configure(text="00:00:00")
                self.start_time = None
                
                # Update recording list
                self.update_last_recording()
                
        except Exception as e:
            print(f"Error in toggle_recording: {str(e)}")
            traceback.print_exc()
            # Try to cleanup in case of error
            self.recording_active = False
            self.start_button.configure(text="Start Recording")
            self.pause_button.configure(state="disabled")
            self.status_label.configure(text="Error occurred")
            self.indicator_canvas.itemconfig(self.indicator_light, fill="gray")

    def toggle_theme(self):
        if self.current_theme == "dark":
            ctk.set_appearance_mode("light")
            self.current_theme = "light"
        else:
            ctk.set_appearance_mode("dark")
            self.current_theme = "dark"

    def upload_custom_cursor(self):
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            filetypes=[("PNG files", "*.png")]
        )
        if file_path:
            cursor_name = os.path.splitext(os.path.basename(file_path))[0]
            new_path = os.path.join(self.recorder.cursor_dir, f"{cursor_name}.png")
            import shutil
            shutil.copy2(file_path, new_path)
            
            # Refresh cursor list
            self.available_cursors = self.recorder.get_available_cursors()
            self.cursor_menu.configure(values=self.available_cursors)
            self.cursor_var.set(cursor_name)
            self.recorder.load_cursor(cursor_name)

    def update_preview(self, frame):
        if frame is not None and isinstance(frame, np.ndarray):
            try:
                # Convert frame to RGB for PIL
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(frame_rgb)
                
                # Create CTkImage with specific size
                photo = ctk.CTkImage(
                    light_image=image,
                    dark_image=image,
                    size=(640, 360)
                )
                
                # Update canvas
                self.preview_canvas.delete("all")
                self.preview_canvas.create_image(
                    320,  # Center x
                    180,  # Center y
                    image=photo,
                    anchor="center"
                )
                self.preview_canvas._image = photo  # Keep reference
                
            except Exception as e:
                print(f"Preview update error: {str(e)}")
                traceback.print_exc()

    def update_last_recording(self):
        if self.recorder.last_recording:
            self.last_recording_label.configure(text=self.recorder.last_recording)
            self.open_recording_button.configure(state="normal")

    def open_last_recording(self):
        if self.recorder.last_recording:
            import os
            os.startfile(self.recorder.last_recording)

    def open_recordings_folder(self):
        import os
        os.startfile(self.recorder.output_dir)

    def pause_resume_recording(self):
        if self.recorder.paused:
            self.recorder.paused = False
            self.pause_button.configure(text="Pause")
        else:
            self.recorder.paused = True
            self.pause_button.configure(text="Resume")

    def check_for_updates(self):
        """Check for available updates and prompt user."""
        if self.version_control.check_for_updates():
            update_info = self.version_control.get_update_info()
            response = ctk.CTkMessagebox(
                title="Update Available",
                message=f"A new version ({update_info['latest_version']}) is available.\nWould you like to update now?",
                icon="info",
                option_1="Yes",
                option_2="No"
            )
            
            if response.get() == "Yes":
                success, message = self.version_control.download_update()
                if not success:
                    ctk.CTkMessagebox(
                        title="Update Failed",
                        message=message,
                        icon="error"
                    )

if __name__ == "__main__":
    app = RecorderGUI()
    app.window.mainloop()