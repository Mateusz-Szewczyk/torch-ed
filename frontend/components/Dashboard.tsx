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

// Typy
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

// Funkcja pomocnicza do sortowania
const sortByDateAscending = <T extends { date: string }>(data: T[]): T[] =>
  [...data].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

// Definiujemy kolory pobierane z CSS (globals.css)
const chartColors = {
  primary: 'hsl(var(--primary))',
  secondary: 'hsl(var(--secondary))',
  accent: 'hsl(var(--accent))',
  border: 'hsl(var(--border))',
  foreground: 'hsl(var(--foreground))',
};

// Komponent spinnera ładowania
const LoadingSpinner = ({ progress }: { progress: number }) => {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center justify-center h-screen text-foreground">
      <h2 className="text-2xl mb-4">{t('loadingData')}</h2>
      <div className="w-1/2 bg-muted rounded-full">
        <div
          className="bg-primary text-xs font-medium text-primary-foreground text-center p-0.5 leading-none rounded-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        >
          {progress}%
        </div>
      </div>
    </div>
  );
};

// Sekcja filtrowania
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
    <div className="flex flex-wrap justify-center mb-8 gap-4 text-foreground">
      <div className="flex flex-col space-y-1">
        <label htmlFor="start-date" className="text-sm font-medium">
          {t('filter.dateFrom')}
        </label>
        <input
          id="start-date"
          type="date"
          value={filterStartDate}
          onChange={(e) => setFilterStartDate(e.target.value)}
          className="border border-border px-3 py-2 rounded-md bg-background text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
        />
      </div>
      <div className="flex flex-col space-y-1">
        <label htmlFor="end-date" className="text-sm font-medium">
          {t('filter.dateTo')}
        </label>
        <input
          id="end-date"
          type="date"
          value={filterEndDate}
          onChange={(e) => setFilterEndDate(e.target.value)}
          className="border border-border px-3 py-2 rounded-md bg-background text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
        />
      </div>
      <div className="flex flex-col space-y-1">
        <label htmlFor="exam-select" className="text-sm font-medium">
          {t('filter.selectExam')}
        </label>
        <select
          id="exam-select"
          value={selectedExamId ?? ''}
          onChange={(e) => setSelectedExamId(e.target.value ? parseInt(e.target.value) : null)}
          className="border border-border px-3 py-2 rounded-md bg-background text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
        >
          <option value="">{t('filter.all')}</option>
          {examOptions.map(({ id, name }) => (
            <option key={id} value={id}>
              {name}
            </option>
          ))}
        </select>
      </div>
      <div className="flex flex-col space-y-1">
        <label htmlFor="deck-select" className="text-sm font-medium">
          {t('filter.selectDeck')}
        </label>
        <select
          id="deck-select"
          value={selectedDeckId ?? ''}
          onChange={(e) => setSelectedDeckId(e.target.value ? parseInt(e.target.value) : null)}
          className="border border-border px-3 py-2 rounded-md bg-background text-foreground focus:ring-2 focus:ring-primary focus:outline-none"
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

// Sekcja z „Cookbookiem”
const CookbookSection = () => {
  const { t } = useTranslation();

  return (
    <div className="border border-border rounded-lg p-6 bg-card text-card-foreground shadow-sm">
      <h2 className="text-2xl font-bold mb-4 text-primary">{t('cookbookTitle')}</h2>

      <p className="mb-4 text-foreground/90">
        {t('cookbookIntro')}
      </p>

      <h3 className="text-xl font-semibold mb-2 text-primary">{t('cookbook.flashcardsLimit')}</h3>
      <p className="mb-4 text-foreground/80">
        {t('cookbook.flashcardsLimitInfo')}
      </p>

      <h3 className="text-xl font-semibold mb-2 text-primary">{t('cookbook.promptInstructions')}</h3>
      <p className="mb-4 text-foreground/80">{t('cookbook.promptIntro')}</p>

      <div className="bg-accent/10 p-4 rounded-lg mb-4 border border-border">
        <h4 className="font-semibold text-lg mb-2 text-secondary-foreground">{t('cookbook.example1Title')}</h4>
        <p className="text-sm mb-2 text-foreground/80">
          &#34;Please generate 40 flashcards for studying before the computer networks exam, using the file I uploaded earlier.&#34;
        </p>
      </div>

      <div className="bg-accent/10 p-4 rounded-lg mb-4 border border-border">
        <h4 className="font-semibold text-lg mb-2 text-secondary-foreground">{t('cookbook.example2Title')}</h4>
        <p className="text-sm mb-2 text-foreground/80">
          &#34;Please create an exam for studying before the computer networks exam consisting of 30 questions, using the file I uploaded earlier.&#34;
        </p>
      </div>

      <p className="mb-4 text-foreground/90">
        {t('cookbook.usageTips')}
      </p>

      <h3 className="text-xl font-semibold mb-2 text-primary">{t('cookbook.chatUseExplanation')}</h3>
      <p className="mb-4 text-foreground/80">
        {t('cookbook.chatUseExplanationInfo')}
      </p>

      <h3 className="text-xl font-semibold mb-2 text-primary">{t('cookbook.waitTimeExplanation')}</h3>
      <p className="mb-4 text-foreground/80">
        {t('cookbook.waitTimeExplanationInfo')}
      </p>

      <h3 className="text-xl font-semibold mb-2 text-primary">{t('cookbook.progressTracking')}</h3>
      <p className="mb-4 text-foreground/80">
        {t('cookbook.progressTrackingInfo')}
      </p>
    </div>
  );
};

