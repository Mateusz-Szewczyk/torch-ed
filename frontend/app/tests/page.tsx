'use client';

import React, { useState, useEffect, useCallback, MouseEvent } from "react";
import { EditExamDialog } from "@/components/EditExamDialog";
import { Button } from "@/components/ui/button";
import {
  PlusCircle,
  BookOpen,
  Loader2,
  Info,
  ChevronRight,
  MoreVertical,
  Edit2,
  Trash2,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { CustomTooltip } from "@/components/CustomTooltip";
import { StudyExam } from "@/components/StudyExam";
import { useTranslation } from "react-i18next";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

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
  description: string;
  created_at: string;
  // If conversation_id is missing or 0, a new conversation should be created.
  conversation_id?: number;
  questions: ExamQuestion[];
}

export default function ExamsPage() {
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [studyingExam, setStudyingExam] = useState<Exam | null>(null);
  const [openCollapsibles, setOpenCollapsibles] = useState<{ [key: number]: boolean }>({});

  const { t } = useTranslation();

  // Define base URLs.
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_RAG_URL || "http://localhost:8043/api";
  const EXAMS_API_BASE = `${API_BASE_URL}/exams/`;
  const CONVERSATIONS_URL = `${API_BASE_URL}/chats/`;

  /**
   * Fetch exams from the backend.
   */
  const fetchExams = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(EXAMS_API_BASE, {
        method: "GET",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || t("error_fetch_exams") || "Error fetching exams.");
      }
      const data: Exam[] = await res.json();
      setExams(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(t("error_unexpected_fetch_exams") || "Unexpected error fetching exams.");
      }
      console.error("Error fetching exams:", err);
    } finally {
      setLoading(false);
    }
  }, [EXAMS_API_BASE, t]);

  useEffect(() => {
    fetchExams();
  }, [fetchExams]);

  /**
   * Create or update an exam.
   */
  const handleSave = async (updatedExam: Exam) => {
    try {
      const bodyData = {
        name: updatedExam.name,
        description: updatedExam.description,
        questions: updatedExam.questions.map((q) => ({
          id: q.id,
          text: q.text,
          answers: q.answers.map((a) =>
            a.id
              ? { id: a.id, text: a.text, is_correct: a.is_correct }
              : { text: a.text, is_correct: a.is_correct }
          ),
        })),
        conversation_id: updatedExam.conversation_id || 0,
      };

      if (updatedExam.id === 0) {
        // Create new exam – conversation_id defaults to 0.
        const res = await fetch(EXAMS_API_BASE, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(bodyData),
        });
        if (!res.ok) {
          const errorData = await res.json();
          throw new Error(errorData.detail || t("error_saving_exam") || "Error creating exam.");
        }
        const newExam: Exam = await res.json();
        setExams((prev) => [...prev, newExam]);
      } else {
        // Update existing exam.
        const res = await fetch(`${EXAMS_API_BASE}${updatedExam.id}/`, {
          method: "PUT",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(bodyData),
        });
        if (!res.ok) {
          const errorData = await res.json();
          throw new Error(errorData.detail || t("error_saving_exam") || "Error updating exam.");
        }
        const updatedExamFromServer: Exam = await res.json();
        setExams((prev) =>
          prev.map((exam) => (exam.id === updatedExamFromServer.id ? updatedExamFromServer : exam))
        );
      }
    } catch (err: unknown) {
      console.error("Error saving exam:", err);
      if (err instanceof Error) {
        setError(`${t("error_saving_exam")}: ${err.message}`);
      } else {
        setError(t("error_unexpected_saving_exam") || "Unexpected error saving exam.");
      }
    }
  };

  /**
   * Delete an exam.
   */
  const handleDelete = async (examId: number) => {
    try {
      const res = await fetch(`${EXAMS_API_BASE}${examId}/`, {
        method: "DELETE",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || t("error_deleting_exam") || "Error deleting exam.");
      }
      setExams((prev) => prev.filter((exam) => exam.id !== examId));
    } catch (err: unknown) {
      if (err instanceof Error) {
        console.error("Error deleting exam:", err);
        setError(`${t("error_deleting_exam")}: ${err.message}`);
      } else {
        console.error(err);
        setError(t("error_unexpected_deleting_exam") || "Unexpected error deleting exam.");
      }
    }
  };

  /**
   * Start an exam study session:
   * 1) If the exam does not have a conversation_id (or it is 0), create a new conversation
   *    (the server will update the exam with the new conversation_id).
   * 2) Re-fetch the exam from the server to get the updated conversation_id.
   * 3) Enter study mode using the exam's conversation_id.
   */
  const handleStudy = async (exam: Exam) => {
    try {
      let finalExam: Exam = exam;

      if (!exam.conversation_id || exam.conversation_id === 0) {
        // Create a new conversation for the exam.
        const convRes = await fetch(CONVERSATIONS_URL, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ exam_id: exam.id, title: exam.name }),
        });
        if (!convRes.ok) {
          const convErr = await convRes.json();
          let errorMsg = "Failed to create conversation.";
          if (Array.isArray(convErr.detail)) {
            errorMsg = convErr.detail
              .map((detailErr: unknown) =>
                typeof detailErr === "object" && detailErr !== null && "msg" in detailErr
                  ? (detailErr as { msg: string }).msg
                  : String(detailErr)
              )
              .join(", ");
          } else if (typeof convErr.detail === "string") {
            errorMsg = convErr.detail;
          }
          throw new Error(errorMsg);
        }
        // Re-fetch the exam to get the updated conversation_id.
        const updatedExamResp = await fetch(`${EXAMS_API_BASE}${exam.id}/`, {
          method: "GET",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
        });
        if (!updatedExamResp.ok) {
          const fetchErr = await updatedExamResp.json();
          throw new Error(fetchErr.detail || "Could not re-fetch updated exam.");
        }
        finalExam = await updatedExamResp.json();
        // Update the local exams list.
        setExams((prev) => prev.map((e) => (e.id === exam.id ? finalExam : e)));
      }

      // Enter study mode for the exam using its conversation_id.
      setStudyingExam(finalExam);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(`${t("error_starting_study")}: ${err.message}`);
      } else {
        setError(t("error_unexpected_starting_study") || "Unexpected error starting exam session.");
      }
      console.error("Error starting exam session:", err);
    }
  };

  const handleExitStudy = () => {
    setStudyingExam(null);
  };

  const toggleCollapsible = (examId: number) => {
    setOpenCollapsibles((prev) => ({
      ...prev,
      [examId]: !prev[examId],
    }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <Loader2 className="mr-2 h-16 w-16 animate-spin text-primary" />
        <span className="text-xl font-semibold text-primary">
          {t("loading_exams")}
        </span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen p-4 bg-background">
        <Card className="w-full max-w-sm bg-card shadow-lg">
          <CardHeader>
            <CardTitle className="text-destructive">{t("error")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-destructive">{error}</p>
          </CardContent>
          <CardFooter>
            <Button onClick={fetchExams} className="bg-primary hover:bg-primary-dark text-primary-foreground">
              {t("try_again")}
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  if (studyingExam) {
    return <StudyExam exam={studyingExam} onExit={handleExitStudy} />;
  }

  return (
    <div className="p-4 max-w-full mx-auto bg-background">
      {/* Header Section */}
      <div className="text-center mb-6 flex flex-col items-center justify-center space-y-2">
        <h1 className="text-5xl font-extrabold text-primary">
          {t("tests")}
        </h1>
        <div className="flex items-center space-x-2">
          <CustomTooltip content={t("tests_tooltip")}>
            <Button variant="ghost" size="icon" className="hover:text-primary">
              <Info className="h-6 w-6" />
              <span className="sr-only">{t("more_information")}</span>
            </Button>
          </CustomTooltip>
        </div>
      </div>

      {exams.length === 0 ? (
        <div className="flex flex-col items-center justify-center">
          <Card className="w-full max-w-2xl bg-card shadow-lg">
            <CardHeader>
              <CardTitle className="text-3xl font-bold text-primary">
                {t("welcome_tests")}
              </CardTitle>
              <CardDescription className="text-xl text-secondary">
                {t("get_started_create_test")}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center justify-center space-y-6 py-12">
              <BookOpen className="h-40 w-40 text-muted-foreground" />
              <p className="text-center text-muted-foreground text-xl">
                {t("no_tests_available")}
              </p>
            </CardContent>
            <CardFooter className="flex justify-center space-x-4">
              <EditExamDialog
                exam={{ id: 0, name: "", description: "", created_at: "", questions: [] }}
                onSave={handleSave}
                trigger={
                  <Button className="flex items-center space-x-2 px-6 py-3 bg-primary hover:bg-primary-dark text-primary-foreground">
                    <PlusCircle className="h-6 w-6" />
                    <span>{t("create_your_first_test")}</span>
                  </Button>
                }
              />
            </CardFooter>
          </Card>
        </div>
      ) : (
        <>
          {/* Button for creating a new exam */}
          <div className="mb-8 flex justify-end">
            <EditExamDialog
              exam={{ id: 0, name: "", description: "", created_at: "", questions: [] }}
              onSave={handleSave}
              trigger={
                <Button className="flex items-center space-x-2 px-6 py-3 bg-primary hover:bg-primary-dark text-primary-foreground">
                  <PlusCircle className="h-6 w-6" />
                  <span>{t("create_new_test")}</span>
                </Button>
              }
            />
          </div>

          {/* Exams grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 gap-8">
            {exams.map((exam) => (
              <Card key={exam.id} className="flex flex-col min-h-[350px] bg-card shadow-lg relative">
                <CardHeader className="flex flex-col">
                  <div className="flex justify-between items-center space-x-4">
                    <CardTitle className="text-2xl font-bold truncate text-primary">
                      {exam.name}
                    </CardTitle>
                    <Collapsible
                      open={openCollapsibles[exam.id] || false}
                      onOpenChange={() => toggleCollapsible(exam.id)}
                    >
                      <CollapsibleTrigger asChild>
                        <Button variant="ghost" size="sm" className="p-1 hover:text-primary" aria-label="Opcje">
                          <MoreVertical className="h-5 w-5" />
                        </Button>
                      </CollapsibleTrigger>
                      <CollapsibleContent className="absolute right-4 top-16 bg-card border border-border rounded-md shadow-lg z-50 p-2">
                        <div className="flex flex-col">
                          <EditExamDialog
                            exam={exam}
                            onSave={handleSave}
                            trigger={
                              <Button
                                variant="ghost"
                                size="sm"
                                className="flex items-center justify-start w-full px-4 py-2 hover:bg-secondary/80 text-primary"
                                onClick={(e: MouseEvent<HTMLButtonElement>) => {
                                  e.stopPropagation();
                                  setOpenCollapsibles((prev) => ({ ...prev, [exam.id]: false }));
                                }}
                              >
                                <Edit2 className="h-4 w-4 mr-2" />
                                {t("edit")}
                              </Button>
                            }
                          />
                          <Button
                            variant="ghost"
                            size="sm"
                            className="flex items-center justify-start w-full px-4 py-2 text-destructive hover:bg-secondary/80"
                            onClick={(e: MouseEvent<HTMLButtonElement>) => {
                              e.stopPropagation();
                              handleDelete(exam.id);
                              setOpenCollapsibles((prev) => ({ ...prev, [exam.id]: false }));
                            }}
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            {t("delete")}
                          </Button>
                        </div>
                      </CollapsibleContent>
                    </Collapsible>
                  </div>
                  <CardDescription className="mt-3 text-lg break-words text-muted-foreground">
                    {exam.description || t("no_description")}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex-grow">
                  <p className="text-lg text-muted-foreground">
                    {exam.questions.length} {t("questions_lowercase")}
                  </p>
                </CardContent>
                <CardFooter className="mt-auto flex justify-end space-x-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleStudy(exam)}
                    className="flex items-center space-x-2 px-4 py-2"
                  >
                    <span>{t("study")}</span>
                    <ChevronRight className="h-5 w-5" />
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
