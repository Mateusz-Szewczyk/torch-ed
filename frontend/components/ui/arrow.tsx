import { motion } from "framer-motion"
import type React from "react"

interface ArrowProps {
  start: { x: number; y: number }
  end: { x: number; y: number }
}

export const Arrow: React.FC<ArrowProps> = ({ start, end }) => {
  const dx = end.x - start.x
  const dy = end.y - start.y
  const angle = Math.atan2(dy, dx) * (180 / Math.PI)
  const length = Math.sqrt(dx * dx + dy * dy)

  return (
    <motion.div
      style={{
        position: "absolute",
        top: start.y,
        left: start.x,
        width: length,
        height: 2,
        background: "hsl(var(--primary))",
        transformOrigin: "left center",
        transform: `rotate(${angle}deg)`,
      }}
      initial={{ opacity: 0, scale: 0 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0 }}
      transition={{ duration: 0.3 }}
    >
      <motion.div
        style={{
          position: "absolute",
          right: -6,
          top: -4,
          width: 0,
          height: 0,
          borderTop: "5px solid transparent",
          borderBottom: "5px solid transparent",
          borderLeft: "10px solid hsl(var(--primary))",
        }}
      />
    </motion.div>
  )
}

