import os


import openai
from flask import Flask, request

app = Flask(__name__)


@app.route("/", methods=("GET", "POST"))
def answer():
    if request.method == "POST":
        prompt = request.json['prompt']
        openai.api_key = os.getenv("OPENAI_API_KEY")
        response = openai.Completion.create(
            model="text-davinci-002",
            prompt=prompt,
            max_tokens=2048,
            temperature=0.6,
        )
        print(response)

        result = response.choices[0].text
        return result


if __name__ == "__main__":
    app.run(debug=True)
