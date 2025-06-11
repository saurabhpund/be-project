import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import axios from 'axios';
import Login from '../pages/Login';
import Signup from '../pages/Signup';

// Mock axios
jest.mock('axios');

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  clear: jest.fn()
};
global.localStorage = localStorageMock;

// Mock window.location
const mockLocation = { href: '' };
delete window.location;
window.location = mockLocation;

// Helper function to render components with router
const renderWithRouter = (component) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('Authentication Tests', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
    localStorage.clear();
  });

  describe('Login Component Tests', () => {
    test('renders login form with all required fields', () => {
      renderWithRouter(<Login />);
      
      expect(screen.getByPlaceholderText(/Enter username/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Enter email/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Enter password/i)).toBeInTheDocument();
      expect(screen.getByText(/Select Role/i)).toBeInTheDocument();
      expect(screen.getByText(/Login/i)).toBeInTheDocument();
    });

    test('shows error when form is submitted with empty fields', async () => {
      renderWithRouter(<Login />);
      
      fireEvent.click(screen.getByText(/Login/i));
      
      expect(await screen.findByText(/All fields are required/i)).toBeInTheDocument();
    });

    test('successful login flow', async () => {
      const mockResponse = {
        data: {
          success: true,
          token: 'test-token',
          user_data: { username: 'testuser', role: 'student' }
        }
      };
      axios.post.mockResolvedValueOnce(mockResponse);

      renderWithRouter(<Login />);

      // Fill in the form
      fireEvent.change(screen.getByPlaceholderText(/Enter username/i), {
        target: { value: 'testuser' }
      });
      fireEvent.change(screen.getByPlaceholderText(/Enter email/i), {
        target: { value: 'test@example.com' }
      });
      fireEvent.change(screen.getByPlaceholderText(/Enter password/i), {
        target: { value: 'password123' }
      });
      fireEvent.change(screen.getByDisplayValue(/Select Role/i), {
        target: { value: 'student' }
      });

      // Submit the form
      fireEvent.click(screen.getByText(/Login/i));

      await waitFor(() => {
        expect(axios.post).toHaveBeenCalledWith(
          expect.stringContaining('/auth/login'),
          {
            username: 'testuser',
            email: 'test@example.com',
            password: 'password123',
            role: 'student'
          },
          expect.any(Object)
        );
        expect(localStorage.setItem).toHaveBeenCalledWith('token', 'test-token');
        expect(localStorage.setItem).toHaveBeenCalledWith('username', 'testuser');
        expect(window.location.href).toBe('/dashboard');
      });
    });

    test('handles login failure', async () => {
      axios.post.mockRejectedValueOnce(new Error('Invalid credentials'));

      renderWithRouter(<Login />);

      // Fill in the form
      fireEvent.change(screen.getByPlaceholderText(/Enter username/i), {
        target: { value: 'testuser' }
      });
      fireEvent.change(screen.getByPlaceholderText(/Enter email/i), {
        target: { value: 'test@example.com' }
      });
      fireEvent.change(screen.getByPlaceholderText(/Enter password/i), {
        target: { value: 'wrongpassword' }
      });
      fireEvent.change(screen.getByDisplayValue(/Select Role/i), {
        target: { value: 'student' }
      });

      // Submit the form
      fireEvent.click(screen.getByText(/Login/i));

      expect(await screen.findByText(/Invalid Credentials/i)).toBeInTheDocument();
    });
  });

  describe('Signup Component Tests', () => {
    test('renders signup form with all required fields', () => {
      renderWithRouter(<Signup />);
      
      expect(screen.getByPlaceholderText(/Enter username/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Enter your email/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Enter password/i)).toBeInTheDocument();
      expect(screen.getByText(/Select Role/i)).toBeInTheDocument();
      expect(screen.getByText(/Signup/i)).toBeInTheDocument();
    });

    test('successful signup flow', async () => {
      const mockResponse = {
        data: {
          success: true,
          token: 'test-token',
          message: 'User registered successfully'
        }
      };
      axios.post.mockResolvedValueOnce(mockResponse);

      renderWithRouter(<Signup />);

      // Fill in the form
      fireEvent.change(screen.getByPlaceholderText(/Enter username/i), {
        target: { value: 'newuser' }
      });
      fireEvent.change(screen.getByPlaceholderText(/Enter your email/i), {
        target: { value: 'new@example.com' }
      });
      fireEvent.change(screen.getByPlaceholderText(/Enter password/i), {
        target: { value: 'password123' }
      });
      fireEvent.change(screen.getByDisplayValue(/Select Role/i), {
        target: { value: 'student' }
      });

      // Submit the form
      fireEvent.click(screen.getByText(/Signup/i));

      await waitFor(() => {
        expect(axios.post).toHaveBeenCalledWith(
          expect.stringContaining('/auth/signup'),
          {
            username: 'newuser',
            email: 'new@example.com',
            password: 'password123',
            role: 'student'
          },
          expect.any(Object)
        );
        expect(localStorage.setItem).toHaveBeenCalledWith('token', 'test-token');
        expect(window.location.href).toBe('/dashboard');
      });
    });

    test('handles signup failure - username already exists', async () => {
      axios.post.mockRejectedValueOnce({
        response: {
          data: {
            success: false,
            message: 'Username already exists'
          }
        }
      });

      renderWithRouter(<Signup />);

      // Fill in the form
      fireEvent.change(screen.getByPlaceholderText(/Enter username/i), {
        target: { value: 'existinguser' }
      });
      fireEvent.change(screen.getByPlaceholderText(/Enter your email/i), {
        target: { value: 'existing@example.com' }
      });
      fireEvent.change(screen.getByPlaceholderText(/Enter password/i), {
        target: { value: 'password123' }
      });
      fireEvent.change(screen.getByDisplayValue(/Select Role/i), {
        target: { value: 'student' }
      });

      // Submit the form
      fireEvent.click(screen.getByText(/Signup/i));

      expect(await screen.findByText(/Username already exists/i)).toBeInTheDocument();
    });

    test('validates password length', async () => {
      renderWithRouter(<Signup />);

      // Fill in the form with short password
      fireEvent.change(screen.getByPlaceholderText(/Enter username/i), {
        target: { value: 'newuser' }
      });
      fireEvent.change(screen.getByPlaceholderText(/Enter your email/i), {
        target: { value: 'new@example.com' }
      });
      fireEvent.change(screen.getByPlaceholderText(/Enter password/i), {
        target: { value: 'short' }
      });
      fireEvent.change(screen.getByDisplayValue(/Select Role/i), {
        target: { value: 'student' }
      });

      // Submit the form
      fireEvent.click(screen.getByText(/Signup/i));

      expect(await screen.findByText(/Password must be at least 8 characters/i)).toBeInTheDocument();
    });
  });
}); 