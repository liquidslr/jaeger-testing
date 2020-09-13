from flask import Flask, render_template, request, make_response, g
from redis import Redis
import os
import socket
import random
import json

import sys
import time
import logging
import random
from jaeger_client import Config


option_a = os.getenv('OPTION_A', "Cats")
option_b = os.getenv('OPTION_B', "Dogs")
hostname = socket.gethostname()

app = Flask(__name__)

def init_tracer(service):
    logging.getLogger('').handlers = []
    logging.basicConfig(format='%(message)s', level=logging.DEBUG)    
    config = Config(
        config={
            'sampler': {
                'type': 'const',
                'param': 1,
            },
            'local_agent': {
                'reporting_host': "127.0.0.1",
                'reporting_port': 5775,
            },
            'logging': True,
        },
        service_name=service,
    )
    return config.initialize_tracer()

tracer = init_tracer('voting')

def get_redis():
    if not hasattr(g, 'redis'):
        g.redis = Redis(host="redis", db=0, socket_timeout=5)
    return g.redis

@app.route("/", methods=['POST','GET'])
def hello():
    with tracer.start_active_span('booking') as scope:
        voter_id = request.cookies.get('voter_id')

        if not voter_id:
            voter_id = hex(random.getrandbits(64))[2:-1]

        scope.span.set_tag('movie', voter_id)

        vote = None

        if request.method == 'POST':
            redis = get_redis()
            vote = request.form['vote']
            data = json.dumps({'voter_id': voter_id, 'vote': vote})
            redis.rpush('votes', data)

        resp = make_response(render_template(
            'index.html',
            option_a=option_a,
            option_b=option_b,
            hostname=hostname,
            vote=vote,
        ))
        resp.set_cookie('voter_id', voter_id)
        return resp


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True, threaded=True)
    # yield to IOLoop to flush the spans
    time.sleep(2)
    tracer.close()

