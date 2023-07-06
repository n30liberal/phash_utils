import cv2
import json
import string
import argparse
import pyperclip
import screeninfo
import subprocess
import tkinter as tk
import pygetwindow as gw
import tkinter.messagebox as messagebox

from pathlib import Path
from PIL import ImageTk, Image
from user_config import blacklisted_phash_path
from user_config import readable_size, readable_duration
from user_config import extracted_frames_path, collections_directory


def copy_to_clipboard(file_name):
    pyperclip.copy(file_name)
    messagebox.showinfo("Copied Filename", f"Copied to clipboard.\n{file_name}")


def add_to_blacklist(phash):
    with open(blacklisted_phash_path, "a") as file:
        file.write(phash + "\n")
    messagebox.showinfo(
        "Blacklisted Phash", f"{phash}\n\nAdded to blacklist.", icon="warning"
    )


def extract_first_frame(file_path):
    video_path = Path(file_path)

    relative_path = video_path.relative_to(collections_directory)

    # Create the target directory structure inside the trash directory
    target_dir = extracted_frames_path / relative_path.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    video = cv2.VideoCapture(str(video_path))
    success, frame = video.read()

    def sanitize_filename(filename):
        valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        sanitized_filename = "".join(c for c in filename if c in valid_chars)
        return sanitized_filename

    if success:
        output_filename = sanitize_filename(video_path.stem)
        output_file = target_dir / f"{output_filename}.jpg"

        cv2.imwrite(str(output_file), frame)
        video.release()

        return str(output_file)

    else:
        return None


def kill_program_by_window_title(window_title):
    command = f"sudo powershell.exe \"Get-Process | Where-Object {{ $_.MainWindowTitle -eq '{window_title}' }} | ForEach-Object {{ $_.Kill() }}\""
    subprocess.run(command, shell=True)


def find_vscode_window(PartialWindowTitle):
    windows = gw.getWindowsWithTitle(PartialWindowTitle)
    if windows:
        vscode_window = windows[0]
        vscode_window.activate()
    else:
        print(f"No windows found with: {PartialWindowTitle}")


kill_program_by_window_title("file_comparison_gui.py")


parser = argparse.ArgumentParser(description="Compare two files")
parser.add_argument("--data", type=str, help="Data in JSON format", required=True)
args = parser.parse_args()
data = json.loads(args.data)


biggest_file_entry = data["biggest_file_entry"]
smaller_file_entry = data["smaller_file_entry"]

biggest_file_phash = biggest_file_entry["phash"]

biggest_file_entry_file_path = biggest_file_entry["file_path"]
smaller_file_entry_file_path = smaller_file_entry["file_path"]

biggest_file_entry_media_type = biggest_file_entry["media_type"]
smaller_file_entry_media_type = smaller_file_entry["media_type"]

biggest_file_entry_basename = biggest_file_entry["file_basename"]
smaller_file_entry_basename = smaller_file_entry["file_basename"]

biggest_file_entry_file_size = biggest_file_entry["file_size"]
smaller_file_entry_file_size = smaller_file_entry["file_size"]

biggest_file_entry_duration = biggest_file_entry["duration"] or 0
smaller_file_entry_duration = smaller_file_entry["duration"] or 0


# if either the media_types are video, we need to change the file_path to extract(path)
if biggest_file_entry_media_type == "video":
    biggest_file_entry_file_path = extract_first_frame(biggest_file_entry_file_path)

if smaller_file_entry_media_type == "video":
    smaller_file_entry_file_path = extract_first_frame(smaller_file_entry_file_path)


def main():
    root = tk.Tk()
    root.title("file_comparison_gui.py")
    root.configure(background="#000")
    root.resizable(False, False)
    root.wm_attributes("-topmost", True)  # Keep the window always on top

    # we gotta define these early so we can use them in the geometry
    left_image = Image.open(biggest_file_entry_file_path)
    left_image.thumbnail((500, 700))
    left_image = ImageTk.PhotoImage(left_image)

    right_image = Image.open(smaller_file_entry_file_path)
    right_image.thumbnail((500, 700))
    right_image = ImageTk.PhotoImage(right_image)

    # width should be left_image.width + right_image.width
    # height should be max(left_image.height, right_image.height)
    window_width = left_image.width() + right_image.width() + 8
    window_height = max(left_image.height(), right_image.height()) + 150

    # i prefer this on my second monitor
    monitor_index = 1

    root.update_idletasks()

    monitors = screeninfo.get_monitors()

    if monitor_index < len(monitors):
        monitor = monitors[monitor_index]
    else:
        monitor = monitors[0]  # Use the primary monitor as a fallback

    x_coordinate = int((monitor.width / 2) - (window_width / 2))
    y_coordinate = int((monitor.height / 2) - (window_height / 2))

    x_coordinate += monitor.x
    y_coordinate += monitor.y

    root.geometry(
        "{}x{}+{}+{}".format(window_width, window_height, x_coordinate, y_coordinate)
    )

    padding_label = tk.Label(root, bg="#000")
    padding_label.grid(row=0, column=0, pady=25)

    info_label = tk.Label(
        root,
        text=biggest_file_phash,
        font=("bold", 30),
        fg="#fff",
        bg="#000",
        cursor="hand2",
    )

    info_label.grid(row=0, column=0, pady=5)
    info_label.bind("<Button-1>", lambda e: add_to_blacklist(biggest_file_phash))

    media_container = tk.Frame(root, width=1000, height=700, bg="#000")
    media_container.grid(row=1, column=0, pady=0)

    left_frame = tk.Frame(media_container, bg="#000")
    left_frame.grid(row=0, column=0, padx=0)

    left_label = tk.Label(
        left_frame,
        text="Biggest File\nFile Size: {0}\nDuration: {1}".format(
            readable_size(biggest_file_entry_file_size),
            readable_duration(biggest_file_entry_duration),
        ),
        font=("bold", 12),
        fg="#fff",
        bg="#000",
        cursor="hand2",
    )

    left_label.config(font=("bold", 10), justify="center", anchor="w", padx=10)
    left_label.pack(pady=10)

    left_label.bind(
        "<Button-1>", lambda e: copy_to_clipboard(biggest_file_entry_basename)
    )

    left_image_label = tk.Label(left_frame, image=left_image, bg="#000")
    left_image_label.pack()

    right_frame = tk.Frame(media_container, bg="#000")
    right_frame.grid(row=0, column=1, padx=0)

    right_label = tk.Label(
        right_frame,
        text="Smaller File\nFile Size: {0}\nDuration: {1}".format(
            readable_size(smaller_file_entry_file_size),
            readable_duration(smaller_file_entry_duration),
        ),
        font=("bold", 12),
        fg="#fff",
        bg="#000",
        cursor="hand2",
    )
    right_label.config(font=("bold", 10), justify="center", anchor="w", padx=10)

    right_label.pack(pady=10)

    right_label.bind(
        "<Button-1>", lambda e: copy_to_clipboard(smaller_file_entry_basename)
    )

    right_image_label = tk.Label(right_frame, image=right_image, bg="#000")
    right_image_label.pack()

    find_vscode_window("remove_dupes.py")
    root.mainloop()


if __name__ == "__main__":
    main()
