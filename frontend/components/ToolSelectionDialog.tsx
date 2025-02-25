"use client"

import React, { useState, useEffect, useRef } from "react"
import { motion, AnimatePresence, Reorder } from "framer-motion"
import { ArrowUp, ArrowDown, Plus, X } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogClose
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Arrow } from "@/components/ui/arrow"
import { CustomTooltip } from "@/components/CustomTooltip"
import { useTranslation } from "react-i18next"

const ToolSelectionDialog: React.FC<{
  isOpen: boolean
  onOpenChange: (open: boolean) => void
  selectedTools: string[]
  setSelectedTools: React.Dispatch<React.SetStateAction<string[]>>
  availableTools: string[]
}> = ({ isOpen, onOpenChange, selectedTools, setSelectedTools, availableTools }) => {
  const { t } = useTranslation()
  const [tempSelectedTools, setTempSelectedTools] = useState<string[]>(selectedTools)
  // Refy do elementów – inicjalnie pusta tablica
  const toolRefs = useRef<(HTMLDivElement | null)[]>([])

  // Resetujemy tablicę refów przy każdej zmianie listy narzędzi
  useEffect(() => {
    toolRefs.current = new Array(tempSelectedTools.length).fill(null)
  }, [tempSelectedTools])

  useEffect(() => {
    setTempSelectedTools(selectedTools)
  }, [selectedTools])

  const moveToolUp = (index: number) => {
    if (index > 0) {
      const newTools = [...tempSelectedTools]
      ;[newTools[index - 1], newTools[index]] = [newTools[index], newTools[index - 1]]
      setTempSelectedTools(newTools)
    }
  }

  const moveToolDown = (index: number) => {
    if (index < tempSelectedTools.length - 1) {
      const newTools = [...tempSelectedTools]
      ;[newTools[index], newTools[index + 1]] = [newTools[index + 1], newTools[index]]
      setTempSelectedTools(newTools)
    }
  }

  const handleSave = () => {
    setSelectedTools(tempSelectedTools)
    onOpenChange(false)
  }

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader className="flex items-center justify-between">
          <DialogTitle className="text-2xl font-bold mb-4">
            {t("toolbox.select_order_title")}
          </DialogTitle>
          <CustomTooltip content={t("toolbox.tooltip_description")}>
            <span className="cursor-pointer text-muted-foreground font-bold">?</span>
          </CustomTooltip>
        </DialogHeader>
        <div className="space-y-6">
          {/* Lista wybranych narzędzi z możliwością przeciągania */}
          <Reorder.Group
            axis="y"
            values={tempSelectedTools}
            onReorder={setTempSelectedTools}
            className="space-y-4 relative"
          >
            {tempSelectedTools.map((tool, index) => (
              <Reorder.Item
                key={tool}
                value={tool}
                ref={(el) => {
                  toolRefs.current[index] = el
                }}
                className="flex items-center space-x-2 bg-secondary p-3 rounded-lg relative cursor-grab"
              >
                <span className="font-medium">
                  {t(`toolbox.${tool.toLowerCase().replace(/\s/g, "_")}`)}
                </span>
                <div className="flex-grow" />
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => moveToolUp(index)}
                  disabled={index === 0}
                >
                  <ArrowUp className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => moveToolDown(index)}
                  disabled={index === tempSelectedTools.length - 1}
                >
                  <ArrowDown className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() =>
                    setTempSelectedTools((prev) => prev.filter((t) => t !== tool))
                  }
                >
                  <X className="h-4 w-4" />
                </Button>
              </Reorder.Item>
            ))}
          </Reorder.Group>
          {/* Dynamiczne strzałki między elementami */}
          {tempSelectedTools.length > 1 &&
            tempSelectedTools.slice(0, -1).map((_, index) => {
              const startEl = toolRefs.current[index]
              const endEl = toolRefs.current[index + 1]
              if (startEl && endEl) {
                const startRect = startEl.getBoundingClientRect()
                const endRect = endEl.getBoundingClientRect()
                return (
                  <Arrow
                    key={`arrow-${index}`}
                    start={{
                      x: startRect.left + startRect.width / 2,
                      y: startRect.bottom,
                    }}
                    end={{
                      x: endRect.left + endRect.width / 2,
                      y: endRect.top,
                    }}
                  />
                )
              }
              return null
            })}
          {/* Dostępne narzędzia */}
          <div>
            <h4 className="text-lg font-semibold mb-3">
              {t("toolbox.available_tools")}
            </h4>
            <div className="flex flex-wrap gap-2">
              <AnimatePresence>
                {availableTools
                  .filter((tool) => !tempSelectedTools.includes(tool))
                  .map((tool) => (
                    <motion.div
                      key={tool}
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.8 }}
                      transition={{ duration: 0.2 }}
                    >
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          setTempSelectedTools((prev) => [...prev, tool])
                        }
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        {t(`toolbox.${tool.toLowerCase().replace(/\s/g, "_")}`)}
                      </Button>
                    </motion.div>
                  ))}
              </AnimatePresence>
            </div>
          </div>
        </div>
        <div className="flex justify-end space-x-2 mt-6">
          <DialogClose>
            <Button variant="outline">{t("toolbox.cancel")}</Button>
          </DialogClose>
          <Button onClick={handleSave}>{t("toolbox.save")}</Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default ToolSelectionDialog
