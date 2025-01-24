// File: Dashboard.tsx
'use client';

import React, { useEffect, useState, useContext, useMemo } from 'react';
import Link from 'next/link';
import {
    LineChart, Line,
    BarChart, Bar,
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

// LoadingSpinner Component
const LoadingSpinner = ({ progress }: { progress: number }) => {
    const { t } = useTranslation();
    return (
        <div className="flex flex-col items-center justify-center h-screen text-foreground">
            <h2 className="text-2xl mb-4">{t('loadingData')}</h2>
            <div className="w-1/2 bg-muted rounded-full">
                <div
                    className="bg-primary text-xs font-medium text-primary-foreground text-center p-0.5 leading-none rounded-full"
                    style={{ width: `${progress}%` }}
                >
                    {progress}%
                </div>
            </div>
        </div>
    );
};

// FilterSection Component
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
        <div className="flex flex-wrap justify-center mb-8 space-x-4 text-foreground">
            <div>
                <label htmlFor="start-date" className="block mb-2">
                    {t('filter.dateFrom')}
                </label>
                <input
                    id="start-date"
                    type="date"
                    value={filterStartDate}
                    onChange={(e) => setFilterStartDate(e.target.value)}
                    className="border border-border p-2 rounded bg-background text-foreground"
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
                    className="border border-border p-2 rounded bg-background text-foreground"
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
                    className="border border-border p-2 rounded bg-background text-foreground"
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
                    className="border border-border p-2 rounded bg-background text-foreground"
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

// CookbookSection Component
const CookbookSection = () => {
    const { t } = useTranslation();

    return (
        <div className="border-2 border-border rounded-lg p-6 bg-card text-card-foreground">
            <h2 className="text-2xl font-bold mb-4">{t('cookbookTitle')}</h2>

            <p className="mb-4 text-lg">
                {t('cookbookIntro')}
            </p>

            <h3 className="text-xl font-semibold mb-2">{t('cookbook.flashcardsLimit')}</h3>
            <p className="mb-4">
                {t('cookbook.flashcardsLimitInfo')}
            </p>

            <h3 className="text-xl font-semibold mb-2">{t('cookbook.promptInstructions')}</h3>
            <p className="mb-4">{t('cookbook.promptIntro')}</p>

            <div className="bg-card p-4 rounded-lg shadow-sm mb-4 border border-border">
                <h4 className="font-semibold text-lg mb-2">{t('cookbook.example1Title')}</h4>
                <p className="text-sm mb-2">
                    &#34;Please generate 40 flashcards for studying before the computer networks exam, using the file I uploaded earlier.&#34;
                </p>
            </div>

            <div className="bg-card p-4 rounded-lg shadow-sm mb-4 border border-border">
                <h4 className="font-semibold text-lg mb-2">{t('cookbook.example2Title')}</h4>
                <p className="text-sm mb-2">
                    &#34;Please create an exam for studying before the computer networks exam consisting of 30 questions, using the file I uploaded earlier.&#34;
                </p>
            </div>

            <p className="mb-4 text-lg">
                {t('cookbook.usageTips')}
            </p>

            <h3 className="text-xl font-semibold mb-2">{t('cookbook.chatUseExplanation')}</h3>
            <p className="mb-4">
                {t('cookbook.chatUseExplanationInfo')}
            </p>

            <h3 className="text-xl font-semibold mb-2">{t('cookbook.waitTimeExplanation')}</h3>
            <p className="mb-4">
                {t('cookbook.waitTimeExplanationInfo')}
            </p>

            {/* New Information Added */}
            <h3 className="text-xl font-semibold mb-2">{t('cookbook.progressTracking')}</h3>
            <p className="mb-4">
                {t('cookbook.progressTrackingInfo')}
            </p>
        </div>
    );
};

// Dashboard Component
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

    // Prepare filter options by deduplicating based on deck_names
    const deckOptions = useMemo(() => {
        if (!data) return [];
        return Object.entries(data.deck_names).map(([id, name]) => ({
            id: parseInt(id, 10),
            name,
        }));
    }, [data]);

    // Prepare exam options by deduplicating based on exam_id
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

    // Process filtered data
    const filteredData = useMemo(() => {
        if (!data) return null;

        let filteredStudySessions = data.study_sessions;
        let filteredStudyRecords = data.study_records;
        let filteredExamResults = data.exam_results;
        let filteredExamDailyAverage = data.exam_daily_average;
        let filteredFlashcardDailyAverage = data.flashcard_daily_average;
        let filteredSessionDurations = data.session_durations;
        let filteredUserFlashcards = data.user_flashcards;

        // Filter by date
        if (filterStartDate || filterEndDate) {
            const start = filterStartDate ? new Date(filterStartDate) : null;
            const end = filterEndDate ? new Date(filterEndDate) : null;

            // Filter study_sessions by date
            filteredStudySessions = filteredStudySessions.filter((session) => {
                const sessionStartDate = new Date(session.started_at);
                if (start && sessionStartDate < start) return false;
                if (end && sessionStartDate > end) return false;
                return true;
            });
            console.log(`Filtered Study Sessions by Date: ${filteredStudySessions.length}`);

            // Filter study_records by date and session_id
            filteredStudyRecords = filteredStudyRecords.filter((record) => {
                const recordDate = new Date(record.reviewed_at);
                if (start && recordDate < start) return false;
                if (end && recordDate > end) return false;
                // Additionally ensure session_id is in the filtered study_sessions
                if (record.session_id === null) return false;
                const session = filteredStudySessions.find((session) => session.id === record.session_id);
                return session !== undefined;
            });
            console.log(`Filtered Study Records by Date and Session ID: ${filteredStudyRecords.length}`);

            // Filter exam_results by date
            filteredExamResults = filteredExamResults.filter((exam) => {
                const examDate = new Date(exam.started_at);
                if (start && examDate < start) return false;
                if (end && examDate > end) return false;
                return true;
            });
            console.log(`Filtered Exam Results by Date: ${filteredExamResults.length}`);

            // Filter exam_daily_average by date
            filteredExamDailyAverage = filteredExamDailyAverage.filter((avg) => {
                const avgDate = new Date(avg.date);
                if (start && avgDate < start) return false;
                if (end && avgDate > end) return false;
                return true;
            });
            console.log(`Filtered Exam Daily Average by Date: ${filteredExamDailyAverage.length}`);

            // Filter flashcard_daily_average based on filtered study_records
            const flashcardRatingsMap = new Map<string, { total: number; count: number }>();
            filteredStudyRecords.forEach((record) => {
                if (record.reviewed_at && record.rating !== null) {
                    const date = record.reviewed_at.split('T')[0];
                    if (!flashcardRatingsMap.has(date)) {
                        flashcardRatingsMap.set(date, { total: 0, count: 0 });
                    }
                    const entry = flashcardRatingsMap.get(date)!;
                    entry.total += record.rating;
                    entry.count += 1;
                }
            });

            filteredFlashcardDailyAverage = Array.from(flashcardRatingsMap.entries()).map(([date, { total, count }]) => ({
                date,
                average_rating: count > 0 ? parseFloat((total / count).toFixed(2)) : 0,
            }));
            console.log(`Calculated Flashcard Daily Average based on Filtered Data: ${filteredFlashcardDailyAverage.length}`);

            // Filter session_durations based on filtered study_sessions
            const relevantSessionDates = new Set(filteredStudySessions.map(session => session.started_at.split('T')[0]));
            filteredSessionDurations = filteredSessionDurations.filter((duration) => relevantSessionDates.has(duration.date));
            console.log(`Filtered Session Durations by Relevant Sessions: ${filteredSessionDurations.length}`);
        }

        // Filter by exam
        if (selectedExamId) {
            filteredExamResults = filteredExamResults.filter((exam) => exam.exam_id === selectedExamId);
            console.log(`Filtered Exam Results by Exam ID (${selectedExamId}): ${filteredExamResults.length}`);
        }

        // Filter by deck
        if (selectedDeckId) {
            // Filter study_sessions by deck_id
            filteredStudySessions = filteredStudySessions.filter((session) => session.deck_id === selectedDeckId);
            console.log(`Filtered Study Sessions by Deck ID (${selectedDeckId}): ${filteredStudySessions.length}`);

            // Get session_ids based on deck_id
            const sessionIds = new Set(filteredStudySessions.map(session => session.id));

            // Filter study_records based on session_id in sessionIds
            filteredStudyRecords = filteredStudyRecords.filter((record) => record.session_id !== null && sessionIds.has(record.session_id));
            console.log(`Filtered Study Records by Deck ID (${selectedDeckId}): ${filteredStudyRecords.length}`);
        }

        // Filter user_flashcards associated with filtered study_records
        const userFlashcardIds = new Set(
            filteredStudyRecords
                .map(record => record.user_flashcard_id)
                .filter(id => id !== null) as number[]
        );
        filteredUserFlashcards = data.user_flashcards.filter(card => userFlashcardIds.has(card.id));
        console.log(`Filtered User Flashcards: ${filteredUserFlashcards.length}`);

        return {
            ...data,
            study_sessions: filteredStudySessions,
            study_records: filteredStudyRecords,
            exam_results: filteredExamResults,
            exam_daily_average: filteredExamDailyAverage,
            flashcard_daily_average: filteredFlashcardDailyAverage,
            session_durations: filteredSessionDurations,
            user_flashcards: filteredUserFlashcards,
        };
    }, [data, filterStartDate, filterEndDate, selectedExamId, selectedDeckId]);

    // Prepare data for charts

    // 1. Average Exam Scores Over Time
    const examLineChartData = useMemo(() => {
        if (!filteredData) return [];
        return sortByDateAscending(
            filteredData.exam_daily_average.map((record) => ({
                date: record.date,
                average_score: record.average_score,
            }))
        );
    }, [filteredData]);

    // 2. Time Spent Studying for Exams
    const examStudyTimeData = useMemo(() => {
        if (!filteredData) return [];
        const studyTimeMap = new Map<string, number>();
        filteredData.exam_results
            .filter((exam) => exam.started_at && exam.completed_at)
            .forEach((exam) => {
                const start = new Date(exam.started_at);
                const end = new Date(exam.completed_at!);
                const duration = (end.getTime() - start.getTime()) / (1000 * 60 * 60); // in hours
                const date = start.toISOString().split('T')[0];
                studyTimeMap.set(date, (studyTimeMap.get(date) || 0) + parseFloat(duration.toFixed(2)));
            });
        console.log(`Exam Study Time Data: ${Array.from(studyTimeMap.entries()).length} entries`);
        return sortByDateAscending(
            Array.from(studyTimeMap.entries()).map(([date, study_time]) => ({
                date,
                study_time: parseFloat(study_time.toFixed(2)),
            }))
        );
    }, [filteredData]);

    // 3. Exam Score Distribution (Histogram)
    const histogramExamResultsData = useMemo(() => {
        if (!filteredData) return [];
        // Create buckets for exam score distribution (0-9, 10-19, ..., 90-99, 100)
        const buckets = Array.from({ length: 11 }, (_, i) => ({
            score: i < 10 ? `${i * 10}-${i * 10 + 9}` : '100',
            count: 0,
        }));

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

        console.log(`Histogram Exam Results Data: ${buckets.length} buckets`);
        return buckets;
    }, [filteredData]);

    // 4. Study Sessions and Exams per Day
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
        console.log(`Combined Exam Data: ${combinedMap.size} dates`);
        return sortByDateAscending(
            Array.from(combinedMap.entries()).map(([date, counts]) => ({
                date,
                study_sessions: counts.study_sessions,
                exams_completed: counts.exams_completed,
            }))
        );
    }, [filteredData]);

    // 5. Average Flashcard Ratings Over Time
    const flashcardLineChartData = useMemo(() => {
        if (!filteredData) return [];
        return sortByDateAscending(
            filteredData.flashcard_daily_average.map((record) => ({
                date: record.date,
                average_rating: record.average_rating,
            }))
        );
    }, [filteredData]);

    // 6. Total Time Spent Studying Flashcards (unchanged: used for "Total Time Studying Flashcards")
    const totalStudyTimeData = useMemo(() => {
        if (!filteredData) return [];
        const studyTimeMap = new Map<string, number>();
        const relevantSessions = filteredData.study_sessions;
        relevantSessions.forEach((session) => {
            const sessionDate = session.started_at.split('T')[0];
            const durationRecord = filteredData.session_durations.find(d => d.date === sessionDate);
            if (durationRecord) {
                studyTimeMap.set(sessionDate, (studyTimeMap.get(sessionDate) || 0) + durationRecord.duration_hours);
            }
        });
        console.log(`Total Study Time Data: ${Array.from(studyTimeMap.entries()).length} entries`);
        return sortByDateAscending(
            Array.from(studyTimeMap.entries()).map(([date, total_study_time]) => ({
                date,
                total_study_time: parseFloat(total_study_time.toFixed(2)),
            }))
        );
    }, [filteredData]);

    // 7. Planned Study Sessions (Line Chart)
    const nextReviewTimelineData = useMemo(() => {
        if (!filteredData) return [];
        const reviewMap = new Map<string, number>();
        filteredData.user_flashcards
            .filter((card) => card.next_review)
            .forEach((card) => {
                const date = card.next_review.split('T')[0];
                reviewMap.set(date, (reviewMap.get(date) || 0) + 1);
            });
        console.log(`Next Review Timeline Data: ${reviewMap.size} dates`);
        return sortByDateAscending(
            Array.from(reviewMap.entries()).map(([date, count]) => ({
                date,
                count,
            }))
        );
    }, [filteredData]);

    // 8. Flashcards Solved Daily (Bar Chart)
    const flashcardsSolvedDaily = useMemo(() => {
        if (!filteredData) return [];
        const solvedMap = new Map<string, number>();
        filteredData.study_records
            .filter((record) => record.session_id !== null)
            .forEach((record) => {
                const date = record.reviewed_at.split('T')[0];
                solvedMap.set(date, (solvedMap.get(date) || 0) + 1);
            });
        console.log(`Flashcards Solved Daily: ${solvedMap.size} dates`);
        return sortByDateAscending(
            Array.from(solvedMap.entries()).map(([date, count]) => ({
                date,
                count,
            }))
        );
    }, [filteredData]);

    // 9. Flashcards Solved by Hour (NEW CHART)
    // Aggregates all "reviewed_at" times to show how many flashcards were solved at each hour of the day (0–23).
    const flashcardsByHourData = useMemo(() => {
        if (!filteredData) return [];
        const hourMap = new Map<number, number>();

        // Consider each study record's reviewed_at to extract the hour
        filteredData.study_records.forEach((record) => {
            if (!record.reviewed_at) return;
            const hour = new Date(record.reviewed_at).getHours(); // 0–23
            hourMap.set(hour, (hourMap.get(hour) || 0) + 1);
        });

        // Convert the map to an array of { hour, count } sorted by hour
        const result = Array.from(hourMap.entries())
            .sort((a, b) => a[0] - b[0])
            .map(([hour, count]) => ({ hour, count }));

        console.log('Flashcards By Hour Data:', result);
        return result;
    }, [filteredData]);

    // Average number of flashcards solved daily
    const averageFlashcardsSolved = useMemo(() => {
        if (flashcardsSolvedDaily.length === 0) return 0;
        const total = flashcardsSolvedDaily.reduce((acc, record) => acc + record.count, 0);
        return total / flashcardsSolvedDaily.length;
    }, [flashcardsSolvedDaily]);

    // Conditional rendering
    if (loading) {
        return <LoadingSpinner progress={progress} />;
    }

    if (error) {
        return <div className="text-destructive text-center mt-10">{error}</div>;
    }

    if (!filteredData) {
        return <div className="text-center mt-10 text-foreground">{t('noData')}</div>;
    }

    return (
        <div className="p-4 w-full text-foreground">
            <h2 className="text-2xl font-bold mb-6 text-center">{t('dashboardTitle')}</h2>

            {/* Filter section */}
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

            {/* Rest of the dashboard content */}
            <div className="space-y-8">
                {/* Exam Analysis */}
                <div className="border border-border rounded-lg p-4">
                    <button
                        className="flex justify-between items-center w-full text-left focus:outline-none"
                        onClick={() => setIsExamAnalysisOpen(!isExamAnalysisOpen)}
                    >
                        <div className="flex items-center space-x-2">
                            <TestTube className="h-6 w-6 text-primary" />
                            <h3 className="text-xl font-bold">{t('examAnalysis')}</h3>
                        </div>
                        {isExamAnalysisOpen ? (
                            <ChevronUp className="h-6 w-6 text-primary" />
                        ) : (
                            <ChevronDown className="h-6 w-6 text-primary" />
                        )}
                    </button>
                    {isExamAnalysisOpen && (
                        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-8">
                            {filteredData.exam_results.length === 0 ? (
                                <div
                                    className="col-span-2 bg-accent border border-accent-foreground text-accent-foreground px-4 py-3 rounded relative"
                                    role="alert"
                                >
                                    <strong className="font-bold">{t('noExams.title')}</strong>
                                    <span className="block sm:inline">
                                        {t('noExams.description')}
                                    </span>
                                    <div className="mt-4">
                                        <Link href="/tests">
                                            <a className="bg-primary text-primary-foreground font-bold py-2 px-4 rounded hover:brightness-110">
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
                                                <Line
                                                    type="monotone"
                                                    dataKey="average_score"
                                                    name={t('averageScore')}
                                                    stroke="#82ca9d"
                                                />
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
                <div className="border border-border rounded-lg p-4">
                    <button
                        className="flex justify-between items-center w-full text-left focus:outline-none"
                        onClick={() => setIsFlashcardAnalysisOpen(!isFlashcardAnalysisOpen)}
                    >
                        <div className="flex items-center space-x-2">
                            <BookOpen className="h-6 w-6 text-secondary" />
                            <h3 className="text-xl font-bold">{t('flashcardAnalysis')}</h3>
                        </div>
                        {isFlashcardAnalysisOpen ? (
                            <ChevronUp className="h-6 w-6 text-secondary" />
                        ) : (
                            <ChevronDown className="h-6 w-6 text-secondary" />
                        )}
                    </button>
                    {isFlashcardAnalysisOpen && (
                        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-8">
                            {filteredData.user_flashcards.length === 0 ? (
                                <div
                                    className="col-span-2 bg-accent border border-accent-foreground text-accent-foreground px-4 py-3 rounded relative"
                                    role="alert"
                                >
                                    <strong className="font-bold">{t('noFlashcards.title')}</strong>
                                    <span className="block sm:inline">
                                        {t('noFlashcards.description')}
                                    </span>
                                    <div className="mt-4">
                                        <Link href="/flashcards">
                                            <a className="bg-secondary text-secondary-foreground font-bold py-2 px-4 rounded hover:brightness-110">
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
                                                <Line
                                                    type="monotone"
                                                    dataKey="average_rating"
                                                    name={t('averageRating')}
                                                    stroke="#82ca9d"
                                                />
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

                                    {/* Flashcards Solved by Hour (NEW) */}
                                    <div className="md:col-span-2">
                                        <h4 className="text-lg font-semibold mb-2">
                                            {t('flashcardsSolvedByHour')}
                                        </h4>
                                        <ResponsiveContainer width="100%" height={300}>
                                            <BarChart data={flashcardsByHourData}>
                                                <CartesianGrid strokeDasharray="3 3" />
                                                {/* X-axis for hours (0-23) */}
                                                <XAxis dataKey="hour" />
                                                <YAxis allowDecimals={false} />
                                                <Tooltip />
                                                <Legend />
                                                <Bar dataKey="count" name={t('flashcardsSolved')} fill="#8884d8" />
                                            </BarChart>
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
                                                <Line
                                                    type="monotone"
                                                    dataKey="count"
                                                    name={t('numberOfFlashcards')}
                                                    stroke="#82ca9d"
                                                />
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
                                                {t('averageFlashcardsSolvedDaily')}{' '}
                                                <strong>{averageFlashcardsSolved.toFixed(2)}</strong>
                                            </p>
                                        </div>
                                    </div>
                                </>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Horizontal Line */}
            <hr className="my-8 border-t border-gray-300" />

            {/* Cookbook section */}
            <CookbookSection />
        </div>
    );
};

export default Dashboard;
