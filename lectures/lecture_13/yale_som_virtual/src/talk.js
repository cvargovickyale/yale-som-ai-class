// Who you can walk up to and talk to. Each id here has a matching AI avatar
// (a PydanticAI agent) in backend/people.py.

// 3D roots you can talk to; Player raycasts against these from the crosshair
export const TALKABLES = new Set()

export const PEOPLE_INFO = {
  zaman: { name: 'Prof. Tauhid Zaman', course: 'MGT 409 · AI Foundations for Managers', room: 'Classroom 2200' },
}

// who you are chatting with right now (read every frame by Professor)
export const TALKING = { id: null }

// typing in the chat box must not walk the player or toggle the map
export const typing = (e) => e.target instanceof HTMLElement && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')
