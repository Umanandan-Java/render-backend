from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import mysql.connector
import jwt
import datetime

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173"], supports_credentials=True)
 # Allows cookies to be passed from frontend
app.config['SECRET_KEY'] = 'your_super_secret_key'  # Replace with a secure key in production

# --- DB Connection ---
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "hopper.proxy.rlwy.net"),
        port=int(os.getenv("DB_PORT", 31860)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "GKdnjVtectMPqhifAkiaAzqRQdYCnCty"),
        database=os.getenv("DB_NAME", "railway")
    )


def verify_jwt():
    token = request.cookies.get('token')
    if not token:
        return None
    try:
        decoded = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return decoded
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

@app.route('/create_account', methods=['POST'])
def create_account():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM useraccounts WHERE username = %s", (username,))
        if cursor.fetchone():
            return jsonify({'error': 'Username already exists'}), 409

        sql = "INSERT INTO useraccounts (username, password) VALUES (%s, %s)"
        cursor.execute(sql, (username, password))
        connection.commit()
        return jsonify({'message': 'Account created successfully'}), 201

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500

    finally:
        cursor.close()
        connection.close()

# --- Login (set JWT cookie) ---
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM useraccounts WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and user['password'] == password:
            token = jwt.encode({
                'username': username,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=2)
            }, app.config['SECRET_KEY'])

            response = make_response(jsonify({'success': True}))
            response.set_cookie('token', token, httponly=True, samesite='Strict')
            return response, 200

        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

    except mysql.connector.Error as err:
        return jsonify({'message': f"Error: {err}"}), 500

    finally:
        cursor.close()
        connection.close()

# --- Student Registration (Protected) ---
@app.route('/datasubmission', methods=['POST'])
def handlesubmission():
    user = verify_jwt()
    if not user:
        return jsonify({'message': 'Unauthorized'}), 401

    data = request.get_json()
    name = data.get('name')
    course = data.get('course')
    mobile = data.get('mobile')
    location = data.get('location')

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        sql = "INSERT INTO students_info (name, course, mobile, location) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (name, course, mobile, location))
        connection.commit()
        return jsonify({'message': 'Student registered successfully'}), 201

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500

    finally:
        cursor.close()
        connection.close()

@app.route('/admin/data', methods=['GET'])
def admin_data():
    user = verify_jwt()
    if not user:
        return jsonify({'message': 'Unauthorized'}), 401

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM students_info")
        result = cursor.fetchall()
        return jsonify(result), 200

    except mysql.connector.Error as err:
        return jsonify({'error': str(err)}), 500

    finally:
        cursor.close()
        connection.close()

@app.route('/logout', methods=['POST'])
def logout():
    response = make_response(jsonify({'message': 'Logged out successfully'}))
    response.set_cookie('token', '', expires=0, httponly=True, samesite='Strict')
    return response, 200

# --- Run App ---
if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=5000)

