import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000/api/'; // Django backend URL

export const getNotes = async () => {
    try {
        const response = await axios.get(`${API_URL}notes/`);
        return response.data;
    } catch (error) {
        console.error('Error fetching notes:', error);
        return [];
    }
};

// Add more API functions as needed
