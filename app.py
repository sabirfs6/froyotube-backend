import subprocess
import os
from fastapi import FastAPI, Response, HTTPException
import yt_dlp

app = FastAPI(title="FroyoTube Proxy")

@app.get("/")
def home():
    return {"status": "FroyoTube Proxy is running online!"}

@app.get("/search")
def search_videos(q: str):
    ydl_opts = {
        'extract_flat': True,
        'max_results': 15,
        'quiet': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            results = ydl.extract_info(f"ytsearch15:{q}", download=False)
            videos = []
            for entry in results.get('entries', []):
                videos.append({
                    "id": entry.get('id'),
                    "title": entry.get('title'),
                    "duration": entry.get('duration'),
                    "thumbnail": f"https://img.youtube.com/vi/{entry.get('id')}/hqdefault.jpg"
                })
            return {"results": videos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stream")
def stream_video(url: str):
    try:
        ydl_opts = {'format': 'best[height<=360]/best[ext=mp4]/best'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = info.get('url')
            
        if not stream_url:
            raise HTTPException(status_code=404, detail="Stream URL not found")

        # FFmpeg transcoder tuned for Android 2.2 ARMv6 hardware limits
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', stream_url,
            '-vf', 'scale=320:240',
            '-c:v', 'libx264',
            '-profile:v', 'baseline',
            '-level', '3.0',
            '-b:v', '250k',
            '-c:a', 'aac',
            '-b:a', '64k',
            '-ar', '22050',
            '-f', 'mp4',
            '-movflags', 'frag_keyframe+empty_moov',
            'pipe:1'
        ]

        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        def generator():
            try:
                while True:
                    chunk = process.stdout.read(8192)
                    if not chunk:
                        break
                    yield chunk
            finally:
                process.terminate()

        return Response(generator(), media_type="video/mp4")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("app:app", host="0.0.0.0", port=port)
