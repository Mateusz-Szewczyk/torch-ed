'use client';

import React, { useState } from 'react';
import {
    LineChart, Line,
    BarChart, Bar,
    PieChart, Pie, Cell,
    XAxis, YAxis,
    Tooltip, Legend,
    ResponsiveContainer
} from 'recharts';

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
}

const Dashboard: React.FC<{ data: DashboardData }> = ({ data }) => {
    const [selectedExamId, setSelectedExamId] = useState<number | null>(null);
    const [selectedDeckId, setSelectedDeckId] = useState<number | null>(null);

    // Filtry
    const filteredExamResults = selectedExamId
        ? data.exam_results.filter((exam) => exam.exam_id === selectedExamId)
        : data.exam_results;

    const filteredStudyRecords = selectedDeckId
        ? data.study_records.filter((record) => {
            const session = data.study_sessions.find((session) => session.id === record.session_id);
            return session?.deck_id === selectedDeckId;
        })
        : data.study_records;

    // Kolory
    const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042'];

    return (
        <div className="p-4">
            <h2 className="text-2xl font-bold mb-6">Dashboard Nauki</h2>

            {/* Sekcja Egzaminów */}
            <div className="mb-12">
                <h3 className="text-xl font-bold mb-4">Analiza Egzaminów</h3>
                <div className="mb-4">
                    <label htmlFor="exam-select" className="block mb-2">
                        Wybierz egzamin:
                    </label>
                    <select
                        id="exam-select"
                        className="border p-2 rounded w-full"
                        onChange={(e) => setSelectedExamId(Number(e.target.value) || null)}
                    >
                        <option value="">Wszystkie</option>
                        {Array.from(new Set(data.exam_results.map((exam) => exam.exam_id))).map((examId) => (
                            <option key={examId} value={examId}>
                                Egzamin {examId}
                            </option>
                        ))}
                    </select>
                </div>
                <ResponsiveContainer width="100%" height={300}>
                    <LineChart
                        data={filteredExamResults.map((exam) => ({
                            date: exam.started_at.split('T')[0],
                            score: exam.score,
                        }))}
                    >
                        <XAxis dataKey="date" />
                        <YAxis domain={[0, 100]} />
                        <Tooltip />
                        <Legend />
                        <Line type="monotone" dataKey="score" name="Wynik Egzaminu" stroke="#82ca9d" />
                    </LineChart>
                </ResponsiveContainer>

                {/* Kolejne wykresy dla egzaminów */}
                <div className="grid grid-cols-2 gap-4 mt-8">
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart
                            data={filteredExamResults.map((exam) => ({
                                date: exam.started_at.split('T')[0],
                                score: exam.score,
                            }))}
                        >
                            <XAxis dataKey="date" />
                            <YAxis />
                            <Tooltip />
                            <Legend />
                            <Bar dataKey="score" name="Wynik Egzaminu" fill="#8884d8" />
                        </BarChart>
                    </ResponsiveContainer>

                    <ResponsiveContainer width="100%" height={300}>
                        <PieChart>
                            <Pie
                                data={filteredExamResults.map((exam) => ({
                                    name: `Egzamin ${exam.exam_id}`,
                                    value: exam.score,
                                }))}
                                dataKey="value"
                                nameKey="name"
                                cx="50%"
                                cy="50%"
                                outerRadius={100}
                                label
                            >
                                {filteredExamResults.map((_, index) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                            </Pie>
                            <Tooltip />
                            <Legend />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Sekcja Fiszek */}
            <div>
                <h3 className="text-xl font-bold mb-4">Analiza Fiszek</h3>
                <div className="mb-4">
                    <label htmlFor="deck-select" className="block mb-2">
                        Wybierz zestaw fiszek:
                    </label>
                    <select
                        id="deck-select"
                        className="border p-2 rounded w-full"
                        onChange={(e) => setSelectedDeckId(Number(e.target.value) || null)}
                    >
                        <option value="">Wszystkie</option>
                        {Array.from(new Set(data.study_sessions.map((session) => session.deck_id))).map((deckId) => (
                            <option key={deckId} value={deckId}>
                                Zestaw {deckId}
                            </option>
                        ))}
                    </select>
                </div>
                <ResponsiveContainer width="100%" height={300}>
                    <LineChart
                        data={filteredStudyRecords.map((record) => ({
                            date: record.reviewed_at.split('T')[0],
                            rating: record.rating,
                        }))}
                    >
                        <XAxis dataKey="date" />
                        <YAxis domain={[0, 5]} />
                        <Tooltip />
                        <Legend />
                        <Line type="monotone" dataKey="rating" name="Ocena Fiszek" stroke="#8884d8" />
                    </LineChart>
                </ResponsiveContainer>

                {/* Kolejne wykresy dla fiszek */}
                <div className="grid grid-cols-2 gap-4 mt-8">
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart
                            data={filteredStudyRecords.map((record) => ({
                                date: record.reviewed_at.split('T')[0],
                                rating: record.rating,
                            }))}
                        >
                            <XAxis dataKey="date" />
                            <YAxis />
                            <Tooltip />
                            <Legend />
                            <Bar dataKey="rating" name="Ocena Fiszek" fill="#82ca9d" />
                        </BarChart>
                    </ResponsiveContainer>

                    <ResponsiveContainer width="100%" height={300}>
                        <PieChart>
                            <Pie
                                data={filteredStudyRecords.map((record) => ({
                                    name: `Fiszek ${record.id}`,
                                    value: record.rating,
                                }))}
                                dataKey="value"
                                nameKey="name"
                                cx="50%"
                                cy="50%"
                                outerRadius={100}
                                label
                            >
                                {filteredStudyRecords.map((_, index) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                            </Pie>
                            <Tooltip />
                            <Legend />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
};

export default Dashboard;
