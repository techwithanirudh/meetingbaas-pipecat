import argparse
import asyncio
import os
from dotenv import load_dotenv
from .proxy import main as proxy_main

load_dotenv(override=True)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Customize the Proxy server."
    )
    return parser.parse_args()


async def main():
    args = parse_arguments()
    await proxy_main()

def start():
    asyncio.run(main())

if __name__ == "__main__":
    start()
