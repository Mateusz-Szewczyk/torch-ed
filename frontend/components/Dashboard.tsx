'use client';

import React, { useEffect, useState, useContext } from 'react';
import {
    BarChart, Bar,
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
    session_durations: { date: string; duration: number }[];
}


const Dashboard: React.FC = () => {
    const { isAuthenticated } = useContext(AuthContext);
    const [data, setData] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [progress, setProgress] = useState<number>(0);
    const [error, setError] = useState<string | null>(null);

    const [filters, setFilters] = useState<{
        dateRange: [string | null, string | null];
        examId: number | null;
        deckId: number | null;
    }>({
        dateRange: [null, null],
        examId: null,
        deckId: null,
    });

    useEffect(() => {
        const fetchData = async () => {
            setProgress(10);
            try {
                if (!isAuthenticated) {
                    throw new Error('Unauthorized. Please log in.');
                }

                let queryParams = '';
                if (filters.dateRange[0] && filters.dateRange[1]) {
                    queryParams += `date_start=${filters.dateRange[0]}&date_end=${filters.dateRange[1]}&`;
                }
                if (filters.examId) {
                    queryParams += `exam_id=${filters.examId}&`;
                }
                if (filters.deckId) {
                    queryParams += `deck_id=${filters.deckId}&`;
                }

                const response = await fetch(`/api/dashboard?${queryParams}`, {
                    credentials: 'include',
                });

                setProgress(60);

                if (!response.ok) {
                    throw new Error('Failed to fetch data.');
                }

                const result: DashboardData = await response.json();
                setData(result);
                setProgress(100);
            } catch (err) {
                console.error(err);
                setError('Błąd podczas ładowania danych.');
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [filters, isAuthenticated]);

    if (loading) {
        return (
            <div className="loading-screen">
                <p>Ładowanie danych... {progress}%</p>
                <div className="progress-bar" style={{ width: `${progress}%`, backgroundColor: '#4caf50', height: '5px' }}></div>
            </div>
        );
    }

    if (error) {
        return <div className="text-red-600">{error}</div>;
    }

    if (!data) {
        return <div className="text-center">Brak danych do wyświetlenia.</div>;
    }

    const sessionDurations = data.session_durations.map(({ date, duration }) => ({
        date,
        duration,
    }));

    const activeDays = data.study_sessions.reduce<Record<string, number>>((acc, session) => {
        const day = new Date(session.started_at).toLocaleDateString('pl-PL', { weekday: 'long' });
        acc[day] = (acc[day] || 0) + 1;
        return acc;
    }, {});

    const activeDaysData = Object.keys(activeDays).map((day) => ({
        day,
        sessions: activeDays[day],
    }));

    return (
        <div className="p-4">
            <h2 className="text-2xl font-bold mb-6">Twój Dashboard</h2>

            {/* Filtry */}
            <div className="filters mb-8">
                <label>
                    Od:
                    <input
                        type="date"
                        onChange={(e) =>
                            setFilters({
                                ...filters,
                                dateRange: [e.target.value, filters.dateRange[1]],
                            })
                        }
                    />
                </label>
                <label>
                    Do:
                    <input
                        type="date"
                        onChange={(e) =>
                            setFilters({
                                ...filters,
                                dateRange: [filters.dateRange[0], e.target.value],
                            })
                        }
                    />
                </label>
                <label>
                    Egzamin:
                    <select
                        onChange={(e) =>
                            setFilters({ ...filters, examId: e.target.value ? parseInt(e.target.value) : null })
                        }
                    >
                        <option value="">Wybierz egzamin</option>
                        {data.exam_results.map((exam) => (
                            <option key={exam.id} value={exam.id}>
                                Egzamin {exam.id}
                            </option>
                        ))}
                    </select>
                </label>
                <label>
                    Zestaw fiszek:
                    <select
                        onChange={(e) =>
                            setFilters({ ...filters, deckId: e.target.value ? parseInt(e.target.value) : null })
                        }
                    >
                        <option value="">Wybierz zestaw</option>
                        {data.study_sessions.map((session) => (
                            <option key={session.deck_id} value={session.deck_id}>
                                Zestaw {session.deck_id}
                            </option>
                        ))}
                    </select>
                </label>
            </div>

            {/* Czas spędzony na sesjach nauki */}
            <div className="mb-8">
                <h3 className="text-xl font-semibold mb-4">Czas Spędzony na Sesjach Nauki</h3>
                <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={sessionDurations}>
                        <XAxis dataKey="date" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="duration" name="Czas (godziny)" fill="#8884d8" />
                    </BarChart>
                </ResponsiveContainer>
            </div>

            {/* Najbardziej aktywne dni tygodnia */}
            <div className="mb-8">
                <h3 className="text-xl font-semibold mb-4">Najbardziej Aktywne Dni Tygodnia</h3>
                <ResponsiveContainer width="100%" height={300}>
                    <RadarChart data={activeDaysData}>
                        <PolarGrid />
                        <PolarAngleAxis dataKey="day" />
                        <PolarRadiusAxis />
                        <Radar dataKey="sessions" name="Sesje" fill="#82ca9d" fillOpacity={0.6} />
                        <Legend />
                    </RadarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default Dashboard;
