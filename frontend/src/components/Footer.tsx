export default function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer className="site-footer mt-20 px-4 pb-10 pt-8">
      <div className="page-wrap flex flex-col items-center justify-between gap-3 text-center sm:flex-row sm:text-left">
        <p className="m-0 text-sm text-[#6B7280]">
          &copy; {year} Actuate · Ops Brief for transport managers
        </p>
        <p className="m-0 text-xs font-semibold tracking-[0.02em] text-[#6B7280]">
          OTA SLA 95% · Safety ack &lt; 30 min
        </p>
      </div>
    </footer>
  )
}
