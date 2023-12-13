from openai import OpenAI
client = OpenAI(api_key='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')

completion = client.chat.completions.create(
  model="gpt-3.5-turbo",
  messages=[
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ]
)

print(completion.choices[0].message)
