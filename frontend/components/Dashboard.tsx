// File: Dashboard.tsx
import React, { useEffect, useState, useContext, useMemo } from 'react';
import Link from 'next/link'; // Import dla nawigacji
import {
    LineChart, Line,
    BarChart, Bar,
    PieChart, Pie, Cell,
    AreaChart, Area,
    XAxis, YAxis,
    Tooltip, Legend,
    ResponsiveContainer,
    CartesianGrid,
} from 'recharts';
import {
    ChevronDown,
    ChevronUp,
    BookOpen,
    TestTube,
} from 'lucide-react';
import { AuthContext } from '@/contexts/AuthContext';
import { useTranslation } from 'react-i18next';

// Define COLORS
const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#FF6666'];

// Types
type DateString = string;

interface ExamResult {
    id: number;
    exam_id: number;
    exam_name: string;
    user_id: number;
    started_at: DateString;
    completed_at: DateString | null;
    score: number;
}

interface StudyRecord {
    id: number;
    session_id: number | null;
    user_flashcard_id: number | null;
    rating: number;
    reviewed_at: DateString;
}

interface StudySession {
    id: number;
    user_id: number;
    deck_id: number;
    deck_name: string;
    started_at: DateString;
    completed_at: DateString | null;
}

interface UserFlashcard {
    id: number;
    user_id: number;
    flashcard_id: number;
    ef: number;
    interval: number;
    repetitions: number;
    next_review: DateString;
}

interface SessionDuration {
    date: DateString;
    duration_hours: number;
}

interface DashboardData {
    study_records: StudyRecord[];
    user_flashcards: UserFlashcard[];
    study_sessions: StudySession[];
    exam_results: ExamResult[];
    session_durations: SessionDuration[];
    exam_daily_average: {
        date: DateString;
        average_score: number;
    }[];
    flashcard_daily_average: {
        date: DateString;
        average_rating: number;
    }[];
    deck_names: Record<number, string>;
}

// Helper functions
const sortByDateAscending = <T extends { date: string }>(data: T[]): T[] =>
    [...data].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

