export interface Course {
  id: number | null
  course_id: string
  course_number: string
  course_title: string
  course_category: string
  course_type: string
  course_session: string
  course_description: string
  faculty_1: string
  faculty_1_email: string
  faculty_bio: string
  daytimes: string
  timings_day: string
  timings_start: string
  timings_end: string
  room: string
  section: string
  units: string
  term_code: string
  syllabus: string
  old_syllabus: string
  [key: string]: unknown
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant" | "error"
  text: string
  toolsUsed?: string[]
}
