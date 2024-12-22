import openai

# 替换为你的 OpenAI API 密钥
openai.api_key = 'your-api-key'

def generate_text(prompt):
    response = openai.Completion.create(
        engine="text-davinci-003",  # 使用适当的引擎
        prompt=prompt,
        max_tokens=150
    )
    return response.choices[0].text.strip()

if __name__ == "__main__":
    prompt = "随便说句话："
    result = generate_text(prompt)
    print(result)
