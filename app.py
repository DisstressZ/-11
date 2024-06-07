from flask import Flask, Response, request, jsonify, render_template
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
import io

try:
    from werkzeug.wsgi import FileWrapper
except ImportError:
    from werkzeug import FileWrapper

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
jwt = JWTManager(app)
db = SQLAlchemy(app)

global STATE
STATE = {}

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


with app.app_context():
    db.create_all()


@app.route('/')
def root():
    return render_template('/index.html')

@app.route('/redirect', methods=['POST'])
@jwt_required()
def rd():
    req = request.get_json()
    key = req['_key']

    if req['filename'] == STATE[key]['filename']:
        attachment = io.BytesIO(b'')
    else:
        attachment = io.BytesIO(STATE[key]['im'])

    w = FileWrapper(attachment)
    resp = Response(w, mimetype='text/plain', direct_passthrough=True)
    resp.headers['filename'] = STATE[key]['filename']

    return resp

@app.route('/posted_events', methods=['POST'])
@jwt_required()
def event_post():
    global STATE

    req = request.get_json()
    key = req['_key']

    STATE[key]['events'].append(request.get_json())
    return jsonify({'ok': True})


@app.route('/login', methods=['POST'])
def login():
    req = request.get_json()
    username = req.get('username', None)
    password = req.get('password', None)

    user = User.query.filter_by(username=username, password=password).first()
    if not user:
        return jsonify({'msg': 'Bad username or password'}), 401

    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token)

@app.route('/register', methods=['POST'])
def register():
    req = request.get_json()
    username = req.get('username', None)
    password = req.get('password', None)

    if User.query.filter_by(username=username).first():
        return jsonify({'msg': 'Username already exists'}), 400

    user = User(username=username, password=password)
    db.session.add(user)
    db.session.commit()

    return jsonify({'msg': 'User registered successfully'})


@app.route('/new_sessions', methods=['POST'])
@jwt_required()
def new_session():
    global STATE

    req = request.get_json()
    key = req['_key']
    STATE[key] = {
        'im': b'',
        'filename': 'none.png',
        'events': []
    }

    return jsonify({'ok': True})

@app.route('/capture_and_send', methods=['POST'])
@jwt_required()
def capture_post():
    global STATE

    with io.BytesIO() as image_data:
        filename = list(request.files.keys())[0]
        key = filename.split('_')[1]
        request.files[filename].save(image_data)
        STATE[key]['im'] = image_data.getvalue()
        STATE[key]['filename'] = filename

    return jsonify({'ok': True})

@app.route('/execute_events', methods=['POST'])
@jwt_required()
def events_get():
    req = request.get_json()
    key = req['_key']
    events_to_execute = STATE[key]['events'].copy()
    STATE[key]['events'] = []
    return jsonify({'events': events_to_execute})

if __name__ == '__main__':
    app.run('0.0.0.0')
