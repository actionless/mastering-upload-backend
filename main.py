import os
import aiohttp
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

load_dotenv()
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN")
PORT = int(os.environ.get("PORT", 10000))
STATIC_PATH = os.getenv("STATIC_PATH")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        FRONTEND_ORIGIN or f"http://localhost:{PORT}",
        # "https://actionless.github.io",
        # "http://localhost:8000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# == Upload to temp.sh ==
async def upload_to_tempsh(file: UploadFile) -> str:
    form = aiohttp.FormData()
    form.add_field('file', await file.read(), filename=file.filename)

    async with aiohttp.ClientSession() as session:
        async with session.post("https://temp.sh/upload", data=form) as resp:
            text = await resp.text()
            if resp.status != 200 or (not text.startswith("https://") and not text.startswith("http://")):
                raise Exception(f"temp.sh upload failed: {resp.status} {text}")
            return text.strip()


# == Upload to 0x0.st ==
async def upload_to_0x0(file: UploadFile, expires=None) -> str:
    form = aiohttp.FormData()
    form.add_field('file', await file.read(), filename=file.filename)
    if expires:
        form.add_field('expires', expires)  # e.g. '24'
    headers = {
        "user-agent": "curl/8.13.0"
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post("https://0x0.st", data=form) as resp:
            text = await resp.text()
            if resp.status != 200 or not text.startswith("https://"):
                raise Exception(f"0x0.st upload failed: {resp.status} {text}")
            return text.strip()


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        # try temp.sh first, fallback to 0x0.st
        try:
            link = await upload_to_tempsh(file)
        except Exception as e:
            print(e)
            link = await upload_to_0x0(file)

        return JSONResponse({"link": link})
    except Exception as e:
        print(e)
        return JSONResponse({"error": str(e)}, status_code=500)


if STATIC_PATH is not None:
    _STATIC_PATH: str = STATIC_PATH

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(_STATIC_PATH + "/index.html")


def run() -> None:
    uvicorn.run(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    run()
