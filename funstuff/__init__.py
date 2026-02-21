async def load_cogs():
    for filename in os.listdir("./funstuff"):
        if filename.endswith(".py") and filename != "__init__.py":
            await bot.load_extension(f"funstuff.{filename[:-3]}")
