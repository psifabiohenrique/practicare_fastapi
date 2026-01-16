import asyncio

from src.ai.chains.record_generation import RecordGenerationChain


async def run():
    ia = RecordGenerationChain()
    result = await ia.generate("Isto é só um teste.")
    return result


asyncio.run(run())

# generate_record.delay(
#     "d5ae69ba-cfe0-4415-b545-aca695168e36", "Isto é só um teste"
# )
