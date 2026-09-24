export interface Course {
  "Course ID": string
  "Course Number": string
  "Course Title": string
  "Course Category": string
  "Course Type": string
  "Course Description": string
  "Faculty 1": string
  "Faculty 1 Email"?: string
  "Daytimes": string
  "Timings Day"?: string
  "Timings StartTime"?: string
  "Timings EndTime"?: string
  "Room"?: string
  "Units"?: string
  "Section"?: string
  faculty_bio?: string
  [key: string]: unknown
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant" | "error"
  text: string
  toolsUsed?: string[]
}
