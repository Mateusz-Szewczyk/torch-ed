"use client"

import type React from "react"
import { useState, useEffect } from "react"
import { motion, AnimatePresence, Reorder } from "framer-motion"
import {Plus, X, GripVertical, FileText, Brain, TestTube, Globe, Sparkles, Info} from "lucide-react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useTranslation } from "react-i18next"
import { CustomTooltip } from "@/components/CustomTooltip";

interface ToolSelectionDialogProps {
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  selectedTools: string[]
  setSelectedTools: React.Dispatch<React.SetStateAction<string[]>>
  availableTools: string[]
}

// Tool icons mapping
const getToolIcon = (tool: string) => {
  const toolKey = tool.toLowerCase().replace(/\s/g, "_")
  const iconMap: Record<string, React.ReactNode> = {
    wiedza_z_plików: <FileText className="h-4 w-4" />,
    generowanie_fiszek: <Brain className="h-4 w-4" />,
    generowanie_egzaminu: <TestTube className="h-4 w-4" />,
    wyszukaj_w_internecie: <Globe className="h-4 w-4" />,
  }
  return iconMap[toolKey] || <Sparkles className="h-4 w-4" />
}

const ToolSelectionDialog: React.FC<ToolSelectionDialogProps> = ({
  isOpen,
  onOpenChange,
  selectedTools,
  setSelectedTools,
  availableTools,
}) => {
  const { t } = useTranslation()
  const [tempSelectedTools, setTempSelectedTools] = useState<string[]>(selectedTools)

  useEffect(() => {
    setTempSelectedTools(selectedTools)
  }, [selectedTools])

  const handleSave = () => {
    setSelectedTools(tempSelectedTools)
    onOpenChange(false)
  }

  const handleCancel = () => {
    setTempSelectedTools(selectedTools)
    onOpenChange(false)
  }

  const addTool = (tool: string) => {
    if (!tempSelectedTools.includes(tool)) {
      setTempSelectedTools((prev) => [...prev, tool])
    }
  }

  const removeTool = (tool: string) => {
    setTempSelectedTools((prev) => prev.filter((t) => t !== tool))
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[550px] p-6">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold flex flex-row items-center justify-center">
            {t("toolbox.select_order_title")  || "Configure Tools"}
              <CustomTooltip content={t("toolbox.select_order_tooltip") || "Drag to reorder tools"}>
                <Info className="ml-5 h-5 w-5 text-muted-foreground cursor-pointer" />
              </CustomTooltip>
          </DialogTitle>
        </DialogHeader>

        <div className="py-4 space-y-6">
          {/* Selected tools section */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-muted-foreground">
                {t("toolbox.selected_tools") || "Selected Tools"}
              </h3>
              <Badge variant="outline" className="text-xs">
                {tempSelectedTools.length} / {availableTools.length}
              </Badge>
            </div>

            {tempSelectedTools.length === 0 ? (
              <div className="text-center py-4 border border-dashed border-border rounded-lg">
                <p className="text-sm text-muted-foreground">{t("toolbox.no_tools_selected") || "No tools selected"}</p>
              </div>
            ) : (
              <Reorder.Group axis="y" values={tempSelectedTools} onReorder={setTempSelectedTools} className="space-y-2">
                {tempSelectedTools.map((tool) => (
                  <Reorder.Item key={tool} value={tool} className="touch-manipulation">
                    <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg group">
                      <div className="flex items-center gap-3">
                        <div className="touch-none cursor-grab active:cursor-grabbing">
                          <GripVertical className="h-4 w-4 text-muted-foreground" />
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full bg-background text-foreground">
                            {getToolIcon(tool)}
                          </span>
                          <span className="text-sm font-medium">
                            {t(`toolbox.${tool.toLowerCase().replace(/\s/g, "_")}`)}
                          </span>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 rounded-full opacity-70 hover:opacity-100"
                        onClick={() => removeTool(tool)}
                      >
                        <X className="h-3.5 w-3.5" />
                        <span className="sr-only">Remove</span>
                      </Button>
                    </div>
                  </Reorder.Item>
                ))}
              </Reorder.Group>
            )}
          </div>

          {/* Available tools section */}
          <div>
            <h3 className="text-sm font-medium text-muted-foreground mb-3">
              {t("toolbox.available_tools") || "Available Tools"}
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <AnimatePresence>
                {availableTools
                  .filter((tool) => !tempSelectedTools.includes(tool))
                  .map((tool) => (
                    <motion.div
                      key={tool}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.15 }}
                    >
                      <Button
                        variant="outline"
                        className="w-full justify-start text-sm h-auto py-2.5 px-3"
                        onClick={() => addTool(tool)}
                      >
                        <span className="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full bg-muted mr-2">
                          {getToolIcon(tool)}
                        </span>
                        <span className="truncate">{t(`toolbox.${tool.toLowerCase().replace(/\s/g, "_")}`)}</span>
                        <Plus className="ml-auto h-3.5 w-3.5 flex-shrink-0 opacity-70" />
                      </Button>
                    </motion.div>
                  ))}
              </AnimatePresence>
            </div>
            {availableTools.filter((tool) => !tempSelectedTools.includes(tool)).length === 0 && (
              <div className="text-center py-4 border border-dashed border-border rounded-lg mt-2">
                <p className="text-sm text-muted-foreground">
                  {t("toolbox.all_tools_selected") || "All tools are selected"}
                </p>
              </div>
            )}
          </div>
        </div>

        <DialogFooter className="flex justify-end gap-2 pt-2">
          <Button variant="outline" size="sm" onClick={handleCancel}>
            {t("toolbox.cancel") || "Cancel"}
          </Button>
          <Button size="sm" onClick={handleSave}>
            {t("toolbox.save") || "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default ToolSelectionDialog
