import os
import platform
import signal
import time
import keyboard
import pygame
import time
import threading
import argparse
import cv2 
from PIL import Image
import concurrent.futures
import numpy as np

from image_window import VideoStreamWithAnnotations
from webserv import CustomHTTPRequestHandler, run_server2, set_dialog_file, signal_handler
from thread_safe import shared_data_put_data, shared_data_put_line
from process_frames import FrameProcessor
#from image_window import ImageWindow

# Detect the operating system
os_name = platform.system()
#reader = easyocr.Reader(['en']) #(['ja', 'en']) 

dialogues = {}


frameProcessor =  FrameProcessor()
last_played = -1
show_image_screen = False 
video_stream = None

def format_filename(number):
    # Format the number with leading zeros to ensure it's four digits
    number_padded = f"{number:04d}"

    # Create the file name using the padded number
    file_name = f"ff4_v1_prologue_{number_padded}.mp3"

    return file_name

def play_audio(filename):
    global lang
    print(f"output_en_elevenlabs/{filename}")
    # Initialize the mixer module
    pygame.mixer.init()
    
    # Load the MP3 file
    pygame.mixer.music.load(f"output_v2_{frameProcessor.lang}_elevenlabs/{filename}")
    
    # Play the music
    pygame.mixer.music.play()
    
    # Wait for the music to finish playing
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)  # Wait a bit for the music to finish

# Function to wrap your play_mp3 for threading
def play_audio_threaded(filename):
    # Create a thread targeting the play_mp3 function
    thread = threading.Thread(target=play_audio, args=(filename,))
    thread.start()  # Start the thread


previous_image = Image.new('RGB', (100, 100), (255, 255, 255))

if os_name == 'Windows':
    # Import Windows-specific module
    from windows_screenshot import find_window_id, capture_window_to_file
elif os_name == 'Darwin':
    # Import macOS-specific module
    from osx_screenshot import find_window_id, capture_window_to_file
elif os_name == 'Linux':
    # Import Linux-specific module
    from wsl_screenshot import find_window_id, capture_window_to_file
else:
    raise Exception(f"Unsupported OS: {os_name}")



def process_video(video_path):
    global frameProcessor  
    # Open the video file
    cap = cv2.VideoCapture(video_path)
    
    fps = cap.get(cv2.CAP_PROP_FPS)  # Get the frames per second of the video
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break  # Exit the loop if we've reached the end of the video

        # Process one frame per second (approximately)
        if frame_count % int(fps) == 0:
            # Convert the frame (which is in BGR format) to RGB format for PIL
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            
            # Save to disk
            pil_image.save("window_capture.jpg")
            print(f"Frame at {frame_count//fps} seconds saved as debug.jpg")
            frameProcessor.run_image(pil_image)
        
        frame_count += 1

    cap.release()  # Release the video capture object

def process_video_threaded(video_path, max_workers=10):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)  # Frames per second of the video
    frame_count = 0
    global frameProcessor
    
    # Use ThreadPoolExecutor to manage concurrency
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break  # Exit the loop if we've reached the end of the video

            # Process one frame per second (approximately)
            if frame_count % int(fps) == 0:
                # Convert the frame (which is in BGR format) to RGB format for PIL
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                
                #TODO need to bundle like 10 frames together, cause the previous image check isnt working threaded

                # Submit the frame for processing in a separate thread
                future = executor.submit(frameProcessor.process_frame, pil_image, frame_count, fps)
                futures.append(future)
            
            frame_count += 1
        
        # Wait for all futures to complete processing
        for future in concurrent.futures.as_completed(futures):
            # You can check for exceptions if needed and handle them
            pass

    cap.release()  # Release the video capture object

def process_screenshot(img):
    global last_played
    global frameProcessor
    global dialogues

    closest_match, previous_image, highlighted_image, annotations = frameProcessor.run_image(img)
    print(f"Closest match: {closest_match}")

    if closest_match != None and closest_match != last_played:
        start_time = time.time() # Record the start time
        play_audio_threaded(format_filename(closest_match))
        end_time = time.time()
        print(f"Audio Time taken: {end_time - start_time} seconds")
        last_played = closest_match
        set_annotation_text(annotations)
        
def timed_action_screencapture():
    print("Action triggered by timer")

    window_name = "RetroArch"  # Adjust this to the target window's name
    file_path = os.path.expanduser("window_capture.jpg")  # Save location
    window_id = find_window_id(window_name)
    if window_id:
        img = capture_window_to_file(window_id, file_path)
        process_screenshot(img)

    else:
        print(f"No window found with name containing '{window_name}'.")
        shared_data_put_data(f"No window found with name containing '{window_name}'.")

def set_annotation_text(annotations):
    video_stream.set_annotations(annotations)

def process_screenshots():
    while True:
        timed_action_screencapture()
        print("timed_action_screencapture")
        time.sleep(1)  # Wait for 1 second

def process_cv2_screenshots():
    global video_stream
    print(video_stream)
    while True:
        frame = video_stream.get_latest_frame()
        if frame is not None:
            print("Background task accessing the latest frame...")
            process_screenshot(frame)
            time.sleep(1)  # Wait for 1 second

def main():
    global dialogues
    global dialog_file_path
    global lang
    global frameProcessor
    global show_image_screen
    global video_stream

    #setup_screen()

    print("Press ESC to exit...")
    parser = argparse.ArgumentParser(description="Process a video or do a screencapture.")
    parser.add_argument('-v', '--video', type=str, help="Path to the video file to process.")
    parser.add_argument('-t', '--threads', type=int, default=10, help="Max threads for concurrent processing. Default is 10.")
    parser.add_argument('-w', '--webserver',  action='store_true', help="Enable Webserver")
    parser.add_argument('-jp', '--japanese',  action='store_true', help="Enable Japanese")
    parser.add_argument('-is', '--show_image_screen',  action='store_true', help="Show image screen")

    

    args = parser.parse_args()
    if args.japanese:
        set_dialog_file("dialogues_jp_web.json")
        lang = "jp"
        frameProcessor =  frameProcessor(lang) 

    if args.webserver:
        server_thread = threading.Thread(target=run_server2, args=(8000, ""), daemon=True)
        server_thread.start()
        signal.signal(signal.SIGINT, signal_handler)


        # Main thread: Put data into the shared queue
        shared_data_put_data("Hello from the main thread!")
        shared_data_put_line(0)


    if args.video:
        callback = process_video(args.video) #TODO this wont work yet, need a lambda or something
        #process_video_threaded(args.video)

    if args.show_image_screen:
        video_stream = VideoStreamWithAnnotations(background_task=process_cv2_screenshots)
        try:
            video_stream.run_ss()
        finally:
            video_stream.stop()
    else:
        process_screenshots()


if __name__ == "__main__":
    main()