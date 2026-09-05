import { createFileRoute } from '@tanstack/react-router'
import StackStatus from '../components/StackStatus'

export const Route = createFileRoute('/')({ component: App })

function App() {
  return (
    <main className="page-wrap px-4 pb-8 pt-14">
      <section className="island-shell rise-in grid gap-8 rounded-lg p-6 sm:p-10 lg:grid-cols-2 lg:items-center">
        <div>
          <p className="island-kicker mb-3">ACTUATE · OPS BRIEF</p>
          <h1 className="display-title mb-5 max-w-3xl text-4xl leading-[57.6px] font-bold text-[#1F1F1F] sm:text-5xl">
            Start simple, ship quickly.
          </h1>
          <p className="mb-8 max-w-2xl text-lg leading-7 text-[#333333]">
            This base starter intentionally keeps things light: two routes,
            clean structure, and the essentials you need to build from scratch.
          </p>
          <div className="flex flex-wrap gap-3">
            <a href="/mockup" className="demo-button no-underline">
              View ops brief
            </a>
            <a
              href="/about"
              className="demo-button demo-button-secondary no-underline"
            >
              About this starter
            </a>
          </div>
        </div>
        <div className="rounded-lg border border-[#E5E7EB] bg-[#F7F8FA] p-6">
          <p className="island-kicker mb-2">JUNE SNAPSHOT</p>
          <p className="m-0 text-3xl font-bold text-[#1F1F1F]">93.0% OTA</p>
          <p className="mt-1 mb-4 text-sm text-[#6B7280]">
            211k trips · SLA 95% · 656 Sev-1 alerts
          </p>
          <div className="flex flex-wrap gap-2">
            <span className="demo-pill demo-pill-danger">Breach SLA 95%</span>
            <span className="demo-pill demo-pill-info">Ack SLA 30 min</span>
            <span className="demo-pill">CSAT 4.85</span>
          </div>
        </div>
      </section>

      <section className="mt-8 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
        {[
          [
            'Type-Safe Routing',
            'Routes and links stay in sync across every page.',
          ],
          [
            'Server Functions',
            'Call server code from your UI without creating API boilerplate.',
          ],
          [
            'Streaming by Default',
            'Ship progressively rendered responses for faster experiences.',
          ],
          [
            'Tailwind Native',
            'Design quickly with utility-first styling and reusable tokens.',
          ],
        ].map(([title, desc], index) => (
          <article
            key={title}
            className="island-shell feature-card rise-in rounded-lg p-4"
            style={{ animationDelay: `${index * 90 + 80}ms` }}
          >
            <h2 className="mb-2 text-lg leading-[22px] font-semibold text-[#1F1F1F]">
              {title}
            </h2>
            <p className="m-0 text-sm leading-5 text-[#6B7280]">{desc}</p>
          </article>
        ))}
      </section>

      <StackStatus />

      <section className="island-shell mt-20 rounded-lg p-6">
        <p className="island-kicker mb-2">QUICK START</p>
        <ul className="m-0 list-disc space-y-2 pl-5 text-base text-[#333333]">
          <li>
            Edit <code>src/routes/index.tsx</code> to customize the home page.
          </li>
          <li>
            Update <code>src/components/Header.tsx</code> and{' '}
            <code>src/components/Footer.tsx</code> for brand links.
          </li>
          <li>
            Add routes in <code>src/routes</code> and tweak visual tokens in{' '}
            <code>src/styles.css</code>.
          </li>
        </ul>
      </section>
    </main>
  )
}
