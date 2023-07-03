from pathlib import Path

flask_server = "http://127.0.0.1:5000"

stash_database_path = Path("path/to/your/stash/database.sqlite")

data_directory = Path(__file__).parent / "data"
blacklisted_phash_path = data_directory / "blacklisted_phashes.txt"
database_path = data_directory / "stash_data.sqlite"
phashes_path = data_directory / "phashes.csv"
processed_images_path = data_directory / "phashed_file_ids.txt"

mse_image_threshold = 30
mse_video_threshold = 30

# limits the script to only work with groups that have a summed size of at least n MB
# where 0 is your size in MB
# while being 0, we're not limiting the script at all
# this can be useful when you have a lot of false positives for the smaller files (think tiktok splash screens ruining the phash)
min_group_size = 0 * 1024 * 1024


# limits the script to only work with groups that have a summed duration of at least n seconds
# where 0 is your duration in seconds
# while being 0, we're not limiting the script at all
# this can be useful when you have a lot of false positives for the shorter (think tiktok splash screens ruining the phash)
min_group_duration = 0
