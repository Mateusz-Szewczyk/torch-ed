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

// Definicje interfejsów
interface ExamResult {
    id: number;
    exam_id: number;
    user_id: number;
    started_at: string;
    completed_at: string | null;
    score: number;
}

interface ExamResultAnswer {
    id: number;
    exam_result_id: number;
    question_id: number;
    selected_answer_id: number;
    is_correct: boolean;
    answer_time: string;
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

interface StudyRecord {
    id: number;
    session_id: number | null;
    user_flashcard_id: number | null;
    rating: number;
    reviewed_at: string;
}

interface StudySession {
    id: number;
    user_id: number;
    deck_id: number;
    started_at: string;
    completed_at: string | null;
}

interface DashboardData {
    exam_results: ExamResult[];
    exam_result_answers: ExamResultAnswer[];
    user_flashcards: UserFlashcard[];
    study_records: StudyRecord[];
    study_sessions: StudySession[];
    session_durations: { date: string; duration_hours: number }[];
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#FF6666'];

const Dashboard: React.FC = () => {
    const { isAuthenticated } = useContext(AuthContext);
    const [data, setData] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [progress, setProgress] = useState<number>(0);
    const [error, setError] = useState<string | null>(null);

    // Filtry
    const [filterStartDate, setFilterStartDate] = useState<string>('');
    const [filterEndDate, setFilterEndDate] = useState<string>('');
    const [selectedExamId, setSelectedExamId] = useState<number | null>(null);
    const [selectedDeckId, setSelectedDeckId] = useState<number | null>(null);

    useEffect(() => {
        const fetchDashboardData = async () => {
            try {
                setLoading(true);
                setProgress(10);

                if (!isAuthenticated) {
                    throw new Error('Unauthorized. Please log in.');
                }

                // Użyj zmiennej środowiskowej, jeśli jest skonfigurowana
                const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || '';
                const DASHBOARD_URL = `${API_BASE_URL}/dashboard`;

                const response = await fetch(DASHBOARD_URL, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    credentials: 'include',
                });

                setProgress(50);

                if (!response.ok) {
                    throw new Error('Failed to fetch dashboard data.');
                }

                const result: DashboardData = await response.json();
                setData(result);
                setProgress(100);
            } catch (err: unknown) {
                console.error('Error fetching dashboard data:', err);
                if (err instanceof Error) {
                    setError(err.message);
                } else {
                    setError('Failed to fetch data.');
                }
                setProgress(100);
            } finally {
                setLoading(false);
            }
        };

        fetchDashboardData();
    }, [isAuthenticated]);

    // Funkcja do filtrowania danych
    const getFilteredData = (data: DashboardData): DashboardData => {
        let filteredStudyRecords = data.study_records;
        let filteredExamResults = data.exam_results;

        // Filtruj według daty
        if (filterStartDate && filterEndDate) {
            const start = new Date(filterStartDate);
            const end = new Date(filterEndDate);

            filteredStudyRecords = data.study_records.filter(record => {
                const recordDate = new Date(record.reviewed_at);
                return recordDate >= start && recordDate <= end;
            });

            filteredExamResults = data.exam_results.filter(exam => {
                const examDate = new Date(exam.started_at);
                return examDate >= start && examDate <= end;
            });
        }

        // Filtruj według egzaminu
        if (selectedExamId) {
            filteredExamResults = filteredExamResults.filter(exam => exam.exam_id === selectedExamId);
        }

        // Filtruj według zestawu fiszek
        if (selectedDeckId) {
            filteredStudyRecords = filteredStudyRecords.filter(record => {
                const session = data.study_sessions.find(session => session.id === record.session_id);
                return session?.deck_id === selectedDeckId;
            });
        }

        return {
            ...data,
            study_records: filteredStudyRecords,
            exam_results: filteredExamResults,
        };
    };

