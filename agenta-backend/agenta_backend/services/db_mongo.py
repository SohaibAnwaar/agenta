from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb://username:password@mongo:27017")
database = client["agenta"]

evaluation_rows = database["evaluation_rows"]
evaluations = database["evaluations"]
datasets = database["datasets"]
