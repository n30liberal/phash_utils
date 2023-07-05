import tkinter as tk
from PIL import ImageTk, Image
import argparse
import screeninfo
import subprocess
import cv2
import shutil
from pathlib import Path
from user_config import extracted_frames_path, collections_directory


def extract_first_frame(file_path):
    video_path = Path(file_path)

    relative_path = video_path.relative_to(collections_directory)

    # Create the target directory structure inside the trash directory
    target_dir = extracted_frames_path / relative_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    # Open the video file
    video = cv2.VideoCapture(str(video_path))

    # Read the first frame
    success, frame = video.read()

    if success:
        # Build the output file path
        output_file = target_dir / f"{video_path.stem}.jpg"

        # Save the first frame as an image
        cv2.imwrite(str(output_file), frame)

        # Release the video capture object
        video.release()

        # Return the file path to the extracted frame
        return str(output_file)

    else:
        # Return None if unable to read the first frame
        return None


def clean_leftover_frames():
    # look through the extracted_frames_path directory
    # and remove all files and directories, empty or not

    # THIS DELETES EVERYTHING INSIDE THE EXTRACTED FRAMES DIRECTORY
    for file_path in extracted_frames_path.glob("**/*"):
        if file_path.is_dir():
            shutil.rmtree(file_path)


def kill_program_by_window_title(window_title):
    command = f"sudo powershell.exe \"Get-Process | Where-Object {{ $_.MainWindowTitle -eq '{window_title}' }} | ForEach-Object {{ $_.Kill() }}\""
    subprocess.run(command, shell=True)


kill_program_by_window_title("Comparison")
clean_leftover_frames()


def copy_to_clipboard(file_name):
    # Implement your copy to clipboard functionality here
    pass


def add_to_blacklist(phash):
    # Implement the logic to add the phash to the blacklist
    pass


parser = argparse.ArgumentParser(description="Compare two files")
parser.add_argument(
    "--biggest_file_phash",
    type=str,
    help="The phash of the biggest file",
    required=True,
)
parser.add_argument(
    "--biggest_file_id", type=int, help="The file id of the biggest file", required=True
)
parser.add_argument(
    "--biggest_file_scene_id",
    type=int,
    help="The scene id of the biggest file",
    required=True,
)
parser.add_argument(
    "--biggest_file_path",
    type=str,
    help="The file path of the biggest file",
    required=True,
)
parser.add_argument(
    "--biggest_file_media_type",
    type=str,
    help="The media type of the biggest file",
    required=True,
)
parser.add_argument(
    "--biggest_file_size",
    type=int,
    help="The file size of the biggest file",
    required=True,
)

parser.add_argument(
    "--smallest_file_phash",
    type=str,
    help="The phash of the smallest file",
    required=True,
)
parser.add_argument(
    "--smallest_file_id",
    type=int,
    help="The file id of the smallest file",
    required=True,
)
parser.add_argument(
    "--smallest_file_scene_id",
    type=int,
    help="The scene id of the smallest file",
    required=True,
)
parser.add_argument(
    "--smallest_file_path",
    type=str,
    help="The file path of the smallest file",
    required=True,
)
parser.add_argument(
    "--smallest_file_media_type",
    type=str,
    help="The media type of the smallest file",
    required=True,
)
parser.add_argument(
    "--smallest_file_size",
    type=int,
    help="The file size of the smallest file",
    required=True,
)


args = parser.parse_args()


# if either the media_types are video, we need to change the file_path to extract(path)
if args.biggest_file_media_type == "video":
    args.biggest_file_path = extract_first_frame(args.biggest_file_path)

if args.smallest_file_media_type == "video":
    args.smallest_file_path = extract_first_frame(args.smallest_file_path)


root = tk.Tk()
root.title("Comparison")
root.configure(background="#000")
root.resizable(False, False)

# start the window in the center of the screen
window_width = 875
window_height = 860

# Specify the index of the monitor you want to use (e.g., 0 for the primary monitor, 1 for the second monitor, etc.)
monitor_index = 1

# Update the window to get the correct screen dimensions
root.update_idletasks()

# Get the screen dimensions of the specified monitor
monitors = screeninfo.get_monitors()

if monitor_index < len(monitors):
    monitor = monitors[monitor_index]
else:
    monitor = monitors[0]  # Use the primary monitor as a fallback

# Calculate the center coordinates with an offset for window decorations
x_coordinate = int((monitor.width / 2) - (window_width / 2))
y_coordinate = int((monitor.height / 2) - (window_height / 2))

# Offset the coordinates by the monitor's top-left corner
x_coordinate += monitor.x
y_coordinate += monitor.y

root.geometry(
    "{}x{}+{}+{}".format(window_width, window_height, x_coordinate, y_coordinate)
)

info_label = tk.Label(
    root,
    text=args.biggest_file_phash,
    font=("bold", 30),
    fg="#fff",
    bg="#000",
    cursor="hand2",
)
info_label.grid(row=0, column=0, pady=20)
info_label.bind("<Button-1>", lambda e: add_to_blacklist())

media_container = tk.Frame(root, width=1000, height=700, bg="#000")
media_container.grid(row=1, column=0, pady=0)

left_frame = tk.Frame(media_container, bg="#000")
left_frame.grid(row=0, column=0, padx=20)

left_label = tk.Label(
    left_frame,
    text="Biggest File",
    font=("bold", 12),
    fg="#fff",
    bg="#000",
    cursor="hand2",
)
left_label.pack(pady=10)
left_label.bind("<Button-1>", lambda e: copy_to_clipboard("Biggest File"))

left_image = Image.open(args.biggest_file_path)
left_image.thumbnail((500, 700))  # Resize the image while maintaining aspect ratio
left_image = ImageTk.PhotoImage(left_image)
left_image_label = tk.Label(left_frame, image=left_image, bg="#000")
left_image_label.pack()

right_frame = tk.Frame(media_container, bg="#000")
right_frame.grid(row=0, column=1, padx=20)

right_label = tk.Label(
    right_frame,
    text="File To Remove",
    font=("bold", 12),
    fg="#fff",
    bg="#000",
    cursor="hand2",
)
right_label.pack(pady=10)
right_label.bind("<Button-1>", lambda e: copy_to_clipboard("Smallest File"))

right_image = Image.open(args.smallest_file_path)
right_image.thumbnail((500, 700))  # Resize the image while maintaining aspect ratio
right_image = ImageTk.PhotoImage(right_image)
right_image_label = tk.Label(right_frame, image=right_image, bg="#000")
right_image_label.pack()

root.mainloop()
