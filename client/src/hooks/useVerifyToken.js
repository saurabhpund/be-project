import axios from "axios";
import { useEffect, useState } from "react";

export const useVerifyToken = () => {
  const [user, setUser] = useState(null);  
  const token = localStorage.getItem('token');
  const baseURL = "http://192.168.161.57"

  const verifyToken = async () => {
    if (token) {
      try {
        const response = await axios.get(`${baseURL}:5000/auth/verify`, {
          headers: {
            'Authorization': 'Bearer ' + token,
          },
        });

        setUser(response.data.user_data);  
      } catch (error) {
        console.error('Error verifying token:', error);
        setUser(null);  
      }
    } else {
      setUser(null); 
    }
  };

  useEffect(() => {
    verifyToken();
  }, [token]);  

  return user; 
};
