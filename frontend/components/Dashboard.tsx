'use client';

import React, { useEffect, useState, useContext } from 'react';
import {
    LineChart, Line,
    BarChart, Bar,
    PieChart, Pie, Cell,
    RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
    XAxis, YAxis,
    Tooltip, Legend,
    ResponsiveContainer
} from 'recharts';
import { AuthContext } from '@/contexts/AuthContext';

interface StudyRecord {
    id: number;
    session_id: number | null;
    user_flashcard_id: number | null;
    rating: number;
    reviewed_at: string;
}

interface UserFlashcard {
    id: number;
    user_id: number;
    flashcard_id: number;
    ef: number;
    interval: number;
    repetitions: number;
    next_review: string;
}

interface StudySession {
    id: number;
    user_id: number;
    deck_id: number;
    started_at: string;
    completed_at: string | null;
}

interface ExamResultAnswer {
    id: number;
    exam_result_id: number;
    question_id: number;
    selected_answer_id: number;
    is_correct: boolean;
    answer_time: string;
}

interface ExamResult {
    id: number;
    exam_id: number;
    user_id: number;
    started_at: string;
    completed_at: string | null;
    score: number;
}

interface DashboardData {
    study_records: StudyRecord[];
    user_flashcards: UserFlashcard[];
    study_sessions: StudySession[];
    exam_result_answers: ExamResultAnswer[];
    exam_results: ExamResult[];
}


const Dashboard: React.FC = () => {
    const { isAuthenticated } = useContext(AuthContext);
    const [data, setData] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    const [filterDate, setFilterDate] = useState<{ start: string; end: string }>({
        start: '',
        end: '',
    });
    const [selectedExam, setSelectedExam] = useState<number | null>(null);
    const [selectedDeck, setSelectedDeck] = useState<number | null>(null);

    useEffect(() => {
        const fetchDashboardData = async () => {
            try {
                if (!isAuthenticated) {
                    throw new Error('Unauthorized. Please log in.');
                }

                const response = await fetch('/api/dashboard/', {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    credentials: 'include',
                });

                if (!response.ok) {
                    throw new Error('Failed to fetch dashboard data.');
                }

                const result: DashboardData = await response.json();
                setData(result);
            } catch (err: unknown) {
                console.error('Error fetching dashboard data:', err);
                setError(err instanceof Error ? err.message : 'Unexpected error occurred.');
            } finally {
                setLoading(false);
            }
        };

        fetchDashboardData();
    }, [isAuthenticated]);

    const handleFilterChange = () => {
        // Add logic here to filter `data` based on `filterDate`, `selectedExam`, and `selectedDeck`
    };

    if (loading) {
        return (
            <div className="loading-screen">
                <h2>Ładowanie danych...</h2>
                <progress className="loading-bar" />
            </div>
        );
    }

    if (error) {
        return <p>{error}</p>;
    }

    if (!data) {
        return <p>Brak danych do wyświetlenia.</p>;
    }

    // Filter data based on user selection
    const filteredStudyRecords = data.study_records.filter((record) => {
        const recordDate = new Date(record.reviewed_at).toISOString().split('T')[0];
        const startDate = filterDate.start || '1900-01-01';
        const endDate = filterDate.end || '2100-01-01';
        const withinDateRange = recordDate >= startDate && recordDate <= endDate;
        const matchesDeck = selectedDeck === null || record.session_id === selectedDeck;
        return withinDateRange && matchesDeck;
    });

    const filteredExamResults = data.exam_results.filter((exam) => {
        const examDate = new Date(exam.started_at).toISOString().split('T')[0];
        const startDate = filterDate.start || '1900-01-01';
        const endDate = filterDate.end || '2100-01-01';
        const withinDateRange = examDate >= startDate && examDate <= endDate;
        const matchesExam = selectedExam === null || exam.exam_id === selectedExam;
        return withinDateRange && matchesExam;
    });

    return (
        <div className="p-4">
            <h2 className="text-2xl font-bold mb-6">Twój Dashboard</h2>

            <div className="filters mb-8">
                <label>
                    Data od:
                    <input
                        type="date"
                        value={filterDate.start}
                        onChange={(e) => setFilterDate({ ...filterDate, start: e.target.value })}
                    />
                </label>
                <label>
                    Data do:
                    <input
                        type="date"
                        value={filterDate.end}
                        onChange={(e) => setFilterDate({ ...filterDate, end: e.target.value })}
                    />
                </label>
                <label>
                    Wybierz egzamin:
                    <select
                        value={selectedExam || ''}
                        onChange={(e) => setSelectedExam(Number(e.target.value) || null)}
                    >
                        <option value="">Wszystkie egzaminy</option>
                        {data.exam_results.map((exam) => (
                            <option key={exam.id} value={exam.exam_id}>
                                Egzamin {exam.exam_id}
                            </option>
                        ))}
                    </select>
                </label>
                <label>
                    Wybierz zestaw fiszek:
                    <select
                        value={selectedDeck || ''}
                        onChange={(e) => setSelectedDeck(Number(e.target.value) || null)}
                    >
                        <option value="">Wszystkie zestawy</option>
                        {data.study_sessions.map((session) => (
                            <option key={session.id} value={session.deck_id}>
                                Zestaw {session.deck_id}
                            </option>
                        ))}
                    </select>
                </label>
                <button onClick={handleFilterChange}>Filtruj</button>
            </div>

            {/* Visualization logic */}
            <div className="charts">
                <h3>Wizualizacje wyników po filtrach:</h3>
                <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={filteredStudyRecords}>
                        <XAxis dataKey="reviewed_at" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="rating" fill="#8884d8" />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default Dashboard;
