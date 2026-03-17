from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # debug=false in prod later, change the port adequatly to the pc
    app.run(debug=True, port=5000)