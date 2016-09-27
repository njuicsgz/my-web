import sys
import os
import sys
import time
from flask import Flask, render_template, request
import flask
import json
import uuid

def patch_broken_pipe_error():
    """Monkey Patch BaseServer.handle_error to not write
    a stacktrace to stderr on broken pipe.
    http://stackoverflow.com/a/7913160"""
    import sys
    from SocketServer import BaseServer

    handle_error = BaseServer.handle_error

    def my_handle_error(self, request, client_address):
        type, err, tb = sys.exc_info()
        # there might be better ways to detect the specific erro
	print "got error: %s" % repr(err)
        if repr(err) == "error(32, 'Broken pipe')":
            # you may ignore it...
	    print "got pipe broken error"
        else:
            handle_error(self, request, client_address)

    BaseServer.handle_error = my_handle_error


patch_broken_pipe_error()

class AppInfo:
    def __init__(self):
        self.name = 'my-app'
        self.version = 1.4
        self.ID = uuid.uuid1().get_hex()
        self.is_ready = False
        self.status = 'stopped'

    def timer(self):
        while True:
            now = time.time()
            if self.status == 'starting':
                if now - self.start_time >= 5:
                    self.status = 'running'
                    self.is_ready = True
                    self.start_left_time = 0
                else:
                    self.start_left_time = int(5 - (now - self.start_time))
            yield

    def stop(self):
        self.status = 'stopped'
        self.start_time = None
        self.is_ready = False

    def start(self):
        self.status = 'starting'
        self.is_ready = False
        self.start_time = time.time()
        self.start_left_time = 5

def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

def make_status_response(code, message=''):
    response = flask.make_response(json.dumps({'kind': 'Status', 'code': code, 'message': message}), code)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.headers.pop('Server', None)
    response.status_code = code
    return response

app = Flask(__name__)
app_info = AppInfo()
app_info.start()
timer = app_info.timer()

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.route("/")
def index():
    timer.next()
    return render_template('index.html', app_info = app_info)

@app.route('/ping')
def ping():
    timer.next()
    if app_info.is_ready:
        return make_status_response(200)
    else:
        return make_status_response(500)

@app.route('/stop', methods=['POST'])
def stop():
    app_info.stop()
    return flask.redirect(flask.url_for('index'))

@app.route('/start', methods=['POST'])
def start():
    app_info.start()
    return flask.redirect(flask.url_for('index'))

@app.route('/kill', methods=['POST'])
def kill():
    shutdown_server()
    return flask.redirect(flask.url_for('index'))

def usage():
    print 'python main.py IP PORT'

if len(sys.argv) != 3:
    usage()
    sys.exit(1)

app.run(host=sys.argv[1], port=int(sys.argv[2]), debug=False, use_reloader=False, threaded=True)

