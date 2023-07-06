import os
import sys
import cv2
import json
import shutil
import sqlite3
import argparse
import subprocess

from pathlib import Path
from build_db import build_and_populate_database

from user_config import database_path
from user_config import blacklisted_phash_path
from user_config import prioritized_directories
from user_config import readable_size, readable_duration
from user_config import mse_image_threshold, mse_video_threshold
from user_config import trash_directory, collections_directory

os.system("title remove_dupes.py")

parser = argparse.ArgumentParser(description="Script description")

parser.add_argument(
    "--remove-duplicates",
    action="store_true",
    help="Run the pHash Processor (removes duplicate files)",
)
parser.add_argument(
    "--rebuild-database",
    action="store_true",
    help="Rebuild our database with new data from StashApp",
)
parser.add_argument(
    "--auto-delete", action="store_true", help="Override value for auto_delete"
)
parser.add_argument(
    "--direct-delete", action="store_true", help="Override value for direct_delete"
)
parser.add_argument(
    "--allowed-media-types", nargs="+", help="Override value for allowed_media_types"
)
parser.add_argument(
    "--min-group-size", type=int, help="Override value for min_group_size"
)
parser.add_argument(
    "--min-group-duration", type=float, help="Override value for min_group_duration"
)
parser.add_argument(
    "--whitelist-models", nargs="+", help="Override value for whitelist_models"
)
parser.add_argument(
    "--blacklist-models", nargs="+", help="Override value for blacklist_models"
)
parser.add_argument(
    "--output-to-window",
    action="store_true",
    help="Override value for output_to_window",
)
args = parser.parse_args()

if args.auto_delete:
    auto_delete = args.auto_delete
else:
    from user_config import auto_delete
if args.direct_delete:
    direct_delete = args.direct_delete
else:
    from user_config import direct_delete
if args.allowed_media_types:
    allowed_media_types = args.allowed_media_types
else:
    from user_config import allowed_media_types
if args.min_group_size:
    min_group_size = args.min_group_size
else:
    from user_config import min_group_size
if args.min_group_duration:
    min_group_duration = args.min_group_duration
else:
    from user_config import min_group_duration
if args.whitelist_models:
    whitelist_models = args.whitelist_models
else:
    from user_config import whitelist_models
if args.blacklist_models:
    blacklist_models = args.blacklist_models
else:
    from user_config import blacklist_models
if args.output_to_window:
    output_to_window = args.output_to_window
else:
    from user_config import output_to_window


def update_videos(biggest_file_entry, smaller_file_entry):
    data = {
        "biggest_file_entry": biggest_file_entry,
        "smaller_file_entry": smaller_file_entry,
    }

    json_data = json.dumps(data)

    file_comparison_gui = Path(__file__).resolve().parent / "file_comparison_gui.py"

    subprocess.Popen(["python", str(file_comparison_gui), "--data", json_data])


def file_to_list(file_path):
    with open(file_path, "r") as f:
        return [line.strip() for line in f]


