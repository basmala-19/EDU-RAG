from openai import OpenAI

from ..config import get_openrouter_api_key, get_openrouter_base_url

def get_llm_response(model_name: str, prompt: str) -> str:
    """Send a request using credentials supplied by the local .env file."""
    client = OpenAI(
        base_url=get_openrouter_base_url(),
        api_key=get_openrouter_api_key(),
    )
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        extra_body={
            "reasoning": {
                "enabled": False
            }
        }
    )

    return response.choices[0].message.content
