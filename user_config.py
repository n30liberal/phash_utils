from pathlib import Path


def readable_size(bytes):
    if bytes < 1024:
        return f"{bytes} B"
    elif bytes < 1024**2:
        return f"{bytes / 1024:.2f} KB"
    elif bytes < 1024**3:
        return f"{bytes / 1024 ** 2:.2f} MB"
    elif bytes < 1024**4:
        return f"{bytes / 1024 ** 3:.2f} GB"
    else:
        return f"{bytes / 1024 ** 4:.2f} TB"


def readable_duration(float):
    seconds = int(float)

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


# path to your stash database [we're only reading from it, but it's still a good idea to make a backup]
stash_database_path = Path("path/to/stash/database.sqlite")

# paths to all the files/dirs we're going to be using
data_directory = Path(__file__).parent / "data"
blacklisted_phash_path = data_directory / "blacklisted_phashes.txt"
database_path = data_directory / "stash_data.sqlite"
phashes_path = data_directory / "phashes.csv"
processed_images_path = data_directory / "phashed_file_ids.txt"

direct_delete = False
trash_directory = Path("path/to/trash/directory") # folder you dedicate to trash, so you can easily restore stuff
collections_directory = Path("path/to/your/isos") # main root folder for your collections
extracted_frames_path = Path("path/to/your/extracted/frames") # this dir gets deleted each call

auto_delete = False
output_to_window = False

mse_image_threshold = 40
mse_video_threshold = 40

prioritized_directories = ["premium"]
allowed_media_types = ["video"]
min_group_size = 0 * 1024 * 1024
min_group_duration = 0
whitelist_models = []
blacklist_models = []

image_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp", ".jfif"]
video_extensions = [
    ".mp4",
    ".mkv",
    ".mov",
    ".m4v",
    ".wmv",
    ".gif",
    ".avi",
    ".ts",
    ".mpg",
    ".flv",
    ".mpeg",
]
