// src/components/ExamsPage.tsx
'use client'

import { useState, useEffect } from 'react'
import { EditExamDialog } from '@/components/EditExamDialog'
import axios from 'axios'
import { Button } from "@/components/ui/button"
import { PlusCircle, BookOpen, Loader2, Info, ChevronRight, MoreVertical, Edit2, Trash2 } from 'lucide-react'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { CustomTooltip } from '@/components/CustomTooltip'
import { StudyExam } from '@/components/StudyExam'
import { useTranslation } from 'react-i18next';
import React from 'react'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';

interface ExamAnswer {
  id: number;
  text: string;
  is_correct: boolean;
}

interface ExamQuestion {
  id: number;
  text: string;
  answers: ExamAnswer[];
}

interface Exam {
  id: number;
  name: string;
  description?: string;
  created_at: string;
  questions: ExamQuestion[];
}

export default function ExamsPage() {
  const [exams, setExams] = useState<Exam[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [studyingExam, setStudyingExam] = useState<Exam | null>(null)

  const { t } = useTranslation();

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8043/api/exams/'

  const fetchExams = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await axios.get<Exam[]>(API_BASE_URL)
      setExams(response.data)
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response) {
        setError(err.response.data.detail || t('error_fetch_exams'))
      } else {
        setError(t('error_unexpected_fetch_exams'))
      }
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchExams()
  }, [])

  const handleSave = async (updatedExam: Exam) => {
    try {
      if (updatedExam.id === 0) {
        // Create new exam
        const createExamResponse = await axios.post<Exam>(API_BASE_URL, {
          name: updatedExam.name,
          description: updatedExam.description,
          questions: updatedExam.questions.map(q => ({
            text: q.text,
            answers: q.answers.map(a => ({
              text: a.text,
              is_correct: a.is_correct
            }))
          })),
        });
        const newExam = createExamResponse.data;
        setExams(prevExams => [...prevExams, newExam]);
      } else {
        // Update existing exam
        const updateExamResponse = await axios.put<Exam>(`${API_BASE_URL}${updatedExam.id}/`, {
          name: updatedExam.name,
          description: updatedExam.description,
          questions: updatedExam.questions.map(q => {
            if (q.id) {
              return {
                id: q.id,
                text: q.text,
                answers: q.answers.map(a => {
                  if (a.id) {
                    return {
                      id: a.id,
                      text: a.text,
                      is_correct: a.is_correct
                    };
                  } else {
                    return {
                      text: a.text,
                      is_correct: a.is_correct
                    };
                  }
                })
              };
            } else {
              return {
                text: q.text,
                answers: q.answers.map(a => ({
                  text: a.text,
                  is_correct: a.is_correct
                }))
              };
            }
          }),
        });
        const updatedExamFromServer = updateExamResponse.data;
        setExams(prevExams => prevExams.map(exam =>
          exam.id === updatedExamFromServer.id ? updatedExamFromServer : exam
        ));
      }
    } catch (error: unknown) {
      if (axios.isAxiosError(error) && error.response) {
        console.error("Error saving exam:", error.response.data);
        setError(`${t('error_saving_exam')}: ${JSON.stringify(error.response.data)}`);
      } else {
        console.error("Error saving exam:", error);
        setError(t('error_unexpected_saving_exam'));
      }
    }
  };

  const handleDelete = async (examId: number) => {
    try {
      await axios.delete(`${API_BASE_URL}${examId}/`)
      setExams(exams.filter(exam => exam.id !== examId))
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response) {
        console.error("Error deleting exam:", err.response.data);
        setError(`${t('error_deleting_exam')}: ${err.response.data.detail || err.response.statusText}`);
      } else {
        console.error(err)
        setError(t('error_unexpected_deleting_exam'))
      }
    }
  }

  const handleStudy = (exam: Exam) => {
    setStudyingExam(exam);
  }

  const handleExitStudy = () => {
    setStudyingExam(null);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <Loader2 className="mr-2 h-16 w-16 animate-spin text-primary" />
        <span className="text-xl font-semibold text-primary">{t('loading_exams')}</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen p-4 bg-background">
        <Card className="w-full max-w-sm bg-card shadow-lg">
          <CardHeader>
            <CardTitle className="text-destructive">{t('error')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-destructive">{error}</p>
          </CardContent>
          <CardFooter>
            <Button onClick={fetchExams} className="bg-primary hover:bg-primary-dark text-primary-foreground">
              {t('try_again')}
            </Button>
          </CardFooter>
        </Card>
      </div>
    )
  }

  if (studyingExam) {
    return <StudyExam exam={studyingExam} onExit={handleExitStudy} />;
  }

  return (
    <div className="p-4 max-w-full mx-auto bg-background">
      {/* Header Section */}
      <div className="text-center mb-6 flex flex-col items-center justify-center space-y-2">
        <h1 className="text-5xl font-extrabold text-primary">{t('tests')}</h1>
        <div className="flex items-center space-x-2">
          <CustomTooltip className="" content={t('tests_tooltip')}>
            <Button variant="ghost" size="icon" className="text-secondary hover:text-primary">
              <Info className="h-6 w-6" />
              <span className="sr-only">{t('more_information')}</span>
            </Button>
          </CustomTooltip>
        </div>
      </div>

      {/* No Exams Available */}
      {exams.length === 0 ? (
        <div className="flex flex-col items-center justify-center">
          <Card className="w-full max-w-2xl bg-card shadow-lg">
            <CardHeader>
              <CardTitle className="text-3xl font-bold text-primary">{t('welcome_tests')}</CardTitle>
              <CardDescription className="text-xl text-secondary">{t('get_started_create_test')}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center justify-center space-y-6 py-12">
              <BookOpen className="h-40 w-40 text-muted-foreground" />
              <p className="text-center text-muted-foreground text-xl">
                {t('no_tests_available')}
              </p>
            </CardContent>
            <CardFooter className="flex justify-center space-x-4">
              <EditExamDialog
                exam={{ id: 0, name: '', description: '', questions: [] }}
                onSave={handleSave}
                trigger={
                  <Button className="flex items-center space-x-2 px-6 py-3 bg-primary hover:bg-primary-dark text-primary-foreground">
                    <PlusCircle className="h-6 w-6" />
                    <span>{t('create_your_first_test')}</span>
                  </Button>
                }
              />
            </CardFooter>
          </Card>
        </div>
      ) : (
        <>
          {/* Create New Exam Button */}
          <div className="mb-8 flex justify-end">
            <EditExamDialog
              exam={{ id: 0, name: '', description: '', questions: [] }}
              onSave={handleSave}
              trigger={
                <Button className="flex items-center space-x-2 px-6 py-3 bg-primary hover:bg-primary-dark text-primary-foreground">
                  <PlusCircle className="h-6 w-6" />
                  <span>{t('create_new_test')}</span>
                </Button>
              }
            />
          </div>

          {/* Exams Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 gap-8">
            {exams.map(exam => (
              <Card key={exam.id} className="flex flex-col min-h-[350px] bg-card shadow-lg">
                <CardHeader className="flex flex-col">
                  <div className="flex justify-between items-center space-x-4">
                    <CardTitle className="text-2xl font-bold truncate text-primary">{exam.name}</CardTitle>
                    {/* Collapsible Menu for Edit/Delete */}
                    <Collapsible>
                      <CollapsibleTrigger asChild>
                        <Button variant="ghost" size="sm" className="p-1 text-secondary hover:text-primary">
                          <MoreVertical className="h-5 w-5" />
                        </Button>
                      </CollapsibleTrigger>
                      <CollapsibleContent className="absolute right-4 top-16 bg-card border border-border rounded-md shadow-lg z-50">
                        <div className="flex flex-col">
                          <EditExamDialog
                            exam={exam}
                            onSave={handleSave}
                            trigger={
                              <Button
                                variant="ghost"
                                size="sm"
                                className="flex items-center justify-start w-full px-4 py-2 hover:bg-secondary/80 text-primary"
                              >
                                <Edit2 className="h-4 w-4 mr-2" />
                                {t('edit')}
                              </Button>
                            }
                          />
                          <Button
                            variant="ghost"
                            size="sm"
                            className="flex items-center justify-start w-full px-4 py-2 text-destructive hover:bg-secondary/80"
                            onClick={() => handleDelete(exam.id)}
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            {t('delete')}
                          </Button>
                        </div>
                      </CollapsibleContent>
                    </Collapsible>
                  </div>
                  <CardDescription className="mt-3 text-lg break-words text-muted-foreground">
                    {exam.description || t('no_description')}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex-grow">
                  <p className="text-lg text-muted-foreground">
                    {exam.questions.length} {t('questions_lowercase')}
                  </p>
                </CardContent>
                <CardFooter className="mt-auto flex justify-end space-x-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleStudy(exam)}
                    className="flex items-center space-x-2 px-4 py-2"
                  >
                    <span>{t('study')}</span>
                    <ChevronRight className="h-5 w-5" />
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
