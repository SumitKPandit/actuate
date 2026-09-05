import React, { useEffect, useRef, useState } from 'react'

import AlertsSection from './components/AlertsSection'
import ChatPanel from './components/ChatPanel'
import DataQualityBar from './components/DataQualityBar'
import Header from './components/Header'
import KpiPulse from './components/KpiPulse'
import { AuditModal, DataQualityModal, SafetyModal } from './components/Modals'
import RecommendedActions from './components/RecommendedActions'
import Toast from './components/Toast'
import TriggerBanner from './components/TriggerBanner'
import VendorTable from './components/VendorTable'
import { ackAction } from './lib/ops'
import { buildActions, buildAlerts, buildKpis, getFiredTriggers } from './lib/adapters'
import { useCycle } from './lib/useCycle'
import { useInsights } from './lib/useInsights'
import { useOpsData } from './lib/useOpsData'

function queryParam(name) {
  if (typeof window === 'undefined') return null
  return new URLSearchParams(window.location.search).get(name)
}

function writeQueryParam(name, value) {
  if (typeof window === 'undefined') return
  const url = new URL(window.location.href)
  if (value) url.searchParams.set(name, value)
  else url.searchParams.delete(name)
  window.history.replaceState({}, '', `${url.pathname}${url.search}${url.hash}`)
}

function errorMessage(error) {
  return error instanceof Error ? error.message : 'Unable to load operational data.'
}

function SurfaceSkeleton() {
  return (
    <div className="flex flex-col gap-4" aria-label="Loading operational brief">
      <div className="h-28 rounded-lg bg-surface border border-border-light animate-pulse"></div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {Array.from({ length: 6 }, (_, index) => <div key={index} className="h-32 rounded-lg bg-surface border border-border-light animate-pulse"></div>)}
      </div>
      <div className="h-64 rounded-lg bg-surface border border-border-light animate-pulse"></div>
    </div>
  )
}

