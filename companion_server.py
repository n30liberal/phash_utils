from flask import Flask, render_template, request, send_file
import os

from user_config import (
    blacklisted_phash_path,
)

app = Flask(__name__)

video1_path = None
video2_path = None
video1_name = None
video2_name = None
phash = None


@app.route("/")
def index():
    global video1_path, video2_path, video1_name, video2_name, phash

    if (
        video1_path is None
        or video2_path is None
        or phash is None
        or video1_name is None
        or video2_name is None
    ):
        video1_path = ""
        video2_path = ""
        video1_name = ""
        video2_name = ""
        phash = ""

    return render_template(
        "index.html",
        video1_path=video1_path,
        video2_path=video2_path,
        video1_name=video1_name,
        video2_name=video2_name,
        phash=phash,
    )


@app.route("/health-check")
def health_check():
    print("Server is live")
    return "Server is live"


@app.route("/update")
def update_videos():
    global video1_path, video2_path, video1_name, video2_name, phash

    video1_path = request.args.get("video1_path")
    video2_path = request.args.get("video2_path")
    video1_name = request.args.get("video1_name")
    video2_name = request.args.get("video2_name")
    phash = request.args.get("phash")

    if video1_path and video2_path and video1_name and video2_name and phash:
        print("Videos updated successfully")
        return "Videos updated successfully"
    else:
        print("Failed to update videos")
        return "Failed to update videos"


@app.route("/video1")
def serve_video1():
    if video1_path:
        if os.path.exists(video1_path):
            response = send_file(video1_path, mimetype="video/mp4", as_attachment=False)
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response

    return "Video not found", 404


@app.route("/video2")
def serve_video2():
    if video2_path:
        if os.path.exists(video2_path):
            response = send_file(video2_path, mimetype="video/mp4", as_attachment=False)
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response

    return "Video not found", 404


@app.route("/append-to-blacklisted", methods=["POST"])
def append_to_blacklisted():
    data = request.get_json()
    phash = data.get("phash")

    if phash:
        phash = phash.strip()
        with open(blacklisted_phash_path, "a") as f:
            f.write(phash + "\n")
        print("Phash appended to blacklisted_phashes")
        return "Phash appended to blacklisted_phashes"
    else:
        print("Invalid phash")
        return "Invalid phash"


if __name__ == "__main__":
    app.run(debug=True)
