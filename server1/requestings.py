import os
import ffmpeg
from http.server import BaseHTTPRequestHandler, HTTPServer
import json 

API_KEY = "123231"
BASE_DIR = "./jobs"
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB limit for uploads
FFMPEG_THREADS = 2

os.makedirs(BASE_DIR, exist_ok=True)

# -----------------------------
# FFMPEG CALL
# -----------------------------
def ffmpeg_call(input_path, output_path):
    (
        ffmpeg
        .input(input_path)
        .output(
            output_path,
            format="mp4",
            vcodec="libx264",
            acodec="aac",
            pix_fmt="yuv420p",
            movflags="+faststart",
            preset="veryfast",
            threads=FFMPEG_THREADS
        )
        .run(overwrite_output=True, quiet=True)
    )


# -----------------------------
# HTTP HANDLER
# -----------------------------
class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/render":
            self.send_response(404)
            self.end_headers()
            return

        # Authorization
        if self.headers.get("Authorization") != f"Bearer {API_KEY}":
            self.send_response(401)
            self.end_headers()
            return

        # Get content length
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_FILE_SIZE:
            self.send_response(413)
            self.end_headers()
            return

        # Job folder
        job_id = self.headers.get("X-Job-Id", "job")
        job_dir = os.path.join(BASE_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)

        input_path = os.path.join(job_dir, "input.mp4")
        output_path = os.path.join(job_dir, "output.mp4")

        # Save uploaded video
        with open(input_path, "wb") as f:
            remaining = length
            while remaining:
                chunk = self.rfile.read(min(65536, remaining))
                if not chunk:
                    break
                f.write(chunk)
                remaining -= len(chunk)

        # Run ffmpeg first, then respond
        try:
            ffmpeg_call(input_path, output_path)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "output": os.path.abspath(output_path)  # absolute path
            }).encode())
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

# -----------------------------
# SERVER ENTRY
# -----------------------------
def run():
    print("Renderer listening on :8080")
    HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()

if __name__ == "__main__":
    run()