'use client';

import React, { useEffect, useState, useContext } from 'react';
import {
    LineChart, Line,
    BarChart, Bar,
    PieChart, Pie, Cell,
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
    next_review: string | null;
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

interface DashboardResponse {
    study_records: StudyRecord[];
    user_flashcards: UserFlashcard[];
    study_sessions: StudySession[];
    exam_result_answers: ExamResultAnswer[];
    exam_results: ExamResult[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL;
const DASHBOARD_URL = `${API_BASE_URL}/dashboard/`;

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#FF6666'];

const Dashboard: React.FC = () => {
    const { isAuthenticated } = useContext(AuthContext);
    const [data, setData] = useState<DashboardResponse | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchDashboardData = async () => {
            try {
                if (!isAuthenticated) {
                    throw new Error('Unauthorized. Please log in.');
                }

                const response = await fetch(DASHBOARD_URL, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    credentials: 'include',
                });

                if (!response.ok) {
                    if (response.status === 401) {
                        throw new Error('Unauthorized. Please log in.');
                    }
                    throw new Error('Failed to fetch dashboard data.');
                }

                const result: DashboardResponse = await response.json();
                setData(result);
                setLoading(false);
            } catch (err: unknown) {
                console.error('Error fetching dashboard data:', err);
                if (err instanceof Error) {
                    setError(err.message);
                } else {
                    setError('Failed to fetch data.');
                }
                setLoading(false);
            }
        };

        fetchDashboardData();
    }, [isAuthenticated]);

    if (loading) return <p>Loading data...</p>;
    if (error) return <p>{error}</p>;
    if (!data) return <p>No data available.</p>;

    // Data preparation
    const averageRatingData = Object.entries(
        data.study_records.reduce<{ [key: string]: { total: number; count: number } }>((acc, record) => {
            const date = record.reviewed_at.split('T')[0];
            if (!acc[date]) {
                acc[date] = { total: record.rating, count: 1 };
            } else {
                acc[date].total += record.rating;
                acc[date].count += 1;
            }
            return acc;
        }, {})
    ).map(([date, { total, count }]) => ({
        date,
        average_rating: total / count,
    }));

    const sessionsOverTime = Object.entries(
        data.study_sessions.reduce<{ [key: string]: number }>((acc, session) => {
            const date = session.started_at.split('T')[0];
            acc[date] = (acc[date] || 0) + 1;
            return acc;
        }, {})
    ).map(([date, count]) => ({
        date,
        count,
    }));

    const pieData = [
        { name: 'Correct Answers', value: data.exam_result_answers.filter(ans => ans.is_correct).length },
        { name: 'Incorrect Answers', value: data.exam_result_answers.filter(ans => !ans.is_correct).length },
    ];

    return (
        <div className="p-4">
            <h2 className="text-2xl font-bold mb-6">Your Dashboard</h2>

            <div className="mb-8">
                <h3 className="text-xl font-semibold mb-4">Average Rating Per Day</h3>
                <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={averageRatingData}>
                        <XAxis dataKey="date" />
                        <YAxis domain={[0, 5]} />
                        <Tooltip />
                        <Legend />
                        <Line type="monotone" dataKey="average_rating" stroke="#8884d8" />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            <div className="mb-8">
                <h3 className="text-xl font-semibold mb-4">Study Sessions Over Time</h3>
                <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={sessionsOverTime}>
                        <XAxis dataKey="date" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="count" fill="#82ca9d" />
                    </BarChart>
                </ResponsiveContainer>
            </div>

            <div className="mb-8">
                <h3 className="text-xl font-semibold mb-4">Answer Accuracy</h3>
                <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                        <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100}>
                            {pieData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                            ))}
                        </Pie>
                        <Tooltip />
                        <Legend />
                    </PieChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default Dashboard;