    let filteredData: DashboardData | null = null;
    if (data) {
        filteredData = getFilteredData(data);
    }

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-screen">
                <h2 className="text-2xl mb-4">Ładowanie danych...</h2>
                <div className="w-1/2 bg-gray-300 rounded-full">
                    <div
                        className="bg-blue-500 text-xs font-medium text-blue-100 text-center p-0.5 leading-none rounded-full"
                        style={{ width: `${progress}%` }}
                    >
                        {progress}%
                    </div>
                </div>
            </div>
        );
    }

    if (error) {
        return <div className="text-red-500 text-center mt-10">{error}</div>;
    }

    if (!filteredData) {
        return <div className="text-center mt-10">Brak danych do wyświetlenia.</div>;
    }

    // Sekcja Egzaminów - 4 wykresy
    const examLineChartData = filteredData.exam_results.map(exam => ({
        date: exam.started_at.split('T')[0],
        score: exam.score,
    }));

    const examBarChartData = filteredData.exam_results.map(exam => ({
        date: exam.started_at.split('T')[0],
        score: exam.score,
    }));

    const averageExamScore =
        filteredData.exam_results.length > 0
            ? filteredData.exam_results.reduce((acc, exam) => acc + exam.score, 0) / filteredData.exam_results.length
            : 0;

    const examPieChartData = [
        {
            name: 'Średni wynik',
            value: averageExamScore,
        },
        {
            name: 'Pozostało do 100',
            value: 100 - averageExamScore,
        },
    ];

    const examRadarChartData = [
        {
            subject: 'Średni wynik',
            A: averageExamScore,
            fullMark: 100,
        },
    ];

    // Sekcja Fiszek - 4 wykresy
    const flashcardLineChartData = filteredData.study_records.map(record => ({
        date: record.reviewed_at.split('T')[0],
        rating: record.rating,
    }));

    const flashcardBarChartData = filteredData.study_records.map(record => ({
        date: record.reviewed_at.split('T')[0],
        rating: record.rating,
    }));

    const averageFlashcardRating =
        filteredData.study_records.length > 0
            ? filteredData.study_records.reduce((acc, record) => acc + record.rating, 0) / filteredData.study_records.length
            : 0;

    const flashcardPieChartData = [
        {
            name: 'Średnia ocena',
            value: averageFlashcardRating,
        },
        {
            name: 'Pozostało do 5',
            value: 5 - averageFlashcardRating,
        },
    ];

    const flashcardRadarChartData = [
        {
            subject: 'Średnia ocena',
            A: averageFlashcardRating,
            fullMark: 5,
        },
    ];

    return (
        <div className="p-4">
            <h2 className="text-2xl font-bold mb-6 text-center">Twój Dashboard</h2>

            {/* Filtry */}
            <div className="flex flex-wrap justify-center mb-8 space-x-4">
                <div>
                    <label htmlFor="start-date" className="block mb-2">
                        Data od:
                    </label>
                    <input
                        id="start-date"
                        type="date"
                        value={filterStartDate}
                        onChange={(e) => setFilterStartDate(e.target.value)}
                        className="border p-2 rounded"
                    />
                </div>
                <div>
                    <label htmlFor="end-date" className="block mb-2">
                        Data do:
                    </label>
                    <input
                        id="end-date"
                        type="date"
                        value={filterEndDate}
                        onChange={(e) => setFilterEndDate(e.target.value)}
                        className="border p-2 rounded"
                    />
                </div>
                <div>
                    <label htmlFor="exam-select" className="block mb-2">
                        Wybierz egzamin:
                    </label>
                    <select
                        id="exam-select"
                        value={selectedExamId ?? ''}
                        onChange={(e) => setSelectedExamId(e.target.value ? parseInt(e.target.value) : null)}
                        className="border p-2 rounded"
                    >
                        <option value="">Wszystkie</option>
                        {Array.from(new Set(data?.exam_results.map(exam => exam.exam_id))).map(examId => (
                            <option key={examId} value={examId}>
                                Egzamin {examId}
                            </option>
                        ))}
                    </select>
                </div>
                <div>
                    <label htmlFor="deck-select" className="block mb-2">
                        Wybierz zestaw fiszek:
                    </label>
                    <select
                        id="deck-select"
                        value={selectedDeckId ?? ''}
                        onChange={(e) => setSelectedDeckId(e.target.value ? parseInt(e.target.value) : null)}
                        className="border p-2 rounded"
                    >
                        <option value="">Wszystkie</option>
                        {Array.from(new Set(data?.study_sessions.map(session => session.deck_id))).map(deckId => (
                            <option key={deckId} value={deckId}>
                                Zestaw {deckId}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Sekcja Egzaminów */}
            <div className="mb-12">
                <h3 className="text-xl font-bold mb-4 text-center">Analiza Egzaminów</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* Wykres Liniowy - Wyniki Egzaminów w czasie */}
                    <div>
                        <h4 className="text-lg font-semibold mb-2">Wyniki Egzaminów w Czasie</h4>
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={examLineChartData}>
                                <XAxis dataKey="date" />
                                <YAxis domain={[0, 100]} />
                                <Tooltip />
                                <Legend />
                                <Line type="monotone" dataKey="score" name="Wynik" stroke="#82ca9d" />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>

                    {/* Wykres Słupkowy - Wyniki Egzaminów */}
                    <div>
                        <h4 className="text-lg font-semibold mb-2">Wyniki Egzaminów - Słupki</h4>
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={examBarChartData}>
                                <XAxis dataKey="date" />
                                <YAxis domain={[0, 100]} />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="score" name="Wynik" fill="#8884d8" />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>

                    {/* Wykres Kołowy - Średni Wynik Egzaminów */}
                    <div>
                        <h4 className="text-lg font-semibold mb-2">Średni Wynik Egzaminów</h4>
                        <ResponsiveContainer width="100%" height={300}>
                            <PieChart>
                                <Pie
                                    data={examPieChartData}
                                    dataKey="value"
                                    nameKey="name"
                                    cx="50%"
                                    cy="50%"
                                    outerRadius={100}
                                    label
                                >
                                    {examPieChartData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip />
                                <Legend />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>

                    {/* Wykres Radarowy - Średni Wynik Egzaminów */}
                    <div>
                        <h4 className="text-lg font-semibold mb-2">Średni Wynik Egzaminów - Radar</h4>
                        <ResponsiveContainer width="100%" height={300}>
                            <RadarChart data={examRadarChartData}>
                                <PolarGrid />
                                <PolarAngleAxis dataKey="subject" />
                                <PolarRadiusAxis angle={30} domain={[0, 100]} />
                                <Tooltip />
                                <Legend />
                                <Radar name="Średni Wynik" dataKey="A" stroke="#00C49F" fill="#00C49F" fillOpacity={0.6} />
                            </RadarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Sekcja Fiszek */}
            <div>
                <h3 className="text-xl font-bold mb-4 text-center">Analiza Fiszek</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* Wykres Liniowy - Oceny Fiszek w czasie */}
                    <div>
                        <h4 className="text-lg font-semibold mb-2">Oceny Fiszek w Czasie</h4>
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={flashcardLineChartData}>
                                <XAxis dataKey="date" />
                                <YAxis domain={[0, 5]} />
                                <Tooltip />
                                <Legend />
                                <Line type="monotone" dataKey="rating" name="Ocena" stroke="#82ca9d" />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>

                    {/* Wykres Słupkowy - Oceny Fiszek */}
                    <div>
                        <h4 className="text-lg font-semibold mb-2">Oceny Fiszek - Słupki</h4>
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={flashcardBarChartData}>
                                <XAxis dataKey="date" />
                                <YAxis domain={[0, 5]} />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="rating" name="Ocena" fill="#8884d8" />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>

                    {/* Wykres Kołowy - Średnia Ocena Fiszek */}
                    <div>
                        <h4 className="text-lg font-semibold mb-2">Średnia Ocena Fiszek</h4>
                        <ResponsiveContainer width="100%" height={300}>
                            <PieChart>
                                <Pie
                                    data={flashcardPieChartData}
                                    dataKey="value"
                                    nameKey="name"
                                    cx="50%"
                                    cy="50%"
                                    outerRadius={100}
                                    label
                                >
                                    {flashcardPieChartData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip />
                                <Legend />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>

                    {/* Wykres Radarowy - Średnia Ocena Fiszek */}
                    <div>
                        <h4 className="text-lg font-semibold mb-2">Średnia Ocena Fiszek - Radar</h4>
                        <ResponsiveContainer width="100%" height={300}>
                            <RadarChart data={flashcardRadarChartData}>
                                <PolarGrid />
                                <PolarAngleAxis dataKey="subject" />
                                <PolarRadiusAxis angle={30} domain={[0, 5]} />
                                <Tooltip />
                                <Legend />
                                <Radar name="Średnia Ocena" dataKey="A" stroke="#FFBB28" fill="#FFBB28" fillOpacity={0.6} />
                            </RadarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
