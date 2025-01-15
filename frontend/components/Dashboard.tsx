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
    exam_name: string;
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
    deck_name: string;
    started_at: string;
    completed_at: string | null;
}

interface SessionDuration {
    date: string;
    duration_hours: number;
}

interface DashboardData {
    study_records: StudyRecord[];
    user_flashcards: UserFlashcard[];
    study_sessions: StudySession[];
    exam_result_answers: ExamResultAnswer[];
    exam_results: ExamResult[];
    session_durations: SessionDuration[];
    exam_daily_average: {
        date: string;
        average_score: number;
    }[];
    flashcard_daily_average: {
        date: string;
        average_rating: number;
    }[];
    deck_names: {
        [key: number]: string;
    };
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
                const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || 'http://localhost:8043/api';
                const DASHBOARD_URL = `${API_BASE_URL}/dashboard/`; // Upewnij się, że adres jest poprawny i zawiera trailing slash

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
        let filteredExamDailyAverage = data.exam_daily_average;
        let filteredFlashcardDailyAverage = data.flashcard_daily_average;

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

            filteredExamDailyAverage = data.exam_daily_average.filter(avg => {
                const avgDate = new Date(avg.date);
                return avgDate >= start && avgDate <= end;
            });

            filteredFlashcardDailyAverage = data.flashcard_daily_average.filter(avg => {
                const avgDate = new Date(avg.date);
                return avgDate >= start && avgDate <= end;
            });
        }

        // Filtruj według egzaminu
        if (selectedExamId) {
            filteredExamResults = filteredExamResults.filter(exam => exam.exam_id === selectedExamId);
            // Ponieważ frontend nie ma wystarczających danych do filtrowania exam_daily_average,
            // musisz to zrobić na backendzie, jeśli to konieczne.
        }

        // Filtruj według zestawu fiszek
        if (selectedDeckId) {
            filteredStudyRecords = filteredStudyRecords.filter(record => {
                const session = data.study_sessions.find(session => session.id === record.session_id);
                return session?.deck_id === selectedDeckId;
            });
            // Podobnie, filtrowanie flashcard_daily_average wymaga dodatkowych danych
        }

        return {
            ...data,
            study_records: filteredStudyRecords,
            exam_results: filteredExamResults,
            exam_daily_average: filteredExamDailyAverage,
            flashcard_daily_average: filteredFlashcardDailyAverage,
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
    const examLineChartData = filteredData.exam_daily_average.map(record => ({
        date: record.date,
        average_score: record.average_score,
    }));

    const examBarChartData = filteredData.exam_daily_average.map(record => ({
        date: record.date,
        average_score: record.average_score,
    }));

    const averageExamScore =
        filteredData.exam_daily_average.length > 0
            ? filteredData.exam_daily_average.reduce((acc, record) => acc + record.average_score, 0) / filteredData.exam_daily_average.length
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
    const flashcardLineChartData = filteredData.flashcard_daily_average.map(record => ({
        date: record.date,
        average_rating: record.average_rating,
    }));

    const flashcardBarChartData = filteredData.flashcard_daily_average.map(record => ({
        date: record.date,
        average_rating: record.average_rating,
    }));

    const averageFlashcardRating =
        filteredData.flashcard_daily_average.length > 0
            ? filteredData.flashcard_daily_average.reduce((acc, record) => acc + record.average_rating, 0) / filteredData.flashcard_daily_average.length
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
                        {Array.from(new Set(filteredData.exam_results.map(exam => exam.exam_id))).map(examId => (
                            <option key={examId} value={examId}>
                                {filteredData.exam_results.find(exam => exam.exam_id === examId)?.exam_name || `Egzamin ${examId}`}
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
                        {Array.from(new Set(filteredData.study_sessions.map(session => session.deck_id))).map(deckId => (
                            <option key={deckId} value={deckId}>
                                {filteredData.deck_names[deckId] || `Zestaw ${deckId}`}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Sekcja Egzaminów */}
            <div className="mb-12">
                <h3 className="text-xl font-bold mb-4 text-center">Analiza Egzaminów</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* Wykres Liniowy - Średnie Wyniki Egzaminów w czasie */}
                    <div>
                        <h4 className="text-lg font-semibold mb-2">Średnie Wyniki Egzaminów w Czasie</h4>
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={examLineChartData}>
                                <XAxis dataKey="date" />
                                <YAxis domain={[0, 100]} />
                                <Tooltip />
                                <Legend />
                                <Line type="monotone" dataKey="average_score" name="Średni Wynik" stroke="#82ca9d" />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>

                    {/* Wykres Słupkowy - Średnie Wyniki Egzaminów */}
                    <div>
                        <h4 className="text-lg font-semibold mb-2">Średnie Wyniki Egzaminów - Słupki</h4>
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={examBarChartData}>
                                <XAxis dataKey="date" />
                                <YAxis domain={[0, 100]} />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="average_score" name="Średni Wynik" fill="#8884d8" />
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
                    {/* Wykres Liniowy - Średnie Oceny Fiszek w czasie */}
                    <div>
                        <h4 className="text-lg font-semibold mb-2">Średnie Oceny Fiszek w Czasie</h4>
                        <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={flashcardLineChartData}>
                                <XAxis dataKey="date" />
                                <YAxis domain={[0, 5]} />
                                <Tooltip />
                                <Legend />
                                <Line type="monotone" dataKey="average_rating" name="Średnia Ocena" stroke="#82ca9d" />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>

                    {/* Wykres Słupkowy - Średnie Oceny Fiszek */}
                    <div>
                        <h4 className="text-lg font-semibold mb-2">Średnie Oceny Fiszek - Słupki</h4>
                        <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={flashcardBarChartData}>
                                <XAxis dataKey="date" />
                                <YAxis domain={[0, 5]} />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="average_rating" name="Średnia Ocena" fill="#8884d8" />
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
