import asyncio
import traceback
import sys

sys.path.insert(0, '.')
from llm_pipeline import handle_chat_query_stream

async def run_test():
    try:
        gen = handle_chat_query_stream("Which products are associated with the highest number of billing documents?", [])
        async for chunk in gen:
            print("CHUNK:", chunk)
    except Exception as e:
        print("EXCEPTION IN GEN:", e)
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_test())
