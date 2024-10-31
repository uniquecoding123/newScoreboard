from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://scoreboard_573h_user:vE1hGFQ9bOIrlpOEzAgNHUOUEDMo7bBl@dpg-csg2fte8ii6s73btndi0-a.oregon-postgres.render.com/scoreboard_573h'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'

# Initialize extensions
db = SQLAlchemy(app)
app.app_context().push()
jwt = JWTManager(app)
CORS(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    players = db.relationship('Player', backref='owner', lazy=True)
    team_stats = db.relationship('TeamStats', backref='owner', lazy=True)

class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TeamStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team1_name = db.Column(db.String(80), nullable=False)
    team1_wins = db.Column(db.Integer, nullable=False)
    team2_name = db.Column(db.String(80), nullable=False)
    team2_wins = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Routes
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "Username already exists"}), 409

    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"msg": "User registered successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username).first()

    if not user or not user.password:
        return jsonify({"msg": "Bad username or password"}), 401

    access_token = create_access_token(identity=user.id)
    return jsonify(access_token=access_token), 200

@app.route('/players', methods=['POST'])
@jwt_required()
def add_player():
    user_id = get_jwt_identity()
    data = request.get_json()
    name = data.get('name')
    score = data.get('score')

    # Check if player already exists
    existing_player = Player.query.filter_by(name=name).first()
    if existing_player:
        # Update the player's score
        existing_player.score += score
        db.session.commit()
        return jsonify({"msg": "Player score updated successfully"}), 200

    # If player does not exist, create a new one
    new_player = Player(name=name, score=score, user_id=user_id)
    db.session.add(new_player)
    db.session.commit()
    return jsonify({"msg": "Player added successfully"}), 201

@app.route('/players', methods=['GET'])
@jwt_required()
def get_players():
    user_id = get_jwt_identity()
    players = Player.query.filter_by(user_id=user_id).order_by(Player.score.desc()).all()
    return jsonify([{
        'id': player.id,
        'name': player.name,
        'score': player.score,
        'created_at': player.created_at
    } for player in players]), 200

@app.route('/team', methods=['POST'])
@jwt_required()
def add_team_stats():
    user_id = get_jwt_identity()
    data = request.get_json()
    team1_name = data.get('team1_name')
    team1_wins = data.get('team1_wins')
    team2_name = data.get('team2_name')
    team2_wins = data.get('team2_wins')

    # Check if both teams exist in the database for the logged-in user
    existing_stats = TeamStats.query.filter(
        (TeamStats.user_id == user_id) &  # Ensure we are checking for the current user
        (TeamStats.team1_name == team1_name) &
        (TeamStats.team2_name == team2_name)
    ).first()  # Use .first() to get a single record

    if existing_stats:
        # Update wins for Team 1 and Team 2
        existing_stats.team1_wins += team1_wins
        existing_stats.team2_wins += team2_wins
    else:
        # Create a new entry for the current user
        new_team_stats = TeamStats(
            team1_name=team1_name,
            team1_wins=team1_wins,
            team2_name=team2_name,
            team2_wins=team2_wins,
            user_id=user_id  # Associate the stats with the current user
        )
        db.session.add(new_team_stats)

    db.session.commit()
    return jsonify({"msg": "Team stats added/updated successfully"}), 201


@app.route('/team', methods=['GET'])
@jwt_required()
def get_team_stats():
    user_id = get_jwt_identity()
    team_stats = TeamStats.query.filter_by(user_id=user_id).all()
    return jsonify([{
        'id': stats.id,
        'team1_name': stats.team1_name,
        'team1_wins': stats.team1_wins,
        'team2_name': stats.team2_name,
        'team2_wins': stats.team2_wins
    } for stats in team_stats]), 200

if __name__ == '__main__':
    app.run(debug=True)
