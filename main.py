import asyncio
import bot
import proxy

async def main():
    bot_task = bot.main()
    proxy_task = proxy.main() 

    # Run both tasks in parallel
    await asyncio.gather(bot_task, proxy_task)

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())
