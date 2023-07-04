import sqlite3
import time
import os
from user_config import database_path, stash_database_path
from user_config import image_extensions, video_extensions


DESTRUCTIVE_RUN = True


class DatabaseManager:
    def __init__(self, database_path):
        self.database_path = database_path
        self.conn = None
        self.cursor = None

    def connect(self):
        self.conn = sqlite3.connect(self.database_path)
        self.cursor = self.conn.cursor()

    def disconnect(self):
        self.cursor.close()
        self.conn.close()

    def execute_query(self, query):
        self.cursor.execute(query)

    def fetch_rows(self):
        return self.cursor.fetchall()

    def upsert_data(self, data):
        total_rows = len(data)
        print(f"Total rows to upsert: {total_rows}\n")

        for row in data:
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO files (
                    file_id, scene_id, file_model, file_basename, file_parent,
                    file_path, file_size, media_type, ohash, phash, md5, duration, video_codec,
                    audio_codec, video_format, width, height, bit_rate,
                    frame_rate
                ) VALUES (
                    :file_id, :scene_id, :file_model, :file_basename, :file_parent,
                    :file_path, :file_size, :media_type, :ohash, :phash, :md5, :duration, :video_codec,
                    :audio_codec, :video_format, :width, :height, :bit_rate,
                    :frame_rate
                )
            """,
                row,
            )

    def read_data_from_db(self):
        query = """
        SELECT
        f.id AS file_id,
        f.basename AS file_basename,
        COALESCE((SELECT path FROM folders WHERE id = f.parent_folder_id), '/') AS parent_folder_path,
        f.size AS file_size,
        MAX(CASE WHEN ff.type = 'oshash' THEN ff.fingerprint END) AS ohash,
        MAX(CASE WHEN ff.type = 'phash' THEN ff.fingerprint END) AS phash,
        MAX(CASE WHEN ff.type = 'md5' THEN ff.fingerprint END) AS md5,
        CASE WHEN vf.file_id IS NOT NULL THEN vf.duration ELSE NULL END AS duration,
        CASE WHEN vf.file_id IS NOT NULL THEN vf.video_codec ELSE NULL END AS video_codec,
        CASE WHEN vf.file_id IS NOT NULL THEN vf.audio_codec ELSE NULL END AS audio_codec,
        CASE WHEN vf.file_id IS NOT NULL THEN vf.format ELSE NULL END AS format,
        CASE WHEN vf.file_id IS NOT NULL THEN vf.width ELSE NULL END AS width,
        CASE WHEN vf.file_id IS NOT NULL THEN vf.height ELSE NULL END AS height,
        CASE WHEN vf.file_id IS NOT NULL THEN vf.bit_rate ELSE NULL END AS bit_rate,
        CASE WHEN vf.file_id IS NOT NULL THEN vf.frame_rate ELSE NULL END AS frame_rate,
        sf.scene_id AS scene_id
        FROM
        files f
        LEFT JOIN
        files_fingerprints ff ON f.id = ff.file_id
        LEFT JOIN
        video_files vf ON f.id = vf.file_id
        LEFT JOIN
        scenes_files sf ON f.id = sf.file_id
        GROUP BY
        f.id, f.basename, parent_folder_path, file_size, duration, video_codec, audio_codec, format, width, height, bit_rate, frame_rate, scene_id
        """

        self.execute_query(query)
        rows = self.fetch_rows()
        return rows

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


def check_database_exists(database_path):
    if not database_path.exists():
        print("Database file does not exist.")
        exit()


def convert_to_hex(i: int) -> str:
    u = i + (1 << 64)
    h = hex(u)
    encoded_hex = h[2:]
    return encoded_hex


def restructure_rows(rows):
    restructured_rows = []

    for row in rows:
        if row[2] and row[1]:
            file_path = os.path.join(row[2], row[1])

        if row[1] and (
            row[1].endswith(tuple(image_extensions))
            or row[1].endswith(tuple(video_extensions))
        ):
            if row[1].endswith(tuple(image_extensions)):
                media_type = "image"
            elif row[1].endswith(tuple(video_extensions)):
                media_type = "video"

        reorganized_row = {
            "file_id": row[0] or None,
            "scene_id": row[15] or None,
            "file_model": row[2].split("\\")[3] if row[2] else None,
            "file_basename": row[1] or None,
            "file_parent": row[2].replace("\\", "/") if row[2] else None,
            "file_path": file_path or None,
            "file_size": row[3] or None,
            "media_type": media_type or None,
            "ohash": row[4] or None,
            "phash": convert_to_hex(row[5]) if row[5] else None,
            "md5": row[6] or None,
            "duration": row[7] or None,
            "video_codec": row[8] or None,
            "audio_codec": row[9] or None,
            "video_format": row[10] or None,
            "width": row[11] or None,
            "height": row[12] or None,
            "bit_rate": row[13] or None,
            "frame_rate": row[14] or None,
        }
        restructured_rows.append(reorganized_row)

    return restructured_rows


def build_database(source_database_path, destination_database_path):
    check_database_exists(source_database_path)

    print("Reading data from source database.")
    with DatabaseManager(source_database_path) as source_db:
        data_rows = source_db.read_data_from_db()

    print("Restructuring data for new database.\n")
    restructured_rows = restructure_rows(data_rows)

    with DatabaseManager(destination_database_path) as destination_db:
        print("Upserting data into new database.")
        destination_db.upsert_data(restructured_rows)
        destination_db.conn.commit()


def create_empty_database(database_path):
    print("Creating empty database.\n")
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS files (
            file_id INTEGER PRIMARY KEY,
            scene_id INTEGER,
            file_model TEXT,
            file_basename TEXT,
            file_parent TEXT,
            file_path TEXT,
            file_size INTEGER,
            media_type TEXT,
            ohash TEXT,
            phash TEXT,
            md5 TEXT,
            duration REAL,
            video_codec TEXT,
            audio_codec TEXT,
            video_format TEXT,
            width INTEGER,
            height INTEGER,
            bit_rate INTEGER,
            frame_rate REAL
        )"""
    )

    conn.commit()
    conn.close()


def build_and_populate_database():
    os.system("cls" if os.name == "nt" else "clear")

    start_time = time.time()
    print("\nBuilding database...\n")

    output_database_path = database_path

    # we dont keep persistant information in the database, so we can delete it each time we update it
    # especially since it builds in less than 30 seconds
    # ideally we dont want to rebuild, but instead remove entries that no longer exist in the source database, and add new entries
    # eventually we will, once i figure out the best way to store my generated image phashes long term

    if output_database_path.exists():
        if DESTRUCTIVE_RUN:
            output_database_path.unlink()
            print(f"Deleted existing database file: {output_database_path}")
        else:
            user_choice = input(
                "Database file already exists. Would you like to delete it? (y/n): "
            )
            if user_choice.lower() == "y":
                output_database_path.unlink()
                print(f"Deleted existing database file: {output_database_path}")
            else:
                print("Exiting...")
                exit()

    create_empty_database(output_database_path)

    build_database(stash_database_path, output_database_path)

    print(f"Database built in {time.time() - start_time:.2f} seconds.")
    print()


def main():
    print("This script is not meant to be run as a standalone script.")
    print("Please run remove_dupes.py with the --rebuild-database flag instead.")


if __name__ == "__main__":
    main()
