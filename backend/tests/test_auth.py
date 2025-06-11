import pytest
import bcrypt
import jwt
from unittest.mock import patch, MagicMock
from app import create_app
from config import Config

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_db():
    with patch('app.db') as mock:
        yield mock

class TestAuth:
    def test_signup_success(self, client, mock_db):
        # Mock database operations
        mock_db["users"].find_one.return_value = None
        mock_db["users"].insert_one.return_value = None

        # Test data
        test_data = {
            "username": "testuser",
            "password": "password123",
            "email": "test@example.com",
            "role": "student"
        }

        # Make request
        response = client.post('/auth/signup', json=test_data)

        # Assertions
        assert response.status_code == 201
        assert response.json['success'] is True
        assert 'token' in response.json
        assert response.json['message'] == 'User registered successfully'

        # Verify database calls
        mock_db["users"].find_one.assert_called_once_with({"username": test_data["username"]})
        mock_db["users"].insert_one.assert_called_once()

    def test_signup_duplicate_username(self, client, mock_db):
        # Mock database to return existing user
        mock_db["users"].find_one.return_value = {"username": "testuser"}

        # Test data
        test_data = {
            "username": "testuser",
            "password": "password123",
            "email": "test@example.com",
            "role": "student"
        }

        # Make request
        response = client.post('/auth/signup', json=test_data)

        # Assertions
        assert response.status_code == 409
        assert response.json['success'] is False
        assert response.json['message'] == 'Username already exists'

    def test_signup_missing_fields(self, client):
        # Test data with missing fields
        test_data = {
            "username": "testuser",
            "password": "password123"
            # Missing email and role
        }

        # Make request
        response = client.post('/auth/signup', json=test_data)

        # Assertions
        assert response.status_code == 400
        assert response.json['success'] is False
        assert 'Missing' in response.json['message']

    def test_login_success(self, client, mock_db):
        # Create hashed password
        hashed_password = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt())
        
        # Mock database to return user
        mock_db["users"].find_one.return_value = {
            "username": "testuser",
            "password": hashed_password,
            "email": "test@example.com",
            "role": "student"
        }

        # Test data
        test_data = {
            "username": "testuser",
            "password": "password123"
        }

        # Make request
        response = client.post('/auth/login', json=test_data)

        # Assertions
        assert response.status_code == 200
        assert response.json['success'] is True
        assert 'token' in response.json
        assert response.json['message'] == 'Login successful'
        assert 'user_data' in response.json

    def test_login_invalid_credentials(self, client, mock_db):
        # Mock database to return user
        mock_db["users"].find_one.return_value = {
            "username": "testuser",
            "password": bcrypt.hashpw("correctpassword".encode('utf-8'), bcrypt.gensalt()),
            "email": "test@example.com",
            "role": "student"
        }

        # Test data with wrong password
        test_data = {
            "username": "testuser",
            "password": "wrongpassword"
        }

        # Make request
        response = client.post('/auth/login', json=test_data)

        # Assertions
        assert response.status_code == 401
        assert response.json['success'] is False
        assert response.json['message'] == 'Invalid credentials'

    def test_login_user_not_found(self, client, mock_db):
        # Mock database to return no user
        mock_db["users"].find_one.return_value = None

        # Test data
        test_data = {
            "username": "nonexistentuser",
            "password": "password123"
        }

        # Make request
        response = client.post('/auth/login', json=test_data)

        # Assertions
        assert response.status_code == 404
        assert response.json['success'] is False
        assert response.json['message'] == 'User not found'

    def test_verify_token_success(self, client):
        # Create test token
        test_data = {
            "username": "testuser",
            "role": "student"
        }
        token = jwt.encode(test_data, Config.JWT_SECRET, algorithm="HS256")

        # Make request with token
        response = client.get('/auth/verify', headers={'Authorization': f'Bearer {token}'})

        # Assertions
        assert response.status_code == 200
        assert response.json['success'] is True
        assert response.json['message'] == 'Token is valid'
        assert response.json['user_data']['username'] == test_data['username']
        assert response.json['user_data']['role'] == test_data['role']

    def test_verify_token_missing(self, client):
        # Make request without token
        response = client.get('/auth/verify')

        # Assertions
        assert response.status_code == 401
        assert response.json['success'] is False
        assert response.json['message'] == 'Token is missing'

    def test_verify_token_invalid(self, client):
        # Make request with invalid token
        response = client.get('/auth/verify', headers={'Authorization': 'Bearer invalid_token'})

        # Assertions
        assert response.status_code == 401
        assert response.json['success'] is False
        assert response.json['message'] == 'Invalid token' 