import sqlite3
import imagehash
from PIL import Image
from pathlib import Path
from tqdm import tqdm
import concurrent.futures

from user_config import database_path, phashes_path, processed_images_path


def calculate_phash(image_path):
    try:
        image = Image.open(image_path)
        phash = imagehash.phash(image)
        return phash
    except Exception as e:
        tqdm.write(f"Failed to process {image_path}")
        tqdm.write(f"Error: {e}\n")
        return None


def fetch_image_data(database_path, processed_images_path):
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT file_id, file_parent, file_basename FROM files WHERE md5 IS NOT NULL AND phash IS NULL"
    )
    results = cursor.fetchall()

    processed_data = set()
    if Path(processed_images_path).is_file():
        with open(processed_images_path, "r") as processed_file:
            for line in processed_file:
                file_id = line.strip()
                processed_data.add(file_id)

    filtered_results = [row for row in results if str(row[0]) not in processed_data]

    conn.close()

    return filtered_results


def process_image(row, processed_images_path):
    try:
        file_id = row[0]
        file_parent = row[1]
        file_basename = row[2]
        file_path = Path(file_parent) / file_basename
        phash = calculate_phash(str(file_path))

        with open(processed_images_path, "a") as processed_file:
            processed_file.write(f"{file_id}\n")

        return file_id, phash
    except KeyboardInterrupt:
        return None


def main():
    image_data = fetch_image_data(database_path, processed_images_path)
    progress_bar = tqdm(total=len(image_data))

    with open(phashes_path, "a") as output_csv, concurrent.futures.ThreadPoolExecutor(
        max_workers=3
    ) as executor:
        futures = []
        try:
            for row in image_data:
                future = executor.submit(process_image, row, processed_images_path)
                futures.append(future)

            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result is not None:
                    file_id, phash = result
                    output_csv.write(f"{file_id},{phash}\n")
                    output_csv.flush()
                    progress_bar.update(1)
                else:
                    break
        except KeyboardInterrupt:
            for future in futures:
                future.cancel()
            progress_bar.close()
            print("Process interrupted.")
            return

    progress_bar.close()
    print()
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
