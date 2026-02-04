import openai

client = openai.OpenAI(api_key="your api key")

response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "user", "content": "What is a Sun Temple?"}
    ]
)

print(response.choices[0].message.content)
