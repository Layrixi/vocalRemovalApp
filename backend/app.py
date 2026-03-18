from flask import Flask, render_template
import os


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # debug=false in prod later, change the port adequatly to the pc(if possible)
    #prod code
    app.run(debug=True, port=5000)