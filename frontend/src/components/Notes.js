import React, { useEffect, useState } from 'react';
import { getNotes } from '../api/api';

const Notes = () => {
    const [notes, setNotes] = useState([]);

    useEffect(() => {
        async function fetchNotes() {
            const data = await getNotes();
            setNotes(data);
        }
        fetchNotes();
    }, []);

    return (
        <div>
            <h1>Notes</h1>
            <ul>
                {notes.map((note) => (
                    <li key={note.id}>
                        <h2>{note.title}</h2>
                        <p>{note.content}</p>
                    </li>
                ))}
            </ul>
        </div>
    );
};

export default Notes;
