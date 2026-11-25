import asyncio
import time

from fastapi import FastAPI

app = FastAPI()


@app.get("/sleepio/{seconds}")
async def sleep_for(seconds: int):
    start = time.time()

    print("Going to bed")

    tasks = [asyncio.create_task(asyncio.sleep(1)) for s in range(seconds)]

    for s, task in enumerate(tasks):
        await task
        print(f"zz {s}")

    end = time.time()
    print(f"Total sleep time: {end - start} seconds")

    return "Awake!"
