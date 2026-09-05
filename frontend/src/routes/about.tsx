import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/about')({
  component: About,
})

function About() {
  return (
    <main className="page-wrap px-4 py-12">
      <section className="island-shell rounded-lg p-6 sm:p-8">
        <p className="island-kicker mb-2">ABOUT</p>
        <h1 className="display-title mb-3 text-4xl font-bold text-[#1F1F1F] sm:text-5xl">
          A small starter with room to grow.
        </h1>
        <p className="m-0 max-w-3xl text-base leading-6 text-[#333333]">
          TanStack Start gives you type-safe routing, server functions, and
          modern SSR defaults. Use this as a clean foundation, then layer in
          your own routes, styling, and add-ons.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <a href="/" className="demo-button no-underline">
            Back to brief
          </a>
          <a
            href="/mockup"
            className="demo-button demo-button-secondary no-underline"
          >
            View dashboard mockup
          </a>
        </div>
      </section>
    </main>
  )
}
