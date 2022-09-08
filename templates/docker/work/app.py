from crypt import methods
from flask import Flask, request
import Handler

app = Flask(__name__)

@app.route('/',methods=["POST"])
def index():
  ret = Handler.handler(request.json)
  return ret

if __name__ == '__main__':
  app.run(host="0.0.0.0", debug=True)
