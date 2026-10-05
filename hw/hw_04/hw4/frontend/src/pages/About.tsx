const SECTIONS = [
  {
    title: 'Our story',
    body: "Campus Customs started in 1975 as a small Yale memorabilia shop across the street from campus. That shop at 57 Broadway is still open, and it's still family-run. Now there's a full print and embroidery shop right next door.",
  },
  {
    title: 'What we do',
    body: "Officially licensed Yale apparel for students, alumni, and families. Since we print and stitch in-house, we also make custom gear for teams, clubs, and events, and turn it around fast.",
  },
  {
    title: 'How we work',
    body: "Friendly service and customers who keep coming back for years. Online, the same rule applies: our assistant checks real prices and real stock before it answers. No guessing.",
  },
  {
    title: 'Visit us',
    body: '57 Broadway, New Haven, CT, steps from Yale. Shop online any time.',
  },
]

export default function About() {
  return (
    <>
      <section className="hero">
        <p className="eyebrow">About Us</p>
        <h1>A New Haven shop with a lot of Bulldog pride.</h1>
      </section>
      <section className="panels">
        {SECTIONS.map((s) => (
          <div key={s.title} className="panel">
            <h2>{s.title}</h2>
            <p>{s.body}</p>
          </div>
        ))}
      </section>
    </>
  )
}