class pHashProcessor:
    def __init__(self):
        self.BLACKLISTED_PHASHES = file_to_list(blacklisted_phash_path)

    def connect_to_database(self, database_path):
        conn = sqlite3.connect(database_path)
        return conn

    def disconnect_from_database(self, conn):
        conn.close()

    def read_rows_with_phash(self, conn):
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT file_id, scene_id, file_model, file_basename, file_parent, file_path, file_size,
                media_type, phash, duration, video_codec, audio_codec, video_format, width, height,
                bit_rate, frame_rate
            FROM files
            WHERE phash IS NOT NULL
        """
        )
        rows = cursor.fetchall()
        return rows

    def build_dict_from_rows(self, rows):
        column_names = [
            "file_id",
            "scene_id",
            "file_model",
            "file_basename",
            "file_parent",
            "file_path",
            "file_size",
            "media_type",
            "phash",
            "duration",
            "video_codec",
            "audio_codec",
            "video_format",
            "width",
            "height",
            "bit_rate",
            "frame_rate",
        ]
        result = []
        for row in rows:
            item = {}
            for i, value in enumerate(row):
                if value is None or value == "" or value == "None":
                    item[column_names[i]] = None
                else:
                    item[column_names[i]] = value
            result.append(item)
        return result

    def get_curated_grouped_entries(
        self,
        result_dict,
        min_size=None,
        min_duration=None,
        whitelist=None,
        blacklist=None,
    ):
        # Create curated grouped_entries with only groups containing more than one entry
        curated_grouped_entries = {
            phash: group for phash, group in result_dict.items() if len(group) > 1
        }

        # If whitelist is not None, remove groups where AN entity["file_model"] in a group is not equal to whitelist
        # I.e. at least one entry in a group must match the whitelist, not ALL entries
        if whitelist not in (None, []):
            curated_grouped_entries = {
                phash: group
                for phash, group in curated_grouped_entries.items()
                if any(entry["file_model"] in whitelist for entry in group)
            }

        # if blacklist is not none or in [], remove all groups where at least one entry in the group is in the blacklist
        # i.e. at least one entry in a group must match the blacklist, not ALL entries
        if blacklist not in (None, []):
            curated_grouped_entries = {
                phash: group
                for phash, group in curated_grouped_entries.items()
                if not any(entry["file_model"] in blacklist_models for entry in group)
            }

        # Filter out entries where phash is None or nothing
        curated_grouped_entries = {
            phash: group
            for phash, group in curated_grouped_entries.items()
            if not any(phash_value in (None, "", "None") for phash_value in (phash,))
        }

        # Filter out entries with non-existent file paths
        # while making sure we only preserve groups with more than one entry
        curated_grouped_entries = {
            phash: group
            for phash, group in curated_grouped_entries.items()
            if len(group) > 1
            and all(os.path.exists(entry["file_path"]) for entry in group)
        }

        # we need to remove groups that don't match the allowed_media_types
        # if all entries in a group have a media_type of "video", then we can keep the group
        # if all entries in a group have a media_type of "image", then we remove the group
        # if a group has a mix; i.e. some entries are "video" and some are "image", or some are "None", then we remove the group
        curated_grouped_entries = {
            phash: group
            for phash, group in curated_grouped_entries.items()
            if all(entry["media_type"] in allowed_media_types for entry in group)
            and len(set(entry["media_type"] for entry in group)) == 1
        }

        # if min_size, filter out groups with total size less than min_size
        if min_size is not None:
            curated_grouped_entries = {
                phash: group
                for phash, group in curated_grouped_entries.items()
                if sum(entry["file_size"] for entry in group) >= min_size
            }

        # filter for min_duration if all entries in a group contain a duration
        # idk whats wrong with my logic, so it only works if "image" is not in allowed_media_types
        if "image" not in allowed_media_types:
            if min_duration is not None:
                curated_grouped_entries = {
                    phash: group
                    for phash, group in curated_grouped_entries.items()
                    if all(
                        entry["duration"] is not None and entry["duration"] != "None"
                        for entry in group
                    )
                    and sum(float(entry["duration"]) for entry in group) >= min_duration
                }

        return curated_grouped_entries

    def group_by_phash(self, entries, exact_match=True, blacklisted_phashes=[]):
        if exact_match:
            groups = {}
            for entry in entries:
                phash = entry["phash"]
                if entry["phash"] not in blacklisted_phashes:
                    if phash in groups:
                        groups[phash].append(entry)
                    else:
                        groups[phash] = [entry]
            return groups

    def process_grouped_entries(self, grouped_entries, auto_delete=False):
        # print how many groups exist in curated_grouped_entries
        print(f"Number of groups: {len(grouped_entries)}")

        # print the total amount of space we can potentially save by adding the file sizes of each group, minus the size of the largest file in each group
        theoretical_space_saved = sum(
            sum(entry["file_size"] for entry in group)
            - max(entry["file_size"] for entry in group)
            for group in grouped_entries.values()
        )
        print(f"Theoretical space to save: {readable_size(theoretical_space_saved)}\n")

        # Calculate summed file size for each group
        group_sizes = {
            phash: sum(entry["file_size"] for entry in group)
            for phash, group in grouped_entries.items()
        }

        # Sort groups by summed file size in descending order
        sorted_groups = sorted(
            grouped_entries.values(),
            key=lambda group: group_sizes[group[0]["phash"]],
            reverse=True,
        )

        # Print the summed file size for each group
        for group in sorted_groups:
            phash_value = group[0]["phash"]
            print(
                f"Group - phash: {phash_value} (Summed File Size: {readable_size(group_sizes[phash_value])})"
            )

            self.process_delete_files(group, auto_delete=auto_delete)

    def sort_files_by_size(self, group):
        return sorted(group, key=lambda entry: entry["file_size"], reverse=True)

    def separate_premium_and_non_premium_files(self, sorted_files):
        premium_files = []
        non_premium_files = []
        for entry in sorted_files:
            file_path = Path(entry["file_path"])
            if file_path.parent.name.lower() in [
                directory.lower() for directory in prioritized_directories
            ]:
                premium_files.append(entry)
            else:
                non_premium_files.append(entry)
        return premium_files, non_premium_files

    def find_biggest_file(self, group, premium_files):
        biggest_file = None
        for entry in group:
            if biggest_file is None or entry["file_size"] > biggest_file["file_size"]:
                biggest_file = entry
            elif entry["file_size"] == biggest_file["file_size"]:
                if entry in premium_files:
                    biggest_file = entry
        return biggest_file

    def process_group(self, group, auto_delete=False):
        # Determine media type of group
        media_type = (
            "video"
            if all(entry["media_type"] == "video" for entry in group)
            else "image"
            if all(entry["media_type"] == "image" for entry in group)
            else "None"
            if all(entry["media_type"] == "None" for entry in group)
            else "mixed"
        )

        sorted_files = self.sort_files_by_size(group)
        premium_files, non_premium_files = self.separate_premium_and_non_premium_files(
            sorted_files
        )

        if auto_delete:
            if not self.is_frames_match(
                [entry["file_path"] for entry in premium_files + non_premium_files],
                media_type,
            ):
                print("In auto-delete mode.")
                print("Frames do not match. Skipping group.\n")
                return

        biggest_file = self.find_biggest_file(group, premium_files)
        all_same_model = len(set(entry["file_model"] for entry in group)) == 1

        if all_same_model:
            self.process_same_model_files(
                biggest_file,
                premium_files,
                non_premium_files,
                auto_delete,
                media_type,
            )
        else:
            if auto_delete:
                print("In auto-delete mode.")
                print("Different models. Skipping group.\n")
                return

            self.process_different_model_files(
                group,
                biggest_file,
                premium_files,
                non_premium_files,
                auto_delete,
                media_type,
            )

    def process_same_model_files(
        self, biggest_file, premium_files, non_premium_files, auto_delete, media_type
    ):
        for i, entry in enumerate(premium_files + non_premium_files, start=1):
            if entry != biggest_file:
                frames_match = self.is_frames_match(
                    [entry["file_path"], biggest_file["file_path"]], media_type
                )

                print("Biggest file:")
                print(f"File Model: {biggest_file['file_model']}")
                print(f"File Path: {biggest_file['file_path']}")
                print(f"File Size: {readable_size(biggest_file['file_size'])}")

                if biggest_file["duration"] is not None:
                    print(
                        f"File Duration: {readable_duration(biggest_file['duration'])}\n"
                    )
                else:
                    print()

                print("Ready to delete:")
                print(f"Frames Match: {frames_match}")
                print(f"File Model: {entry['file_model']}")
                print(f"File Path: {entry['file_path']}")
                print(f"File Size: {readable_size(entry['file_size'])}")

                if entry["duration"] is not None:
                    print(f"File Duration: {readable_duration(entry['duration'])}\n")
                else:
                    print()

                if output_to_window:
                    update_videos(biggest_file, entry)

                if i < len(non_premium_files):
                    print(f"File [{i} of {len(non_premium_files)}]")

                if auto_delete:
                    if frames_match:
                        print("Frames match. Deleting file.")
                        self.remove_file(Path(entry["file_path"]))
                        print()
                    else:
                        print("Frames do not match. Skipping file.")
                else:
                    user_choice = input("Do you want to delete this file? (y/n): ")
                    if user_choice.lower() != "n":
                        self.remove_file(Path(entry["file_path"]))
                        print()

    def process_different_model_files(
        self,
        group,
        biggest_file,
        premium_files,
        non_premium_files,
        auto_delete,
        media_type,
    ):
        if not self.is_frames_match(
            [entry["file_path"] for entry in premium_files + non_premium_files],
            media_type,
        ):
            print(f"pHash: {biggest_file['phash']}")
            print("Frames do not match for all files in group. Be weary!\n")

            if auto_delete:
                print("In auto-delete mode.")
                print("Frames do not match. Skipping group.\n")
                return

        file_models = set(entry["file_model"] for entry in group)

        for file_model in file_models:
            files_with_model = [
                entry for entry in group if entry["file_model"] == file_model
            ]
            biggest_file_with_model = max(
                files_with_model, key=lambda entry: entry["file_size"]
            )

            frames_match = self.is_frames_match(
                [biggest_file_with_model["file_path"], biggest_file["file_path"]],
                media_type,
            )

            if output_to_window:
                update_videos(biggest_file, biggest_file_with_model)

            if auto_delete:
                if not frames_match:
                    print("Frames do not match. Skipping group.\n")
                    return

            print(f"Frames Match: {frames_match}")
            print(f"File Model: {file_model}")
            print(f"Biggest File Path: {biggest_file_with_model['file_path']}")
            print(f"File Size: {readable_size(biggest_file_with_model['file_size'])}")
            if biggest_file_with_model["duration"] is not None:
                print(
                    f"File Duration: {readable_duration(biggest_file_with_model['duration'])}\n"
                )
            else:
                print()

        if not auto_delete:
            chosen_model = input("Enter the file model you want to preserve: ")
            print()

            for entry in group:
                if entry["file_model"] != chosen_model:
                    frames_match = self.is_frames_match(
                        [entry["file_path"], biggest_file["file_path"]],
                        media_type,
                    )
                    print("Ready to delete:")
                    print(f"Frames Match: {frames_match}")
                    print(f"File Model: {entry['file_model']}")
                    print(f"File Path: {entry['file_path']}")
                    print(f"File Size: {readable_size(entry['file_size'])}")
                    if entry["duration"] is not None:
                        print(
                            f"File Duration: {readable_duration(entry['duration'])}\n"
                        )
                    else:
                        print()

                    if auto_delete:
                        if frames_match:
                            print("Frames match. Deleting file.")
                            self.remove_file(Path(entry["file_path"]))
                            print()
                        else:
                            print("Frames do not match. Skipping file.")
                    else:
                        user_choice = input("Do you want to delete this file? (y/n): ")
                        if user_choice.lower() != "n":
                            self.remove_file(Path(entry["file_path"]))
                            print()

    def process_delete_files(self, group, auto_delete=False):
        self.process_group(group, auto_delete)

    def is_frames_match(self, file_paths, media_type=None):
        def is_video(path):
            if media_type == "video":
                return True

        def is_image(path):
            if media_type == "image":
                return True

        def is_video_frames_match(video_paths):
            try:
                cap = cv2.VideoCapture(video_paths[0])
                ret, frame1 = cap.read()
                cap.release()

                for path in video_paths[1:]:
                    cap = cv2.VideoCapture(path)
                    ret, frame2 = cap.read()
                    cap.release()

                    if frame1 is None or frame2 is None:
                        return False

                    if frame1.shape != frame2.shape:
                        frame1 = cv2.resize(frame1, frame2.shape[:2][::-1])

                    mse = ((frame1 - frame2) ** 2).mean()

                    if mse > mse_video_threshold:
                        return False

                return True

            except Exception as e:
                print(f"An error occurred: {str(e)}")
                return False

        def is_image_frames_match(image_paths):
            patch_size = 128
            try:
                frame1 = cv2.imread(image_paths[0])

                if frame1 is None:
                    return False

                for path in image_paths[1:]:
                    frame2 = cv2.imread(path)

                    if frame2 is None:
                        return False

                    for i in range(0, frame1.shape[0], patch_size):
                        for j in range(0, frame1.shape[1], patch_size):
                            patch1 = frame1[i : i + patch_size, j : j + patch_size]
                            patch2 = frame2[i : i + patch_size, j : j + patch_size]

                            if patch1.shape != patch2.shape:
                                patch1 = cv2.resize(patch1, patch2.shape[:2][::-1])

                            mse = ((patch1 - patch2) ** 2).mean()

                            if mse > mse_image_threshold:
                                return False

            except Exception as e:
                print(f"Error occurred: {e}")
                return False

            return True

        try:
            if all(is_video(path) for path in file_paths):
                return is_video_frames_match(file_paths)

            if all(is_image(path) for path in file_paths):
                return is_image_frames_match(file_paths)

            print("Unsupported input type")
            print(f"Input paths: {file_paths}")
            input("Press Enter to continue...")
            return False

        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return False

    def remove_file(self, file_path):
        path = Path(file_path)

        if path.exists():
            relative_path = path.relative_to(collections_directory)

            # Create the target directory structure inside the trash directory
            target_dir = trash_directory / relative_path.parent
            target_dir.mkdir(parents=True, exist_ok=True)

            target_path = target_dir / path.name

            while True:
                try:
                    if not direct_delete:
                        shutil.move(str(path), str(target_path))
                        print(f"Moved file to trash: {target_path}")
                    else:
                        path.unlink()
                        print(f"Deleted file: {path}")
                    break
                except FileNotFoundError:
                    pass
                except PermissionError:
                    print(f"Could not move file to trash: {target_path}")

    def move_file(self, file_path, destination):
        source_path = Path(file_path)
        destination_path = Path(destination)
        if source_path.exists():
            try:
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                source_path.rename(destination_path)
                print(f"Moved file: {source_path} to {destination_path}")
            except OSError as e:
                print(f"Error: {e}")


def remove_duplicates():
    processor = pHashProcessor()
    conn = processor.connect_to_database(database_path)
    rows = processor.read_rows_with_phash(conn)
    result_dict = processor.build_dict_from_rows(rows)
    processor.disconnect_from_database(conn)

    grouped_entries = processor.group_by_phash(
        result_dict, blacklisted_phashes=processor.BLACKLISTED_PHASHES
    )

    curated_grouped_entries = processor.get_curated_grouped_entries(
        grouped_entries,
        min_size=min_group_size,
        min_duration=min_group_duration,
        whitelist=whitelist_models,
        blacklist=blacklist_models,
    )

    os.system("cls" if os.name == "nt" else "clear")

    print("Arguments Found:\n")
    print("Using Arguments:")
    for arg in vars(args):
        if getattr(args, arg) is not None:
            if getattr(args, arg) is True:
                print(f"{arg}: {getattr(args, arg)}")
    print("\nUsing Defaults:")
    for arg in vars(args):
        if getattr(args, arg) is None:
            print(f"{arg}: {globals()[arg]}")
        if getattr(args, arg) is False:
            print(f"{arg}: {getattr(args, arg)}")
    print()

    processor.process_grouped_entries(curated_grouped_entries, auto_delete=auto_delete)

    print()


def main():
    os.system("cls" if os.name == "nt" else "clear")

    if args.rebuild_database:
        build_and_populate_database()
    if args.remove_duplicates:
        remove_duplicates()

    if not (args.remove_duplicates or args.rebuild_database):
        while True:
            print("\nWhat would you like to do?\n")
            print("1. Remove duplicate files    [--remove-duplicates]")
            print("2. Rebuild database          [--rebuild-database]")
            print("3. Exit\n")
            choice = input("Enter your choice: ")

            if choice == "1":
                remove_duplicates()
                break
            elif choice == "2":
                build_and_populate_database()
                break
            elif choice == "3":
                sys.exit()
            else:
                print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()
