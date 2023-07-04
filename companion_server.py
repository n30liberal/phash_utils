from flask import (
    Flask,
    render_template,
    request,
    send_file,
    url_for,
    make_response,
    redirect,
)
from flask_socketio import SocketIO, send, emit  # noqa f401

import os, time
from user_config import blacklisted_phash_path

app = Flask(__name__)
socketio = SocketIO(app)

video1_path = None
video2_path = None
video1_name = None
video2_name = None
phash = None


@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


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
        time=time,
    )


@app.route("/health-check")
def health_check():
    print("Server is live")
    return "Server is live"


@app.route("/update")
def update_videos():
    global video1_path, video2_path, video1_name, video2_name, phash, update_flag

    video1_path = request.args.get("video1_path")
    video2_path = request.args.get("video2_path")
    video1_name = request.args.get("video1_name")
    video2_name = request.args.get("video2_name")
    phash = request.args.get("phash")

    if video1_path and video2_path and video1_name and video2_name and phash:
        print("Videos updated successfully")
        cache_buster = int(time.time())
        socketio.emit("refresh", cache_buster, namespace="/")

        # Create a response with cache-control headers
        response = make_response("Videos updated successfully")
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        return response
    else:
        # must be in browser
        return redirect(url_for("index"))


@app.route("/video1")
def serve_video1():
    if video1_path:
        # if path ends in jpg, gif, or png, serve as image
        if (
            video1_path.endswith(".jpg")
            or video1_path.endswith(".jpeg")
            or video1_path.endswith(".gif")
            or video1_path.endswith(".png")
        ):
            response = send_file(video1_path, mimetype="image/gif", as_attachment=False)
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response
        else:
            response = send_file(video1_path, mimetype="video/mp4", as_attachment=False)
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response

    return "Video not found", 404


@app.route("/video2")
def serve_video2():
    if video2_path:
        # if path ends in jpg, gif, or png, serve as image
        if (
            video2_path.endswith(".jpg")
            or video2_path.endswith(".jpeg")
            or video2_path.endswith(".gif")
            or video2_path.endswith(".png")
        ):
            response = send_file(video2_path, mimetype="image/gif", as_attachment=False)
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response
        else:
            response = send_file(video2_path, mimetype="video/mp4", as_attachment=False)
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response


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


@socketio.on("connect", namespace="/")
def handle_connect():
    # Send a welcome message to the connected client
    send("Connected to the server")


if __name__ == "__main__":
    socketio.run(app)