// Główny komponent Dashboard
const Dashboard: React.FC = () => {
  const { t } = useTranslation();
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

  // Stan UI
  const [isExamAnalysisOpen, setIsExamAnalysisOpen] = useState<boolean>(false);
  const [isFlashcardAnalysisOpen, setIsFlashcardAnalysisOpen] = useState<boolean>(false);

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

  // Opcje talii (deckOptions)
  const deckOptions = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.deck_names).map(([id, name]) => ({
      id: parseInt(id, 10),
      name,
    }));
  }, [data]);

  // Opcje egzaminów (examOptions)
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

  // Filtrowanie i obróbka danych
  const filteredData = useMemo(() => {
    if (!data) return null;

    let filteredStudySessions = data.study_sessions;
    let filteredStudyRecords = data.study_records;
    let filteredExamResults = data.exam_results;
    let filteredExamDailyAverage = data.exam_daily_average;
    let filteredFlashcardDailyAverage = data.flashcard_daily_average;
    let filteredSessionDurations = data.session_durations;
    let filteredUserFlashcards = data.user_flashcards;

    // Filtrowanie po dacie
    if (filterStartDate || filterEndDate) {
      const start = filterStartDate ? new Date(filterStartDate) : null;
      const end = filterEndDate ? new Date(filterEndDate) : null;

      // Sesje nauki
      filteredStudySessions = filteredStudySessions.filter((session) => {
        const sessionStartDate = new Date(session.started_at);
        if (start && sessionStartDate < start) return false;
        if (end && sessionStartDate > end) return false;
        return true;
      });

      // Rekordy nauki
      filteredStudyRecords = filteredStudyRecords.filter((record) => {
        const recordDate = new Date(record.reviewed_at);
        if (start && recordDate < start) return false;
        if (end && recordDate > end) return false;
        if (record.session_id === null) return false;
        const session = filteredStudySessions.find((s) => s.id === record.session_id);
        return session !== undefined;
      });

      // Wyniki egzaminów
      filteredExamResults = filteredExamResults.filter((exam) => {
        const examDate = new Date(exam.started_at);
        if (start && examDate < start) return false;
        if (end && examDate > end) return false;
        return true;
      });

      // Średnie dzienne egzaminów
      filteredExamDailyAverage = filteredExamDailyAverage.filter((avg) => {
        const avgDate = new Date(avg.date);
        if (start && avgDate < start) return false;
        if (end && avgDate > end) return false;
        return true;
      });

      // Średnie dzienne fiszek
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

      // Czas trwania sesji
      const relevantSessionDates = new Set(filteredStudySessions.map((s) => s.started_at.split('T')[0]));
      filteredSessionDurations = filteredSessionDurations.filter((dur) => relevantSessionDates.has(dur.date));
    }

    // Filtrowanie po egzaminie
    if (selectedExamId) {
      filteredExamResults = filteredExamResults.filter((exam) => exam.exam_id === selectedExamId);
    }

    // Filtrowanie po talii
    if (selectedDeckId) {
      filteredStudySessions = filteredStudySessions.filter((session) => session.deck_id === selectedDeckId);
      const sessionIds = new Set(filteredStudySessions.map((s) => s.id));
      filteredStudyRecords = filteredStudyRecords.filter(
        (record) => record.session_id !== null && sessionIds.has(record.session_id)
      );
    }

    // Filtrowanie fiszek powiązanych z tymi rekordami nauki
    const userFlashcardIds = new Set(
      filteredStudyRecords.map((r) => r.user_flashcard_id).filter((id) => id !== null) as number[]
    );
    filteredUserFlashcards = data.user_flashcards.filter((card) => userFlashcardIds.has(card.id));

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
        const duration = (end.getTime() - start.getTime()) / (1000 * 60 * 60);
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
      combinedMap.get(date)!.study_sessions += 1;
    });
    filteredData.exam_results.forEach((exam) => {
      const date = exam.started_at.split('T')[0];
      if (!combinedMap.has(date)) {
        combinedMap.set(date, { study_sessions: 0, exams_completed: 0 });
      }
      combinedMap.get(date)!.exams_completed += 1;
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
    filteredData.study_sessions.forEach((session) => {
      const sessionDate = session.started_at.split('T')[0];
      const durationRecord = filteredData.session_durations.find((d) => d.date === sessionDate);
      if (durationRecord) {
        studyTimeMap.set(sessionDate, (studyTimeMap.get(sessionDate) || 0) + durationRecord.duration_hours);
      }
    });
    return sortByDateAscending(
      Array.from(studyTimeMap.entries()).map(([date, total_study_time]) => ({
        date,
        total_study_time: parseFloat(total_study_time.toFixed(2)),
      }))
    );
  }, [filteredData]);

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
      Array.from(reviewMap.entries()).map(([date, count]) => ({ date, count }))
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
      Array.from(solvedMap.entries()).map(([date, count]) => ({ date, count }))
    );
  }, [filteredData]);

  const flashcardsByHourData = useMemo(() => {
    if (!filteredData) return [];
    const hourMap = new Map<number, number>();
    filteredData.study_records.forEach((record) => {
      if (!record.reviewed_at) return;
      const hour = new Date(record.reviewed_at).getHours();
      hourMap.set(hour, (hourMap.get(hour) || 0) + 1);
    });
    return Array.from(hourMap.entries())
      .sort((a, b) => a[0] - b[0])
      .map(([hour, count]) => ({ hour, count }));
  }, [filteredData]);

  const averageFlashcardsSolved = useMemo(() => {
    if (flashcardsSolvedDaily.length === 0) return 0;
    const total = flashcardsSolvedDaily.reduce((acc, record) => acc + record.count, 0);
    return total / flashcardsSolvedDaily.length;
  }, [flashcardsSolvedDaily]);

  // Renderowanie warunkowe
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
    <div className="p-4 w-full text-foreground bg-background">
      <h2 className="text-3xl font-bold mb-6 text-center text-primary">
        {t('dashboardTitle')}
      </h2>

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
        {/* Analiza egzaminów */}
        <div className="border border-border rounded-lg p-4 bg-card shadow-sm">
          <button
            className="flex justify-between items-center w-full text-left focus:outline-none hover:bg-accent/10 p-2 rounded-lg"
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
                <div className="col-span-2 bg-accent/10 border border-accent p-4 rounded-lg">
                  <strong className="font-bold block mb-2">
                    {t('noExams.title')}
                  </strong>
                  <span className="block mb-4">
                    {t('noExams.description')}
                  </span>
                  <Link
                    href="/tests"
                    className="bg-primary text-primary-foreground px-4 py-2 rounded-md hover:brightness-110 transition-all"
                  >
                    {t('noExams.addExam')}
                  </Link>
                </div>
              ) : (
                <>
                  <div>
                    <h4 className="text-lg font-semibold mb-2">
                      {t('averageExamScoresOverTime')}
                    </h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={examLineChartData}>
                        <CartesianGrid
                          stroke={chartColors.border}
                          strokeDasharray="3 3"
                        />
                        <XAxis
                          dataKey="date"
                          stroke={chartColors.foreground}
                          tick={{ fill: chartColors.foreground }}
                        />
                        <YAxis
                          domain={[0, 100]}
                          stroke={chartColors.foreground}
                          tick={{ fill: chartColors.foreground }}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'hsl(var(--card))',
                            borderColor: chartColors.border,
                            borderRadius: 'var(--radius)',
                          }}
                        />
                        <Legend
                          wrapperStyle={{ color: chartColors.foreground }}
                        />
                        <Line
                          type="monotone"
                          dataKey="average_score"
                          stroke={chartColors.primary}
                          strokeWidth={2}
                          dot={{ fill: chartColors.primary }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>

                  <div>
                    <h4 className="text-lg font-semibold mb-2">
                      {t('timeSpentStudyingExams')}
                    </h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={examStudyTimeData}>
                        <CartesianGrid
                          stroke={chartColors.border}
                          strokeDasharray="3 3"
                        />
                        <XAxis
                          dataKey="date"
                          stroke={chartColors.foreground}
                          tick={{ fill: chartColors.foreground }}
                        />
                        <YAxis
                          stroke={chartColors.foreground}
                          tick={{ fill: chartColors.foreground }}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'hsl(var(--card))',
                            borderColor: chartColors.border,
                            borderRadius: 'var(--radius)',
                          }}
                        />
                        <Legend wrapperStyle={{ color: chartColors.foreground }} />
                        <Bar
                          dataKey="study_time"
                          fill={chartColors.primary}
                          radius={[4, 4, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Histogram wyników egzaminów */}
                  <div className="md:col-span-2">
                    <h4 className="text-lg font-semibold mb-2">
                      {t('examScoreDistribution')}
                    </h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={histogramExamResultsData}>
                        <CartesianGrid
                          stroke={chartColors.border}
                          strokeDasharray="3 3"
                        />
                        <XAxis
                          dataKey="score"
                          stroke={chartColors.foreground}
                          tick={{ fill: chartColors.foreground }}
                        />
                        <YAxis
                          allowDecimals={false}
                          stroke={chartColors.foreground}
                          tick={{ fill: chartColors.foreground }}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'hsl(var(--card))',
                            borderColor: chartColors.border,
                            borderRadius: 'var(--radius)',
                          }}
                        />
                        <Legend wrapperStyle={{ color: chartColors.foreground }} />
                        <Bar
                          dataKey="count"
                          fill={chartColors.secondary}
                          radius={[4, 4, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  {/* Sesje i egzaminy na dzień */}
                  <div className="md:col-span-2">
                    <h4 className="text-lg font-semibold mb-2">
                      {t('sessionsAndExamsPerDay')}
                    </h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={combinedExamData}>
                        <CartesianGrid
                          stroke={chartColors.border}
                          strokeDasharray="3 3"
                        />
                        <XAxis
                          dataKey="date"
                          stroke={chartColors.foreground}
                          tick={{ fill: chartColors.foreground }}
                        />
                        <YAxis
                          allowDecimals={false}
                          stroke={chartColors.foreground}
                          tick={{ fill: chartColors.foreground }}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'hsl(var(--card))',
                            borderColor: chartColors.border,
                            borderRadius: 'var(--radius)',
                          }}
                        />
                        <Legend wrapperStyle={{ color: chartColors.foreground }} />
                        <Bar
                          dataKey="study_sessions"
                          fill={chartColors.primary}
                          radius={[4, 4, 0, 0]}
                        />
                        <Bar
                          dataKey="exams_completed"
                          fill={chartColors.secondary}
                          radius={[4, 4, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* Analiza fiszek */}
        <div className="border border-border rounded-lg p-4 bg-card shadow-sm">
          <button
            className="flex justify-between items-center w-full text-left focus:outline-none hover:bg-accent/10 p-2 rounded-lg"
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
                <div className="col-span-2 bg-accent/10 border border-accent p-4 rounded-lg">
                  <strong className="font-bold block mb-2">
                    {t('noFlashcards.title')}
                  </strong>
                  <span className="block mb-4">
                    {t('noFlashcards.description')}
                  </span>
                  <Link
                    href="/flashcards"
                    className="bg-secondary text-secondary-foreground px-4 py-2 rounded-md hover:brightness-110 transition-all"
                  >
                    {t('noFlashcards.addFlashcards')}
                  </Link>
                </div>
              ) : (
                <>
                  <div>
                    <h4 className="text-lg font-semibold mb-2">
                      {t('averageFlashcardRatingsOverTime')}
                    </h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={flashcardLineChartData}>
                        <CartesianGrid
                          stroke={chartColors.border}
                          strokeDasharray="3 3"
                        />
                        <XAxis
                          dataKey="date"
                          stroke={chartColors.foreground}
                          tick={{ fill: chartColors.foreground }}
                        />
                        <YAxis
                          domain={[0, 5]}
                          stroke={chartColors.foreground}
                          tick={{ fill: chartColors.foreground }}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'hsl(var(--card))',
                            borderColor: chartColors.border,
                            borderRadius: 'var(--radius)',
                          }}
                        />
                        <Legend wrapperStyle={{ color: chartColors.foreground }} />
                        <Line
                          type="monotone"
                          dataKey="average_rating"
                          stroke={chartColors.primary}
                          strokeWidth={2}
                          dot={{ fill: chartColors.primary }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>

                  <div>
                    <h4 className="text-lg font-semibold mb-2">
                      {t('totalTimeStudyingFlashcards')}
                    </h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <AreaChart data={totalStudyTimeData}>
                        <defs>
                          <linearGradient id="colorTotalStudy" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={chartColors.primary} stopOpacity={0.8} />
                            <stop offset="95%" stopColor={chartColors.primary} stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid
                          stroke={chartColors.border}
                          strokeDasharray="3 3"
                        />
                        <XAxis
                          dataKey="date"
                          stroke={chartColors.foreground}
                          tick={{ fill: chartColors.foreground }}
                        />
                        <YAxis
                          stroke={chartColors.foreground}
                          tick={{ fill: chartColors.foreground }}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'hsl(var(--card))',
                            borderColor: chartColors.border,
                            borderRadius: 'var(--radius)',
                          }}
                        />
                        <Legend wrapperStyle={{ color: chartColors.foreground }} />
                        <Area
                          type="monotone"
                          dataKey="total_study_time"
                          stroke={chartColors.primary}
                          fill="url(#colorTotalStudy)"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="md:col-span-2">
                    <h4 className="text-lg font-semibold mb-2">
                      {t('flashcardsSolvedByHour')}
                    </h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={flashcardsByHourData}>
                        <CartesianGrid
                          stroke={chartColors.border}
                          strokeDasharray="3 3"
                        />
                        <XAxis
                          dataKey="hour"
                          stroke={chartColors.foreground}
                          tick={{ fill: chartColors.foreground }}
                        />
                        <YAxis
                          allowDecimals={false}
                          stroke={chartColors.foreground}
                          tick={{ fill: chartColors.foreground }}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'hsl(var(--card))',
                            borderColor: chartColors.border,
                            borderRadius: 'var(--radius)',
                          }}
                        />
                        <Legend wrapperStyle={{ color: chartColors.foreground }} />
                        <Bar
                          dataKey="count"
                          fill={chartColors.secondary}
                          radius={[4, 4, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="md:col-span-2">
                    <h4 className="text-lg font-semibold mb-2">
                      {t('plannedStudySessions')}
                    </h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <LineChart data={nextReviewTimelineData}>
                        <CartesianGrid
                          stroke={chartColors.border}
                          strokeDasharray="3 3"
                        />
                        <XAxis
                          dataKey="date"
                          stroke={chartColors.foreground}
                          tick={{ fill: chartColors.foreground }}
                        />
                        <YAxis
                          stroke={chartColors.foreground}
                          tick={{ fill: chartColors.foreground }}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'hsl(var(--card))',
                            borderColor: chartColors.border,
                            borderRadius: 'var(--radius)',
                          }}
                        />
                        <Legend wrapperStyle={{ color: chartColors.foreground }} />
                        <Line
                          type="monotone"
                          dataKey="count"
                          stroke={chartColors.primary}
                          strokeWidth={2}
                          dot={{ fill: chartColors.primary }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="md:col-span-2">
                    <h4 className="text-lg font-semibold mb-2">
                      {t('flashcardsSolvedDaily')}
                    </h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={flashcardsSolvedDaily}>
                        <CartesianGrid
                          stroke={chartColors.border}
                          strokeDasharray="3 3"
                        />
                        <XAxis
                          dataKey="date"
                          stroke={chartColors.foreground}
                          tick={{ fill: chartColors.foreground }}
                        />
                        <YAxis
                          allowDecimals={false}
                          stroke={chartColors.foreground}
                          tick={{ fill: chartColors.foreground }}
                        />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: 'hsl(var(--card))',
                            borderColor: chartColors.border,
                            borderRadius: 'var(--radius)',
                          }}
                        />
                        <Legend wrapperStyle={{ color: chartColors.foreground }} />
                        <Bar
                          dataKey="count"
                          fill={chartColors.secondary}
                          radius={[4, 4, 0, 0]}
                        />
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

      <hr className="my-8 border-t border-border" />

      <CookbookSection />
    </div>
  );
};

export default Dashboard;
