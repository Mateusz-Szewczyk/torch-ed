// src/components/Dashboard.tsx

'use client';

import React, { useEffect, useState } from 'react';
import {
    LineChart, Line,
    BarChart, Bar,
    PieChart, Pie, Cell,
    XAxis, YAxis,
    Tooltip, Legend,
    ResponsiveContainer
} from 'recharts';

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

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#FF6666'];

const Dashboard: React.FC = () => {
    const [data, setData] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchDashboardData = async () => {
            try {
                const token = localStorage.getItem('token'); // Upewnij się, że klucz 'token' jest zgodny z implementacją logowania
                const response = await fetch('/api/dashboard', {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': token ? `Bearer ${token}` : '',
                    },
                });

                if (!response.ok) {
                    if (response.status === 401) {
                        throw new Error('Unauthorized. Please log in.');
                    }
                    throw new Error('Failed to fetch dashboard data.');
                }

                const result: DashboardData = await response.json();
                setData(result);
                setLoading(false);
            } catch (err: unknown) {
                console.error('Error fetching dashboard data:', err);
                if (err instanceof Error) {
                    setError(err.message);
                } else {
                    setError('Nie udało się pobrać danych.');
                }
                setLoading(false);
            }
        };

        fetchDashboardData();
    }, []);

    if (loading) return <p>Ładowanie danych...</p>;
    if (error) return <p>{error}</p>;
    if (!data) return <p>Brak danych do wyświetlenia.</p>;

    // Przygotowanie danych do wizualizacji

    // 1. Średnia ocena fiszek na dzień
    const averageRatingPerDay = data.study_records.reduce<{ [key: string]: { total: number; count: number } }>((acc, record) => {
        const date = record.reviewed_at.split('T')[0];
        if (!acc[date]) {
            acc[date] = { total: record.rating, count: 1 };
        } else {
            acc[date].total += record.rating;
            acc[date].count += 1;
        }
        return acc;
    }, {});

    const averageRatingData = Object.keys(averageRatingPerDay).map(date => ({
        date,
        average_rating: averageRatingPerDay[date].total / averageRatingPerDay[date].count
    })).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

    // 2. Liczba sesji nauki w czasie
    const sessionsOverTime = data.study_sessions.map(session => ({
        date: session.started_at.split('T')[0],
        count: 1
    })).reduce<{ date: string; count: number }[]>((acc, session) => {
        const existing = acc.find(item => item.date === session.date);
        if (existing) {
            existing.count += 1;
        } else {
            acc.push({ date: session.date, count: 1 });
        }
        return acc;
    }, []).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

    // 3. Średnia ocena egzaminów w czasie
    const examScoresOverTime = data.exam_results.map(result => ({
        date: result.started_at.split('T')[0],
        score: result.score
    })).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

    // 4. Wskaźnik poprawnych odpowiedzi na egzaminach
    const totalAnswers = data.exam_result_answers.length;
    const correctAnswers = data.exam_result_answers.filter(answer => answer.is_correct).length;
    const incorrectAnswers = totalAnswers - correctAnswers;

    const pieData = [
        { name: 'Poprawne Odpowiedzi', value: correctAnswers },
        { name: 'Niepoprawne Odpowiedzi', value: incorrectAnswers }
    ];

    return (
        <div className="p-4">
            <h2 className="text-2xl font-bold mb-6">Twój Dashboard</h2>

            {/* Średnia Ocena Fiszek na Dzień */}
            <div className="mb-8">
                <h3 className="text-xl font-semibold mb-4">Średnia Ocena Fiszek na Dzień</h3>
                <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={averageRatingData}>
                        <XAxis dataKey="date" />
                        <YAxis domain={[0, 5]} />
                        <Tooltip />
                        <Legend />
                        <Line type="monotone" dataKey="average_rating" name="Średnia Ocena" stroke="#8884d8" />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            {/* Liczba Sesji Nauki w Czasie */}
            <div className="mb-8">
                <h3 className="text-xl font-semibold mb-4">Liczba Sesji Nauki w Czasie</h3>
                <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={sessionsOverTime}>
                        <XAxis dataKey="date" />
                        <YAxis allowDecimals={false} />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="count" name="Sesje Nauki" fill="#82ca9d" />
                    </BarChart>
                </ResponsiveContainer>
            </div>

            {/* Średnia Ocena Egzaminów w Czasie */}
            <div className="mb-8">
                <h3 className="text-xl font-semibold mb-4">Średnia Ocena Egzaminów w Czasie</h3>
                <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={examScoresOverTime}>
                        <XAxis dataKey="date" />
                        <YAxis domain={[0, 100]} />
                        <Tooltip />
                        <Legend />
                        <Line type="monotone" dataKey="score" name="Ocena Egzaminu" stroke="#8884d8" />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            {/* Wskaźnik Poprawnych Odpowiedzi na Egzaminach */}
            <div className="mb-8">
                <h3 className="text-xl font-semibold mb-4">Wskaźnik Poprawnych Odpowiedzi na Egzaminach</h3>
                <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                        <Pie
                            data={pieData}
                            dataKey="value"
                            nameKey="name"
                            cx="50%"
                            cy="50%"
                            outerRadius={100}
                            label
                        >
                            {pieData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                        </Pie>
                        <Tooltip />
                        <Legend />
                    </PieChart>
                </ResponsiveContainer>
                <p className="mt-2 text-center">Poprawne: {correctAnswers} | Niepoprawne: {incorrectAnswers}</p>
            </div>

            {/* Możesz dodać więcej wykresów, np. Efektywność fiszek, Harmonogram przeglądów, itp. */}
        </div>
    );

};

export default Dashboard;
