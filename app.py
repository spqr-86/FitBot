import os

import openai
from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")


@app.route("/", methods=("GET", "POST"))
def index(*args, **kwargs):
    if request.method == "POST":
        sex = request.form["gender"]
        age = request.form["age"]
        goal = request.form["goal"]
        weight = request.form["weight"]
        response = openai.Completion.create(
            model="text-davinci-002",
            prompt=generate_prompt(sex, age, goal, weight),
            max_tokens=1200,
            temperature=0.6,
        )
        return redirect(url_for("index", result=response.choices[0].text))

    result = request.args.get("result")
    return render_template("index.html", result=result)