// Components
const LoadingSpinner = ({ progress }: { progress: number }) => {
    const { t } = useTranslation();
    return (
        <div className="flex flex-col items-center justify-center h-screen">
            <h2 className="text-2xl mb-4">{t('loadingData')}</h2>
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
};

const FilterSection = ({
    filterStartDate,
    filterEndDate,
    selectedExamId,
    selectedDeckId,
    setFilterStartDate,
    setFilterEndDate,
    setSelectedExamId,
    setSelectedDeckId,
    examOptions,
    deckOptions,
}: {
    filterStartDate: string;
    filterEndDate: string;
    selectedExamId: number | null;
    selectedDeckId: number | null;
    setFilterStartDate: (date: string) => void;
    setFilterEndDate: (date: string) => void;
    setSelectedExamId: (id: number | null) => void;
    setSelectedDeckId: (id: number | null) => void;
    examOptions: { id: number; name: string }[];
    deckOptions: { id: number; name: string }[];
}) => {
    const { t } = useTranslation();
    return (
        <div className="flex flex-wrap justify-center mb-8 space-x-4">
            <div>
                <label htmlFor="start-date" className="block mb-2">
                    {t('filter.dateFrom')}
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
                    {t('filter.dateTo')}
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
                    {t('filter.selectExam')}
                </label>
                <select
                    id="exam-select"
                    value={selectedExamId ?? ''}
                    onChange={(e) => setSelectedExamId(e.target.value ? parseInt(e.target.value) : null)}
                    className="border p-2 rounded"
                >
                    <option value="">{t('filter.all')}</option>
                    {examOptions.map(({ id, name }) => (
                        <option key={id} value={id}>
                            {name}
                        </option>
                    ))}
                </select>
            </div>
            <div>
                <label htmlFor="deck-select" className="block mb-2">
                    {t('filter.selectDeck')}
                </label>
                <select
                    id="deck-select"
                    value={selectedDeckId ?? ''}
                    onChange={(e) => setSelectedDeckId(e.target.value ? parseInt(e.target.value) : null)}
                    className="border p-2 rounded"
                >
                    <option value="">{t('filter.all')}</option>
                    {deckOptions.map(({ id, name }) => (
                        <option key={id} value={id}>
                            {name}
                        </option>
                    ))}
                </select>
            </div>
        </div>
    );
};

const Dashboard: React.FC = () => {
    const { t } = useTranslation();
    const { isAuthenticated } = useContext(AuthContext);
    const [data, setData] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [progress, setProgress] = useState<number>(0);
    const [error, setError] = useState<string | null>(null);

    // Filters
    const [filterStartDate, setFilterStartDate] = useState<string>('');
    const [filterEndDate, setFilterEndDate] = useState<string>('');
    const [selectedExamId, setSelectedExamId] = useState<number | null>(null);
    const [selectedDeckId, setSelectedDeckId] = useState<number | null>(null);

    // UI state
    const [isExamAnalysisOpen, setIsExamAnalysisOpen] = useState<boolean>(false); // Initially collapsed
    const [isFlashcardAnalysisOpen, setIsFlashcardAnalysisOpen] = useState<boolean>(false); // Initially collapsed

    useEffect(() => {
        const fetchDashboardData = async () => {
            try {
                setLoading(true);
                setProgress(10);

                if (!isAuthenticated) {
                    throw new Error(t('pleaseLogin'));
                }

                const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || 'http://localhost:8043/api';
                const response = await fetch(`${API_BASE_URL}/dashboard/`, {
                    credentials: 'include',
                });

                setProgress(50);

                if (!response.ok) {
                    throw new Error(t('fetchError', { statusText: response.statusText }));
                }

                const result: DashboardData = await response.json();
                setData(result);
                setProgress(100);
            } catch (err: unknown) {
                console.error('Error fetching dashboard data:', err);
                setError(err instanceof Error ? err.message : t('fetchErrorGeneric'));
                setProgress(100);
            } finally {
                setLoading(false);
            }
        };

        fetchDashboardData();
    }, [isAuthenticated, t]);

    // Przygotowanie opcji filtrów z deduplikacją na podstawie deck_names
    const deckOptions = useMemo(() => {
        if (!data) return [];
        return Object.entries(data.deck_names).map(([id, name]) => ({
            id: parseInt(id, 10),
            name,
        }));
    }, [data]);

    // Przygotowanie opcji egzaminów z deduplikacją na podstawie exam_id
    const examOptions = useMemo(() => {
        if (!data) return [];
        const uniqueExamsMap = new Map<number, string>();
        data.exam_results.forEach((exam) => {
            if (!uniqueExamsMap.has(exam.exam_id)) {
                uniqueExamsMap.set(exam.exam_id, exam.exam_name || `${t('filter.selectExam')} ${exam.exam_id}`);
            }
        });
        return Array.from(uniqueExamsMap, ([id, name]) => ({ id, name }));
    }, [data, t]);

    // Przetwarzanie filtrowanych danych
    const filteredData = useMemo(() => {
        if (!data) return null;

        let filteredStudyRecords = data.study_records;
        let filteredExamResults = data.exam_results;
        let filteredExamDailyAverage = data.exam_daily_average;
        let filteredFlashcardDailyAverage = data.flashcard_daily_average;
        let filteredUserFlashcards = data.user_flashcards;

        // Filtracja po dacie
        if (filterStartDate && filterEndDate) {
            const start = new Date(filterStartDate);
            const end = new Date(filterEndDate);

            filteredStudyRecords = data.study_records.filter((record) => {
                const recordDate = new Date(record.reviewed_at);
                return recordDate >= start && recordDate <= end;
            });

            filteredExamResults = data.exam_results.filter((exam) => {
                const examDate = new Date(exam.started_at);
                return examDate >= start && examDate <= end;
            });

            filteredExamDailyAverage = data.exam_daily_average.filter((avg) => {
                const avgDate = new Date(avg.date);
                return avgDate >= start && avgDate <= end;
            });

            filteredFlashcardDailyAverage = data.flashcard_daily_average.filter((avg) => {
                const avgDate = new Date(avg.date);
                return avgDate >= start && avgDate <= end;
            });

            // Filtrowanie user_flashcards na podstawie next_review
            filteredUserFlashcards = data.user_flashcards.filter((card) => {
                const nextReviewDate = new Date(card.next_review);
                return nextReviewDate >= start && nextReviewDate <= end;
            });
        }

        // Filtracja po egzaminie
        if (selectedExamId) {
            filteredExamResults = filteredExamResults.filter((exam) => exam.exam_id === selectedExamId);
        }

        // Filtracja po zestawie fiszek
        if (selectedDeckId) {
            filteredStudyRecords = filteredStudyRecords.filter((record) => {
                if (record.session_id === null) return false;
                const session = data.study_sessions.find((session) => session.id === record.session_id);
                return session?.deck_id === selectedDeckId;
            });

            // Filtrowanie user_flashcards powiązanych z przefiltrowanymi study_records
            const filteredUserFlashcardIds = new Set(
                filteredStudyRecords
                    .map(record => record.user_flashcard_id)
                    .filter(id => id !== null) as number[]
            );
            filteredUserFlashcards = data.user_flashcards.filter(card => filteredUserFlashcardIds.has(card.id));
        }

        return {
            ...data,
            study_records: filteredStudyRecords,
            exam_results: filteredExamResults,
            exam_daily_average: filteredExamDailyAverage,
            flashcard_daily_average: filteredFlashcardDailyAverage,
            user_flashcards: filteredUserFlashcards,
        };
    }, [data, filterStartDate, filterEndDate, selectedExamId, selectedDeckId]);

    // Przygotowanie danych do wykresów
    const examLineChartData = useMemo(() => {
        if (!filteredData) return [];
        return sortByDateAscending(
            filteredData.exam_daily_average.map((record) => ({
                date: record.date,
                average_score: record.average_score,
            }))
        );
    }, [filteredData]);

    const examStudyTimeData = useMemo(() => {
        if (!filteredData) return [];
        const studyTimeMap = new Map<string, number>();
        filteredData.exam_results
            .filter((exam) => exam.started_at && exam.completed_at)
            .forEach((exam) => {
                const start = new Date(exam.started_at);
                const end = new Date(exam.completed_at!);
                const duration = (end.getTime() - start.getTime()) / (1000 * 60 * 60); // Duration in hours
                const date = start.toISOString().split('T')[0];
                studyTimeMap.set(date, (studyTimeMap.get(date) || 0) + parseFloat(duration.toFixed(2)));
            });
        return sortByDateAscending(
            Array.from(studyTimeMap.entries()).map(([date, study_time]) => ({
                date,
                study_time: parseFloat(study_time.toFixed(2)),
            }))
        );
    }, [filteredData]);

    const histogramExamResultsData = useMemo(() => {
        if (!filteredData) return [];
        // Tworzenie przedziałów dla rozkładu wyników egzaminów (0-9, 10-19, ..., 90-99, 100)
        const buckets = Array.from({ length: 11 }, (_, i) => ({
            score: i < 10 ? `${i * 10}-${i * 10 + 9}` : '100',
            count: 0,
        }));

        // Wypełnienie przedziałów danymi
        filteredData.exam_results.forEach((exam) => {
            if (exam.score === 100) {
                buckets[10].count += 1;
            } else {
                const bucketIndex = Math.floor(exam.score / 10);
                if (bucketIndex >= 0 && bucketIndex < 10) {
                    buckets[bucketIndex].count += 1;
                }
            }
        });

        return buckets;
    }, [filteredData]);

    const combinedExamData = useMemo(() => {
        if (!filteredData) return [];
        const combinedMap = new Map<string, { study_sessions: number; exams_completed: number }>();
        filteredData.study_sessions.forEach((session) => {
            const date = session.started_at.split('T')[0];
            if (!combinedMap.has(date)) {
                combinedMap.set(date, { study_sessions: 0, exams_completed: 0 });
            }
            const entry = combinedMap.get(date)!;
            entry.study_sessions += 1;
        });
        filteredData.exam_results.forEach((exam) => {
            const date = exam.started_at.split('T')[0];
            if (!combinedMap.has(date)) {
                combinedMap.set(date, { study_sessions: 0, exams_completed: 0 });
            }
            const entry = combinedMap.get(date)!;
            entry.exams_completed += 1;
        });
        return sortByDateAscending(
            Array.from(combinedMap.entries()).map(([date, counts]) => ({
                date,
                study_sessions: counts.study_sessions,
                exams_completed: counts.exams_completed,
            }))
        );
    }, [filteredData]);

    const flashcardLineChartData = useMemo(() => {
        if (!filteredData) return [];
        return sortByDateAscending(
            filteredData.flashcard_daily_average.map((record) => ({
                date: record.date,
                average_rating: record.average_rating,
            }))
        );
    }, [filteredData]);

    const totalStudyTimeData = useMemo(() => {
        if (!filteredData) return [];
        const studyTimeMap = new Map<string, number>();
        filteredData.session_durations.forEach((record) => {
            const date = record.date;
            studyTimeMap.set(date, (studyTimeMap.get(date) || 0) + parseFloat(record.duration_hours.toFixed(2)));
        });
        return sortByDateAscending(
            Array.from(studyTimeMap.entries()).map(([date, total_study_time]) => ({
                date,
                total_study_time: parseFloat(total_study_time.toFixed(2)),
            }))
        );
    }, [filteredData]);

    const flashcardPieChartData = useMemo(() => {
        if (!filteredData) return [];
        const averageRating = filteredData.flashcard_daily_average.length > 0
            ? filteredData.flashcard_daily_average.reduce((acc, record) => acc + record.average_rating, 0) / filteredData.flashcard_daily_average.length
            : 0;
        return [
            {
                name: t('averageRating'),
                value: averageRating,
            },
            {
                name: t('remainingToFive'),
                value: 5 - averageRating,
            },
        ];
    }, [filteredData, t]);

    const nextReviewTimelineData = useMemo(() => {
        if (!filteredData) return [];
        const reviewMap = new Map<string, number>();
        filteredData.user_flashcards
            .filter((card) => card.next_review)
            .forEach((card) => {
                const date = card.next_review.split('T')[0];
                reviewMap.set(date, (reviewMap.get(date) || 0) + 1);
            });
        return sortByDateAscending(
            Array.from(reviewMap.entries()).map(([date, count]) => ({
                date,
                count,
            }))
        );
    }, [filteredData]);

    const flashcardsSolvedDaily = useMemo(() => {
        if (!filteredData) return [];
        const solvedMap = new Map<string, number>();
        filteredData.study_records
            .filter((record) => record.session_id !== null)
            .forEach((record) => {
                const date = record.reviewed_at.split('T')[0];
                solvedMap.set(date, (solvedMap.get(date) || 0) + 1);
            });
        return sortByDateAscending(
            Array.from(solvedMap.entries()).map(([date, count]) => ({
                date,
                count,
            }))
        );
    }, [filteredData]);

    const averageFlashcardsSolved = useMemo(() => {
        if (flashcardsSolvedDaily.length === 0) return 0;
        const total = flashcardsSolvedDaily.reduce((acc, record) => acc + record.count, 0);
        return total / flashcardsSolvedDaily.length;
    }, [flashcardsSolvedDaily]);

    // Warunkowe renderowanie
    if (loading) {
        return <LoadingSpinner progress={progress} />;
    }

    if (error) {
        return <div className="text-red-500 text-center mt-10">{error}</div>;
    }

    if (!filteredData) {
        return <div className="text-center mt-10">{t('noData')}</div>;
    }

    return (
        <div className="p-4 w-full">
            <h2 className="text-2xl font-bold mb-6 text-center">{t('dashboardTitle')}</h2>

            <FilterSection
                filterStartDate={filterStartDate}
                filterEndDate={filterEndDate}
                selectedExamId={selectedExamId}
                selectedDeckId={selectedDeckId}
                setFilterStartDate={setFilterStartDate}
                setFilterEndDate={setFilterEndDate}
                setSelectedExamId={setSelectedExamId}
                setSelectedDeckId={setSelectedDeckId}
                examOptions={examOptions}
                deckOptions={deckOptions}
            />

            <div className="space-y-8">
                {/* Exam Analysis */}
                <div className="border rounded-lg p-4">
                    <button
                        className="flex justify-between items-center w-full text-left focus:outline-none"
                        onClick={() => setIsExamAnalysisOpen(!isExamAnalysisOpen)}
                    >
                        <div className="flex items-center space-x-2">
                            <TestTube className="h-6 w-6 text-blue-500" />
                            <h3 className="text-xl font-bold">{t('examAnalysis')}</h3>
                        </div>
                        {isExamAnalysisOpen ? (
                            <ChevronUp className="h-6 w-6 text-blue-500" />
                        ) : (
                            <ChevronDown className="h-6 w-6 text-blue-500" />
                        )}
                    </button>
                    {isExamAnalysisOpen && (
                        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-8">
                            {filteredData.exam_results.length === 0 ? (
                                <div className="col-span-2 bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded relative" role="alert">
                                    <strong className="font-bold">{t('noExams.title')}</strong>
                                    <span className="block sm:inline">
                                        {t('noExams.description')}
                                    </span>
                                    <div className="mt-4">
                                        <Link href="/tests">
                                            <a className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
                                                {t('noExams.addExam')}
                                            </a>
                                        </Link>
                                    </div>
                                </div>
                            ) : (
                                <>
                                    {/* Average Exam Scores Over Time */}
                                    <div>
                                        <h4 className="text-lg font-semibold mb-2">{t('averageExamScoresOverTime')}</h4>
                                        <ResponsiveContainer width="100%" height={300}>
                                            <LineChart data={examLineChartData}>
                                                <CartesianGrid strokeDasharray="3 3" />
                                                <XAxis dataKey="date" />
                                                <YAxis domain={[0, 100]} />
                                                <Tooltip />
                                                <Legend />
                                                <Line type="monotone" dataKey="average_score" name={t('averageScore')} stroke="#82ca9d" />
                                            </LineChart>
                                        </ResponsiveContainer>
                                    </div>

                                    {/* Time Spent Studying for Exams */}
                                    <div>
                                        <h4 className="text-lg font-semibold mb-2">{t('timeSpentStudyingExams')}</h4>
                                        <ResponsiveContainer width="100%" height={300}>
                                            <BarChart data={examStudyTimeData}>
                                                <CartesianGrid strokeDasharray="3 3" />
                                                <XAxis dataKey="date" />
                                                <YAxis domain={[0, 'auto']} />
                                                <Tooltip />
                                                <Legend />
                                                <Bar dataKey="study_time" name={t('studyTimeHours')} fill="#FF8042" />
                                            </BarChart>
                                        </ResponsiveContainer>
                                    </div>

                                    {/* Exam Score Distribution */}
                                    <div className="md:col-span-2">
                                        <h4 className="text-lg font-semibold mb-2">{t('examScoreDistribution')}</h4>
                                        <ResponsiveContainer width="100%" height={300}>
                                            <BarChart data={histogramExamResultsData}>
                                                <CartesianGrid strokeDasharray="3 3" />
                                                <XAxis dataKey="score" />
                                                <YAxis allowDecimals={false} />
                                                <Tooltip />
                                                <Legend />
                                                <Bar dataKey="count" name={t('numberOfExams')} fill="#FFBB28" />
                                            </BarChart>
                                        </ResponsiveContainer>
                                    </div>

                                    {/* Sessions and Exams per Day */}
                                    <div className="md:col-span-2">
                                        <h4 className="text-lg font-semibold mb-2">{t('sessionsAndExamsPerDay')}</h4>
                                        <ResponsiveContainer width="100%" height={300}>
                                            <BarChart data={combinedExamData}>
                                                <CartesianGrid strokeDasharray="3 3" />
                                                <XAxis dataKey="date" />
                                                <YAxis allowDecimals={false} />
                                                <Tooltip />
                                                <Legend />
                                                <Bar dataKey="study_sessions" name={t('studySessions')} fill="#82ca9d" />
                                                <Bar dataKey="exams_completed" name={t('exams')} fill="#FF8042" />
                                            </BarChart>
                                        </ResponsiveContainer>
                                    </div>
                                </>
                            )}
                        </div>
                    )}
                </div>

                {/* Flashcard Analysis */}
                <div className="border rounded-lg p-4">
                    <button
                        className="flex justify-between items-center w-full text-left focus:outline-none"
                        onClick={() => setIsFlashcardAnalysisOpen(!isFlashcardAnalysisOpen)}
                    >
                        <div className="flex items-center space-x-2">
                            <BookOpen className="h-6 w-6 text-green-500" />
                            <h3 className="text-xl font-bold">{t('flashcardAnalysis')}</h3>
                        </div>
                        {isFlashcardAnalysisOpen ? (
                            <ChevronUp className="h-6 w-6 text-green-500" />
                        ) : (
                            <ChevronDown className="h-6 w-6 text-green-500" />
                        )}
                    </button>
                    {isFlashcardAnalysisOpen && (
                        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-8">
                            {filteredData.user_flashcards.length === 0 ? (
                                <div className="col-span-2 bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded relative" role="alert">
                                    <strong className="font-bold">{t('noFlashcards.title')}</strong>
                                    <span className="block sm:inline">
                                        {t('noFlashcards.description')}
                                    </span>
                                    <div className="mt-4">
                                        <Link href="/flashcards">
                                            <a className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">
                                                {t('noFlashcards.addFlashcards')}
                                            </a>
                                        </Link>
                                    </div>
                                </div>
                            ) : (
                                <>
                                    {/* Average Flashcard Ratings Over Time */}
                                    <div>
                                        <h4 className="text-lg font-semibold mb-2">{t('averageFlashcardRatingsOverTime')}</h4>
                                        <ResponsiveContainer width="100%" height={300}>
                                            <LineChart data={flashcardLineChartData}>
                                                <CartesianGrid strokeDasharray="3 3" />
                                                <XAxis dataKey="date" />
                                                <YAxis domain={[0, 5]} />
                                                <Tooltip />
                                                <Legend />
                                                <Line type="monotone" dataKey="average_rating" name={t('averageRating')} stroke="#82ca9d" />
                                            </LineChart>
                                        </ResponsiveContainer>
                                    </div>

                                    {/* Total Time Spent Studying Flashcards */}
                                    <div>
                                        <h4 className="text-lg font-semibold mb-2">{t('totalTimeStudyingFlashcards')}</h4>
                                        <ResponsiveContainer width="100%" height={300}>
                                            <AreaChart data={totalStudyTimeData}>
                                                <defs>
                                                    <linearGradient id="colorTotalStudy" x1="0" y1="0" x2="0" y2="1">
                                                        <stop offset="5%" stopColor="#82ca9d" stopOpacity={0.8} />
                                                        <stop offset="95%" stopColor="#82ca9d" stopOpacity={0} />
                                                    </linearGradient>
                                                </defs>
                                                <CartesianGrid strokeDasharray="3 3" />
                                                <XAxis dataKey="date" />
                                                <YAxis domain={[0, 'auto']} />
                                                <Tooltip />
                                                <Legend />
                                                <Area
                                                    type="monotone"
                                                    dataKey="total_study_time"
                                                    name={t('studyTimeHours')}
                                                    stroke="#82ca9d"
                                                    fillOpacity={1}
                                                    fill="url(#colorTotalStudy)"
                                                />
                                            </AreaChart>
                                        </ResponsiveContainer>
                                    </div>

                                    {/* Total Time Spent Studying */}
                                    <div className="md:col-span-2">
                                        <h4 className="text-lg font-semibold mb-2">{t('totalTimeStudying')}</h4>
                                        <ResponsiveContainer width="100%" height={300}>
                                            <AreaChart data={totalStudyTimeData}>
                                                <defs>
                                                    <linearGradient id="colorDuration" x1="0" y1="0" x2="0" y2="1">
                                                        <stop offset="5%" stopColor="#FF8042" stopOpacity={0.8} />
                                                        <stop offset="95%" stopColor="#FF8042" stopOpacity={0} />
                                                    </linearGradient>
                                                </defs>
                                                <CartesianGrid strokeDasharray="3 3" />
                                                <XAxis dataKey="date" />
                                                <YAxis domain={[0, 'auto']} />
                                                <Tooltip />
                                                <Legend />
                                                <Area
                                                    type="monotone"
                                                    dataKey="total_study_time"
                                                    name={t('studyTimeHours')}
                                                    stroke="#FF8042"
                                                    fillOpacity={1}
                                                    fill="url(#colorDuration)"
                                                />
                                            </AreaChart>
                                        </ResponsiveContainer>
                                    </div>

                                    {/* Average Flashcard Rating */}
                                    <div className="md:col-span-2">
                                        <h4 className="text-lg font-semibold mb-2">{t('averageFlashcardRating')}</h4>
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

                                    {/* Planned Study Sessions */}
                                    <div className="md:col-span-2">
                                        <h4 className="text-lg font-semibold mb-2">{t('plannedStudySessions')}</h4>
                                        <ResponsiveContainer width="100%" height={300}>
                                            <LineChart data={nextReviewTimelineData}>
                                                <CartesianGrid strokeDasharray="3 3" />
                                                <XAxis dataKey="date" />
                                                <YAxis />
                                                <Tooltip />
                                                <Legend />
                                                <Line type="monotone" dataKey="count" name={t('numberOfFlashcards')} stroke="#82ca9d" />
                                            </LineChart>
                                        </ResponsiveContainer>
                                    </div>

                                    {/* Flashcards Solved Daily */}
                                    <div className="md:col-span-2">
                                        <h4 className="text-lg font-semibold mb-2">{t('flashcardsSolvedDaily')}</h4>
                                        <ResponsiveContainer width="100%" height={300}>
                                            <BarChart data={flashcardsSolvedDaily}>
                                                <CartesianGrid strokeDasharray="3 3" />
                                                <XAxis dataKey="date" />
                                                <YAxis allowDecimals={false} />
                                                <Tooltip />
                                                <Legend />
                                                <Bar dataKey="count" name={t('flashcardsSolved')} fill="#8884d8" />
                                            </BarChart>
                                        </ResponsiveContainer>
                                        <div className="mt-4">
                                            <p className="text-lg">
                                                {t('averageFlashcardsSolvedDaily')} <strong>{averageFlashcardsSolved.toFixed(2)}</strong>
                                            </p>
                                        </div>
                                    </div>
                                </>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );

};

export default Dashboard;
