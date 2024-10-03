import axios from 'axios';


export const DJANGO_API_URL = process.env.REACT_APP_DJANGO_API_URL || 'http://torched:8000';
export const RAG_API_URL = process.env.REACT_APP_RAG_API_URL || 'http://rag:8001';

export const getNotes = async () => {
    try {
        const response = await axios.get(`${DJANGO_API_URL}notes/`);
        return response.data;
    } catch (error) {
        console.error('Error fetching notes:', error);
        return [];
    }
};

// Add more API functions as needed
