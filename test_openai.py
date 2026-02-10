import os
from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

resp = client.responses.create(
    model="gpt-4.1-mini",
    input="Say 'setup ok' in one short sentence."
)

print(resp.output_text)
