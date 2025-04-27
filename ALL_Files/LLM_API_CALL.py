from openai import OpenAI


Open_api_key='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'

deepseek_api = 'sk-43e9043c7ab8480393d34367f2ae997e'

def deepseek_api_call(prompt, base_url="https://api.deepseek.com", model="deepseek-chat"):

    client = OpenAI(api_key=deepseek_api, base_url=base_url)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an financial report analyst as API agent"},
            {"role": "user", "content": prompt},
        ],
        stream=False
    )
    
    # Return the response content
    return response.choices[0].message.content



def openai_api_call(prompt, model="gpt-4o", max_tokens=10000):

    client = OpenAI(api_key=Open_api_key)  # Replace with your OpenAI API key
    print('calling AI Analyst to do the task')

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an financial report analyst as API agent"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0  # Adjust for creativity level
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error: {str(e)}"

