import { useEffect, useMemo, useState } from "react"
import { fetchCourses } from "../api"
import type { Course } from "../types"
import CourseCard from "./CourseCard"

export default function CourseCatalog() {
  const [courses, setCourses] = useState<Course[]>([])
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading")
  const [search, setSearch] = useState("")
  const [category, setCategory] = useState("All")

  useEffect(() => {
    let cancelled = false
    fetchCourses()
      .then((data) => {
        if (!cancelled) {
          setCourses(data)
          setStatus("ready")
        }
      })
      .catch(() => {
        if (!cancelled) setStatus("error")
      })
    return () => {
      cancelled = true
    }
  }, [])

  const categories = useMemo(() => {
    const set = new Set<string>()
    for (const c of courses) {
      const cat = (c.course_category || "").trim()
      if (cat) set.add(cat)
    }
    return ["All", ...Array.from(set).sort()]
  }, [courses])

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase()
    return courses.filter((c) => {
      if (category !== "All" && (c.course_category || "").trim() !== category) {
        return false
      }
      if (!needle) return true
      const haystack = [c.course_number, c.course_title, c.faculty_1, c.course_category, c.daytimes]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
      return haystack.includes(needle)
    })
  }, [courses, search, category])

  return (
    <div className="catalog">
      <div className="catalog-toolbar">
        <div className="catalog-search bevel-in">
          <span aria-hidden>🔍</span>
          <input
            type="text"
            placeholder="Search by number, title, or faculty..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button className="catalog-clear" onClick={() => setSearch("")} aria-label="Clear search">
              ×
            </button>
          )}
        </div>
      </div>

      <div className="catalog-chips">
        {categories.map((cat) => (
          <button
            key={cat}
            className={`chip-btn ${category === cat ? "bevel-in chip-active" : "bevel-raised"}`}
            onClick={() => setCategory(cat)}
          >
            {cat}
          </button>
        ))}
      </div>

      <div className="catalog-list bevel-in">
        {status === "loading" && (
          <div className="catalog-empty">
            <span className="retro-spinner" aria-hidden />
            Loading course catalog…
          </div>
        )}
        {status === "error" && (
          <div className="catalog-empty catalog-error">
            ⚠ Could not reach the course desk. Is the backend running on
            <code> :8000</code>?
          </div>
        )}
        {status === "ready" && filtered.length === 0 && (
          <div className="catalog-empty">No courses match that search. Try another term.</div>
        )}
        {status === "ready" &&
          filtered.map((course) => (
            <CourseCard key={course.id ?? `${course.course_number}-${course.section}`} course={course} />
          ))}
      </div>

      <div className="catalog-statusline">
        {status === "ready" ? `${filtered.length} of ${courses.length} courses` : " "}
      </div>
    </div>
  )
}
