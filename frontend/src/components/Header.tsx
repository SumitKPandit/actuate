import { Link } from '@tanstack/react-router'

export default function Header() {
  return (
    <>
      <div className="announcement-bar px-4 py-2 text-center">
        Ops Brief for transport managers · OTA SLA 95% · Safety ack &lt; 30 min
      </div>
      <header className="site-header sticky top-0 z-50 px-4">
        <nav className="page-wrap flex flex-wrap items-center gap-x-6 gap-y-2 py-4">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-base font-bold text-[#1F1F1F] no-underline"
          >
            <span
              aria-hidden="true"
              className="inline-block h-2.5 w-2.5 rounded-full bg-[#43B02A]"
            />
            Actuate
          </Link>

          <div className="order-3 flex w-full flex-wrap items-center gap-x-5 gap-y-1 pb-1 sm:order-none sm:w-auto sm:flex-nowrap sm:pb-0">
            <Link
              to="/"
              className="nav-link"
              activeProps={{ className: 'nav-link is-active' }}
            >
              Brief
            </Link>
            <Link
              to="/mockup"
              className="nav-link"
              activeProps={{ className: 'nav-link is-active' }}
            >
              Dashboard
            </Link>
            <Link
              to="/about"
              className="nav-link"
              activeProps={{ className: 'nav-link is-active' }}
            >
              About
            </Link>
            <a href="/demo/tanstack-query" className="nav-link">
              Demo
            </a>
          </div>

          <div className="ml-auto flex items-center">
            <Link
              to="/mockup"
              className="demo-button !min-h-0 !px-5 !py-2.5 !text-sm no-underline"
            >
              View brief
            </Link>
          </div>
        </nav>
      </header>
    </>
  )
}