export default function App() {
  const { cycle, cycles, setCycle } = useCycle(queryParam('cycle'))
  const ops = useOpsData(cycle)
  const insights = useInsights(cycle)

  const [selectedVendor, setSelectedVendor] = useState(() => queryParam('vendor'))
  const [ackOverrides, setAckOverrides] = useState({})
  const [ackPending, setAckPending] = useState(() => new Set())
  const [bannerDismissed, setBannerDismissed] = useState(false)
  const [alert1Highlighted, setAlert1Highlighted] = useState(false)
  const [auditModal, setAuditModal] = useState({ open: false, title: '', timestamp: '' })
  const [safetyModalOpen, setSafetyModalOpen] = useState(false)
  const [dataQualityOpen, setDataQualityOpen] = useState(false)
  const [toast, setToast] = useState(null)
  const alert1Ref = useRef(null)
  const toastTimer = useRef(null)

  useEffect(() => {
    writeQueryParam('cycle', cycle)
  }, [cycle])

  const showToast = (title, message) => {
    setToast({ title, message })
    if (toastTimer.current) clearTimeout(toastTimer.current)
    toastTimer.current = setTimeout(() => setToast(null), 3200)
  }

  const handleCycleChange = (nextCycle) => {
    setCycle(nextCycle)
    writeQueryParam('cycle', nextCycle)
  }

  const handleVendorSelect = (vendor) => {
    const nextVendor = selectedVendor === vendor ? null : vendor
    setSelectedVendor(nextVendor)
    writeQueryParam('vendor', nextVendor)
  }

  const reviewAlert = () => {
    setAlert1Highlighted(true)
    setTimeout(() => alert1Ref.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 50)
    setTimeout(() => setAlert1Highlighted(false), 1600)
  }

  const copyVendorMessage = (text) => {
    if (!text) return
    const writeText = typeof navigator !== 'undefined' ? navigator.clipboard?.writeText : null
    if (typeof writeText !== 'function') {
      showToast('Clipboard unavailable', 'The vendor message could not be copied in this browser.')
      return
    }
    Promise.resolve(writeText.call(navigator.clipboard, text)).then(
      () => showToast('Vendor message copied', text),
      () => showToast('Copy failed', 'Clipboard access was denied.')
    )
  }

  const fullActions = ops.data?.actions?.data || []
  const statusById = Object.fromEntries(fullActions.map((action) => [action.id, action.status]))
  const resolvedStatusById = { ...statusById, ...ackOverrides }

  const approveAction = async (id) => {
    if (resolvedStatusById[id] === 'acked' || ackPending.has(id)) return
    setAckOverrides((current) => ({ ...current, [id]: 'acked' }))
    setAckPending((current) => new Set(current).add(id))
    try {
      await ackAction(id, 'Transport Manager')
      showToast('Action acknowledged', 'Action logged to the dispatch mart for Transport Manager.')
    } catch (error) {
      setAckOverrides((current) => {
        const next = { ...current }
        delete next[id]
        return next
      })
      showToast('Action acknowledgement failed', errorMessage(error))
    } finally {
      setAckPending((current) => {
        const next = new Set(current)
        next.delete(id)
        return next
      })
    }
  }

  const briefingData = ops.data?.briefing?.data
  const overviewData = ops.data?.overview?.data
  const actionsData = ops.data?.actions?.data
  const insightsData = insights.data || []
  const briefReady = briefingData != null && overviewData != null && actionsData != null
  const kpis = buildKpis(overviewData, insightsData, briefingData?.safety_open_sev1)
  const alerts = buildAlerts(briefingData?.insights_top5)
  const actions = buildActions(briefingData?.actions_top3, actionsData, statusById, ackOverrides)
  const pendingCount = actions.filter((action) => action.status !== 'acked').length

  return (
    <div className="bg-surface-panel font-sans text-neutral-body antialiased selection:bg-primary/20 min-h-screen">
      <Toast toast={toast} />
      <AuditModal
        open={auditModal.open}
        onClose={() => setAuditModal((current) => ({ ...current, open: false }))}
        actionTitle={auditModal.title}
        timestamp={auditModal.timestamp}
      />
      <SafetyModal open={safetyModalOpen} onClose={() => setSafetyModalOpen(false)} totalOpen={briefingData?.safety_open_sev1 ?? 0} />
      <DataQualityModal open={dataQualityOpen} onClose={() => setDataQualityOpen(false)} />
      <Header cycle={cycle} cycles={cycles} onCycleChange={handleCycleChange} />

      <main className="w-full pt-16 bg-surface-panel">
        <div className="flex flex-col w-full">
          <div className="px-6 py-6 flex flex-col gap-6 max-w-[1600px] mx-auto w-full">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-neutral-muted uppercase tracking-wider">Operational Pipeline</span>
                <span className="material-symbols-outlined text-neutral-muted text-[14px]">chevron_right</span>
                <div className="flex items-center gap-1.5">
                  <span className="px-2 py-0.5 rounded-full text-[11px] bg-surface border border-border-light text-secondary font-semibold">SENSE</span>
                  <span className="text-neutral-muted text-xs">→</span>
                  <span className="px-2 py-0.5 rounded-full text-[11px] bg-error-bg text-error font-semibold animate-pulse border border-error/20">ALERT</span>
                  <span className="text-neutral-muted text-xs">→</span>
                  <span className="px-2 py-0.5 rounded-full text-[11px] bg-surface border border-border-light text-neutral-body font-medium">REASON</span>
                  <span className="text-neutral-muted text-xs">→</span>
                  <span className="px-2 py-0.5 rounded-full text-[11px] bg-surface border border-border-light text-neutral-body font-medium">ASK</span>
                  <span className="text-neutral-muted text-xs">→</span>
                  <span className="px-2 py-0.5 rounded-full text-[11px] bg-success-bg text-primary border border-primary/20 font-bold">ACT</span>
                </div>
              </div>
              <div className="hidden md:flex items-center gap-3 text-neutral-muted text-xs">
                <span>Sensitivity: High (0.85σ)</span>
                <span className="h-3 w-px bg-border-light"></span>
                <span className="text-primary font-semibold flex items-center gap-1">● 100% telemetry live</span>
              </div>
            </div>

            {ops.loading && <SurfaceSkeleton />}
            {!ops.loading && ops.error && <div role="alert" className="bg-error-bg border border-error/30 text-error rounded-lg px-4 py-3 text-sm font-semibold">Unable to load the operational brief: {errorMessage(ops.error)}</div>}
            {!ops.loading && !ops.error && ops.warning && <div role="status" className="bg-warning-bg border border-warning/30 text-warning rounded-lg px-4 py-3 text-sm font-semibold">{ops.warning}</div>}

            {!ops.loading && !ops.error && briefReady && (
              <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
                <div className="xl:col-span-8 flex flex-col gap-6">
                  <TriggerBanner
                    triggers={getFiredTriggers(briefingData)}
                    cycle={cycle}
                    dismissed={bannerDismissed}
                    onDismiss={() => setBannerDismissed(true)}
                    onRestore={() => setBannerDismissed(false)}
                    onReview={reviewAlert}
                    cardRef={null}
                  />
                  <KpiPulse kpis={kpis} onOpenSafety={() => setSafetyModalOpen(true)} />
                  {insights.error && <div className="text-xs text-neutral-muted">Prior-cycle deltas unavailable: {errorMessage(insights.error)}</div>}
                  <AlertsSection
                    alerts={alerts}
                    statusById={resolvedStatusById}
                    ackPending={ackPending}
                    onApprove={approveAction}
                    alert1Ref={alert1Ref}
                    alert1Highlighted={alert1Highlighted}
                  />
                  <RecommendedActions
                    actions={actions}
                    pendingCount={pendingCount}
                    ackPending={ackPending}
                    onApprove={approveAction}
                    onCopyVendor={copyVendorMessage}
                    onViewAudit={(title) => setAuditModal({ open: true, title, timestamp: new Date().toISOString() })}
                  />
                </div>
                <ChatPanel />
              </div>
            )}

            <VendorTable cycle={cycle} selectedVendor={selectedVendor} onSelectVendor={handleVendorSelect} />
            <DataQualityBar onOpen={() => setDataQualityOpen(true)} />
          </div>
        </div>
      </main>
    </div>
  )
}
