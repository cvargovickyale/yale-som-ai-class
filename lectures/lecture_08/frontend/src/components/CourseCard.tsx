import { useState } from "react"
import type { Course } from "../types"

const CATEGORY_ICONS: Record<string, string> = {
  Core: "🎯",
  "Artificial Intelligence": "🤖",
  Finance: "💰",
  Marketing: "📣",
  Strategy: "♟",
  Operations: "⚙",
  Accounting: "🧾",
  Economics: "📈",
  "Organizational Behavior": "🧠",
  "Entrepreneurship & Private Equity": "🚀",
  Healthcare: "🩺",
  "Healthcare Management": "🩺",
  "Real Estate": "🏠",
  Nonprofit: "🤝",
  International: "🌐",
  "Technology Management": "💻",
  "Business & the Law": "⚖",
  "Business and the Law": "⚖",
  "Business & the Environment": "🌱",
  "Asset Management": "🏦",
  "Political Science": "🏛",
  PhD: "🎓",
}

function categoryIcon(category: string): string {
  return CATEGORY_ICONS[category] ?? "📘"
}

export default function CourseCard({ course }: { course: Course }) {
  const [expanded, setExpanded] = useState(false)

  const number = course.course_number || "—"
  const title = course.course_title || "Untitled Course"
  const faculty = course.faculty_1 || "Staff / TBA"
  const category = course.course_category || "General"
  const daytimes = course.daytimes || "Schedule TBA"
  const room = course.room
  const units = course.units
  const description = course.course_description
  const bio = course.faculty_bio

  return (
    <article
      className={`course-card bevel-raised ${expanded ? "course-card-open" : ""}`}
      onClick={() => setExpanded((v) => !v)}
    >
      <div className="course-card-head">
        <span className="course-number-badge bevel-in">{number}</span>
        <span className="course-category-chip">
          {categoryIcon(category)} {category || "General"}
        </span>
      </div>
      <h3 className="course-title">{title}</h3>
      <dl className="course-meta">
        <div>
          <dt>Faculty</dt>
          <dd>{faculty}</dd>
        </div>
        <div>
          <dt>When</dt>
          <dd>{daytimes}</dd>
        </div>
        {room && (
          <div>
            <dt>Room</dt>
            <dd>{room}</dd>
          </div>
        )}
        {units && (
          <div>
            <dt>Units</dt>
            <dd>{units}</dd>
          </div>
        )}
      </dl>
      <button className="course-card-toggle" tabIndex={-1}>
        {expanded ? "▲ less" : "▼ details"}
      </button>
      {expanded && (
        <div className="course-card-details bevel-in">
          {description && <p>{description}</p>}
          {bio && (
            <p className="course-faculty-bio">
              <strong>About {faculty.split(",")[0]}:</strong> {bio}
            </p>
          )}
          {!description && !bio && <p>No further details on file for this course.</p>}
        </div>
      )}
    </article>
  )
}
