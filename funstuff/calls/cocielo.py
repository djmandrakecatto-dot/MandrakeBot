import aiohttp
import asyncio

async def generate_cocielo_video(images: list[str], output="cocielo_chaves.mp4"):
    """
    images: list of image URLs (max 5)
    """
    payload = {
        "images": [
            {
                "type": "url",
                "url": img
            } for img in images[:5]
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Loritta-Python-Test/1.0"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://gabriela.loritta.website/api/v1/videos/cocielo-chaves",
            json=payload,
            headers=headers
        ) as resp:

            if resp.status < 200 or resp.status >= 300:
                raise RuntimeError(f"API failed with status {resp.status}")

            video_bytes = await resp.read()

    with open(output, "wb") as f:
        f.write(video_bytes)

    return output
